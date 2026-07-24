"""Tests for the Sprint 27 shared natural-material framework."""

from dataclasses import FrozenInstanceError
import unittest

from assets import (
    AssetBrowserMetadata,
    MaterialDefinition,
    NATURAL_MATERIALS,
    NaturalMaterial,
    NaturalMaterialRegistry,
    ThumbnailReference,
)
from generators import GenerationRequest, GeneratorFactory
from presets import PresetFactory


class NaturalMaterialTests(unittest.TestCase):
    def test_registry_covers_every_implemented_preset(self):
        preset_ids = {preset.preset_id for preset in PresetFactory.list_all()}
        material_ids = {
            material.preset_id for material in NATURAL_MATERIALS.list_all()
        }
        self.assertEqual(material_ids, preset_ids)
        for preset in PresetFactory.list_all():
            material = NATURAL_MATERIALS.get(preset.preset_id)
            self.assertEqual(material.browser.category, preset.category)

    def test_material_records_are_immutable_and_renderer_neutral(self):
        material = NATURAL_MATERIALS.get("rock")
        self.assertEqual(material.definition.material_id, "natural_rock")
        self.assertIsNone(material.thumbnail)
        self.assertIn("stone", material.browser.keywords)
        with self.assertRaises(FrozenInstanceError):
            material.preset_id = "changed"
        with self.assertRaises(TypeError):
            material.metadata["renderer"] = "fusion"

    def test_thumbnail_and_browser_metadata_are_ready_without_image_loading(self):
        thumbnail = ThumbnailReference("rock_thumbnail", "Rounded natural rock")
        material = NaturalMaterial(
            "sample",
            MaterialDefinition("sample_surface", "Sample", (0.5, 0.5, 0.5)),
            AssetBrowserMetadata("sample", ("natural", "sample")),
            thumbnail,
            {"source": "procedural"},
        )
        self.assertIs(material.thumbnail, thumbnail)
        self.assertEqual(material.metadata["source"], "procedural")

    def test_registry_rejects_duplicate_preset_ids(self):
        material = NATURAL_MATERIALS.get("rock")
        with self.assertRaises(ValueError):
            NaturalMaterialRegistry((material, material))

    def test_generated_assets_use_the_shared_material_definitions(self):
        result = GeneratorFactory.generate_request(
            GenerationRequest(
                "rock",
                {"size": 40.0, "roughness": 0.35, "seed": 1},
                9,
            )
        )
        self.assertIs(
            result.asset.material,
            NATURAL_MATERIALS.get("rock").definition,
        )


class NaturalParameterGroupTests(unittest.TestCase):
    def test_every_preset_uses_standard_form_and_generation_groups(self):
        for preset in PresetFactory.list_all():
            with self.subTest(preset=preset.preset_id):
                self.assertEqual(
                    tuple(group.group_id for group in preset.parameter_groups),
                    ("form", "generation"),
                )
                self.assertEqual(
                    preset.parameter_groups[1].parameter_ids,
                    ("seed", "resolution"),
                )
                grouped = tuple(
                    parameter_id
                    for group in preset.parameter_groups
                    for parameter_id in group.parameter_ids
                )
                self.assertEqual(set(grouped), set(preset.parameter_metadata))
                self.assertEqual(len(grouped), len(set(grouped)))

    def test_parameter_groups_remain_optional_for_legacy_presets(self):
        preset = NaturePresetForCompatibility.create()
        self.assertEqual(preset.parameter_groups, ())


class NaturePresetForCompatibility:
    @staticmethod
    def create():
        from presets import NaturePreset, ParameterMetadata

        return NaturePreset(
            preset_id="legacy",
            display_name="Legacy",
            category="compatibility",
            description="Legacy preset without presentation groups.",
            generator_id="legacy",
            default_parameters={"scale": 1.0},
            parameter_metadata={
                "scale": ParameterMetadata("Scale", "float", 1.0)
            },
            available=True,
        )


if __name__ == "__main__":
    unittest.main()
