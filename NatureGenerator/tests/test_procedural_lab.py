"""Focused tests for the Fusion-independent Procedural Lab foundation."""

from dataclasses import FrozenInstanceError
import unittest

from core.mesh import TriangleMesh
from procedural import (
    DEFAULT_OPERATOR_REGISTRY,
    ExecutionContext,
    OperatorPipeline,
    PassThroughOperator,
    ProceduralInputGeometry,
    ProceduralOperatorRegistry,
    ProceduralRequest,
    SourceType,
    UnknownOperatorError,
    canonical_mesh_digest,
)


def tetrahedron():
    return TriangleMesh(
        (
            (0, 0, 0),
            (1, 0, 0),
            (0, 1, 0),
            (0, 0, 1),
        ),
        (
            (0, 2, 1),
            (0, 1, 3),
            (1, 2, 3),
            (2, 0, 3),
        ),
    )


def input_geometry():
    return ProceduralInputGeometry(
        SourceType.SOLID_BODY,
        tetrahedron(),
        "Source",
        "token-1",
        provenance={"document": "Example"},
    )


class ProceduralContractTests(unittest.TestCase):
    def test_models_and_mappings_are_immutable(self):
        geometry = input_geometry()
        request = ProceduralRequest(
            geometry, "pass_through", {}, ExecutionContext.PREVIEW
        )
        with self.assertRaises(FrozenInstanceError):
            request.operator_id = "other"
        with self.assertRaises(TypeError):
            request.operator_parameters["value"] = 1
        with self.assertRaises(TypeError):
            geometry.provenance["value"] = 1

    def test_input_validates_bounds_and_non_empty_mesh(self):
        with self.assertRaisesRegex(ValueError, "non-empty"):
            ProceduralInputGeometry(
                SourceType.MESH_BODY,
                TriangleMesh((), ()),
                "Empty",
                "token",
            )
        with self.assertRaisesRegex(ValueError, "bounds"):
            ProceduralInputGeometry(
                SourceType.MESH_BODY,
                tetrahedron(),
                "Body",
                "token",
                ((0, 0, 0), (99, 99, 99)),
            )

    def test_registry_is_unique_and_rejects_unknown_operator(self):
        with self.assertRaisesRegex(ValueError, "duplicate operator id"):
            ProceduralOperatorRegistry(
                (PassThroughOperator(), PassThroughOperator())
            )
        with self.assertRaises(UnknownOperatorError):
            DEFAULT_OPERATOR_REGISTRY.get("gyroid")
        self.assertEqual(
            [item.operator_id for item in DEFAULT_OPERATOR_REGISTRY.list_all()],
            [
                "pass_through", "noise_displacement",
                "subdivision", "voronoi_surface",
            ],
        )

    def test_parameter_validation_rejects_unknown_values(self):
        request = ProceduralRequest(
            input_geometry(), "pass_through", {"strength": 1.0}
        )
        with self.assertRaisesRegex(ValueError, "unknown operator parameters"):
            PassThroughOperator().execute(request)


class PassThroughTests(unittest.TestCase):
    def test_preserves_digest_winding_bounds_topology_units_and_provenance(self):
        source = input_geometry()
        request = ProceduralRequest(
            source, "pass_through", {}, ExecutionContext.FINAL
        )
        first = OperatorPipeline(("pass_through",)).execute(request)
        second = OperatorPipeline(("pass_through",)).execute(request)

        self.assertIsNot(first, second)
        self.assertIsNot(first.mesh, source.mesh)
        self.assertEqual(first.mesh.vertices, source.mesh.vertices)
        self.assertEqual(first.mesh.faces, source.mesh.faces)
        self.assertEqual(first.output_digest, source.digest)
        self.assertEqual(first.input_digest, first.output_digest)
        self.assertEqual(first.output_digest, second.output_digest)
        self.assertEqual(first.statistics, source.mesh.statistics())
        self.assertEqual(first.statistics.bounds, source.bounds)
        self.assertTrue(first.statistics.is_watertight)
        self.assertTrue(first.statistics.is_manifold)
        self.assertEqual(first.units, source.units)
        self.assertEqual(first.source_provenance["document"], "Example")
        self.assertEqual(source.mesh, tetrahedron())

    def test_pipeline_order_is_an_immutable_future_compatible_tuple(self):
        pipeline = OperatorPipeline(("pass_through",))
        self.assertEqual(pipeline.operator_ids, ("pass_through",))
        with self.assertRaisesRegex(ValueError, "exactly one"):
            OperatorPipeline(("pass_through", "pass_through"))

    def test_pipeline_has_no_hidden_result_state(self):
        pipeline = OperatorPipeline(("pass_through",))
        request = ProceduralRequest(input_geometry(), "pass_through")
        self.assertIsNot(pipeline.execute(request), pipeline.execute(request))

    def test_digest_is_canonical_for_indexed_mesh(self):
        self.assertEqual(
            canonical_mesh_digest(tetrahedron()),
            canonical_mesh_digest(TriangleMesh(
                tetrahedron().vertices, tetrahedron().faces
            )),
        )
