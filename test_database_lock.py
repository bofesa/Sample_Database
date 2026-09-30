import json
import msvcrt
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from database_lock import DatabaseFileLock, atomic_write_json, file_fingerprint


class DatabaseFileLockTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "shared.json")
        self.locks = []
        atomic_write_json(self.database_path, {"value": 1})

    def tearDown(self):
        for database_lock in reversed(self.locks):
            database_lock.release()
        self.temp_dir.cleanup()

    def make_lock(self):
        database_lock = DatabaseFileLock(self.database_path)
        self.locks.append(database_lock)
        return database_lock

    def test_second_owner_is_read_only_and_receives_metadata(self):
        first = self.make_lock()
        second = self.make_lock()

        self.assertTrue(first.acquire())
        self.assertFalse(second.acquire())
        self.assertEqual(second.owner_metadata.get("token"), first.owner_metadata.get("token"))
        self.assertEqual(second.owner_metadata.get("pid"), os.getpid())

    def test_persistent_sidecar_does_not_look_locked_after_release(self):
        first = self.make_lock()
        self.assertTrue(first.acquire())
        lock_path = first.lock_path
        first.release()

        self.assertTrue(os.path.exists(lock_path))
        second = self.make_lock()
        self.assertTrue(second.acquire())

    def test_process_termination_releases_lock(self):
        script = (
            "import sys,time\n"
            "from database_lock import DatabaseFileLock\n"
            "lock=DatabaseFileLock(sys.argv[1])\n"
            "print('locked' if lock.acquire() else 'failed', flush=True)\n"
            "time.sleep(30)\n"
        )
        child = subprocess.Popen(
            [sys.executable, "-c", script, self.database_path],
            cwd=os.path.dirname(__file__),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            self.assertEqual(child.stdout.readline().strip(), "locked")
            contender = self.make_lock()
            self.assertFalse(contender.acquire())
            contender.release()

            child.kill()
            child.wait(timeout=5)

            replacement = self.make_lock()
            self.assertTrue(replacement.acquire())
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)
            if child.stdout:
                child.stdout.close()
            if child.stderr:
                child.stderr.close()

    def test_malformed_owner_metadata_still_opens_read_only(self):
        lock_path = os.path.join(self.temp_dir.name, ".shared.json.lock")
        with open(lock_path, "w+b", buffering=0) as holder:
            holder.write(b"\0{invalid json")
            holder.seek(0)
            msvcrt.locking(holder.fileno(), msvcrt.LK_NBLCK, 1)
            try:
                contender = self.make_lock()
                self.assertFalse(contender.acquire())
                self.assertEqual(contender.owner_metadata, {})
            finally:
                holder.seek(0)
                msvcrt.locking(holder.fileno(), msvcrt.LK_UNLCK, 1)

    def test_lock_file_permission_error_falls_back_to_read_only(self):
        contender = self.make_lock()
        with mock.patch("database_lock.os.open", side_effect=PermissionError("denied")):
            self.assertFalse(contender.acquire())
        self.assertIn("could not be opened", contender.reason)


class DurableFileTests(unittest.TestCase):
    def test_fingerprint_changes_with_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "database.json")
            atomic_write_json(path, {"value": 1})
            first = file_fingerprint(path)
            atomic_write_json(path, {"value": 2})
            self.assertNotEqual(first, file_fingerprint(path))

    def test_serialization_failure_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "database.json")
            atomic_write_json(path, {"original": True})

            with mock.patch("database_lock.json.dump", side_effect=RuntimeError("simulated failure")):
                with self.assertRaises(RuntimeError):
                    atomic_write_json(path, {"replacement": True})

            with open(path, "r", encoding="utf-8") as stream:
                self.assertEqual(json.load(stream), {"original": True})
            leftovers = [name for name in os.listdir(directory) if name.endswith(".tmp")]
            self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
