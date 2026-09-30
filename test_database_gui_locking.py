import os
import tempfile
import unittest
from unittest import mock

from database_GUI import SampleTreeGUI
from database_lock import atomic_write_json


def write_empty_database(path, sample_system="Test"):
    atomic_write_json(
        path,
        {
            "root": {"id": "SYSTEM", "sample_system": sample_system, "sort_mode": "none"},
            "nodes": [],
        },
    )


class DatabaseGuiLockingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "database.json")
        write_empty_database(self.database_path)
        self.loaded_infos = []

    def tearDown(self):
        for info in self.loaded_infos:
            database_lock = info.get("database_lock")
            if database_lock:
                database_lock.release()
        self.temp_dir.cleanup()

    def run_worker(self):
        gui = SampleTreeGUI.__new__(SampleTreeGUI)
        gui._thread_result = None
        gui._thread_error = None
        gui._thread_load_worker([self.database_path])
        self.assertIsNone(gui._thread_error)
        self.assertEqual(gui._thread_result["failed"], [])
        info = next(iter(gui._thread_result["loaded"].values()))
        self.loaded_infos.append(info)
        return info

    def test_loader_assigns_editable_then_read_only_state(self):
        editable = self.run_worker()
        read_only = self.run_worker()

        self.assertFalse(editable["read_only"])
        self.assertTrue(editable["database_lock"].is_owned())
        self.assertTrue(read_only["read_only"])
        self.assertIsNone(read_only["database_lock"])
        self.assertEqual(
            read_only["lock_owner"].get("token"),
            editable["lock_owner"].get("token"),
        )

    def test_external_change_aborts_save_and_retains_unsaved_state(self):
        info = self.run_worker()
        gui = SampleTreeGUI.__new__(SampleTreeGUI)
        gui.root = None
        gui.multi_trees = {"tree": info}
        gui.sort_state = {"tree": "none"}
        gui.unsaved_changes = {"tree"}
        gui.populate_treeview = lambda: None

        write_empty_database(self.database_path, sample_system="Changed Elsewhere")

        with mock.patch("database_GUI.messagebox.showerror"):
            saved = gui._save_system("tree")

        self.assertFalse(saved)
        self.assertTrue(info["read_only"])
        self.assertIsNone(info["database_lock"])
        self.assertIn("tree", gui.unsaved_changes)


if __name__ == "__main__":
    unittest.main()
