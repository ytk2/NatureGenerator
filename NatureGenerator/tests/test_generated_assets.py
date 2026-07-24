"""Tests for the Sprint 22 generated-asset and export boundaries."""

from dataclasses import FrozenInstanceError
from pathlib import Path
import unittest

from assets import (
    AssetExporter,
    AssetMetadata,
    ExportFormat,
    ExportRequest,
    ExportResult,
    ExporterRegistry,
    GeneratedAsset,
    MappingDefinition,
    MappingMode,
    MaterialDefinition,
    TextureResource,
    TextureSemantic,
    TextureSet,
)
from core.mesh import TriangleMesh
from generators import GenerationRequest, GeneratorFactory


def _mesh():
    return TriangleMesh(
        ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        ((0, 1, 2),),
    )


def _asset():
    return GeneratedAsset(
        mesh=_mesh(),
        material=MaterialDefinition(
            "test_surface",
            "Test Surface",
            (0.2, 0.3, 0.4),
            procedural_parameters={"frequency": 2.0},
        ),
        mapping=MappingDefinition(),
        textures=TextureSet(),
        metadata=AssetMetadata(
            "test_asset", "Test Asset", "rock", "rock", parameters={"seed": 1}
        ),
    )


class GeneratedAssetDefinitionTests(unittest.TestCase):
    def test_complete_asset_uses_existing_triangle_mesh(self):
        asset = _asset()
        self.assertIsInstance(asset.mesh, TriangleMesh)
        self.assertEqual(asset.material.base_color, (0.2, 0.3, 0.4, 1.0))
        self.assertIs(asset.mapping.mode, MappingMode.OBJECT_SPACE)
        self.assertEqual(asset.textures.resources, ())
        self.assertEqual(asset.metadata.coordinate_unit, "mm")

    def test_definitions_are_immutable_and_copy_metadata(self):
        parameters = {"frequency": 2.0}
        material = MaterialDefinition(
            "test_surface", "Test", (0.1, 0.2, 0.3), procedural_parameters=parameters
        )
        parameters.clear()
        self.assertEqual(material.procedural_parameters["frequency"], 2.0)
        with self.assertRaises(TypeError):
            material.procedural_parameters["frequency"] = 3.0
        with self.assertRaises(FrozenInstanceError):
            material.roughness = 0.2

    def test_material_and_mapping_reject_invalid_numeric_values(self):
        with self.assertRaises(ValueError):
            MaterialDefinition("bad", "Bad", (1.1, 0.0, 0.0))
        with self.assertRaises(ValueError):
            MappingDefinition(scale=(1.0, 0.0, 1.0))

    def test_texture_set_indexes_unique_renderer_neutral_semantics(self):
        resource = TextureResource(
            "base_color_map",
            TextureSemantic.BASE_COLOR,
            "image/png",
            b"not-yet-decoded",
            1,
            1,
        )
        textures = TextureSet((resource,))
        self.assertIs(textures.get(TextureSemantic.BASE_COLOR), resource)
        self.assertIsNone(textures.get(TextureSemantic.NORMAL))
        with self.assertRaises(ValueError):
            TextureSet((resource, resource))

    def test_runtime_result_contains_asset_without_replacing_mesh(self):
        result = GeneratorFactory.generate_request(
            GenerationRequest(
                "rock",
                {"size": 40.0, "roughness": 0.35, "seed": 1},
                9,
            )
        )
        self.assertIs(result.asset.mesh, result.mesh)
        self.assertEqual(result.asset.metadata.preset_id, "rock")
        self.assertEqual(result.asset.metadata.generator_id, "rock")
        self.assertEqual(result.asset.metadata.parameters["resolution"], 9)
        self.assertEqual(result.asset.textures.resources, ())


class _RecordingExporter(AssetExporter):
    def __init__(self):
        self.request = None

    @property
    def format(self):
        return ExportFormat.GLTF

    def export(self, request):
        self.request = request
        return ExportResult((request.destination,))


class ExportArchitectureTests(unittest.TestCase):
    def test_registry_routes_by_format_without_production_export(self):
        exporter = _RecordingExporter()
        registry = ExporterRegistry()
        registry.register(exporter)
        request = ExportRequest(_asset(), Path("asset.gltf"), ExportFormat.GLTF)
        result = registry.export(request)
        self.assertIs(exporter.request, request)
        self.assertEqual(result.files, (Path("asset.gltf"),))

    def test_unregistered_format_is_explicit(self):
        with self.assertRaises(LookupError):
            ExporterRegistry().get(ExportFormat.USDZ)


if __name__ == "__main__":
    unittest.main()
