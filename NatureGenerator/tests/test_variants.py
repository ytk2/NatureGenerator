"""Tests for Fusion-independent curated generator variants."""

from types import MappingProxyType
import unittest

from generators import GenerationRequest, GeneratorFactory
from presets import PresetFactory
from variants import VariantDefinition, VariantFactory, VariantRegistry


class VariantDefinitionTests(unittest.TestCase):
    def test_definition_is_immutable_and_copies_values(self):
        values = {"roughness": 0.2}
        variant = VariantDefinition(
            "rock_test", "rock", "Test", "Test rock values.", values
        )
        values["roughness"] = 0.6
        self.assertIsInstance(variant.parameter_values, MappingProxyType)
        self.assertEqual(variant.parameter_values["roughness"], 0.2)
        with self.assertRaises(TypeError):
            variant.parameter_values["roughness"] = 0.4

    def test_stable_identifiers_are_required(self):
        with self.assertRaises(ValueError):
            VariantDefinition("Rock Test", "rock", "Test", "Description", {"seed": 1})


class VariantRegistryTests(unittest.TestCase):
    def test_catalog_is_complete_and_deterministically_ordered(self):
        expected = {
            "sponge": ("Fine", "Balanced", "Bold"),
            "coral": ("Fine Branching", "Balanced", "Massive"),
            "rock": ("Smooth", "Weathered", "Rugged"),
            "bark": ("Subtle", "Grooved", "Twisted"),
            "root": ("Sparse", "Balanced", "Dense"),
        }
        self.assertEqual(len(VariantFactory.list_all()), 15)
        for preset_id, names in expected.items():
            self.assertEqual(
                tuple(item.display_name for item in VariantFactory.list_for_preset(preset_id)),
                names,
            )

    def test_duplicate_id_and_display_name_are_rejected(self):
        registry = VariantRegistry()
        first = VariantDefinition(
            "rock_one", "rock", "One", "First test.", {"seed": 1}
        )
        registry.register(first)
        with self.assertRaises(ValueError):
            registry.register(first)
        with self.assertRaises(ValueError):
            registry.register(VariantDefinition(
                "rock_two", "rock", "One", "Duplicate label.", {"seed": 2}
            ))

    def test_unknown_preset_and_parameter_are_rejected(self):
        registry = VariantRegistry()
        with self.assertRaises(ValueError):
            registry.register(VariantDefinition(
                "unknown_test", "unknown", "Test", "Unknown preset.", {"seed": 1}
            ))
        with self.assertRaises(ValueError):
            registry.register(VariantDefinition(
                "rock_wrong", "rock", "Wrong", "Cross-preset parameter.",
                {"cell_size": 10.0},
            ))

    def test_type_bounds_and_cross_parameter_rules_are_rejected(self):
        cases = (
            VariantDefinition("rock_bad_type", "rock", "Bad Type", "Bad type.",
                              {"seed": 1.5}),
            VariantDefinition("rock_bad_bound", "rock", "Bad Bound", "Bad bound.",
                              {"roughness": 1.0}),
            VariantDefinition("bark_bad_ratio", "bark", "Bad Ratio", "Bad ratio.",
                              {"diameter": 30.0, "bark_depth": 15.0}),
            VariantDefinition("root_bad_ratio", "root", "Bad Ratio", "Bad ratio.",
                              {"length": 40.0, "root_radius": 20.0}),
        )
        for variant in cases:
            with self.subTest(variant=variant.variant_id):
                with self.assertRaises((TypeError, ValueError)):
                    VariantRegistry().register(variant)

    def test_every_variant_covers_exact_preset_parameters(self):
        for variant in VariantFactory.list_all():
            with self.subTest(variant=variant.variant_id):
                preset = PresetFactory.get(variant.preset_id)
                self.assertEqual(
                    set(variant.parameter_values), set(preset.parameter_metadata)
                )


class VariantGenerationTests(unittest.TestCase):
    def test_every_variant_generates_deterministically(self):
        for variant in VariantFactory.list_all():
            values = dict(variant.parameter_values)
            resolution = values.pop("resolution")
            request = GenerationRequest(variant.preset_id, values, resolution)
            with self.subTest(variant=variant.variant_id):
                first = GeneratorFactory.generate_request(request)
                second = GeneratorFactory.generate_request(request)
                self.assertEqual(first.mesh, second.mesh)
                self.assertGreater(first.statistics.vertex_count, 0)
                self.assertGreater(first.statistics.face_count, 0)


if __name__ == "__main__":
    unittest.main()
