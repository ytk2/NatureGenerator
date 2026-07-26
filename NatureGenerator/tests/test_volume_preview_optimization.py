"""Focused Sprint 37 tests for Gyroid Volume Preview optimization."""

from dataclasses import replace
import math
import unittest
from unittest.mock import patch

from commands.gyroid_volume import execute_gyroid_volume
from volume import (
    BoundaryMode,
    GeometryMode,
    GyroidVolumeRequest,
    PreviewQuality,
    VolumeExecutionContext,
    VolumeSafetyLimitError,
    estimate_volume_cost,
    generate_gyroid_volume,
    select_volume_resolution,
    validate_volume_cost,
)


def preview(quality=PreviewQuality.STANDARD, **overrides):
    values = {
        "resolution_x": 16,
        "resolution_y": 16,
        "resolution_z": 16,
        "preview_quality": quality,
        "execution_context": VolumeExecutionContext.PREVIEW,
    }
    values.update(overrides)
    return GyroidVolumeRequest(**values)


class PreviewResolutionPolicyTests(unittest.TestCase):
    def test_quality_scales_and_default_are_explicit(self):
        self.assertIs(
            GyroidVolumeRequest().preview_quality, PreviewQuality.STANDARD
        )
        expected = {
            PreviewQuality.DRAFT: (40, 30, 20),
            PreviewQuality.STANDARD: (60, 45, 30),
            PreviewQuality.FINAL: (80, 60, 40),
        }
        for quality, resolution in expected.items():
            with self.subTest(quality=quality):
                request = preview(
                    quality,
                    resolution_x=80,
                    resolution_y=60,
                    resolution_z=40,
                )
                selection = select_volume_resolution(request)
                self.assertEqual(selection.final_resolution, (80, 60, 40))
                self.assertEqual(selection.effective_resolution, resolution)
                self.assertEqual(request.resolution, (80, 60, 40))

    def test_round_half_up_minimum_and_anisotropic_axes(self):
        selection = select_volume_resolution(
            preview(
                PreviewQuality.DRAFT,
                resolution_x=17,
                resolution_y=19,
                resolution_z=8,
            )
        )
        self.assertEqual(selection.effective_resolution, (9, 10, 8))

    def test_apply_always_uses_final_resolution(self):
        for quality in PreviewQuality:
            request = GyroidVolumeRequest(
                preview_quality=quality,
                resolution_x=17,
                resolution_y=19,
                resolution_z=21,
            )
            self.assertEqual(
                select_volume_resolution(request).effective_resolution,
                (17, 19, 21),
            )


class VolumeCostEstimateTests(unittest.TestCase):
    def test_surface_counts_are_exact(self):
        estimate = estimate_volume_cost(
            preview(
                resolution_x=80,
                resolution_y=60,
                resolution_z=40,
            )
        )
        self.assertEqual(estimate.final_resolution, (80, 60, 40))
        self.assertEqual(estimate.effective_resolution, (60, 45, 30))
        self.assertEqual(estimate.scalar_samples_per_field, 60 * 45 * 30)
        self.assertEqual(estimate.total_scalar_samples, 60 * 45 * 30)
        self.assertEqual(estimate.cell_count, 59 * 44 * 29)
        self.assertEqual(estimate.stored_scalar_field_count, 1)
        self.assertEqual(
            estimate.estimated_scalar_grid_bytes, 60 * 45 * 30 * 8
        )

    def test_thickened_cap_accounts_for_two_grids_and_cap_work(self):
        estimate = estimate_volume_cost(
            preview(
                geometry_mode=GeometryMode.THICKENED,
                boundary_mode=BoundaryMode.CAP,
            )
        )
        self.assertEqual(estimate.effective_resolution, (12, 12, 12))
        self.assertEqual(estimate.scalar_samples_per_field, 12 ** 3)
        self.assertEqual(estimate.total_scalar_samples, 2 * 12 ** 3)
        self.assertEqual(estimate.stored_scalar_field_count, 2)
        self.assertEqual(estimate.estimated_scalar_grid_bytes, 2 * 12 ** 3 * 8)
        self.assertGreater(estimate.estimated_cap_triangles, 0)

    def test_preview_and_apply_use_distinct_limits_and_effective_resolution(self):
        draft = preview(
            PreviewQuality.DRAFT,
            resolution_x=160,
            resolution_y=160,
            resolution_z=160,
        )
        draft_estimate = estimate_volume_cost(draft)
        self.assertEqual(draft_estimate.effective_resolution, (80, 80, 80))
        validate_volume_cost(draft, draft_estimate)

        apply = replace(draft, execution_context=VolumeExecutionContext.APPLY)
        apply_estimate = estimate_volume_cost(apply)
        self.assertEqual(apply_estimate.effective_resolution, (160, 160, 160))
        with self.assertRaisesRegex(
            VolumeSafetyLimitError,
            "Apply for TPMS Type gyroid.*"
            "requested final resolution 160 × 160 × 160.*"
            "4,096,000 scalar samples.*active limit of 2,000,000",
        ):
            validate_volume_cost(apply, apply_estimate)

    def test_rejection_occurs_before_sampling_with_actionable_context(self):
        request = preview(
            PreviewQuality.FINAL,
            resolution_x=100,
            resolution_y=100,
            resolution_z=100,
        )
        with patch("volume.VoxelGrid.sample") as sample:
            with self.assertRaisesRegex(
                VolumeSafetyLimitError,
                "Preview \\(Final\\).*final resolution.*effective resolution.*"
                "1,000,000 scalar samples.*approximately.*750,000",
            ):
                generate_gyroid_volume(request)
        sample.assert_not_called()


class PreviewGeometryAndTimingTests(unittest.TestCase):
    def test_final_preview_preserves_all_sprint_36_default_digests(self):
        expected = {
            (GeometryMode.SURFACE, BoundaryMode.OPEN):
                "997b710b2675435be9e3c1a15a2bdc5bf4b9938e0cfedfe94e01d867acb67f56",
            (GeometryMode.SURFACE, BoundaryMode.CAP):
                "9c7965d3d43052176fd6e5c94ba0d66767fd8cd0c7b9a9be1beb6f01e1c86fc7",
            (GeometryMode.THICKENED, BoundaryMode.OPEN):
                "5ba3480988ccbda7809df98aa33159497e68b8eb2751214b4a6093ad52e9279c",
            (GeometryMode.THICKENED, BoundaryMode.CAP):
                "b47c0c5f21819b2b9f5cb06996fe3e3cb71102b10985b0bf70618165dcfe1121",
        }
        for modes, digest in expected.items():
            with self.subTest(modes=modes):
                result = generate_gyroid_volume(
                    GyroidVolumeRequest(
                        geometry_mode=modes[0],
                        boundary_mode=modes[1],
                        preview_quality=PreviewQuality.FINAL,
                        execution_context=VolumeExecutionContext.PREVIEW,
                    )
                )
                self.assertEqual(result.digest, digest)

    def test_draft_standard_final_are_deterministic_and_increase_detail(self):
        results = []
        for quality in PreviewQuality:
            first = generate_gyroid_volume(preview(quality))
            second = generate_gyroid_volume(preview(quality))
            self.assertEqual(first.digest, second.digest)
            results.append(first)
        self.assertLess(
            results[0].statistics.face_count,
            results[1].statistics.face_count,
        )
        self.assertLess(
            results[1].statistics.face_count,
            results[2].statistics.face_count,
        )

    def test_final_preview_and_apply_have_identical_core_geometry(self):
        for geometry_mode in GeometryMode:
            for boundary_mode in BoundaryMode:
                with self.subTest(
                    geometry_mode=geometry_mode,
                    boundary_mode=boundary_mode,
                ):
                    common = {
                        "geometry_mode": geometry_mode,
                        "boundary_mode": boundary_mode,
                        "resolution_x": 16,
                        "resolution_y": 16,
                        "resolution_z": 16,
                    }
                    preview_result = generate_gyroid_volume(
                        GyroidVolumeRequest(
                            preview_quality=PreviewQuality.FINAL,
                            execution_context=VolumeExecutionContext.PREVIEW,
                            **common
                        )
                    )
                    apply_result = generate_gyroid_volume(
                        GyroidVolumeRequest(**common)
                    )
                    self.assertEqual(preview_result.mesh, apply_result.mesh)
                    self.assertEqual(preview_result.digest, apply_result.digest)

    def test_timings_are_finite_nonnegative_and_open_closure_is_zero(self):
        result = generate_gyroid_volume(preview(PreviewQuality.DRAFT))
        timings = result.timings
        values = (
            timings.validation_and_estimation,
            timings.scalar_field_sampling,
            timings.iso_surface_extraction,
            timings.boundary_closure,
            timings.geometry_validation,
            timings.total_core,
        )
        self.assertTrue(all(math.isfinite(value) and value >= 0 for value in values))
        self.assertEqual(timings.boundary_closure, 0.0)
        self.assertGreaterEqual(
            timings.total_core,
            sum(values[:-1]) * 0.99,
        )

    def test_timings_do_not_affect_result_equality_or_digest(self):
        first = generate_gyroid_volume(preview(PreviewQuality.DRAFT))
        second = generate_gyroid_volume(preview(PreviewQuality.DRAFT))
        self.assertEqual(first, second)
        self.assertEqual(first.digest, second.digest)

    def test_fusion_insertion_timing_is_reported_outside_core_result(self):
        observed = []
        result, body = execute_gyroid_volume(
            preview(PreviewQuality.DRAFT),
            lambda mesh, name: {"mesh": mesh, "name": name},
            "preview",
            observed.append,
        )
        self.assertEqual(body["mesh"], result.mesh)
        self.assertEqual(len(observed), 1)
        self.assertTrue(math.isfinite(observed[0]))
        self.assertGreaterEqual(observed[0], 0.0)


if __name__ == "__main__":
    unittest.main()
