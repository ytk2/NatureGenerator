"""Tests for ordered three-slot Procedural Lab operator stacks."""

from dataclasses import FrozenInstanceError
import unittest

from commands.procedural_lab import execute_procedural_stack
from core.mesh import TriangleMesh
from fusion.procedural_preview import ProceduralPreviewController
from procedural import (
    ExecutionContext,
    OperatorInvocation,
    OperatorPipeline,
    ProceduralInputGeometry,
    ProceduralStackRequest,
    SourceType,
    canonical_mesh_digest,
)


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


def geometry():
    return ProceduralInputGeometry(
        SourceType.MESH_BODY,
        cube_mesh(),
        "Stack Source",
        "stack-source",
        provenance={"document": "Stack Test"},
    )


NOISE = {
    "amplitude": 2.0,
    "scale": 20.0,
    "octaves": 3,
    "persistence": 0.5,
    "lacunarity": 2.0,
    "seed": 7,
}

VORONOI = {
    "cell_size": 20.0,
    "depth": -1.5,
    "edge_width": 3.0,
    "falloff": 2.0,
    "jitter": 0.75,
    "seed": 11,
}


def execute(*invocations):
    request = ProceduralStackRequest(
        geometry(), tuple(invocations), ExecutionContext.FINAL
    )
    operator_ids = tuple(item.operator_id for item in invocations)
    return OperatorPipeline(operator_ids).execute_stack(request)


class OperatorStackContractTests(unittest.TestCase):
    def test_invocations_and_parameters_are_immutable_and_isolated(self):
        first = OperatorInvocation("noise_displacement", NOISE)
        second_values = dict(NOISE)
        second_values["seed"] = 50
        second = OperatorInvocation("noise_displacement", second_values)
        request = ProceduralStackRequest(geometry(), (first, second))

        self.assertEqual(request.invocations[0].operator_parameters["seed"], 7)
        self.assertEqual(request.invocations[1].operator_parameters["seed"], 50)
        with self.assertRaises(TypeError):
            first.operator_parameters["seed"] = 100
        with self.assertRaises(FrozenInstanceError):
            first.operator_id = "pass_through"

    def test_stack_requires_one_to_three_invocations(self):
        with self.assertRaisesRegex(ValueError, "one and three"):
            ProceduralStackRequest(geometry(), ())
        four = tuple(
            OperatorInvocation("pass_through") for _ in range(4)
        )
        with self.assertRaisesRegex(ValueError, "one and three"):
            ProceduralStackRequest(geometry(), four)

    def test_legacy_single_operator_execution_remains_compatible(self):
        invocation = OperatorInvocation("pass_through")
        result = execute(invocation)
        self.assertEqual(result.input_digest, result.output_digest)
        self.assertEqual(result.mesh, cube_mesh())
        self.assertEqual(result.execution_metadata["operator_count"], 1)


class OperatorStackExecutionTests(unittest.TestCase):
    def test_subdivision_then_noise_executes_top_to_bottom(self):
        result = execute(
            OperatorInvocation("subdivision", {"level": 1}),
            OperatorInvocation("noise_displacement", NOISE),
        )
        self.assertEqual(len(result.mesh.vertices), 26)
        self.assertEqual(len(result.mesh.faces), 48)
        self.assertEqual(
            result.execution_metadata["operator_stack"],
            "subdivision>noise_displacement",
        )

    def test_changing_operator_order_changes_result(self):
        subdivision_then_noise = execute(
            OperatorInvocation("subdivision", {"level": 1}),
            OperatorInvocation("noise_displacement", NOISE),
        )
        noise_then_subdivision = execute(
            OperatorInvocation("noise_displacement", NOISE),
            OperatorInvocation("subdivision", {"level": 1}),
        )
        self.assertNotEqual(
            subdivision_then_noise.output_digest,
            noise_then_subdivision.output_digest,
        )
        self.assertEqual(
            len(subdivision_then_noise.mesh.faces),
            len(noise_then_subdivision.mesh.faces),
        )

    def test_three_stage_mixed_chain_is_deterministic(self):
        invocations = (
            OperatorInvocation("subdivision", {"level": 1}),
            OperatorInvocation("voronoi_surface", VORONOI),
            OperatorInvocation("noise_displacement", NOISE),
        )
        first = execute(*invocations)
        second = execute(*invocations)
        self.assertEqual(first.output_digest, second.output_digest)
        self.assertEqual(first.mesh, second.mesh)
        self.assertEqual(first.execution_metadata["operator_count"], 3)
        self.assertEqual(
            first.execution_metadata["operator_stack"],
            "subdivision>voronoi_surface>noise_displacement",
        )

    def test_each_mixed_chain_produces_valid_distinct_output(self):
        chains = (
            (
                OperatorInvocation("subdivision", {"level": 1}),
                OperatorInvocation("voronoi_surface", VORONOI),
            ),
            (
                OperatorInvocation("voronoi_surface", VORONOI),
                OperatorInvocation("noise_displacement", NOISE),
            ),
            (
                OperatorInvocation("subdivision", {"level": 1}),
                OperatorInvocation("noise_displacement", NOISE),
            ),
        )
        digests = []
        for chain in chains:
            result = execute(*chain)
            self.assertTrue(result.statistics.is_watertight)
            self.assertEqual(result.statistics.boundary_edge_count, 0)
            digests.append(result.output_digest)
        self.assertEqual(len(set(digests)), len(digests))

    def test_stack_does_not_mutate_original_input(self):
        source = geometry()
        digest = canonical_mesh_digest(source.mesh)
        request = ProceduralStackRequest(
            source,
            (
                OperatorInvocation("subdivision", {"level": 1}),
                OperatorInvocation("noise_displacement", NOISE),
            ),
        )
        OperatorPipeline(
            ("subdivision", "noise_displacement")
        ).execute_stack(request)
        self.assertEqual(canonical_mesh_digest(source.mesh), digest)

    def test_application_command_inserts_only_final_stack_mesh(self):
        request = ProceduralStackRequest(
            geometry(),
            (
                OperatorInvocation("subdivision", {"level": 1}),
                OperatorInvocation("noise_displacement", NOISE),
            ),
        )
        inserted = []
        sentinel_body = object()
        result, body = execute_procedural_stack(
            request,
            lambda mesh, name: inserted.append((mesh, name)) or sentinel_body,
            "NatureGenerator Procedural — Operator Stack",
        )
        self.assertIs(body, sentinel_body)
        self.assertEqual(len(inserted), 1)
        self.assertIs(inserted[0][0], result.mesh)
        self.assertEqual(
            inserted[0][1], "NatureGenerator Procedural — Operator Stack"
        )

    def test_preview_replacement_is_unchanged_for_stack_output(self):
        controller = ProceduralPreviewController()
        first = type("Body", (), {"isValid": True, "deleted": False})()
        first.deleteMe = lambda: setattr(first, "deleted", True)
        second = type("Body", (), {"isValid": True, "deleted": False})()
        second.deleteMe = lambda: setattr(second, "deleted", True)
        controller.replace(lambda: first)
        controller.replace(lambda: second)
        self.assertTrue(first.deleted)
        self.assertIs(controller.body, second)
        controller.cleanup()
        self.assertTrue(second.deleted)
