"""End-to-end tests for the preset-to-mesh generator runtime."""

from dataclasses import FrozenInstanceError
from pathlib import Path
import unittest

from core.mesh import TriangleMesh
from generators import (
    Generator,
    GeneratorFactory,
    GeneratorResult,
    GyroidGenerator,
    InvalidGeneratorParameters,
    MeshExtractionError,
    UnavailablePresetError,
    UnknownGeneratorError,
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
