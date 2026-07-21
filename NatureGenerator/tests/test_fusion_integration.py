"""Tests for the Fusion boundary that run without Autodesk's Python runtime."""

import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from commands.generate_sponge import generate_sponge
from core.mesh import TriangleMesh
from fusion.mesh_body import MeshBodyBuilder, triangle_mesh_data


class GenerateSpongeCommandTests(unittest.TestCase):
    def test_command_runs_runtime_and_passes_mesh_to_adapter(self):
        received = []
        sentinel_body = object()

        def insert_mesh(mesh, name):
            received.append((mesh, name))
            return sentinel_body

        result, body = generate_sponge(insert_mesh)

        self.assertIs(body, sentinel_body)
        self.assertEqual(result.preset_id, "sponge")
        self.assertEqual(result.generator_id, "gyroid")
        self.assertEqual(received, [(result.mesh, "NatureGenerator Sponge")])

    def test_command_rejects_missing_mesh_body(self):
        with self.assertRaisesRegex(RuntimeError, "did not return"):
            generate_sponge(lambda mesh, name: None)


class MeshBodyAdapterTests(unittest.TestCase):
    def test_triangle_mesh_data_flattens_indexed_mesh(self):
        mesh = TriangleMesh(
            vertices=((0, 0, 0), (1, 0, 0), (0, 1, 0)),
            faces=((0, 1, 2),),
        )
        coordinates, indices = triangle_mesh_data(mesh)
        self.assertEqual(
            coordinates,
            [0.0, 0.0, 0.0, 0.1, 0.0, 0.0, 0.0, 0.1, 0.0],
        )
        self.assertEqual(indices, [0, 1, 2])

    def test_triangle_mesh_data_rejects_empty_mesh(self):
        with self.assertRaisesRegex(ValueError, "at least one triangle"):
            triangle_mesh_data(TriangleMesh(vertices=(), faces=()))

    def test_builder_inserts_data_into_supplied_design(self):
        mesh = TriangleMesh(
            vertices=((0, 0, 0), (1, 0, 0), (0, 1, 0)),
            faces=((0, 1, 2),),
        )
        calls = []
        body = SimpleNamespace(name="")

        class MeshBodies:
            def addByTriangleMeshData(
                self, coordinates, indices, normals, normal_indices
            ):
                calls.append((coordinates, indices, normals, normal_indices))
                return body

        design = SimpleNamespace(
            rootComponent=SimpleNamespace(meshBodies=MeshBodies())
        )
        adsk = ModuleType("adsk")
        adsk.core = ModuleType("adsk.core")
        adsk.fusion = ModuleType("adsk.fusion")
        with patch.dict(
            sys.modules,
            {"adsk": adsk, "adsk.core": adsk.core, "adsk.fusion": adsk.fusion},
        ):
            created = MeshBodyBuilder().build(mesh, "Test Sponge", design)

        self.assertIs(created, body)
        self.assertEqual(body.name, "Test Sponge")
        self.assertEqual(calls[0][1], [0, 1, 2])
        self.assertEqual(calls[0][2:], ([], []))


class FusionDependencyBoundaryTests(unittest.TestCase):
    def test_adsk_imports_exist_only_in_fusion_adapter(self):
        package_root = Path(__file__).parents[1]
        for folder in ("core", "generators", "presets", "commands"):
            for module in (package_root / folder).glob("*.py"):
                self.assertNotIn("import adsk", module.read_text(encoding="utf-8"))
        entry_point = (package_root / "NatureGenerator.py").read_text(encoding="utf-8")
        self.assertNotIn("import adsk", entry_point)

        fusion_sources = "\n".join(
            module.read_text(encoding="utf-8")
            for module in (package_root / "fusion").glob("*.py")
        )
        self.assertIn("import adsk", fusion_sources)

    def test_entry_point_imports_without_autodesk_runtime(self):
        entry_path = Path(__file__).parents[1] / "NatureGenerator.py"
        spec = importlib.util.spec_from_file_location("addin_entry", str(entry_path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(callable(module.run))
        self.assertTrue(callable(module.stop))


if __name__ == "__main__":
    unittest.main()
