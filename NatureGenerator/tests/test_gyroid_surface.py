"""Focused tests for deterministic Gyroid Surface deformation."""

import unittest

from commands.procedural_lab import execute_procedural_stack
from core.mesh import TriangleMesh
from fusion.procedural_preview import ProceduralPreviewController
from procedural import (
    DEFAULT_OPERATOR_REGISTRY,
    GyroidSurfaceOperator,
    OperatorInvocation,
    OperatorPipeline,
    ProceduralInputGeometry,
    ProceduralRequest,
    ProceduralStackRequest,
    SourceType,
    canonical_mesh_digest,
    gyroid_field,
    gyroid_response,
    vertex_normals,
)


DEFAULTS = {
    "period": 20.0,
    "amplitude": 2.0,
    "threshold": 0.0,
    "band_width": 0.35,
    "phase_x": 0.0,
    "phase_y": 0.0,
    "phase_z": 0.0,
    "invert": False,
}

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
    "depth": 1.5,
    "edge_width": 3.0,
    "falloff": 2.0,
    "jitter": 0.75,
    "seed": 11,
}


def grid_mesh(size=9, spacing=3.5):
    vertices = tuple(
        (x * spacing + 0.75, y * spacing + 1.25, 2.0)
        for y in range(size)
        for x in range(size)
    )
    faces = []
    for y in range(size - 1):
        for x in range(size - 1):
            a = y * size + x
            faces.extend((
                (a, a + 1, a + size + 1),
                (a, a + size + 1, a + size),
            ))
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
        "Gyroid Source",
        "gyroid-source",
        provenance={"document": "Gyroid Test"},
    )


def execute(parameters=None, mesh=None):
    values = dict(DEFAULTS)
    if parameters:
        values.update(parameters)
    request = ProceduralRequest(
        geometry(mesh), "gyroid_surface", values
    )
    return OperatorPipeline(("gyroid_surface",)).execute(request)


def execute_stack(mesh, *invocations):
    request = ProceduralStackRequest(geometry(mesh), tuple(invocations))
    return OperatorPipeline(tuple(
        invocation.operator_id for invocation in invocations
    )).execute_stack(request)


class GyroidPrimitiveTests(unittest.TestCase):
    def test_field_matches_definition_and_is_periodic(self):
        position = (3.0, 7.0, 11.0)
        first = gyroid_field(position, 20.0)
        shifted = gyroid_field((23.0, 7.0, 11.0), 20.0)
        self.assertAlmostEqual(first, shifted)
        self.assertAlmostEqual(gyroid_field((0.0, 0.0, 0.0), 20.0), 0.0)

    def test_response_is_smooth_bounded_and_centered_on_threshold(self):
        self.assertEqual(gyroid_response(0.4, 0.4, 0.35), 1.0)
        self.assertEqual(gyroid_response(0.75, 0.4, 0.35), 0.0)
        self.assertEqual(gyroid_response(-1.0, 0.4, 0.35), 0.0)
        middle = gyroid_response(0.575, 0.4, 0.35)
        self.assertGreater(middle, 0.0)
        self.assertLess(middle, 1.0)


class GyroidSurfaceOperatorTests(unittest.TestCase):
    def test_registry_contains_gyroid_surface_and_parameters(self):
        operator = DEFAULT_OPERATOR_REGISTRY.get("gyroid_surface")
        self.assertIsInstance(operator, GyroidSurfaceOperator)
        self.assertEqual(operator.display_name, "Gyroid Surface")
        self.assertEqual(
            tuple(item.parameter_id for item in operator.parameter_definitions),
            tuple(DEFAULTS),
        )

    def test_same_input_is_deterministic_with_canonical_digest(self):
        first = execute()
        second = execute()
        self.assertEqual(first.mesh, second.mesh)
        self.assertEqual(first.output_digest, second.output_digest)
        self.assertEqual(
            first.output_digest,
            "46c987447bd0b9bc9bfc7b32c3851b38b46ac46e6bfd51ed9b667cd7c3ccbb69",
        )

    def test_amplitude_zero_is_exact_identity(self):
        source = grid_mesh()
        result = execute({"amplitude": 0.0}, source)
        self.assertEqual(result.mesh, source)
        self.assertEqual(result.input_digest, result.output_digest)

    def test_positive_and_negative_amplitudes_move_oppositely(self):
        source = grid_mesh()
        normals = vertex_normals(source)
        positive = execute({"amplitude": 4.0}, source).mesh
        negative = execute({"amplitude": -4.0}, source).mesh
        moved = 0
        for index, position in enumerate(source.vertices):
            positive_projection = sum(
                (positive.vertices[index][axis] - position[axis])
                * normals[index][axis]
                for axis in range(3)
            )
            negative_projection = sum(
                (negative.vertices[index][axis] - position[axis])
                * normals[index][axis]
                for axis in range(3)
            )
            self.assertAlmostEqual(positive_projection, -negative_projection)
            if positive_projection > 0.0:
                moved += 1
        self.assertGreater(moved, 0)

    def test_each_pattern_parameter_changes_output(self):
        baseline = execute().output_digest
        alternatives = (
            {"period": 11.0},
            {"threshold": 0.6},
            {"band_width": 0.8},
            {"phase_x": 0.7},
            {"phase_y": -0.9},
            {"phase_z": 1.1},
            {"invert": True},
        )
        for parameters in alternatives:
            with self.subTest(parameters=parameters):
                self.assertNotEqual(execute(parameters).output_digest, baseline)

    def test_invert_reverses_displacement_direction(self):
        source = grid_mesh()
        regular = execute(mesh=source).mesh
        inverted = execute({"invert": True}, source).mesh
        for index, position in enumerate(source.vertices):
            for axis in range(3):
                self.assertAlmostEqual(
                    regular.vertices[index][axis] - position[axis],
                    -(inverted.vertices[index][axis] - position[axis]),
                )

    def test_closed_topology_winding_units_and_provenance_are_preserved(self):
        source = cube_mesh()
        before = source.statistics()
        result = execute(mesh=source)
        after = result.statistics
        self.assertEqual(len(result.mesh.vertices), len(source.vertices))
        self.assertEqual(result.mesh.faces, source.faces)
        self.assertEqual(
            after.connected_component_count, before.connected_component_count
        )
        self.assertEqual(
            after.boundary_edge_count, before.boundary_edge_count
        )
        self.assertEqual(
            after.nonmanifold_edge_count, before.nonmanifold_edge_count
        )
        self.assertEqual(
            after.inconsistent_winding_edge_count,
            before.inconsistent_winding_edge_count,
        )
        self.assertEqual(result.units, "mm")
        self.assertEqual(result.source_provenance["document"], "Gyroid Test")

    def test_open_mesh_remains_open_and_source_is_immutable(self):
        source = grid_mesh()
        digest = canonical_mesh_digest(source)
        result = execute(mesh=source)
        self.assertGreater(result.statistics.boundary_edge_count, 0)
        self.assertEqual(result.mesh.faces, source.faces)
        self.assertEqual(canonical_mesh_digest(source), digest)

    def test_degenerate_triangle_is_ignored_when_usable_geometry_exists(self):
        source = TriangleMesh(
            (
                (0, 0, 0), (10, 0, 0), (0, 10, 0),
                (20, 0, 0), (30, 0, 0), (40, 0, 0),
            ),
            ((0, 1, 2), (3, 4, 5)),
        )
        result = execute(mesh=source)
        self.assertEqual(result.mesh.faces, source.faces)
        self.assertEqual(len(result.mesh.vertices), len(source.vertices))

    def test_input_with_no_usable_triangle_is_rejected(self):
        source = TriangleMesh(
            ((0, 0, 0), (10, 0, 0), (20, 0, 0)),
            ((0, 1, 2),),
        )
        with self.assertRaisesRegex(ValueError, "no usable"):
            execute(mesh=source)

    def test_invalid_parameters_are_rejected(self):
        invalid = (
            ({"period": 0.9}, "Period"),
            ({"period": 501.0}, "Period"),
            ({"amplitude": -50.1}, "Amplitude"),
            ({"amplitude": 50.1}, "Amplitude"),
            ({"threshold": -1.6}, "Threshold"),
            ({"threshold": 1.6}, "Threshold"),
            ({"band_width": 0.0}, "Band Width"),
            ({"phase_x": 6.284}, "Phase X"),
            ({"invert": 1}, "Invert"),
        )
        for values, message in invalid:
            with self.subTest(values=values):
                with self.assertRaisesRegex((TypeError, ValueError), message):
                    execute(values)


class GyroidStackAndLifecycleTests(unittest.TestCase):
    def test_level_four_subdivision_then_gyroid_is_deterministic(self):
        invocations = (
            OperatorInvocation("subdivision", {"level": 4}),
            OperatorInvocation("gyroid_surface", DEFAULTS),
        )
        first = execute_stack(cube_mesh(), *invocations)
        second = execute_stack(cube_mesh(), *invocations)
        self.assertEqual(len(first.mesh.faces), 3072)
        self.assertEqual(first.mesh, second.mesh)
        self.assertEqual(first.output_digest, second.output_digest)

    def test_gyroid_works_after_subdivision_and_before_noise(self):
        result = execute_stack(
            cube_mesh(),
            OperatorInvocation("subdivision", {"level": 1}),
            OperatorInvocation("gyroid_surface", DEFAULTS),
            OperatorInvocation("noise_displacement", NOISE),
        )
        self.assertEqual(len(result.mesh.vertices), 26)
        self.assertEqual(len(result.mesh.faces), 48)
        self.assertEqual(
            result.execution_metadata["operator_stack"],
            "subdivision>gyroid_surface>noise_displacement",
        )

    def test_gyroid_and_noise_order_changes_output(self):
        source = grid_mesh()
        gyroid_noise = execute_stack(
            source,
            OperatorInvocation("gyroid_surface", DEFAULTS),
            OperatorInvocation("noise_displacement", NOISE),
        )
        noise_gyroid = execute_stack(
            source,
            OperatorInvocation("noise_displacement", NOISE),
            OperatorInvocation("gyroid_surface", DEFAULTS),
        )
        self.assertNotEqual(
            gyroid_noise.output_digest, noise_gyroid.output_digest
        )

    def test_gyroid_and_voronoi_work_in_both_orders(self):
        source = grid_mesh()
        gyroid_voronoi = execute_stack(
            source,
            OperatorInvocation("gyroid_surface", DEFAULTS),
            OperatorInvocation("voronoi_surface", VORONOI),
        )
        voronoi_gyroid = execute_stack(
            source,
            OperatorInvocation("voronoi_surface", VORONOI),
            OperatorInvocation("gyroid_surface", DEFAULTS),
        )
        self.assertNotEqual(
            gyroid_voronoi.output_digest, voronoi_gyroid.output_digest
        )

    def test_preview_and_apply_insert_only_final_mesh(self):
        request = ProceduralStackRequest(
            geometry(cube_mesh()),
            (
                OperatorInvocation("subdivision", {"level": 1}),
                OperatorInvocation("gyroid_surface", DEFAULTS),
            ),
        )
        inserted = []
        body = object()
        result, returned = execute_procedural_stack(
            request,
            lambda mesh, name: inserted.append((mesh, name)) or body,
            "Gyroid Stack",
        )
        self.assertIs(returned, body)
        self.assertEqual(inserted, [(result.mesh, "Gyroid Stack")])

        controller = ProceduralPreviewController()
        first = type("Body", (), {"isValid": True, "deleted": False})()
        first.deleteMe = lambda: setattr(first, "deleted", True)
        second = type("Body", (), {"isValid": True, "deleted": False})()
        second.deleteMe = lambda: setattr(second, "deleted", True)
        controller.replace(lambda: first)
        controller.replace(lambda: second)
        self.assertTrue(first.deleted)
        controller.cleanup()
        self.assertTrue(second.deleted)
