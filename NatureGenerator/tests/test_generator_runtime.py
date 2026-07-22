"""End-to-end tests for the preset-to-mesh generator runtime."""

from dataclasses import FrozenInstanceError
from pathlib import Path
import unittest

from core.mesh import TriangleMesh
from generators import (
    DEFAULT_RESOLUTION,
    MAX_RESOLUTION,
    MIN_RESOLUTION,
    Generator,
    GeneratorFactory,
    GeneratorResult,
    GenerationRequest,
    GyroidGenerator,
    InvalidGeneratorParameters,
    MeshExtractionError,
    UnavailablePresetError,
    UnknownGeneratorError,
    UnknownPresetError,
)
from presets import NaturePreset, PresetFactory


class GeneratorFactoryTests(unittest.TestCase):
    def test_resolves_gyroid_by_stable_id(self):
        generator = GeneratorFactory.create("gyroid")
        self.assertIsInstance(generator, GyroidGenerator)
        self.assertEqual(generator.generator_id, "gyroid")

    def test_unknown_generator_has_meaningful_error(self):
        with self.assertRaisesRegex(UnknownGeneratorError, "unknown generator_id"):
            GeneratorFactory.create("missing")

    def test_unavailable_preset_is_rejected_before_resolution(self):
        with self.assertRaisesRegex(UnavailablePresetError, "gray_scott"):
            GeneratorFactory.generate(PresetFactory.get("coral"))

    def test_request_rejects_unavailable_preset(self):
        request = GenerationRequest("coral", {}, DEFAULT_RESOLUTION)
        with self.assertRaisesRegex(UnavailablePresetError, "not implemented"):
            GeneratorFactory.generate_request(request)

    def test_request_rejects_unknown_preset(self):
        request = GenerationRequest("missing", {}, DEFAULT_RESOLUTION)
        with self.assertRaisesRegex(UnknownPresetError, "unknown preset_id"):
            GeneratorFactory.generate_request(request)


class GenerationRequestTests(unittest.TestCase):
    def test_request_is_immutable_and_defensively_copies_overrides(self):
        overrides = {"cell_size": 12.0, "thickness": 0.25}
        request = GenerationRequest("sponge", overrides, 19)
        overrides["cell_size"] = 99.0

        self.assertEqual(request.parameter_overrides["cell_size"], 12.0)
        with self.assertRaises(TypeError):
            request.parameter_overrides["cell_size"] = 20.0
        with self.assertRaises(FrozenInstanceError):
            request.resolution = 21

    def test_resolution_validation(self):
        for value in (MIN_RESOLUTION, DEFAULT_RESOLUTION, MAX_RESOLUTION):
            self.assertEqual(GenerationRequest("sponge", {}, value).resolution, value)
        for value in (MIN_RESOLUTION - 1, MAX_RESOLUTION + 1):
            with self.assertRaisesRegex(ValueError, "between"):
                GenerationRequest("sponge", {}, value)
        for value in (True, 17.0, "17"):
            with self.assertRaisesRegex(TypeError, "integer"):
                GenerationRequest("sponge", {}, value)

    def test_non_finite_parameter_overrides_are_rejected(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaisesRegex(TypeError, "finite"):
                GenerationRequest("sponge", {"cell_size": value}, 17)


class GyroidGeneratorTests(unittest.TestCase):
    def test_sponge_runs_end_to_end(self):
        preset = PresetFactory.get("sponge")
        result = GeneratorFactory.generate(preset)

        self.assertIsInstance(result, GeneratorResult)
        self.assertIsInstance(result.mesh, TriangleMesh)
        self.assertGreater(len(result.mesh.vertices), 0)
        self.assertGreater(len(result.mesh.faces), 0)
        self.assertEqual(result.statistics, result.mesh.statistics())
        self.assertGreater(result.statistics.vertex_count, 0)
        self.assertGreater(result.statistics.face_count, 0)
        self.assertTrue(result.statistics.is_manifold)
        self.assertFalse(result.statistics.is_watertight)
        self.assertGreater(result.statistics.boundary_edge_count, 0)
        self.assertTrue(any("boundary_edges" in warning for warning in result.warnings))
        self.assertEqual(result.generator_id, "gyroid")
        self.assertEqual(result.preset_id, "sponge")
        self.assertGreater(result.elapsed_time, 0.0)

    def test_parameter_overrides_are_validated(self):
        with self.assertRaisesRegex(InvalidGeneratorParameters, "cell_size"):
            GeneratorFactory.generate(
                PresetFactory.get("sponge"), {"cell_size": 0.0}
            )
        with self.assertRaisesRegex(InvalidGeneratorParameters, "unknown"):
            GeneratorFactory.generate(
                PresetFactory.get("sponge"), {"unknown": 1.0}
            )
        with self.assertRaisesRegex(InvalidGeneratorParameters, "at most"):
            GeneratorFactory.generate(
                PresetFactory.get("sponge"), {"thickness": 1.5}
            )

    def test_request_applies_valid_parameter_overrides(self):
        thin = GeneratorFactory.generate_request(
            GenerationRequest(
                "sponge", {"cell_size": 12.0, "thickness": 0.1}, 17
            )
        )
        thick = GeneratorFactory.generate_request(
            GenerationRequest(
                "sponge", {"cell_size": 12.0, "thickness": 0.4}, 17
            )
        )
        self.assertGreater(thin.statistics.face_count, 0)
        self.assertGreater(thick.statistics.face_count, 0)
        self.assertNotEqual(thin.statistics.face_count, thick.statistics.face_count)

    def test_legacy_factory_api_keeps_default_resolution(self):
        legacy = GeneratorFactory.generate(PresetFactory.get("sponge"))
        requested = GeneratorFactory.generate_request(
            GenerationRequest("sponge", {}, DEFAULT_RESOLUTION)
        )
        self.assertEqual(
            legacy.statistics.vertex_count, requested.statistics.vertex_count
        )
        self.assertEqual(legacy.statistics.face_count, requested.statistics.face_count)

    def test_request_rejects_invalid_cell_size_and_thickness(self):
        for cell_size in (0.0, -1.0, 0.5, 101.0):
            request = GenerationRequest(
                "sponge", {"cell_size": cell_size, "thickness": 0.2}, 17
            )
            with self.assertRaisesRegex(InvalidGeneratorParameters, "cell_size"):
                GeneratorFactory.generate_request(request)
        for thickness in (-0.1, 1.1):
            request = GenerationRequest(
                "sponge", {"cell_size": 10.0, "thickness": thickness}, 17
            )
            with self.assertRaisesRegex(InvalidGeneratorParameters, "thickness"):
                GeneratorFactory.generate_request(request)

    def test_resolution_changes_mesh_density(self):
        low = GeneratorFactory.generate_request(
            GenerationRequest("sponge", {}, MIN_RESOLUTION)
        )
        high = GeneratorFactory.generate_request(
            GenerationRequest("sponge", {}, 25)
        )
        self.assertGreater(high.statistics.vertex_count, low.statistics.vertex_count)
        self.assertGreater(high.statistics.face_count, low.statistics.face_count)

    def test_empty_extraction_has_meaningful_error(self):
        preset = NaturePreset(
            preset_id="empty_gyroid",
            display_name="Empty Gyroid",
            category="test",
            description="Gyroid configured outside its value range.",
            generator_id="gyroid",
            default_parameters={"cell_size": 10.0, "thickness": 2.0},
            available=True,
        )
        with self.assertRaisesRegex(MeshExtractionError, "no triangles"):
            GeneratorFactory.generate(preset)

    def test_result_is_immutable(self):
        result = GeneratorFactory.generate(PresetFactory.get("sponge"))
        with self.assertRaises(FrozenInstanceError):
            result.elapsed_time = 0.0


class GeneratorRuntimeDependencyTests(unittest.TestCase):
    def test_runtime_has_no_fusion_numpy_or_dynamic_discovery_imports(self):
        generator_root = Path(__file__).parents[1] / "generators"
        runtime_modules = (
            "generator.py",
            "generator_factory.py",
            "gyroid_generator.py",
            "result.py",
            "request.py",
        )
        forbidden = (
            "import adsk",
            "from adsk",
            "import numpy",
            "from numpy",
            "importlib",
            "pkgutil",
            "glob(",
            "os.listdir",
        )
        for name in runtime_modules:
            source = (generator_root / name).read_text(encoding="utf-8")
            for marker in forbidden:
                self.assertNotIn(marker, source, "{} contains {}".format(name, marker))


if __name__ == "__main__":
    unittest.main()
