"""Focused tests for Classic Bone geometry and Family integration."""

from dataclasses import FrozenInstanceError
import hashlib
import math
import time
import unittest

from generators import GenerationRequest, GeneratorFactory
from generators.bone_families import (
    BoneFamilyDefinition,
    BoneFamilyRegistry,
    CLASSIC_BONE_FAMILY,
)
from generators.generator import InvalidGeneratorParameters


CLASSIC_BONE_DIGEST = (
    "cd9e140272b39890105e9b17ab50befaa62dd59d73f8dee91d7bfe174f995eb0"
)


def _generate(overrides=None, resolution=33, family_id="classic_bone"):
    return GeneratorFactory.generate_request(GenerationRequest(
        "bone", {} if overrides is None else overrides, resolution, family_id
    ))


def _cross_section_extent(mesh, center, width):
    points = [
        vertex for vertex in mesh.vertices
        if abs(vertex[0] - center) <= width / 2.0
    ]
    y_extent = max(point[1] for point in points) - min(point[1] for point in points)
    z_extent = max(point[2] for point in points) - min(point[2] for point in points)
    return math.sqrt(y_extent * z_extent)


class BoneFamilyTests(unittest.TestCase):
    def test_classic_definition_and_registry_are_immutable(self):
        self.assertIsInstance(CLASSIC_BONE_FAMILY, BoneFamilyDefinition)
        self.assertEqual(CLASSIC_BONE_FAMILY.family_id, "classic_bone")
        self.assertEqual(CLASSIC_BONE_FAMILY.display_name, "Classic Bone")
        self.assertIs(BoneFamilyRegistry.get("classic_bone"), CLASSIC_BONE_FAMILY)
        self.assertEqual(BoneFamilyRegistry.list_all(), (CLASSIC_BONE_FAMILY,))
        with self.assertRaises(TypeError):
            CLASSIC_BONE_FAMILY.parameter_values["seed"] = 9
        with self.assertRaises(FrozenInstanceError):
            CLASSIC_BONE_FAMILY.display_name = "Changed"
        with self.assertRaises(KeyError):
            BoneFamilyRegistry.get("missing_bone")

    def test_classic_family_contains_all_focused_parameters(self):
        self.assertEqual(
            tuple(CLASSIC_BONE_FAMILY.parameter_values),
            (
                "length", "shaft_radius", "end_scale", "curvature",
                "asymmetry", "surface_detail", "seed", "resolution",
            ),
        )


class ClassicBoneGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        started = time.perf_counter()
        cls.result = _generate()
        cls.elapsed = time.perf_counter() - started

    def test_digest_is_stable_and_legacy_request_is_identical(self):
        digest = hashlib.sha256(repr((
            self.result.mesh.vertices, self.result.mesh.faces
        )).encode("ascii")).hexdigest()
        self.assertEqual(digest, CLASSIC_BONE_DIGEST)
        legacy = _generate(family_id="")
        self.assertEqual(legacy.mesh.vertices, self.result.mesh.vertices)
        self.assertEqual(legacy.mesh.faces, self.result.mesh.faces)

    def test_topology_is_closed_manifold_and_manufacturable(self):
        statistics = self.result.statistics
        self.assertTrue(statistics.is_watertight)
        self.assertTrue(statistics.is_manifold)
        self.assertEqual(statistics.connected_component_count, 1)
        self.assertEqual(statistics.boundary_edge_count, 0)
        self.assertEqual(statistics.nonmanifold_edge_count, 0)
        self.assertEqual(statistics.nonmanifold_vertex_count, 0)
        self.assertEqual(statistics.degenerate_face_count, 0)
        self.assertEqual(statistics.inconsistent_winding_edge_count, 0)
        self.assertTrue(all(
            math.isfinite(value)
            for vertex in self.result.mesh.vertices for value in vertex
        ))

    def test_silhouette_is_elongated_with_enlarged_ends_and_narrow_middle(self):
        minimum, maximum = self.result.statistics.bounds
        x_span = maximum[0] - minimum[0]
        y_span = maximum[1] - minimum[1]
        self.assertGreater(x_span / y_span, 2.5)
        middle = _cross_section_extent(
            self.result.mesh, (minimum[0] + maximum[0]) / 2.0, x_span * 0.08
        )
        left = _cross_section_extent(
            self.result.mesh, minimum[0] + x_span * 0.10, x_span * 0.12
        )
        right = _cross_section_extent(
            self.result.mesh, maximum[0] - x_span * 0.10, x_span * 0.12
        )
        self.assertGreater(left, middle * 1.8)
        self.assertGreater(right, middle * 1.8)
        self.assertGreater(abs(left - right), 0.5)

    def test_curvature_and_grounding_are_non_empty(self):
        minimum, maximum = self.result.statistics.bounds
        x_mid = (minimum[0] + maximum[0]) / 2.0
        middle = [
            vertex for vertex in self.result.mesh.vertices
            if abs(vertex[0] - x_mid) < (maximum[0] - minimum[0]) * 0.04
        ]
        mean_y = sum(vertex[1] for vertex in middle) / len(middle)
        self.assertGreater(mean_y, 1.0)
        grounded = [
            vertex for vertex in self.result.mesh.vertices
            if abs(vertex[2] - minimum[2]) < 1e-9
        ]
        self.assertGreaterEqual(len(grounded), 8)

    def test_seed_is_deterministic_and_changes_geometry(self):
        repeated = _generate()
        changed = _generate({"seed": 8})
        self.assertEqual(repeated.mesh.vertices, self.result.mesh.vertices)
        self.assertEqual(repeated.mesh.faces, self.result.mesh.faces)
        self.assertNotEqual(changed.mesh.vertices, self.result.mesh.vertices)

    def test_preview_and_final_preserve_major_silhouette(self):
        preview = _generate(resolution=25)
        preview_bounds = preview.statistics.bounds
        final_bounds = self.result.statistics.bounds
        for axis in range(3):
            preview_span = preview_bounds[1][axis] - preview_bounds[0][axis]
            final_span = final_bounds[1][axis] - final_bounds[0][axis]
            self.assertAlmostEqual(preview_span / final_span, 1.0, delta=0.08)

    def test_generated_asset_defaults_and_identity(self):
        asset = self.result.asset
        self.assertIs(asset.mesh, self.result.mesh)
        self.assertEqual(asset.metadata.family_id, "classic_bone")
        self.assertEqual(asset.material.material_id, "natural_bone")
        self.assertEqual(asset.material.base_color, (0.82, 0.79, 0.68, 1.0))
        self.assertEqual(asset.material.metallic, 0.0)
        self.assertEqual(asset.mapping.mode.value, "object_space")
        self.assertEqual(asset.textures.resources, ())

    def test_default_generation_meets_local_performance_target(self):
        self.assertLess(self.elapsed, 3.0)

    def test_invalid_parameters_and_family_fail_clearly(self):
        for overrides in (
            {"length": 20.0},
            {"shaft_radius": 2.0},
            {"end_scale": 3.0},
            {"curvature": -0.1},
            {"asymmetry": 1.1},
            {"surface_detail": 0.5},
            {"seed": 1.5},
            {"unknown": 1},
        ):
            with self.assertRaises(InvalidGeneratorParameters):
                _generate(overrides)
        with self.assertRaises(InvalidGeneratorParameters):
            _generate(resolution=17)
        with self.assertRaisesRegex(
            InvalidGeneratorParameters, "unknown bone family"
        ):
            _generate(family_id="missing_bone")

    def test_supported_parameter_extremes_remain_single_closed_solids(self):
        cases = (
            {
                "length": 180.0, "shaft_radius": 8.0, "end_scale": 1.2,
                "curvature": 1.0, "asymmetry": 1.0, "surface_detail": 0.4,
                "seed": 2147483647,
            },
            {
                "length": 60.0, "shaft_radius": 22.0, "end_scale": 2.1,
                "curvature": 0.0, "asymmetry": 0.0, "surface_detail": 0.0,
                "seed": 0,
            },
        )
        for parameters in cases:
            result = _generate(parameters, resolution=21)
            self.assertTrue(result.statistics.is_watertight)
            self.assertTrue(result.statistics.is_manifold)
            self.assertEqual(result.statistics.connected_component_count, 1)
            self.assertEqual(result.statistics.degenerate_face_count, 0)


if __name__ == "__main__":
    unittest.main()
