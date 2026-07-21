"""Unit tests for the pure-Python geometry core."""

from io import BytesIO, StringIO
import math
from pathlib import Path
import struct
import tempfile
import unittest

from core.mesh import TriangleMesh
from core.scalar_field import evaluate
from core.stl_writer import write_ascii, write_ascii_stream, write_binary_stream
from core.voxel_grid import VoxelGrid


class ScalarFieldTests(unittest.TestCase):
    def test_evaluate_accepts_finite_numeric_values(self):
        self.assertEqual(evaluate(lambda x, y, z: x + y + z, (1, 2, 3)), 6.0)

    def test_evaluate_rejects_non_finite_values(self):
        with self.assertRaises(ValueError):
            evaluate(lambda x, y, z: math.nan, (0, 0, 0))


class VoxelGridTests(unittest.TestCase):
    def test_samples_inclusive_bounds_with_x_varying_fastest(self):
        grid = VoxelGrid.sample(
            lambda x, y, z: x + 10 * y + 100 * z,
            (0, 0, 0),
            (2, 4, 6),
            (3, 3, 3),
        )

        self.assertEqual(grid.spacing, (1.0, 2.0, 3.0))
        self.assertEqual(grid.value_at(2, 1, 1), 322.0)
        self.assertEqual(grid.point_at(2, 2, 2), (2.0, 4.0, 6.0))
        self.assertEqual(grid.cell_shape, (2, 2, 2))
        self.assertEqual(grid.cell_corner_indices(0, 0, 0), (0, 1, 4, 3, 9, 10, 13, 12))
        self.assertEqual(len(list(grid.iter_cells())), 8)

    def test_rejects_invalid_grid_dimensions(self):
        with self.assertRaises(ValueError):
            VoxelGrid.sample(lambda x, y, z: 0, (0, 0, 0), (1, 1, 1), (1, 2, 2))

    def test_rejects_wrong_sample_count(self):
        with self.assertRaises(ValueError):
            VoxelGrid((0, 0, 0), (1, 1, 1), (2, 2, 2), (0.0,))


class TriangleMeshTests(unittest.TestCase):
    def setUp(self):
        self.mesh = TriangleMesh(
            vertices=((0, 0, 0), (1, 0, 0), (0, 1, 0)),
            faces=((0, 1, 2),),
        )

    def test_computes_right_hand_face_normal(self):
        self.assertEqual(self.mesh.face_normal(0), (0.0, 0.0, 1.0))

    def test_rejects_out_of_range_face_index(self):
        with self.assertRaises(ValueError):
            TriangleMesh(vertices=((0, 0, 0),), faces=((0, 1, 2),))

    def test_rejects_zero_area_face_when_normal_is_requested(self):
        mesh = TriangleMesh(
            vertices=((0, 0, 0), (1, 0, 0), (2, 0, 0)),
            faces=((0, 1, 2),),
        )
        with self.assertRaises(ValueError):
            mesh.face_normal(0)


class StlWriterTests(unittest.TestCase):
    def setUp(self):
        self.mesh = TriangleMesh(
            vertices=((0, 0, 0), (1, 0, 0), (0, 1, 0)),
            faces=((0, 1, 2),),
        )

    def test_writes_ascii_stl(self):
        stream = StringIO()
        write_ascii_stream(self.mesh, stream, "test mesh")
        output = stream.getvalue()

        self.assertTrue(output.startswith("solid test_mesh\n"))
        self.assertIn("facet normal 0 0 1", output)
        self.assertEqual(output.count("      vertex "), 3)
        self.assertTrue(output.endswith("endsolid test_mesh\n"))

    def test_writes_binary_stl(self):
        stream = BytesIO()
        write_binary_stream(self.mesh, stream, "test")
        output = stream.getvalue()

        self.assertEqual(len(output), 84 + 50)
        self.assertEqual(struct.unpack("<I", output[80:84])[0], 1)
        self.assertEqual(struct.unpack("<3f", output[84:96]), (0.0, 0.0, 1.0))

    def test_writes_stl_to_a_file(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "triangle.stl"
            write_ascii(self.mesh, destination)

            self.assertTrue(destination.read_text(encoding="ascii").startswith("solid "))


if __name__ == "__main__":
    unittest.main()
