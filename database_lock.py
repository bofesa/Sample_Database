"""Per-database process locking and durable file helpers."""

from __future__ import annotations

import getpass
import hashlib
import json
import os
import socket
import tempfile
import time
import uuid
from datetime import datetime, timezone

try:
    import msvcrt
except ImportError:  # pragma: no cover - the desktop application is Windows-only
    msvcrt = None


LOCK_BYTE_OFFSET = 0
METADATA_OFFSET = 1


def file_fingerprint(path):
    """Return a content fingerprint for conflict detection."""
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_write_json(path, data, indent=2):
    """Write JSON durably, then atomically replace the destination."""
    target = os.path.abspath(path)
    directory = os.path.dirname(target) or os.curdir
    base = os.path.basename(target)
    fd, temp_path = tempfile.mkstemp(prefix=f".{base}.", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, indent=indent)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, target)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise
    return target


class DatabaseFileLock:
    """Hold an OS byte-range lock beside a database for this object's lifetime."""

    def __init__(self, database_path):
        self.database_path = os.path.abspath(database_path)
        directory = os.path.dirname(self.database_path)
        basename = os.path.basename(self.database_path)
        self.lock_path = os.path.join(directory, f".{basename}.lock")
        self.owner_metadata = {}
        self.reason = ""
        self._stream = None
        self._owned = False
        self._token = uuid.uuid4().hex

    @property
    def acquired(self):
        return self._owned

    def acquire(self):
        """Try once to acquire the lock; return True only for editable ownership."""
        if self._owned:
            return True
        if msvcrt is None:
            self.reason = "Operating-system database locking is unavailable on this platform."
            return False

        try:
            fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o666)
            stream = os.fdopen(fd, "r+b", buffering=0)
        except OSError as exc:
            self.reason = f"The lock file could not be opened: {exc}"
            return False

        try:
            stream.seek(0, os.SEEK_END)
            if stream.tell() < METADATA_OFFSET:
                stream.seek(LOCK_BYTE_OFFSET)
                stream.write(b"\0")
                stream.flush()

            stream.seek(LOCK_BYTE_OFFSET)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                self.owner_metadata = self._read_metadata(stream)
                self.reason = "The database is already open for editing in another application instance."
                stream.close()
                return False

            self._stream = stream
            self._owned = True
            self.owner_metadata = self._make_metadata()
            try:
                self._write_metadata()
            except Exception as exc:
                self.reason = f"The lock was acquired, but its owner information could not be written: {exc}"
                self.release()
                self.owner_metadata = {}
                return False
            return True
        except Exception as exc:
            self.reason = f"The database lock could not be established: {exc}"
            try:
                stream.close()
            except Exception:
                pass
            return False

    def is_owned(self):
        if not self._owned or self._stream is None or self._stream.closed:
            return False
        try:
            metadata = self._read_metadata(self._stream, retries=1)
            return metadata.get("token") == self._token
        except Exception:
            return False

    def release(self):
        stream = self._stream
        was_owned = self._owned
        self._owned = False
        self._stream = None
        if stream is None:
            return
        try:
            if was_owned and msvcrt is not None:
                stream.seek(LOCK_BYTE_OFFSET)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        finally:
            try:
                stream.close()
            except OSError:
                pass

    def _make_metadata(self):
        try:
            username = getpass.getuser()
        except Exception:
            username = "unknown"
        return {
            "version": 1,
            "hostname": socket.gethostname(),
            "username": username,
            "pid": os.getpid(),
            "opened_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "database_path": self.database_path,
            "token": self._token,
        }

    def _write_metadata(self):
        payload = json.dumps(self.owner_metadata, ensure_ascii=True).encode("utf-8")
        self._stream.seek(METADATA_OFFSET)
        self._stream.write(payload)
        self._stream.truncate()
        self._stream.flush()
        os.fsync(self._stream.fileno())

    @staticmethod
    def _read_metadata(stream, retries=5):
        for attempt in range(retries):
            try:
                stream.seek(METADATA_OFFSET)
                payload = stream.read()
                if payload:
                    value = json.loads(payload.decode("utf-8"))
                    if isinstance(value, dict):
                        return value
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                pass
            if attempt + 1 < retries:
                time.sleep(0.05)
        return {}

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

    def __del__(self):
        try:
            self.release()
        except Exception:
            pass
