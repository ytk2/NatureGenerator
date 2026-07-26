"""Focused tests for deterministic rectangular-domain boundary closure."""

import math
import unittest

from core.marching_tetrahedra import extract_isosurface
from core.mesh import TriangleMesh
from core.voxel_grid import VoxelGrid
from volume import (
    BoundaryClosureError,
    BoundaryMode,
    GyroidVolumeField,
    GyroidVolumeRequest,
    VolumeExecutionContext,
    boundary_paths,
    boundary_tolerance,
    canonical_volume_mesh_digest,
    classify_boundary_edges,
    close_rectangular_boundary,
    generate_gyroid_volume,
    validate_cap_complexity,
)


def focused_request(mode=BoundaryMode.OPEN, **overrides):
    values = {
        "resolution_x": 16,
        "resolution_y": 16,
        "resolution_z": 16,
        "boundary_mode": mode,
    }
    values.update(overrides)
    return GyroidVolumeRequest(**values)


def open_fixture(request=None):
    request = request or focused_request()
    field = GyroidVolumeField(
        request.period, request.phase_x, request.phase_y, request.phase_z
    )
    grid = VoxelGrid.sample(
        field, request.minimum, request.maximum, request.resolution
    )
    mesh = extract_isosurface(grid, request.iso_value)
    return grid, mesh


class OpenBoundaryRegressionTests(unittest.TestCase):
    def test_sprint_34_open_geometry_digest_and_boundary_are_unchanged(self):
        result = generate_gyroid_volume(focused_request())
        self.assertEqual(
            result.digest,
            "2a762f15dcc93985901ac77d926357ef0b9d0b697137474bd30216c76992a0ba",
        )
        self.assertEqual(result.statistics.boundary_edge_count, 1296)
        self.assertFalse(result.statistics.is_watertight)
        self.assertEqual(result.boundary_behavior, "open_at_bounds")

    def test_sprint_34_true_default_digest_is_unchanged(self):
        result = generate_gyroid_volume(GyroidVolumeRequest())
        self.assertEqual(
            result.digest,
            "997b710b2675435be9e3c1a15a2bdc5bf4b9938e0cfedfe94e01d867acb67f56",
        )


class CappedBoundaryGeometryTests(unittest.TestCase):
    def test_default_cap_is_deterministic_watertight_and_manifold(self):
        request = focused_request(BoundaryMode.CAP)
        first = generate_gyroid_volume(request)
        second = generate_gyroid_volume(request)
        statistics = first.statistics
        self.assertEqual(first.mesh, second.mesh)
        self.assertEqual(first.digest, second.digest)
        self.assertEqual(
            first.digest,
            "34279fdbf2842833b4a304de85e809c89890be317cf121216c79be764ea40834",
        )
        self.assertEqual(statistics.boundary_edge_count, 0)
        self.assertEqual(statistics.nonmanifold_edge_count, 0)
        self.assertEqual(statistics.inconsistent_winding_edge_count, 0)
        self.assertEqual(statistics.degenerate_face_count, 0)
        self.assertTrue(statistics.is_manifold)
        self.assertTrue(statistics.is_watertight)
        self.assertTrue(math.isfinite(statistics.signed_volume))
        self.assertGreater(statistics.signed_volume, 0.0)
        self.assertEqual(
            statistics.bounds,
            ((-30.0, -30.0, -30.0), (30.0, 30.0, 30.0)),
        )
        self.assertEqual(first.boundary_behavior, "capped_at_bounds")

    def test_closure_does_not_mutate_grid_or_open_mesh(self):
        grid, mesh = open_fixture()
        vertices = mesh.vertices
        faces = mesh.faces
        values = grid.values
        closed = close_rectangular_boundary(mesh, grid, 0.0)
        self.assertEqual(mesh.vertices, vertices)
        self.assertEqual(mesh.faces, faces)
        self.assertEqual(grid.values, values)
        self.assertNotEqual(closed.faces, faces)

    def test_caps_exist_with_outward_winding_on_all_six_planes(self):
        grid, mesh = open_fixture()
        closed = close_rectangular_boundary(mesh, grid, 0.0)
        new_faces = closed.faces[len(mesh.faces):]
        planes = (
            (0, -30.0, -1.0), (0, 30.0, 1.0),
            (1, -30.0, -1.0), (1, 30.0, 1.0),
            (2, -30.0, -1.0), (2, 30.0, 1.0),
        )
        for axis, coordinate, direction in planes:
            matching = [
                face for face in new_faces
                if all(
                    abs(closed.vertices[index][axis] - coordinate) < 1e-8
                    for index in face
                )
            ]
            self.assertGreater(len(matching), 0)
            for face in matching:
                face_index = closed.faces.index(face)
                normal = closed.face_normal(face_index)
                self.assertGreater(normal[axis] * direction, 0.999999)

    def test_anisotropic_non_cubic_closure_uses_spacing_tolerance(self):
        request = focused_request(
            BoundaryMode.CAP,
            width=45.0,
            depth=70.0,
            height=35.0,
            resolution_x=13,
            resolution_y=18,
            resolution_z=11,
            phase_x=0.31,
            phase_y=-0.17,
            phase_z=0.23,
        )
        grid, _ = open_fixture(request)
        self.assertAlmostEqual(
            boundary_tolerance(grid), min(grid.spacing) * 1e-7
        )
        result = generate_gyroid_volume(request)
        self.assertTrue(result.statistics.is_watertight)
        self.assertEqual(result.statistics.boundary_edge_count, 0)
        self.assertEqual(
            result.statistics.bounds,
            ((-22.5, -35.0, -17.5), (22.5, 35.0, 17.5)),
        )

    def test_nested_face_loops_are_preserved_as_a_hole(self):
        def annular_field(x, y, z):
            radius_squared = y * y + z * z
            return (radius_squared - 0.45) * (radius_squared - 1.7)

        grid = VoxelGrid.sample(
            annular_field, (-2, -2, -2), (2, 2, 2), (18, 24, 24)
        )
        opened = extract_isosurface(grid, 0.0)
        classified = classify_boundary_edges(
            opened, (-2, -2, -2), (2, 2, 2),
            boundary_tolerance(grid),
        )
        self.assertGreaterEqual(len(classified["x_min"]), 2)
        closed = close_rectangular_boundary(opened, grid, 0.0)
        self.assertTrue(closed.statistics().is_watertight)
        self.assertEqual(closed.statistics().boundary_edge_count, 0)


class BoundaryContourValidationTests(unittest.TestCase):
    def setUp(self):
        self.minimum = (-1.0, -1.0, -1.0)
        self.maximum = (1.0, 1.0, 1.0)
        self.plane = ("x_min", 0, -1.0)
        self.tolerance = 1e-8

    def test_multiple_loops_on_one_plane_are_ordered_deterministically(self):
        mesh = TriangleMesh(
            (
                (-1, -0.9, -0.9), (-1, -0.4, -0.9),
                (-1, -0.4, -0.4), (-1, -0.9, -0.4),
                (-1, 0.4, 0.4), (-1, 0.9, 0.4),
                (-1, 0.9, 0.9), (-1, 0.4, 0.9),
            ),
            (),
        )
        edges = (
            (0, 1), (1, 2), (2, 3), (3, 0),
            (4, 5), (5, 6), (6, 7), (7, 4),
        )
        first = boundary_paths(
            mesh, edges, self.plane, self.minimum, self.maximum,
            self.tolerance,
        )
        second = boundary_paths(
            mesh, tuple(reversed(edges)), self.plane,
            self.minimum, self.maximum, self.tolerance,
        )
        self.assertEqual(first, second)
        self.assertEqual(len(first), 2)

    def test_malformed_open_chain_away_from_box_edge_is_rejected(self):
        mesh = TriangleMesh(
            ((-1, -0.5, 0), (-1, 0, 0.5), (-1, 0.5, 0)), ()
        )
        with self.assertRaisesRegex(
            BoundaryClosureError, "open endpoint"
        ):
            boundary_paths(
                mesh, ((0, 1), (1, 2)), self.plane,
                self.minimum, self.maximum, self.tolerance,
            )

    def test_self_intersecting_loop_is_rejected(self):
        mesh = TriangleMesh(
            (
                (-1, -0.8, -0.8), (-1, 0.8, 0.8),
                (-1, -0.8, 0.8), (-1, 0.8, -0.8),
            ),
            (),
        )
        with self.assertRaisesRegex(
            BoundaryClosureError, "self-intersect"
        ):
            boundary_paths(
                mesh,
                ((0, 1), (1, 2), (2, 3), (3, 0)),
                self.plane,
                self.minimum,
                self.maximum,
                self.tolerance,
            )

    def test_cap_complexity_policy_is_deterministic(self):
        first = validate_cap_complexity(
            40, 50, 60, VolumeExecutionContext.PREVIEW
        )
        second = validate_cap_complexity(
            40, 50, 60, VolumeExecutionContext.PREVIEW
        )
        self.assertEqual(first, second)
        self.assertIsInstance(first, int)
