import json
import os
import tempfile
import unittest
from unittest import mock

import treelib

import database_classes
import id_policy
from database_GUI import SampleTreeGUI, deserialize_tree, serialize_tree


class CollisionProbabilityTests(unittest.TestCase):
    def test_two_ids_have_one_over_namespace_collision_probability(self):
        self.assertAlmostEqual(
            id_policy.collision_probability(2, 6, processing_step=False),
            1 / (16 ** 6),
            places=14,
        )
        self.assertAlmostEqual(
            id_policy.collision_probability(2, 6, processing_step=True),
            1 / (16 ** 5),
            places=14,
        )

    def test_recommendation_uses_displayed_sample_probability(self):
        self.assertEqual(id_policy.recommend_total_length(1000, 0.0001), 9)

    def test_recommendation_reports_when_range_is_insufficient(self):
        self.assertIsNone(id_policy.recommend_total_length(16 ** 31, 0.0001))

    def test_probability_boundaries(self):
        self.assertEqual(id_policy.collision_probability(0, 6), 0.0)
        self.assertEqual(id_policy.collision_probability(1, 6), 0.0)
        self.assertEqual(id_policy.collision_probability((16 ** 5) + 1, 6, True), 1.0)


class IdentifierGenerationTests(unittest.TestCase):
    def test_generated_ids_use_total_display_length(self):
        sample_id = id_policy.generate_random_id(8, processing_step=False)
        process_id = id_policy.generate_random_id(8, processing_step=True)
        self.assertEqual(len(sample_id), 8)
        self.assertEqual(len(process_id), 8)
        self.assertTrue(process_id.startswith("P"))

    def test_duplicate_candidate_is_retried_case_insensitively(self):
        candidates = iter(["abcdef", "ABCDEF", "123456"])

        def candidate_factory(_length, _processing):
            return next(candidates)

        generated = id_policy.generate_unique_id(
            {"ABCDEF"},
            6,
            candidate_factory=candidate_factory,
        )
        self.assertEqual(generated, "123456")

    def test_gui_allocator_uses_only_supplied_tree(self):
        tree = treelib.Tree()
        tree.create_node("SYSTEM", "SYSTEM", data={"Sample_System": "Test"})
        tree.create_node("Sample", "abcdef", parent="SYSTEM", data={})
        candidates = iter(["ABCDEF", "123456"])

        with mock.patch("database_GUI.get_id_total_length", return_value=6), \
                mock.patch("id_policy.generate_random_id", side_effect=lambda *_args: next(candidates)), \
                mock.patch("os.walk", side_effect=AssertionError("filesystem scan is not allowed")):
            generated = SampleTreeGUI._generate_node_id(tree, database_classes.Sample)

        self.assertEqual(generated, "123456")

    def test_internal_generated_id_is_not_a_property(self):
        sample = database_classes.Sample(_generated_id="123456")
        process = database_classes.Processing_Step(_generated_id="P12345")
        self.assertEqual(sample.id, "123456")
        self.assertEqual(process.id, "P12345")
        self.assertNotIn("_generated_id", sample.properties)
        self.assertNotIn("_generated_id", process.properties)

    def test_dynamic_classes_use_their_declared_id_namespace(self):
        wafer = database_classes.Wafer(_generated_id="123456", material="Cu")
        annealing = database_classes.Annealing(
            _generated_id="P12345",
            temperature_C="500",
            duration="1 h",
        )
        self.assertEqual(wafer.id, "123456")
        self.assertEqual(annealing.id, "P12345")

    def test_mixed_length_ids_round_trip_unchanged(self):
        tree = treelib.Tree()
        tree.create_node("SYSTEM", "SYSTEM", data={"Sample_System": "Mixed", "sort_mode": "none"})
        short = database_classes.Wafer(_generated_id="123456", material="Cu")
        long = database_classes.Chip(_generated_id="12345678")
        tree.create_node("Wafer", short.id, parent="SYSTEM", data={"obj": short})
        tree.create_node("Chip", long.id, parent=short.id, data={"obj": long})

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "mixed.json")
            serialize_tree(tree, path, sort_mode="none")
            loaded = deserialize_tree(path)

        self.assertIsNotNone(loaded.get_node("123456"))
        self.assertEqual(loaded.parent("12345678").identifier, "123456")


class StructureSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.structure_path = os.path.join(self.temp_dir.name, "database_structure.json")
        with open(self.structure_path, "w", encoding="utf-8") as stream:
            json.dump({
                "Sample": {"base": None, "required": [], "custom": [], "permitted_children": []},
                "Processing_Step": {"base": "Sample", "required": [], "custom": [], "permitted_children": []},
            }, stream)
        self.path_patch = mock.patch.object(
            database_classes,
            "DATABASE_STRUCTURE_FILE",
            self.structure_path,
        )
        self.path_patch.start()

    def tearDown(self):
        self.path_patch.stop()
        self.temp_dir.cleanup()

    def test_missing_setting_defaults_to_six(self):
        self.assertEqual(database_classes.get_id_total_length(), 6)

    def test_only_length_is_persisted(self):
        database_classes.set_id_total_length(8)
        with open(self.structure_path, "r", encoding="utf-8") as stream:
            schema = json.load(stream)
        self.assertEqual(schema["__settings__"], {"id_total_length": 8})
        self.assertNotIn("projected_node_count", json.dumps(schema))
        self.assertNotIn("collision_target", json.dumps(schema))

    def test_length_cannot_decrease(self):
        database_classes.set_id_total_length(8)
        with self.assertRaises(ValueError):
            database_classes.set_id_total_length(7)
        self.assertEqual(database_classes.get_id_total_length(), 8)

    def test_settings_are_not_schema_classes(self):
        schema = database_classes.load_database_structure()
        schema["__settings__"] = {"id_total_length": 8}
        self.assertNotIn("__settings__", database_classes.schema_class_names(schema))

    def test_locked_structure_is_not_overwritten(self):
        structure_lock = database_classes.DatabaseFileLock(self.structure_path)
        self.assertTrue(structure_lock.acquire())
        try:
            with self.assertRaises(RuntimeError):
                database_classes.set_id_total_length(8)
        finally:
            structure_lock.release()
        self.assertEqual(database_classes.get_id_total_length(), 6)


if __name__ == "__main__":
    unittest.main()
