"""Tests for internal Rock families built only from pipeline parameters."""

from collections import Counter
from dataclasses import FrozenInstanceError
import hashlib
import math
import unittest

from generators import GenerationRequest, GeneratorFactory
from generators.rock_families import (
    DEFAULT_ROCK_FAMILY,
    RIVER_STONE_FAMILY,
    RockFamilyRegistry,
)
from generators.rock_generator import RockGenerator, _RockField
from generators.rock_pipeline import RockGenerationContext, build_surface_detail


def _digest(mesh):
    return hashlib.sha256(
        repr((mesh.vertices, mesh.faces)).encode("ascii")
    ).hexdigest()


class RockFamilyDefinitionTests(unittest.TestCase):
    def test_registry_exposes_immutable_parameter_only_families(self):
        self.assertIs(RockFamilyRegistry.get("default"), DEFAULT_ROCK_FAMILY)
        self.assertIs(
            RockFamilyRegistry.get("river_stone"), RIVER_STONE_FAMILY
        )
        self.assertEqual(
            tuple(item.family_id for item in RockFamilyRegistry.list_all()),
            ("default", "river_stone"),
        )
        with self.assertRaises(FrozenInstanceError):
            RIVER_STONE_FAMILY.display_name = "Changed"
        with self.assertRaises(TypeError):
            RockFamilyRegistry._definitions["changed"] = RIVER_STONE_FAMILY
        with self.assertRaises(KeyError):
            RockFamilyRegistry.get("granite")

    def test_river_stone_uses_all_three_existing_pipeline_stages(self):
        field = _RockField(40.0, 0.35, 1, RIVER_STONE_FAMILY)
        self.assertEqual(field.context.seed, 1)
        self.assertEqual(len(field.facet_layout.planes), 2)
        self.assertEqual(
            field.surface_detail,
            build_surface_detail(field.context, RIVER_STONE_FAMILY.surface),
        )
        self.assertLess(
            field.surface_detail.fbm_amplitude,
            _RockField(40.0, 0.35, 1).surface_detail.fbm_amplitude,
        )
        self.assertLess(field.macro_shape.radii[2], field.macro_shape.radii[1])

    def test_river_stone_preserves_roughness_scaling(self):
        low = build_surface_detail(
            RockGenerationContext.create(40.0, 0.10, 1),
            RIVER_STONE_FAMILY.surface,
        )
        high = build_surface_detail(
            RockGenerationContext.create(40.0, 0.70, 1),
            RIVER_STONE_FAMILY.surface,
        )
        self.assertGreater(high.fbm_amplitude, low.fbm_amplitude)
        self.assertGreater(high.ridge_amplitude, low.ridge_amplitude)


class RiverStoneGenerationTests(unittest.TestCase):
    _PARAMETERS = {"size": 40.0, "roughness": 0.35, "seed": 1}

    def _generate(self, parameters=None, resolution=25):
        return RockGenerator().generate_family(
            GenerationRequest(
                "rock",
                self._PARAMETERS if parameters is None else parameters,
                resolution,
            ),
            "river_stone",
        )

    def test_output_is_deterministic_and_seed_sensitive(self):
        first = self._generate(resolution=17)
        repeated = self._generate(resolution=17)
        changed = self._generate(
            {"size": 40.0, "roughness": 0.35, "seed": 2}, 17
        )
        self.assertEqual(first, repeated)
        self.assertNotEqual(first.vertices, changed.vertices)

    def test_final_digest_is_stable(self):
        self.assertEqual(
            _digest(self._generate()),
            "61264e6e929229247ac7b4d89f2916f5c5cb875dc985c5c258fa79334c18abd4",
        )

    def test_mesh_is_finite_closed_manifold_and_single_component(self):
        mesh = self._generate()
        statistics = mesh.statistics()
        self.assertTrue(statistics.is_watertight)
        self.assertTrue(statistics.is_manifold)
        self.assertEqual(statistics.connected_component_count, 1)
        self.assertEqual(statistics.degenerate_face_count, 0)
        self.assertTrue(all(
            math.isfinite(value)
            for vertex in mesh.vertices
            for value in vertex
        ))

    def test_shape_is_flatter_and_has_no_large_non_ground_planar_region(self):
        river = self._generate()
        smooth = GeneratorFactory.generate_request(GenerationRequest(
            "rock",
            {"size": 40.0, "roughness": 0.10, "seed": 1},
            25,
        ))
        river_stats = river.statistics()
        smooth_stats = smooth.statistics
        river_spans = tuple(
            river_stats.bounds[1][axis] - river_stats.bounds[0][axis]
            for axis in range(3)
        )
        smooth_spans = tuple(
            smooth_stats.bounds[1][axis] - smooth_stats.bounds[0][axis]
            for axis in range(3)
        )
        self.assertLess(
            river_spans[2] / max(river_spans[:2]),
            smooth_spans[2] / max(smooth_spans[:2]),
        )

        normal_counts = Counter(
            tuple(round(value, 5) for value in river.face_normal(index))
            for index in range(len(river.faces))
        )
        ground_faces = normal_counts.pop((0.0, -0.0, -1.0))
        self.assertGreater(ground_faces, 0)
        self.assertLessEqual(max(normal_counts.values()), 4)

    def test_existing_variant_digests_remain_unchanged(self):
        cases = (
            (
                {"size": 40.0, "roughness": 0.10, "seed": 1},
                17,
                "29d6402a0148637fd00cbc1274d8f6be6c9f8901b2b856e2de75dc43f91bdc3e",
            ),
            (
                {"size": 40.0, "roughness": 0.35, "seed": 1},
                17,
                "30a709c32fb7dd16b87f0388f21c6e24e12b6ad990b2872dd31f9549956e7c1d",
            ),
            (
                {"size": 45.0, "roughness": 0.62, "seed": 23},
                25,
                "040bd703ef44549b418fdb5fd6804b9e36ce93e372cbbea00e5e63a8b8ffadde",
            ),
        )
        for parameters, resolution, expected in cases:
            result = GeneratorFactory.generate_request(GenerationRequest(
                "rock", parameters, resolution
            ))
            self.assertEqual(_digest(result.mesh), expected)


if __name__ == "__main__":
    unittest.main()
