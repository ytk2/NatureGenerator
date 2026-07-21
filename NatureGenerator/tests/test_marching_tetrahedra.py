"""Correctness tests for dependency-free marching tetrahedra."""

import math
from pathlib import Path
import tempfile
import unittest

from core.marching_tetrahedra import extract_field, extract_isosurface
from core.stl_writer import validate_stl, write_ascii, write_binary
from core.voxel_grid import VoxelGrid


class MarchingTetrahedraTests(unittest.TestCase):
    def test_interpolates_a_plane_and_orients_normals(self):
        grid = VoxelGrid.sample(lambda x, y, z: x, (-1, -1, -1), (1, 1, 1), (3, 3, 3))
        mesh = extract_isosurface(grid)

        self.assertGreater(len(mesh.faces), 0)
        self.assertTrue(all(abs(vertex[0]) < 1e-12 for vertex in mesh.vertices))
        self.assertTrue(all(normal[0] > 0.999999 for normal in mesh.face_normals()))
        self.assertEqual(len(mesh.vertices), len(set(mesh.vertices)))

    def test_extracts_a_watertight_sphere(self):
        def sphere(x, y, z):
            return x * x + y * y + z * z - 0.65 * 0.65

        mesh = extract_field(sphere, (-1, -1, -1), (1, 1, 1), (9, 9, 9))
        statistics = mesh.statistics()

        self.assertGreater(statistics.vertex_count, 0)
        self.assertGreater(statistics.face_count, 0)
        self.assertTrue(statistics.is_watertight)
        self.assertEqual(statistics.boundary_edge_count, 0)
        self.assertEqual(statistics.nonmanifold_edge_count, 0)
        self.assertEqual(len(mesh.vertices), len(set(mesh.vertices)))
        self.assertGreater(statistics.surface_area, 0.0)
        self.assertIsNotNone(statistics.bounds)
        for vertex, normal in zip(mesh.vertices, mesh.vertex_normals()):
            self.assertTrue(all(math.isfinite(component) for component in normal))
            self.assertGreater(sum(a * b for a, b in zip(vertex, normal)), 0.0)

    def test_empty_surface_returns_an_empty_mesh(self):
        mesh = extract_field(lambda x, y, z: 1.0, (-1, -1, -1), (1, 1, 1), (3, 3, 3))
        self.assertEqual(mesh.vertices, ())
        self.assertEqual(mesh.faces, ())
        self.assertFalse(mesh.statistics().is_watertight)

    def test_rejects_non_finite_iso_value(self):
        grid = VoxelGrid.sample(lambda x, y, z: x, (-1, -1, -1), (1, 1, 1), (2, 2, 2))
        with self.assertRaises(ValueError):
            extract_isosurface(grid, math.nan)

    def test_generated_stl_files_validate(self):
        mesh = extract_field(
            lambda x, y, z: x * x + y * y + z * z - 0.5,
            (-1, -1, -1),
            (1, 1, 1),
            (7, 7, 7),
        )
        with tempfile.TemporaryDirectory() as directory:
            ascii_path = Path(directory) / "sphere-ascii.stl"
            binary_path = Path(directory) / "sphere-binary.stl"
            write_ascii(mesh, ascii_path, "sphere")
            write_binary(mesh, binary_path, "sphere")

            ascii_result = validate_stl(ascii_path, len(mesh.faces))
            binary_result = validate_stl(binary_path, len(mesh.faces))
            self.assertTrue(ascii_result.valid, ascii_result.message)
            self.assertEqual(ascii_result.encoding, "ascii")
            self.assertTrue(binary_result.valid, binary_result.message)
            self.assertEqual(binary_result.encoding, "binary")

    def test_stl_validation_rejects_malformed_ascii(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.stl"
            path.write_text(
                "solid invalid\n"
                "facet normal nan 0 1\n"
                "outer loop\n"
                "vertex 0 0 0\nvertex 1 0 0\nvertex 0 1 0\n"
                "endloop\nendfacet\nendsolid invalid\n",
                encoding="ascii",
            )
            self.assertFalse(validate_stl(path).valid)


if __name__ == "__main__":
    unittest.main()
