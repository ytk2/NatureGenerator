"""Tests for mesh construction, cleanup, validation, and export."""

from io import StringIO
import unittest

from core.mesh import TriangleMesh
from core.mesh_builder import MeshBuilder
from core.mesh_optimizer import optimize_mesh
from core.mesh_validator import MeshValidator
from core.obj_writer import write_obj_stream
from core.ply_writer import write_ply_stream


def tetrahedron() -> TriangleMesh:
    """Return a consistently outward-wound closed tetrahedron."""

    return TriangleMesh(
        vertices=((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)),
        faces=((0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)),
    )


class MeshBuilderTests(unittest.TestCase):
    def test_exact_welding_reuses_vertices(self):
        builder = MeshBuilder()
        builder.add_triangle((0, 0, 0), (1, 0, 0), (0, 1, 0))
        builder.add_triangle((0, 0, 0), (0, 1, 0), (0, 0, 1))
        mesh = builder.build()

        self.assertEqual(len(mesh.vertices), 4)
        self.assertEqual(len(mesh.faces), 2)

    def test_tolerance_welding_uses_euclidean_distance(self):
        builder = MeshBuilder(weld_tolerance=0.01)
        first = builder.add_vertex((0, 0, 0))
        near = builder.add_vertex((0.005, 0.005, 0.0))
        far = builder.add_vertex((0.02, 0, 0))

        self.assertEqual(first, near)
        self.assertNotEqual(first, far)


class MeshOptimizationTests(unittest.TestCase):
    def test_removes_duplicates_degenerates_and_unused_vertices(self):
        dirty = TriangleMesh(
            vertices=(
                (0, 0, 0),
                (1, 0, 0),
                (0, 1, 0),
                (0, 0, 0),
                (2, 0, 0),
                (9, 9, 9),
            ),
            faces=((0, 1, 2), (3, 1, 2), (0, 1, 4)),
        )
        optimized = optimize_mesh(dirty)
        statistics = optimized.statistics()

        self.assertEqual(statistics.vertex_count, 3)
        self.assertEqual(statistics.face_count, 1)
        self.assertEqual(statistics.duplicate_face_count, 0)
        self.assertEqual(statistics.degenerate_face_count, 0)
        self.assertEqual(statistics.unused_vertex_count, 0)


class MeshValidatorTests(unittest.TestCase):
    def test_accepts_a_closed_oriented_manifold(self):
        report = MeshValidator(require_watertight=True).validate(tetrahedron())

        self.assertTrue(report.valid)
        self.assertTrue(report.manifold)
        self.assertTrue(report.watertight)
        self.assertEqual(report.statistics.edge_count, 6)
        self.assertEqual(report.statistics.connected_component_count, 1)
        self.assertAlmostEqual(report.statistics.signed_volume, 1.0 / 6.0)

    def test_reports_open_mesh_as_warning_or_error_by_policy(self):
        mesh = TriangleMesh(((0, 0, 0), (1, 0, 0), (0, 1, 0)), ((0, 1, 2),))

        open_report = MeshValidator().validate(mesh)
        closed_report = MeshValidator(require_watertight=True).validate(mesh)
        self.assertTrue(open_report.valid)
        self.assertFalse(open_report.watertight)
        self.assertFalse(closed_report.valid)
        self.assertIn("boundary_edges", {issue.code for issue in closed_report.issues})

    def test_reports_inconsistent_winding(self):
        mesh = TriangleMesh(
            vertices=((0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)),
            faces=((0, 1, 2), (1, 2, 3)),
        )
        report = MeshValidator().validate(mesh)

        self.assertFalse(report.valid)
        self.assertEqual(report.statistics.inconsistent_winding_edge_count, 1)

    def test_reports_bow_tie_nonmanifold_vertex(self):
        mesh = TriangleMesh(
            vertices=(
                (0, 0, 0),
                (1, 0, 0),
                (0, 1, 0),
                (-1, 0, 0),
                (0, -1, 0),
            ),
            faces=((0, 1, 2), (0, 3, 4)),
        )
        report = MeshValidator().validate(mesh)

        self.assertFalse(report.valid)
        self.assertEqual(report.statistics.nonmanifold_edge_count, 0)
        self.assertEqual(report.statistics.nonmanifold_vertex_count, 1)


class MeshExporterTests(unittest.TestCase):
    def test_obj_contains_indexed_vertices_normals_and_faces(self):
        stream = StringIO()
        write_obj_stream(tetrahedron(), stream, "test mesh")
        lines = stream.getvalue().splitlines()

        self.assertIn("o test_mesh", lines)
        self.assertEqual(sum(line.startswith("v ") for line in lines), 4)
        self.assertEqual(sum(line.startswith("vn ") for line in lines), 4)
        self.assertEqual(sum(line.startswith("f ") for line in lines), 4)
        self.assertIn("f 1//1 3//3 2//2", lines)

    def test_ply_header_and_record_counts_match_mesh(self):
        stream = StringIO()
        write_ply_stream(tetrahedron(), stream)
        output = stream.getvalue()

        self.assertTrue(output.startswith("ply\nformat ascii 1.0\n"))
        self.assertIn("element vertex 4\n", output)
        self.assertIn("element face 4\n", output)
        self.assertIn("property double nx\n", output)


if __name__ == "__main__":
    unittest.main()
