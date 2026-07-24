"""Focused tests for deterministic Voronoi Surface deformation."""

import math
import unittest

from core.mesh import TriangleMesh
from procedural import (
    DEFAULT_OPERATOR_REGISTRY,
    OperatorPipeline,
    ProceduralInputGeometry,
    ProceduralRequest,
    SourceType,
    VoronoiSurfaceOperator,
    boundary_mask,
    canonical_mesh_digest,
    lattice_site,
    nearest_site_distances,
    vertex_normals,
)


DEFAULTS = {
    "cell_size": 20.0,
    "depth": 2.0,
    "edge_width": 3.0,
    "falloff": 2.0,
    "jitter": 0.75,
    "seed": 0,
}


def grid_mesh(size=7, spacing=5.0):
    vertices = tuple(
        (x * spacing + 1.25, y * spacing + 2.5, 0.0)
        for y in range(size)
        for x in range(size)
    )
    faces = []
    for y in range(size - 1):
        for x in range(size - 1):
            a = y * size + x
            faces.extend(((a, a + 1, a + size + 1), (a, a + size + 1, a + size)))
    return TriangleMesh(vertices, tuple(faces))


def cube_mesh():
    return TriangleMesh(
        (
            (3, 5, 7), (13, 5, 7), (13, 15, 7), (3, 15, 7),
            (3, 5, 17), (13, 5, 17), (13, 15, 17), (3, 15, 17),
        ),
        (
            (0, 2, 1), (0, 3, 2),
            (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4),
            (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6),
            (3, 0, 4), (3, 4, 7),
        ),
    )


def geometry(mesh=None):
    return ProceduralInputGeometry(
        SourceType.MESH_BODY,
        mesh or grid_mesh(),
        "Voronoi Source",
        "voronoi-source",
        provenance={"document": "Voronoi Test"},
    )


def execute(parameters=None, mesh=None):
    values = dict(DEFAULTS)
    if parameters:
        values.update(parameters)
    request = ProceduralRequest(
        geometry(mesh), "voronoi_surface", values
    )
    return OperatorPipeline(("voronoi_surface",)).execute(request)


class VoronoiPrimitiveTests(unittest.TestCase):
    def test_site_generation_is_deterministic_and_jitter_is_bounded(self):
        first = lattice_site((2, -1, 4), 20.0, 0.75, 50)
        second = lattice_site((2, -1, 4), 20.0, 0.75, 50)
        self.assertEqual(first, second)
        for axis, coordinate in enumerate(first):
            cell_index = (2, -1, 4)[axis]
            self.assertGreaterEqual(coordinate, cell_index * 20.0)
            self.assertLessEqual(coordinate, (cell_index + 1) * 20.0)
        self.assertEqual(
            lattice_site((2, -1, 4), 20.0, 0.0, 50),
            (50.0, -10.0, 90.0),
        )

    def test_nearest_distances_are_finite_and_ordered(self):
        nearest, second = nearest_site_distances(
            (12.3, -4.5, 8.9), 20.0, 0.75, 100
        )
        self.assertTrue(math.isfinite(nearest))
        self.assertTrue(math.isfinite(second))
        self.assertLessEqual(nearest, second)

    def test_local_search_matches_wider_brute_force_reference(self):
        for point in (
            (-31.2, 7.3, 19.8),
            (0.0, 0.0, 0.0),
            (18.4, 22.7, -5.1),
            (81.9, -44.2, 12.6),
        ):
            for jitter in (0.0, 0.75, 1.0):
                with self.subTest(point=point, jitter=jitter):
                    local = nearest_site_distances(
                        point, 20.0, jitter, 50, search_radius=1
                    )
                    reference = nearest_site_distances(
                        point, 20.0, jitter, 50, search_radius=4
                    )
                    self.assertAlmostEqual(local[0], reference[0])
                    self.assertAlmostEqual(local[1], reference[1])

    def test_boundary_mask_is_strong_at_boundaries_and_weak_inside_cells(self):
        self.assertEqual(boundary_mask(0.0, 3.0, 2.0), 1.0)
        self.assertEqual(boundary_mask(3.0, 3.0, 2.0), 0.0)
        self.assertGreater(
            boundary_mask(0.5, 3.0, 2.0),
            boundary_mask(2.0, 3.0, 2.0),
        )


class VoronoiSurfaceOperatorTests(unittest.TestCase):
    def test_registry_contains_voronoi_surface(self):
        operator = DEFAULT_OPERATOR_REGISTRY.get("voronoi_surface")
        self.assertIsInstance(operator, VoronoiSurfaceOperator)
        self.assertEqual(operator.display_name, "Voronoi Surface")
        self.assertEqual(
            tuple(item.parameter_id for item in operator.parameter_definitions),
            (
                "cell_size", "depth", "edge_width",
                "falloff", "jitter", "seed",
            ),
        )

    def test_same_input_is_deterministic_without_hidden_state(self):
        first = execute()
        second = execute()
        self.assertIsNot(first, second)
        self.assertEqual(first.output_digest, second.output_digest)
        self.assertEqual(first.mesh, second.mesh)

    def test_different_seed_changes_geometry(self):
        self.assertNotEqual(
            execute({"seed": 1}).output_digest,
            execute({"seed": 50}).output_digest,
        )

    def test_depth_zero_exactly_preserves_input_digest(self):
        source = grid_mesh()
        result = execute({"depth": 0.0}, source)
        self.assertEqual(result.input_digest, result.output_digest)
        self.assertEqual(result.mesh, source)

    def test_positive_and_negative_depth_move_in_opposite_directions(self):
        source = grid_mesh()
        normals = vertex_normals(source)
        positive = execute({"depth": 4.0}, source).mesh
        negative = execute({"depth": -4.0}, source).mesh
        moved = 0
        for index, position in enumerate(source.vertices):
            positive_delta = tuple(
                positive.vertices[index][axis] - position[axis]
                for axis in range(3)
            )
            negative_delta = tuple(
                negative.vertices[index][axis] - position[axis]
                for axis in range(3)
            )
            positive_projection = sum(
                positive_delta[axis] * normals[index][axis]
                for axis in range(3)
            )
            negative_projection = sum(
                negative_delta[axis] * normals[index][axis]
                for axis in range(3)
            )
            self.assertAlmostEqual(positive_projection, -negative_projection)
            if positive_projection > 0:
                moved += 1
        self.assertGreater(moved, 0)

    def test_each_pattern_parameter_changes_output(self):
        baseline = execute()
        alternatives = (
            execute({"cell_size": 10.0}),
            execute({"edge_width": 7.0}),
            execute({"falloff": 5.0}),
            execute({"jitter": 0.0}),
            execute({"jitter": 1.0}),
        )
        for result in alternatives:
            self.assertNotEqual(result.output_digest, baseline.output_digest)

    def test_reordered_vertices_receive_same_object_space_pattern(self):
        source = grid_mesh(size=4)
        order = tuple(reversed(range(len(source.vertices))))
        old_to_new = {old: new for new, old in enumerate(order)}
        reordered = TriangleMesh(
            tuple(source.vertices[old] for old in order),
            tuple(
                tuple(old_to_new[index] for index in face)
                for face in source.faces
            ),
        )
        original_result = execute(mesh=source).mesh
        reordered_result = execute(mesh=reordered).mesh
        original_by_position = dict(zip(source.vertices, original_result.vertices))
        reordered_by_position = dict(
            zip(reordered.vertices, reordered_result.vertices)
        )
        self.assertEqual(original_by_position, reordered_by_position)

    def test_topology_winding_units_and_provenance_are_preserved(self):
        source = cube_mesh()
        before = source.statistics()
        result = execute(mesh=source)
        after = result.statistics
        self.assertEqual(len(result.mesh.vertices), len(source.vertices))
        self.assertEqual(result.mesh.faces, source.faces)
        self.assertEqual(
            after.connected_component_count, before.connected_component_count
        )
        self.assertEqual(after.boundary_edge_count, 0)
        self.assertEqual(
            after.nonmanifold_edge_count, before.nonmanifold_edge_count
        )
        self.assertEqual(
            after.inconsistent_winding_edge_count,
            before.inconsistent_winding_edge_count,
        )
        self.assertEqual(result.units, "mm")
        self.assertEqual(result.source_provenance["document"], "Voronoi Test")

    def test_open_input_remains_open_and_input_is_not_mutated(self):
        source = grid_mesh()
        digest = canonical_mesh_digest(source)
        result = execute(mesh=source)
        self.assertGreater(result.statistics.boundary_edge_count, 0)
        self.assertEqual(result.mesh.faces, source.faces)
        self.assertEqual(canonical_mesh_digest(source), digest)

    def test_invalid_parameters_are_rejected(self):
        invalid = (
            ({"cell_size": 0.9}, "Cell Size"),
            ({"cell_size": 501.0}, "Cell Size"),
            ({"depth": -20.1}, "Depth"),
            ({"depth": 20.1}, "Depth"),
            ({"edge_width": 0.0}, "Edge Width"),
            ({"edge_width": 51.0}, "Edge Width"),
            ({"falloff": 0.2}, "Falloff"),
            ({"falloff": 8.1}, "Falloff"),
            ({"jitter": -0.1}, "Jitter"),
            ({"jitter": 1.1}, "Jitter"),
            ({"seed": 1.5}, "Seed"),
        )
        for values, message in invalid:
            with self.subTest(values=values):
                with self.assertRaisesRegex((TypeError, ValueError), message):
                    execute(values)
