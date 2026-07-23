"""Focused tests for the internal three-stage Rock generation pipeline."""

from dataclasses import FrozenInstanceError
import math
import unittest

from generators.rock_pipeline import (
    FacetLayoutDefinition,
    MacroShapeDefinition,
    RockGenerationContext,
    SurfaceDetailDefinition,
    build_facet_layout,
    build_macro_shape,
    build_surface_detail,
)
from generators.value_noise import DeterministicValueNoise


class MacroShapeStageTests(unittest.TestCase):
    def _build(self, seed=11, roughness=0.35):
        context = RockGenerationContext.create(40.0, roughness, seed)
        return context, build_macro_shape(
            context, DeterministicValueNoise(seed)
        )

    def test_definition_is_immutable_deterministic_and_seed_sensitive(self):
        context, first = self._build()
        _, repeated = self._build()
        _, changed = self._build(seed=12)
        self.assertIsInstance(first, MacroShapeDefinition)
        self.assertEqual(first, repeated)
        self.assertNotEqual(first, changed)
        with self.assertRaises(FrozenInstanceError):
            first.ground_offset = 0.0
        self.assertGreater(context.roughness_response, 0.0)

    def test_proportions_orientation_mass_and_ground_are_valid(self):
        context, definition = self._build(roughness=0.70)
        self.assertTrue(all(value > 0.0 for value in definition.radii))
        self.assertTrue(all(
            context.size * 0.25 < value < context.size * 0.60
            for value in definition.radii
        ))
        for axis in definition.orientation:
            self.assertAlmostEqual(
                math.sqrt(sum(value * value for value in axis)), 1.0
            )
        for left in range(3):
            for right in range(left + 1, 3):
                self.assertAlmostEqual(sum(
                    definition.orientation[left][index]
                    * definition.orientation[right][index]
                    for index in range(3)
                ), 0.0)
        self.assertLessEqual(
            math.sqrt(sum(value * value for value in definition.center_offset)),
            context.size * 0.10,
        )
        self.assertGreater(definition.ground_offset, 0.70)
        self.assertLess(definition.ground_offset, 1.0)


class FacetLayoutStageTests(unittest.TestCase):
    def _build(self, seed=11):
        context = RockGenerationContext.create(40.0, 0.62, seed)
        return build_facet_layout(context, DeterministicValueNoise(seed))

    def test_layout_is_immutable_deterministic_and_seed_sensitive(self):
        first = self._build()
        self.assertIsInstance(first, FacetLayoutDefinition)
        self.assertEqual(first, self._build())
        self.assertNotEqual(first, self._build(seed=12))
        with self.assertRaises(FrozenInstanceError):
            first.planes = ()

    def test_planes_have_bounded_count_normals_weights_and_mixed_scales(self):
        layout = self._build()
        self.assertGreaterEqual(len(layout.planes), 3)
        self.assertLessEqual(len(layout.planes), 8)
        self.assertGreaterEqual(len({facet.scale for facet in layout.planes}), 3)
        for facet in layout.planes:
            self.assertAlmostEqual(
                math.sqrt(sum(value * value for value in facet.normal)), 1.0
            )
            self.assertTrue(all(math.isfinite(value) for value in facet.normal))
            self.assertGreater(facet.offset, 0.60)
            self.assertLess(facet.offset, 1.10)
            self.assertGreater(facet.weight, 0.0)
            self.assertLessEqual(facet.weight, 1.0)


class SurfaceDetailStageTests(unittest.TestCase):
    def _build(self, roughness):
        return build_surface_detail(
            RockGenerationContext.create(40.0, roughness, 11)
        )

    def test_settings_are_immutable_deterministic_and_bounded(self):
        first = self._build(0.35)
        self.assertIsInstance(first, SurfaceDetailDefinition)
        self.assertEqual(first, self._build(0.35))
        with self.assertRaises(FrozenInstanceError):
            first.fbm_octaves = 1
        self.assertGreaterEqual(first.fbm_octaves, 3)
        self.assertLessEqual(first.fbm_octaves, 8)
        self.assertGreater(first.fbm_frequency, 0.0)
        self.assertLess(first.fbm_frequency, 2.0)
        self.assertGreater(first.fbm_lacunarity, 1.0)
        self.assertLess(first.fbm_lacunarity, 3.0)
        self.assertGreater(first.fbm_gain, 0.0)
        self.assertLess(first.fbm_gain, 1.0)
        self.assertGreater(first.ridge_frequency, 0.0)
        self.assertLess(first.ridge_frequency, 10.0)
        numeric = (
            first.fbm_amplitude,
            first.ridge_amplitude,
            first.ridge_center,
        )
        self.assertTrue(all(math.isfinite(value) for value in numeric))
        self.assertTrue(all(0.0 <= value <= 0.50 for value in numeric))

    def test_roughness_controls_detail_amplitudes_and_seeded_samples(self):
        low = self._build(0.10)
        high = self._build(0.70)
        self.assertGreater(high.fbm_amplitude, low.fbm_amplitude * 3.0)
        self.assertGreater(high.ridge_amplitude, low.ridge_amplitude * 10.0)
        point = (0.3, -0.2, 0.5)
        first = high.deformation(point, DeterministicValueNoise(11))
        repeated = high.deformation(point, DeterministicValueNoise(11))
        changed = high.deformation(point, DeterministicValueNoise(12))
        self.assertEqual(first, repeated)
        self.assertNotEqual(first, changed)
        self.assertTrue(all(math.isfinite(value) for value in (
            low.deformation(point, DeterministicValueNoise(11)),
            first,
            changed,
        )))


if __name__ == "__main__":
    unittest.main()
