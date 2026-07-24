"""Focused tests for deterministic midpoint Subdivision."""

import unittest
from unittest.mock import patch

from core.mesh import TriangleMesh
from fusion.procedural_preview import ProceduralPreviewController
from procedural import (
    DEFAULT_OPERATOR_REGISTRY,
    ExecutionContext,
    OperatorInvocation,
    OperatorPipeline,
    ProceduralInputGeometry,
    ProceduralRequest,
    ProceduralStackRequest,
    SUBDIVISION_APPLY_MAX_FACES,
    SUBDIVISION_PREVIEW_MAX_FACES,
    SourceType,
    SubdivisionFaceLimitError,
    SubdivisionOperator,
    canonical_mesh_digest,
    enforce_subdivision_face_limit,
    estimate_subdivision_faces,
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


def execute(level=1, mesh=None, context=ExecutionContext.FINAL):
    request = ProceduralRequest(
        geometry(mesh), "subdivision", {"level": level}, context
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

    def test_levels_four_and_five_execute_on_small_fixture(self):
        source = TriangleMesh(
            ((0, 0, 0), (2, 0, 0), (0, 2, 0)), ((0, 1, 2),)
        )
        level_four = subdivide(source, 4)
        level_five = subdivide(source, 5)
        self.assertEqual(len(level_four.faces), 256)
        self.assertEqual(len(level_five.faces), 1024)

    def test_levels_one_to_three_digests_are_unchanged(self):
        expected = {
            1: "15f095aea072057e05b11fe6e821363c3f3a2495afef966b962d8fa0f36f3db2",
            2: "1aba4b30db935af0058b49b603e9d9b039ef5c751ed7af550efcf69c86793233",
            3: "d462d1f545c462cdf9e7069cc6e2f306f422ba31d940e77e48899fe541b49a13",
        }
        for level, digest in expected.items():
            with self.subTest(level=level):
                self.assertEqual(
                    canonical_mesh_digest(subdivide(cube_mesh(), level)),
                    digest,
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
        definition = operator.parameter_definitions[0]
        self.assertEqual(definition.default_value, 1)
        self.assertEqual(definition.minimum, 1)
        self.assertEqual(definition.maximum, 5)

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

    def test_operator_rejects_levels_outside_supported_range(self):
        for level in (0, 6):
            with self.subTest(level=level):
                with self.assertRaisesRegex(ValueError, "Subdivision Level"):
                    execute(level)
        with self.assertRaisesRegex(TypeError, "Subdivision Level"):
            execute(1.5)


class SubdivisionSafetyPolicyTests(unittest.TestCase):
    def test_exact_face_count_prediction_uses_integer_arithmetic(self):
        self.assertEqual(estimate_subdivision_faces(12, 1), 48)
        self.assertEqual(estimate_subdivision_faces(12, 4), 3072)
        self.assertEqual(estimate_subdivision_faces(12, 5), 12288)
        self.assertIsInstance(estimate_subdivision_faces(12, 5), int)

    def test_preview_limit_accepts_boundary_and_rejects_next_face(self):
        self.assertEqual(
            enforce_subdivision_face_limit(
                500_000, 5, ExecutionContext.PREVIEW
            ),
            SUBDIVISION_PREVIEW_MAX_FACES,
        )
        with self.assertRaisesRegex(
            SubdivisionFaceLimitError,
            "500,001 faces.*Preview limit of 500,000",
        ):
            enforce_subdivision_face_limit(
                500_001, 5, ExecutionContext.PREVIEW
            )

    def test_apply_limit_accepts_boundary_and_rejects_next_face(self):
        self.assertEqual(
            enforce_subdivision_face_limit(
                1_000_000, 5, ExecutionContext.FINAL
            ),
            SUBDIVISION_APPLY_MAX_FACES,
        )
        with self.assertRaisesRegex(
            SubdivisionFaceLimitError,
            "1,000,001 faces.*Apply limit of 1,000,000",
        ):
            enforce_subdivision_face_limit(
                1_000_001, 5, ExecutionContext.FINAL
            )

    def test_rejection_happens_before_subdivision_and_preserves_source(self):
        base = cube_mesh()
        source = TriangleMesh(base.vertices, base.faces * 41)
        digest = canonical_mesh_digest(source)
        with patch(
            "procedural.operators.subdivide"
        ) as subdivision_kernel:
            with self.assertRaisesRegex(
                SubdivisionFaceLimitError, "Preview limit"
            ):
                execute(
                    5,
                    source,
                    ExecutionContext.PREVIEW,
                )
            subdivision_kernel.assert_not_called()
        self.assertEqual(canonical_mesh_digest(source), digest)

    def test_rejection_removes_existing_preview_and_leaves_no_partial_body(self):
        controller = ProceduralPreviewController()
        previous = type(
            "Body", (), {"isValid": True, "deleted": False}
        )()
        previous.deleteMe = lambda: setattr(previous, "deleted", True)
        controller.replace(lambda: previous)

        def rejected_creation():
            enforce_subdivision_face_limit(
                500_001, 5, ExecutionContext.PREVIEW
            )

        with self.assertRaises(SubdivisionFaceLimitError):
            controller.replace(rejected_creation)
        self.assertTrue(previous.deleted)
        self.assertIsNone(controller.body)

    def test_prediction_uses_mesh_entering_later_stack_slot(self):
        request = ProceduralStackRequest(
            geometry(),
            (
                OperatorInvocation("subdivision", {"level": 1}),
                OperatorInvocation("subdivision", {"level": 4}),
            ),
        )
        result = OperatorPipeline(
            ("subdivision", "subdivision")
        ).execute_stack(request)
        self.assertEqual(len(result.mesh.faces), 12 * (4 ** 5))
        self.assertEqual(
            result.execution_metadata["predicted_face_count"],
            48 * (4 ** 4),
        )
