"""Focused tests for deterministic Noise Displacement."""

import math
import unittest

from core.mesh import TriangleMesh
from procedural import (
    DEFAULT_OPERATOR_REGISTRY,
    NoiseDisplacementOperator,
    OperatorPipeline,
    ProceduralInputGeometry,
    ProceduralRequest,
    SourceType,
    canonical_mesh_digest,
    vertex_normals,
)


def cube_mesh():
    vertices = (
        (3, 5, 7), (13, 5, 7), (13, 15, 7), (3, 15, 7),
        (3, 5, 17), (13, 5, 17), (13, 15, 17), (3, 15, 17),
    )
    faces = (
        (0, 2, 1), (0, 3, 2),
        (4, 5, 6), (4, 6, 7),
        (0, 1, 5), (0, 5, 4),
        (1, 2, 6), (1, 6, 5),
        (2, 3, 7), (2, 7, 6),
        (3, 0, 4), (3, 4, 7),
    )
    return TriangleMesh(vertices, faces)


def geometry(mesh=None):
    return ProceduralInputGeometry(
        SourceType.MESH_BODY,
        mesh or cube_mesh(),
        "Input Mesh",
        "mesh-token",
        provenance={"document": "Noise Test"},
    )


DEFAULTS = {
    "amplitude": 2.0,
    "scale": 20.0,
    "octaves": 3,
    "persistence": 0.5,
    "lacunarity": 2.0,
    "seed": 0,
}


def execute(parameters=None, mesh=None):
    values = dict(DEFAULTS)
    if parameters:
        values.update(parameters)
    request = ProceduralRequest(
        geometry(mesh), "noise_displacement", values
    )
    return OperatorPipeline(("noise_displacement",)).execute(request)


class VertexNormalTests(unittest.TestCase):
    def test_planar_normals_are_area_weighted_and_normalized(self):
        mesh = TriangleMesh(
            ((0, 0, 0), (2, 0, 0), (2, 1, 0), (0, 1, 0)),
            ((0, 1, 2), (0, 2, 3)),
        )
        self.assertEqual(
            vertex_normals(mesh),
            ((0, 0, 1), (0, 0, 1), (0, 0, 1), (0, 0, 1)),
        )

    def test_reversing_winding_reverses_planar_normals(self):
        forward = TriangleMesh(
            ((0, 0, 0), (1, 0, 0), (0, 1, 0)), ((0, 1, 2),)
        )
        reversed_mesh = TriangleMesh(
            forward.vertices, ((0, 2, 1),)
        )
        self.assertEqual(vertex_normals(forward)[0], (0, 0, 1))
        self.assertEqual(vertex_normals(reversed_mesh)[0], (0, 0, -1))

    def test_cube_normals_are_finite_and_unit_length(self):
        for normal in vertex_normals(cube_mesh()):
            self.assertTrue(all(math.isfinite(value) for value in normal))
            self.assertAlmostEqual(
                math.sqrt(sum(value * value for value in normal)), 1.0
            )

    def test_degenerate_only_mesh_fails_clearly(self):
        collinear = TriangleMesh(
            ((0, 0, 0), (1, 0, 0), (2, 0, 0)), ((0, 1, 2),)
        )
        with self.assertRaisesRegex(ValueError, "non-degenerate triangle"):
            vertex_normals(collinear)

    def test_isolated_vertex_uses_deterministic_finite_fallback(self):
        isolated = TriangleMesh(
            ((0, 0, 0), (1, 0, 0), (0, 1, 0), (8, 8, 8)),
            ((0, 1, 2),),
        )
        first = vertex_normals(isolated)
        second = vertex_normals(isolated)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 4)
        for normal in first:
            self.assertTrue(all(math.isfinite(value) for value in normal))
            self.assertAlmostEqual(
                math.sqrt(sum(value * value for value in normal)), 1.0
            )

    def test_cancelled_adjacent_normals_use_strongest_face_fallback(self):
        mesh = TriangleMesh(
            (
                (0, 0, 0), (1, 0, 0), (0, 1, 0),
                (0, -1, 0), (0, 0, 1),
            ),
            (
                (0, 1, 2),
                (0, 1, 3),
                (0, 4, 1),
            ),
        )
        normals = vertex_normals(mesh)
        self.assertEqual(len(normals), len(mesh.vertices))
        self.assertTrue(all(
            math.isfinite(value)
            for normal in normals
            for value in normal
        ))


class NoiseDisplacementTests(unittest.TestCase):
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

    def test_zero_amplitude_exactly_preserves_digest(self):
        result = execute({"amplitude": 0.0})
        self.assertEqual(result.output_digest, result.input_digest)
        self.assertEqual(result.mesh, cube_mesh())

    def test_each_shape_parameter_has_a_deterministic_effect(self):
        baseline = execute()
        alternatives = (
            execute({"amplitude": 5.0}),
            execute({"scale": 7.0}),
            execute({"octaves": 5}),
            execute({"persistence": 0.8}),
            execute({"lacunarity": 3.0}),
        )
        for result in alternatives:
            self.assertNotEqual(result.output_digest, baseline.output_digest)
        self.assertNotEqual(baseline.statistics.bounds, cube_mesh().statistics().bounds)

    def test_input_is_not_mutated(self):
        source = cube_mesh()
        digest = canonical_mesh_digest(source)
        execute(mesh=source)
        self.assertEqual(canonical_mesh_digest(source), digest)

    def test_topology_and_winding_are_preserved(self):
        source = cube_mesh()
        result = execute(mesh=source)
        before = source.statistics()
        after = result.statistics
        self.assertEqual(len(result.mesh.vertices), len(source.vertices))
        self.assertEqual(len(result.mesh.faces), len(source.faces))
        self.assertEqual(result.mesh.faces, source.faces)
        self.assertEqual(
            after.connected_component_count, before.connected_component_count
        )
        self.assertEqual(after.boundary_edge_count, 0)
        self.assertEqual(after.nonmanifold_edge_count, before.nonmanifold_edge_count)
        self.assertEqual(
            after.inconsistent_winding_edge_count,
            before.inconsistent_winding_edge_count,
        )

    def test_registry_contains_all_procedural_operators(self):
        self.assertEqual(
            tuple(item.operator_id for item in DEFAULT_OPERATOR_REGISTRY.list_all()),
            (
                "pass_through", "noise_displacement",
                "subdivision", "voronoi_surface", "gyroid_surface",
            ),
        )
        self.assertIsInstance(
            DEFAULT_OPERATOR_REGISTRY.get("noise_displacement"),
            NoiseDisplacementOperator,
        )

    def test_invalid_parameters_are_rejected(self):
        invalid = (
            ({"amplitude": -0.1}, "Amplitude"),
            ({"amplitude": 51.0}, "Amplitude"),
            ({"scale": 0.0}, "Scale"),
            ({"octaves": 0}, "Octaves"),
            ({"octaves": 7}, "Octaves"),
            ({"persistence": -0.1}, "Persistence"),
            ({"persistence": 1.1}, "Persistence"),
            ({"lacunarity": 1.0}, "Lacunarity"),
            ({"lacunarity": 4.1}, "Lacunarity"),
            ({"seed": 1.5}, "Seed"),
        )
        for values, message in invalid:
            with self.subTest(values=values):
                with self.assertRaisesRegex((TypeError, ValueError), message):
                    execute(values)
