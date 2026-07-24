"""Tests for the Fusion-independent nature preset framework."""

from dataclasses import FrozenInstanceError
from pathlib import Path
import unittest

from generators.gyroid import GyroidField
from generators.bark_families import BarkFamilyRegistry
from generators.bone_families import BoneFamilyRegistry
from generators.coral_families import CoralFamilyRegistry
from generators.rock_families import RockFamilyRegistry
from generators.root_families import RootFamilyRegistry
from generators.sponge_families import SpongeFamilyRegistry
from preset_catalog import PresetCatalog
from presets import (
    NaturePreset,
    ParameterMetadata,
    PresetDefinition,
    PresetFactory,
    PresetRegistry,
)


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

    def test_bone_is_available_with_stable_metadata_and_defaults(self):
        bone = PresetFactory.get("bone")
        self.assertTrue(bone.available)
        self.assertEqual(bone.generator_id, "bone")
        self.assertEqual(
            tuple(bone.parameter_metadata),
            (
                "length", "shaft_radius", "end_scale", "curvature",
                "asymmetry", "surface_detail", "seed", "resolution",
            ),
        )
        self.assertEqual(bone.parameter_metadata["length"].unit, "mm")
        self.assertEqual(bone.parameter_metadata["shaft_radius"].unit, "mm")
        self.assertEqual(bone.parameter_metadata["resolution"].preview_resolutions,
                         (21, 25))

    def test_coral_maps_to_available_coral_generator(self):
        coral = PresetFactory.get("coral")
        self.assertTrue(coral.available)
        self.assertEqual(coral.generator_id, "coral")
        self.assertEqual(
            set(coral.default_parameters),
            {"cell_size", "thickness", "seed", "resolution"},
        )

    def test_rock_is_available_with_stable_metadata(self):
        rock = PresetFactory.get("rock")
        self.assertTrue(rock.available)
        self.assertEqual(rock.preset_id, "rock")
        self.assertEqual(rock.generator_id, "rock")
        self.assertEqual(
            tuple(rock.parameter_metadata),
            ("size", "roughness", "seed", "resolution"),
        )
        self.assertEqual(rock.parameter_metadata["size"].value_type, "length")
        self.assertEqual(rock.parameter_metadata["size"].unit, "mm")
        self.assertGreater(rock.parameter_metadata["size"].minimum, 0)
        self.assertEqual(rock.parameter_metadata["seed"].value_type, "integer")
        self.assertEqual(rock.parameter_metadata["resolution"].minimum, 9)
        self.assertEqual(rock.parameter_metadata["resolution"].maximum, 41)

    def test_bark_is_available_with_stable_metadata_and_defaults(self):
        bark = PresetFactory.get("bark")
        self.assertTrue(bark.available)
        self.assertEqual(bark.preset_id, "bark")
        self.assertEqual(bark.generator_id, "bark")
        self.assertEqual(
            tuple(bark.parameter_metadata),
            ("diameter", "height", "bark_depth", "groove_scale", "twist", "seed", "resolution"),
        )
        self.assertEqual(dict(bark.default_parameters), {
            "diameter": 80.0, "height": 120.0, "bark_depth": 4.0,
            "groove_scale": 18.0, "twist": 0.0, "seed": 10,
            "resolution": 33,
        })
        for key in ("diameter", "height", "bark_depth", "groove_scale"):
            self.assertEqual(bark.parameter_metadata[key].value_type, "length")
            self.assertEqual(bark.parameter_metadata[key].unit, "mm")
            self.assertGreater(bark.parameter_metadata[key].minimum, 0)
        self.assertEqual(bark.parameter_metadata["seed"].value_type, "integer")
        self.assertEqual(bark.parameter_metadata["resolution"].minimum, 29)
        self.assertEqual(bark.parameter_metadata["resolution"].maximum, 41)

    def test_root_is_available_with_stable_metadata_and_defaults(self):
        root = PresetFactory.get("root")
        self.assertTrue(root.available)
        self.assertEqual(root.preset_id, "root")
        self.assertEqual(root.generator_id, "root")
        self.assertEqual(tuple(root.parameter_metadata), (
            "length", "root_radius", "branch_count", "branching", "spread",
            "taper", "gravity", "seed", "resolution",
        ))
        self.assertEqual(dict(root.default_parameters), {
            "length": 100.0, "root_radius": 8.0, "branch_count": 5,
            "branching": 0.45, "spread": 0.65, "taper": 0.65,
            "gravity": 0.70, "seed": 11, "resolution": 37,
        })
        for key in ("length", "root_radius"):
            self.assertEqual(root.parameter_metadata[key].value_type, "length")
            self.assertEqual(root.parameter_metadata[key].unit, "mm")
        self.assertEqual(root.parameter_metadata["branch_count"].maximum, 8)
        self.assertEqual(root.parameter_metadata["root_radius"].minimum, 4.0)
        self.assertEqual(root.parameter_metadata["resolution"].minimum, 37)

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

        parameters = dict(sponge.default_parameters)
        parameters.pop("resolution")
        parameters.pop("seed")
        field = GyroidField(**parameters)
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
            {"coral", "bone", "bark", "sponge", "rock", "root"},
        )

    def test_catalog_composes_family_metadata_without_changing_preset_api(self):
        rock = PresetCatalog.get("rock")
        self.assertIsInstance(rock, PresetDefinition)
        self.assertIs(rock.preset, PresetFactory.get("rock"))
        self.assertIs(rock.families, RockFamilyRegistry)
        self.assertEqual(
            tuple(family.display_name for family in rock.families.list_all()),
            (
                "Classic Rock", "Layered Rock", "Weathered Rock", "River Rock",
                "Smooth", "Weathered", "Rugged", "River Stone",
                "Granite", "Basalt", "Broken Rock",
            ),
        )

    def test_every_implemented_preset_has_a_family_registry(self):
        definitions = {
            definition.preset_id: definition
            for definition in PresetCatalog.list_all()
        }
        self.assertEqual(
            set(definitions),
            {"coral", "bone", "bark", "sponge", "rock", "root"},
        )
        self.assertIs(definitions["bark"].families, BarkFamilyRegistry)
        self.assertIs(definitions["bone"].families, BoneFamilyRegistry)
        self.assertIs(definitions["coral"].families, CoralFamilyRegistry)
        self.assertIs(definitions["root"].families, RootFamilyRegistry)
        self.assertIs(definitions["sponge"].families, SpongeFamilyRegistry)

    def test_bone_catalog_exposes_classic_family_metadata(self):
        definition = PresetCatalog.get("bone")
        self.assertIs(definition.families, BoneFamilyRegistry)
        families = definition.families.list_all()
        self.assertEqual(len(families), 1)
        self.assertEqual(families[0].family_id, "classic_bone")
        self.assertEqual(families[0].display_name, "Classic Bone")

    def test_root_catalog_exposes_classic_family_metadata(self):
        definition = PresetCatalog.get("root")
        self.assertIs(definition.families, RootFamilyRegistry)
        families = definition.families.list_all()
        self.assertEqual(len(families), 1)
        self.assertEqual(families[0].family_id, "classic_root")
        self.assertEqual(families[0].display_name, "Classic Root")
        self.assertEqual(
            tuple(families[0].parameter_values),
            (
                "length", "root_radius", "branch_count", "branching", "spread",
                "taper", "gravity", "seed", "resolution",
            ),
        )

    def test_sponge_catalog_exposes_classic_family_metadata(self):
        definition = PresetCatalog.get("sponge")
        self.assertIs(definition.families, SpongeFamilyRegistry)
        families = definition.families.list_all()
        self.assertEqual(len(families), 1)
        self.assertEqual(families[0].family_id, "classic_sponge")
        self.assertEqual(families[0].display_name, "Classic Sponge")
        self.assertEqual(
            tuple(families[0].parameter_values),
            ("cell_size", "thickness", "seed", "resolution"),
        )

    def test_bark_catalog_exposes_classic_family_metadata(self):
        definition = PresetCatalog.get("bark")
        self.assertIs(definition.families, BarkFamilyRegistry)
        families = definition.families.list_all()
        self.assertEqual(len(families), 1)
        self.assertEqual(families[0].family_id, "classic_bark")
        self.assertEqual(families[0].display_name, "Classic Bark")
        self.assertEqual(
            tuple(families[0].parameter_values),
            (
                "diameter", "height", "bark_depth", "groove_scale",
                "twist", "seed", "resolution",
            ),
        )

    def test_coral_catalog_exposes_classic_family_metadata(self):
        definition = PresetCatalog.get("coral")
        self.assertIs(definition.families, CoralFamilyRegistry)
        families = definition.families.list_all()
        self.assertEqual(len(families), 1)
        self.assertEqual(families[0].family_id, "classic_coral")
        self.assertEqual(families[0].display_name, "Classic Coral")
        self.assertEqual(
            tuple(families[0].parameter_values),
            ("cell_size", "thickness", "seed", "resolution"),
        )

    def test_definition_rejects_family_registry_for_another_preset(self):
        with self.assertRaises(ValueError):
            PresetDefinition(sample_preset("different"), RockFamilyRegistry)


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
