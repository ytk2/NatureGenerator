"""Tests for the Fusion-independent nature preset framework."""

from dataclasses import FrozenInstanceError
from pathlib import Path
import unittest

from generators.gyroid import GyroidField
from presets import NaturePreset, ParameterMetadata, PresetFactory, PresetRegistry


def sample_preset(preset_id="sample", category="test"):
    """Return a minimal unavailable preset for registry tests."""

    return NaturePreset(
        preset_id=preset_id,
        display_name=preset_id.title(),
        category=category,
        description="Test preset.",
        generator_id="future",
        default_parameters={"scale": 1.0},
        parameter_metadata={
            "scale": ParameterMetadata(
                display_name="Scale",
                value_type="float",
                default_value=1.0,
                minimum=0.1,
                maximum=10.0,
                unit="mm",
                description="Test scale.",
            )
        },
        available=False,
        unavailable_reason="Test generator is unavailable.",
    )


class NaturePresetTests(unittest.TestCase):
    def test_preset_and_parameter_metadata_are_immutable(self):
        preset = sample_preset()
        with self.assertRaises(FrozenInstanceError):
            preset.display_name = "Changed"
        with self.assertRaises(FrozenInstanceError):
            preset.parameter_metadata["scale"].unit = "cm"
        with self.assertRaises(TypeError):
            preset.default_parameters["scale"] = 2.0
        with self.assertRaises(TypeError):
            preset.parameter_metadata["scale"] = preset.parameter_metadata["scale"]

    def test_defensively_copies_parameter_dictionaries(self):
        defaults = {"scale": 1.0}
        scale_metadata = ParameterMetadata("Scale", "float", 1.0)
        metadata = {"scale": scale_metadata}
        preset = NaturePreset(
            preset_id="defensive",
            display_name="Defensive",
            category="test",
            description="Defensive copy test.",
            generator_id="future",
            default_parameters=defaults,
            parameter_metadata=metadata,
            available=False,
            unavailable_reason="Future generator.",
        )

        defaults["scale"] = 9.0
        defaults["new"] = 2.0
        metadata.clear()
        self.assertEqual(preset.default_parameters, {"scale": 1.0})
        self.assertEqual(preset.parameter_metadata, {"scale": scale_metadata})

    def test_unavailable_presets_are_explicit(self):
        for preset_id in ("coral", "bone", "bark", "rock"):
            preset = PresetFactory.get(preset_id)
            self.assertFalse(preset.available)
            self.assertTrue(preset.unavailable_reason)
            self.assertNotEqual(preset.generator_id, "gyroid")

    def test_stable_ids_reject_display_text(self):
        with self.assertRaises(ValueError):
            NaturePreset(
                preset_id="Not Stable",
                display_name="Invalid",
                category="test",
                description="Invalid stable ID.",
                generator_id="future",
                default_parameters={},
                available=False,
                unavailable_reason="Invalid test preset.",
            )

    def test_sponge_maps_to_existing_gyroid_field(self):
        sponge = PresetFactory.get("sponge")
        self.assertTrue(sponge.available)
        self.assertEqual(sponge.generator_id, "gyroid")

        field = GyroidField(**dict(sponge.default_parameters))
        self.assertEqual(field.cell_size, 10.0)
        self.assertEqual(field.thickness, 0.2)
        self.assertEqual(field.sample(0.0, 0.0, 0.0), -0.2)


class PresetRegistryTests(unittest.TestCase):
    def test_factory_lookup_by_id(self):
        self.assertEqual(PresetFactory.get("coral").display_name, "Coral")
        with self.assertRaises(KeyError):
            PresetFactory.get("missing")

    def test_category_filtering(self):
        self.assertEqual(
            tuple(preset.preset_id for preset in PresetFactory.list_by_category("AQUATIC")),
            ("coral", "sponge"),
        )
        self.assertEqual(PresetFactory.list_by_category("missing"), ())

    def test_ordering_is_deterministic_independent_of_registration_order(self):
        first = PresetRegistry()
        second = PresetRegistry()
        presets = (
            sample_preset("zebra", "second"),
            sample_preset("alpha", "first"),
            sample_preset("beta", "first"),
        )
        for preset in presets:
            first.register(preset)
        for preset in reversed(presets):
            second.register(preset)

        first_ids = tuple(preset.preset_id for preset in first.list_all())
        second_ids = tuple(preset.preset_id for preset in second.list_all())
        self.assertEqual(first_ids, ("alpha", "beta", "zebra"))
        self.assertEqual(first_ids, second_ids)

    def test_duplicate_ids_are_rejected(self):
        registry = PresetRegistry()
        registry.register(sample_preset())
        with self.assertRaises(ValueError):
            registry.register(sample_preset())

    def test_factory_exposes_all_initial_presets(self):
        self.assertEqual(
            {preset.preset_id for preset in PresetFactory.list_all()},
            {"coral", "bone", "bark", "sponge", "rock"},
        )


class PresetDependencyTests(unittest.TestCase):
    def test_presets_have_no_fusion_numpy_or_dynamic_discovery_imports(self):
        preset_root = Path(__file__).parents[1] / "presets"
        forbidden = (
            "import adsk",
            "from adsk",
            "import numpy",
            "from numpy",
            "import core",
            "from core",
            "import generators",
            "from generators",
        )
        discovery_markers = ("importlib", "pkgutil", "glob(", "os.listdir")
        for module in preset_root.glob("*.py"):
            source = module.read_text(encoding="utf-8")
            for marker in forbidden + discovery_markers:
                self.assertNotIn(marker, source, "{} contains {}".format(module, marker))


if __name__ == "__main__":
    unittest.main()
