"""Focused tests for deterministic midpoint Subdivision."""

import unittest

from core.mesh import TriangleMesh
from procedural import (
    DEFAULT_OPERATOR_REGISTRY,
    OperatorPipeline,
    ProceduralInputGeometry,
    ProceduralRequest,
    SourceType,
    SubdivisionOperator,
    canonical_mesh_digest,
    subdivide,
    subdivide_once,
)


def cube_mesh():
    return TriangleMesh(
        (
            (0, 0, 0), (10, 0, 0), (10, 10, 0), (0, 10, 0),
            (0, 0, 10), (10, 0, 10), (10, 10, 10), (0, 10, 10),
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
        mesh or cube_mesh(),
        "Subdivision Source",
        "subdivision-source",
        provenance={"document": "Subdivision Test"},
    )


def execute(level=1, mesh=None):
    request = ProceduralRequest(
        geometry(mesh), "subdivision", {"level": level}
    )
    return OperatorPipeline(("subdivision",)).execute(request)


class MidpointKernelTests(unittest.TestCase):
    def test_one_triangle_becomes_four_with_shared_edge_midpoints(self):
        source = TriangleMesh(
            ((0, 0, 0), (2, 0, 0), (0, 2, 0)), ((0, 1, 2),)
        )
        result = subdivide_once(source)
        self.assertEqual(
            result.vertices,
            (
                (0, 0, 0), (2, 0, 0), (0, 2, 0),
                (1, 0, 0), (1, 1, 0), (0, 1, 0),
            ),
        )
        self.assertEqual(
            result.faces,
            ((0, 3, 5), (3, 1, 4), (5, 4, 2), (3, 4, 5)),
        )

    def test_adjacent_triangles_reuse_one_midpoint_for_shared_edge(self):
        source = TriangleMesh(
            ((0, 0, 0), (2, 0, 0), (2, 2, 0), (0, 2, 0)),
            ((0, 1, 2), (0, 2, 3)),
        )
        result = subdivide_once(source)
        self.assertEqual(len(result.vertices), 9)
        shared = [
            index for index, vertex in enumerate(result.vertices)
            if vertex == (1, 1, 0)
        ]
        self.assertEqual(len(shared), 1)
        self.assertEqual(
            sum(shared[0] in face for face in result.faces), 6
        )

    def test_levels_are_iterative_and_deterministic(self):
        source = cube_mesh()
        for level, expected_vertices, expected_faces in (
            (1, 26, 48),
            (2, 98, 192),
            (3, 386, 768),
        ):
            with self.subTest(level=level):
                first = subdivide(source, level)
                second = subdivide(source, level)
                self.assertEqual(len(first.vertices), expected_vertices)
                self.assertEqual(len(first.faces), expected_faces)
                self.assertEqual(first, second)
                self.assertEqual(
                    canonical_mesh_digest(first),
                    canonical_mesh_digest(second),
                )

    def test_invalid_levels_are_rejected(self):
        for value in (True, 1.5, "1"):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    subdivide(cube_mesh(), value)
        with self.assertRaises(ValueError):
            subdivide(cube_mesh(), 0)


class SubdivisionOperatorTests(unittest.TestCase):
    def test_registry_contains_subdivision(self):
        operator = DEFAULT_OPERATOR_REGISTRY.get("subdivision")
        self.assertIsInstance(operator, SubdivisionOperator)
        self.assertEqual(operator.display_name, "Subdivision")
        self.assertEqual(
            tuple(item.parameter_id for item in operator.parameter_definitions),
            ("level",),
        )

    def test_operator_preserves_shape_topology_winding_units_and_provenance(self):
        source = cube_mesh()
        before = source.statistics()
        result = execute(2, source)
        after = result.statistics
        self.assertEqual(after.bounds, before.bounds)
        self.assertAlmostEqual(after.surface_area, before.surface_area)
        self.assertAlmostEqual(after.signed_volume, before.signed_volume)
        self.assertEqual(
            after.connected_component_count, before.connected_component_count
        )
        self.assertEqual(after.boundary_edge_count, before.boundary_edge_count)
        self.assertEqual(
            after.nonmanifold_edge_count, before.nonmanifold_edge_count
        )
        self.assertEqual(
            after.inconsistent_winding_edge_count,
            before.inconsistent_winding_edge_count,
        )
        self.assertTrue(after.is_manifold)
        self.assertTrue(after.is_watertight)
        self.assertEqual(result.units, "mm")
        self.assertEqual(result.source_provenance["document"], "Subdivision Test")
        self.assertEqual(result.execution_metadata["level"], 2)

    def test_disconnected_and_open_mesh_topology_is_preserved(self):
        mesh = TriangleMesh(
            (
                (0, 0, 0), (1, 0, 0), (0, 1, 0),
                (3, 0, 0), (4, 0, 0), (3, 1, 0),
            ),
            ((0, 1, 2), (3, 4, 5)),
        )
        before = mesh.statistics()
        after = execute(1, mesh).statistics
        self.assertEqual(after.connected_component_count, 2)
        self.assertEqual(after.connected_component_count, before.connected_component_count)
        self.assertEqual(after.boundary_edge_count, before.boundary_edge_count * 2)

    def test_input_is_not_mutated_and_result_has_no_hidden_state(self):
        source = cube_mesh()
        digest = canonical_mesh_digest(source)
        first = execute(1, source)
        second = execute(1, source)
        self.assertEqual(canonical_mesh_digest(source), digest)
        self.assertIsNot(first, second)
        self.assertEqual(first.output_digest, second.output_digest)

    def test_operator_rejects_levels_outside_sprint_30_range(self):
        for level in (0, 4):
            with self.subTest(level=level):
                with self.assertRaisesRegex(ValueError, "Subdivision Level"):
                    execute(level)
        with self.assertRaisesRegex(TypeError, "Subdivision Level"):
            execute(1.5)
