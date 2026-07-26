"""Focused Sprint 36 tests for finite-thickness Gyroid Volume geometry."""

import math
import unittest
from unittest.mock import patch

from volume import (
    BoundaryMode,
    GeometryMode,
    GyroidVolumeField,
    GyroidVolumeRequest,
    ThickenedGyroidField,
    VolumeExecutionContext,
    PreviewQuality,
    VolumeSafetyLimitError,
    generate_gyroid_volume,
)


def thickened_request(boundary=BoundaryMode.OPEN, **overrides):
    values = {
        "geometry_mode": GeometryMode.THICKENED,
        "boundary_mode": boundary,
        "resolution_x": 16,
        "resolution_y": 16,
        "resolution_z": 16,
    }
    values.update(overrides)
    return GyroidVolumeRequest(**values)


class ThickenedGyroidFieldTests(unittest.TestCase):
    def test_analytical_world_gradient_matches_finite_differences(self):
        field = GyroidVolumeField(23.0, 0.31, -0.17, 0.23)
        point = (2.7, -4.1, 6.3)
        analytical = field.gradient(*point)
        step = 1e-5
        numerical = []
        for axis in range(3):
            before = list(point)
            after = list(point)
            before[axis] -= step
            after[axis] += step
            numerical.append(
                (field(*after) - field(*before)) / (2.0 * step)
            )
        for actual, expected in zip(analytical, numerical):
            self.assertAlmostEqual(actual, expected, places=8)

    def test_band_has_two_sides_and_thickness_changes_it(self):
        surface = GyroidVolumeField(20.0)
        thin = ThickenedGyroidField(surface, 0.0, 1.0)
        thick = ThickenedGyroidField(surface, 0.0, 2.0)
        self.assertLess(thin(0.0, 0.0, 0.0), 0.0)
        self.assertGreater(thin(2.0, 2.0, 2.0), 0.0)
        self.assertGreater(thin(-2.0, -2.0, -2.0), 0.0)
        self.assertLess(thick(1.0, 1.0, 1.0), thin(1.0, 1.0, 1.0))

    def test_field_is_deterministic_and_accounts_for_period_iso_and_phase(self):
        base = ThickenedGyroidField(
            GyroidVolumeField(20.0, 0.2, -0.3, 0.4), 0.1, 1.25
        )
        point = (3.0, -5.0, 7.0)
        self.assertEqual(base(*point), base(*point))
        alternatives = (
            ThickenedGyroidField(
                GyroidVolumeField(18.0, 0.2, -0.3, 0.4), 0.1, 1.25
            ),
            ThickenedGyroidField(
                GyroidVolumeField(20.0, 0.7, -0.3, 0.4), 0.1, 1.25
            ),
            ThickenedGyroidField(
                GyroidVolumeField(20.0, 0.2, -0.3, 0.4), 0.35, 1.25
            ),
        )
        for changed in alternatives:
            self.assertNotEqual(changed(*point), base(*point))


class WallThicknessValidationTests(unittest.TestCase):
    def test_thickened_mode_rejects_zero_negative_and_out_of_range_values(self):
        for value in (0.0, -1.0, 20.1, float("nan")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    thickened_request(wall_thickness=value)

    def test_surface_mode_ignores_inactive_finite_wall_thickness(self):
        baseline = generate_gyroid_volume(
            GyroidVolumeRequest(
                resolution_x=16, resolution_y=16, resolution_z=16
            )
        )
        ignored = generate_gyroid_volume(
            GyroidVolumeRequest(
                geometry_mode=GeometryMode.SURFACE,
                wall_thickness=0.0,
                resolution_x=16,
                resolution_y=16,
                resolution_z=16,
            )
        )
        self.assertEqual(ignored.mesh, baseline.mesh)
        self.assertEqual(ignored.digest, baseline.digest)

    def test_under_resolved_wall_is_rejected_before_sampling(self):
        request = thickened_request(
            width=500.0,
            depth=500.0,
            height=500.0,
            resolution_x=8,
            resolution_y=8,
            resolution_z=8,
            wall_thickness=0.1,
        )
        with patch("volume.VoxelGrid.sample") as sample:
            with self.assertRaisesRegex(
                VolumeSafetyLimitError, "too thin.*increase the resolution"
            ):
                generate_gyroid_volume(request)
            sample.assert_not_called()

    def test_band_that_consumes_sampled_domain_is_rejected_clearly(self):
        with self.assertRaisesRegex(
            VolumeSafetyLimitError,
            "consumes the sampled scalar domain",
        ):
            generate_gyroid_volume(
                thickened_request(wall_thickness=20.0, period=1.0)
            )

    def test_oversized_thickened_preview_is_rejected_before_sampling(self):
        request = GyroidVolumeRequest(
            geometry_mode=GeometryMode.THICKENED,
            resolution_x=100,
            resolution_y=100,
            resolution_z=100,
            execution_context=VolumeExecutionContext.PREVIEW,
            preview_quality=PreviewQuality.FINAL,
        )
        with patch("volume.VoxelGrid.sample") as sample:
            with self.assertRaises(VolumeSafetyLimitError):
                generate_gyroid_volume(request)
            sample.assert_not_called()

    def test_two_grid_scalar_cost_is_enforced_before_sampling(self):
        request = GyroidVolumeRequest(
            geometry_mode=GeometryMode.THICKENED,
            resolution_x=100,
            resolution_y=80,
            resolution_z=50,
            execution_context=VolumeExecutionContext.PREVIEW,
            preview_quality=PreviewQuality.FINAL,
        )
        with patch("volume.sample_thickened_band_grids") as sample:
            with self.assertRaisesRegex(
                VolumeSafetyLimitError, "scalar samples"
            ):
                generate_gyroid_volume(request)
            sample.assert_not_called()


class SurfaceCompatibilityTests(unittest.TestCase):
    def test_default_open_digest_is_exactly_sprint_35(self):
        result = generate_gyroid_volume(GyroidVolumeRequest())
        self.assertEqual(
            result.digest,
            "997b710b2675435be9e3c1a15a2bdc5bf4b9938e0cfedfe94e01d867acb67f56",
        )

    def test_default_cap_digest_is_exactly_sprint_35(self):
        result = generate_gyroid_volume(
            GyroidVolumeRequest(boundary_mode=BoundaryMode.CAP)
        )
        self.assertEqual(
            result.digest,
            "9c7965d3d43052176fd6e5c94ba0d66767fd8cd0c7b9a9be1beb6f01e1c86fc7",
        )


class ThickenedGeometryTests(unittest.TestCase):
    def test_open_is_deterministic_two_sided_and_measured_open(self):
        first = generate_gyroid_volume(thickened_request())
        second = generate_gyroid_volume(thickened_request())
        statistics = first.statistics
        self.assertEqual(first.mesh, second.mesh)
        self.assertEqual(first.digest, second.digest)
        self.assertEqual(first.scalar_bytes, 16 * 16 * 16 * 8 * 2)
        self.assertEqual(
            first.digest,
            "69e31826085981cf5c65f5e4ab5f77cbbdc28a422a549ac55bf169ddac36319a",
        )
        self.assertGreater(statistics.boundary_edge_count, 0)
        self.assertFalse(statistics.is_watertight)
        self.assertTrue(statistics.is_manifold)
        self.assertEqual(statistics.nonmanifold_edge_count, 0)
        self.assertEqual(statistics.nonmanifold_vertex_count, 0)
        self.assertEqual(statistics.inconsistent_winding_edge_count, 0)
        self.assertEqual(statistics.degenerate_face_count, 0)
        self.assertEqual(statistics.duplicate_face_count, 0)

    def test_cap_is_clean_watertight_manifold_with_positive_volume(self):
        first = generate_gyroid_volume(
            thickened_request(BoundaryMode.CAP)
        )
        second = generate_gyroid_volume(
            thickened_request(BoundaryMode.CAP)
        )
        statistics = first.statistics
        self.assertEqual(first.mesh, second.mesh)
        self.assertEqual(first.digest, second.digest)
        self.assertEqual(
            first.digest,
            "b8bc6d62a8cda831ab26ca841473d667dec892c613be15240663bcdb245de41d",
        )
        self.assertTrue(statistics.is_watertight)
        self.assertTrue(statistics.is_manifold)
        self.assertEqual(statistics.boundary_edge_count, 0)
        self.assertEqual(statistics.nonmanifold_edge_count, 0)
        self.assertEqual(statistics.nonmanifold_vertex_count, 0)
        self.assertEqual(statistics.inconsistent_winding_edge_count, 0)
        self.assertEqual(statistics.degenerate_face_count, 0)
        self.assertEqual(statistics.duplicate_face_count, 0)
        self.assertTrue(math.isfinite(statistics.signed_volume))
        self.assertGreater(statistics.signed_volume, 0.0)

    def test_wall_thickness_changes_output_deterministically(self):
        thin = generate_gyroid_volume(
            thickened_request(wall_thickness=0.75)
        )
        thick = generate_gyroid_volume(
            thickened_request(wall_thickness=2.0)
        )
        self.assertNotEqual(thin.digest, thick.digest)
        self.assertEqual(
            thin.digest,
            generate_gyroid_volume(
                thickened_request(wall_thickness=0.75)
            ).digest,
        )

    def test_minimum_thin_wall_and_thicker_wall_are_supported(self):
        common = {
            "width": 10.0,
            "depth": 10.0,
            "height": 10.0,
            "period": 5.0,
            "phase_x": 0.31,
            "phase_y": -0.17,
            "phase_z": 0.23,
        }
        thin = generate_gyroid_volume(
            thickened_request(
                BoundaryMode.CAP, wall_thickness=0.1, **common
            )
        )
        thick = generate_gyroid_volume(
            thickened_request(
                BoundaryMode.CAP, wall_thickness=5.0, **common
            )
        )
        self.assertTrue(thin.statistics.is_watertight)
        self.assertTrue(thick.statistics.is_watertight)
        self.assertNotEqual(thin.digest, thick.digest)

    def test_non_cubic_independent_axis_resolution_cap_is_valid(self):
        result = generate_gyroid_volume(
            thickened_request(
                BoundaryMode.CAP,
                width=45.0,
                depth=70.0,
                height=35.0,
                resolution_x=13,
                resolution_y=18,
                resolution_z=11,
                phase_x=0.31,
                phase_y=-0.17,
                phase_z=0.23,
            )
        )
        self.assertTrue(result.statistics.is_watertight)
        self.assertTrue(result.statistics.is_manifold)
        self.assertEqual(
            result.statistics.bounds,
            ((-22.5, -35.0, -17.5), (22.5, 35.0, 17.5)),
        )

    def test_period_iso_phase_dimensions_and_resolution_change_geometry(self):
        baseline = generate_gyroid_volume(thickened_request()).digest
        alternatives = (
            thickened_request(period=18.0),
            thickened_request(iso_value=0.25),
            thickened_request(phase_x=0.31),
            thickened_request(phase_y=-0.17),
            thickened_request(phase_z=0.23),
            thickened_request(width=55.0),
            thickened_request(depth=52.0),
            thickened_request(height=48.0),
            thickened_request(resolution_x=17),
            thickened_request(resolution_y=17),
            thickened_request(resolution_z=17),
        )
        for changed in alternatives:
            with self.subTest(changed=changed):
                self.assertNotEqual(
                    generate_gyroid_volume(changed).digest, baseline
                )
