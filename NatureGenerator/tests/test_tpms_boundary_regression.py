"""Sprint 38 regression for near-degenerate extracted boundary slivers."""

import math
from types import SimpleNamespace
import unittest

from fusion.gyroid_volume_preview import GyroidVolumePreviewController
from volume import (
    BoundaryMode,
    GeometryMode,
    PreviewQuality,
    TPMSFieldFactory,
    TPMSVolumeRequest,
    TPMSType,
    VolumeExecutionContext,
    canonical_volume_mesh_digest,
    estimate_volume_cost,
    generate_tpms_volume,
)
from volume.boundary_closure import close_rectangular_band_boundary
from volume.iso_surface import extract_isosurface
from volume.thickened_field import (
    ThickenedTPMSField,
    combine_wall_surfaces,
    sample_thickened_band_grids,
)


def reproduction(**overrides):
    values = {
        "preview_quality": PreviewQuality.STANDARD,
        "tpms_type": TPMSType.GYROID,
        "geometry_mode": GeometryMode.THICKENED,
        "wall_thickness": 2.0,
        "width": 60.0,
        "depth": 60.0,
        "height": 60.0,
        "period": 30.0,
        "iso_value": 0.06,
        "resolution_x": 40,
        "resolution_y": 40,
        "resolution_z": 40,
        "phase_x": 0.12566,
        "phase_y": 0.0,
        "phase_z": 0.0,
        "boundary_mode": BoundaryMode.CAP,
        "execution_context": VolumeExecutionContext.PREVIEW,
    }
    values.update(overrides)
    return TPMSVolumeRequest(**values)


def schwarz_p_surface(**overrides):
    values = {
        "preview_quality": PreviewQuality.STANDARD,
        "tpms_type": TPMSType.SCHWARZ_P,
        "geometry_mode": GeometryMode.SURFACE,
        "width": 40.0,
        "depth": 40.0,
        "height": 40.0,
        "period": 20.0,
        "iso_value": 0.0,
        "resolution_x": 40,
        "resolution_y": 40,
        "resolution_z": 40,
        "phase_x": 0.0,
        "phase_y": 0.0,
        "phase_z": 0.0,
        "boundary_mode": BoundaryMode.CAP,
        "execution_context": VolumeExecutionContext.PREVIEW,
    }
    values.update(overrides)
    return TPMSVolumeRequest(**values)


class BoundarySliverRegressionTests(unittest.TestCase):
    def assert_clean_closed(self, result):
        statistics = result.statistics
        self.assertEqual(statistics.boundary_edge_count, 0)
        self.assertEqual(statistics.nonmanifold_edge_count, 0)
        self.assertEqual(statistics.nonmanifold_vertex_count, 0)
        self.assertEqual(statistics.inconsistent_winding_edge_count, 0)
        self.assertEqual(statistics.degenerate_face_count, 0)
        self.assertEqual(statistics.duplicate_face_count, 0)
        self.assertTrue(statistics.is_watertight)
        self.assertTrue(statistics.is_manifold)
        self.assertTrue(math.isfinite(statistics.signed_volume))
        self.assertGreater(statistics.signed_volume, 0.0)

    def test_exact_standard_preview_is_clean_and_deterministic(self):
        request = reproduction()
        self.assertEqual(
            estimate_volume_cost(request).effective_resolution, (30, 30, 30)
        )
        first = generate_tpms_volume(request)
        second = generate_tpms_volume(request)
        self.assert_clean_closed(first)
        self.assertEqual(first.mesh, second.mesh)
        self.assertEqual(first.digest, second.digest)
        self.assertEqual(
            first.digest,
            "1d0f2f196955a71095dd82a21e168cfbc3198e3545bf9ccd06cd8adc706b3e9a",
        )

    def test_open_wall_and_grids_remain_immutable_during_repair(self):
        request = reproduction()
        estimate = estimate_volume_cost(request)
        field = TPMSFieldFactory.create(
            request.tpms_type,
            request.period,
            request.phase_x,
            request.phase_y,
            request.phase_z,
        )
        band = ThickenedTPMSField(
            field, request.iso_value, request.wall_thickness
        )
        upper, lower = sample_thickened_band_grids(
            band,
            request.minimum,
            request.maximum,
            estimate.effective_resolution,
        )
        open_mesh = combine_wall_surfaces(
            extract_isosurface(upper, 0.0),
            extract_isosurface(lower, 0.0),
        )
        mesh_snapshot = (open_mesh.vertices, open_mesh.faces)
        grid_snapshot = (upper.values, lower.values)
        closed = close_rectangular_band_boundary(open_mesh, upper, lower)
        self.assertEqual(
            (open_mesh.vertices, open_mesh.faces), mesh_snapshot
        )
        self.assertEqual((upper.values, lower.values), grid_snapshot)
        self.assertEqual(
            canonical_volume_mesh_digest(closed),
            "1d0f2f196955a71095dd82a21e168cfbc3198e3545bf9ccd06cd8adc706b3e9a",
        )

    def test_neighboring_phases_zero_and_non_cubic_fixture_are_valid(self):
        cases = (
            reproduction(phase_x=0.12565),
            reproduction(phase_x=0.12567),
            reproduction(phase_x=0.0),
            reproduction(
                width=55.0,
                depth=48.0,
                height=42.0,
                resolution_x=36,
                resolution_y=38,
                resolution_z=40,
            ),
        )
        for request in cases:
            with self.subTest(request=request):
                self.assert_clean_closed(generate_tpms_volume(request))

    def test_apply_uses_final_40_cubed_and_is_valid(self):
        result = generate_tpms_volume(
            reproduction(execution_context=VolumeExecutionContext.APPLY)
        )
        self.assertEqual(
            result.cost_estimate.effective_resolution, (40, 40, 40)
        )
        self.assert_clean_closed(result)

    def test_corrected_preview_controller_owns_exactly_one_body(self):
        controller = GyroidVolumePreviewController()
        first = SimpleNamespace(isValid=True, deleted=False)
        first.deleteMe = lambda: setattr(first, "deleted", True)
        second = SimpleNamespace(isValid=True, deleted=False)
        second.deleteMe = lambda: setattr(second, "deleted", True)
        controller.replace(lambda: first)
        controller.replace(lambda: second)
        self.assertTrue(first.deleted)
        self.assertIs(controller.body, second)


class SchwarzPIsovalueAmbiguityTests(unittest.TestCase):
    def assert_clean_closed(self, result):
        statistics = result.statistics
        self.assertEqual(statistics.boundary_edge_count, 0)
        self.assertEqual(statistics.nonmanifold_edge_count, 0)
        self.assertEqual(statistics.nonmanifold_vertex_count, 0)
        self.assertEqual(statistics.inconsistent_winding_edge_count, 0)
        self.assertEqual(statistics.degenerate_face_count, 0)
        self.assertEqual(statistics.duplicate_face_count, 0)
        self.assertTrue(statistics.is_watertight)
        self.assertTrue(statistics.is_manifold)
        self.assertTrue(math.isfinite(statistics.signed_volume))
        self.assertNotEqual(statistics.signed_volume, 0.0)
        self.assertEqual(
            statistics.bounds,
            ((-20.0, -20.0, -20.0), (20.0, 20.0, 20.0)),
        )

    def test_exact_standard_preview_is_deterministic_and_closed(self):
        request = schwarz_p_surface()
        first = generate_tpms_volume(request)
        second = generate_tpms_volume(request)
        self.assertEqual(
            first.cost_estimate.effective_resolution, (30, 30, 30)
        )
        self.assert_clean_closed(first)
        self.assertEqual(first.mesh, second.mesh)
        self.assertEqual(first.digest, second.digest)
        self.assertEqual(
            first.digest,
            "89a2b5b3308767bca015a00abaa27dfd59e9f7ffd075ca666f444c098e5bf8c2",
        )

    def test_final_preview_and_apply_resolve_exact_isovalue_ambiguity(self):
        preview = generate_tpms_volume(
            schwarz_p_surface(preview_quality=PreviewQuality.FINAL)
        )
        apply = generate_tpms_volume(
            schwarz_p_surface(
                execution_context=VolumeExecutionContext.APPLY
            )
        )
        self.assertEqual(
            preview.cost_estimate.effective_resolution, (40, 40, 40)
        )
        self.assert_clean_closed(preview)
        self.assertEqual(preview.mesh, apply.mesh)
        self.assertEqual(preview.digest, apply.digest)
        self.assertEqual(
            preview.digest,
            "56a568e21f4b1644c8142a465e6d0e5f1cc70808f51926a9b2744b185e79806c",
        )

    def test_draft_standard_and_final_are_valid(self):
        for quality, effective in (
            (PreviewQuality.DRAFT, (20, 20, 20)),
            (PreviewQuality.STANDARD, (30, 30, 30)),
            (PreviewQuality.FINAL, (40, 40, 40)),
        ):
            with self.subTest(quality=quality):
                result = generate_tpms_volume(
                    schwarz_p_surface(preview_quality=quality)
                )
                self.assertEqual(
                    result.cost_estimate.effective_resolution, effective
                )
                self.assert_clean_closed(result)

    def test_open_neighboring_iso_phase_and_non_cubic_cases_are_valid(self):
        cases = (
            schwarz_p_surface(boundary_mode=BoundaryMode.OPEN),
            schwarz_p_surface(iso_value=-0.01),
            schwarz_p_surface(iso_value=0.01),
            schwarz_p_surface(phase_x=-0.03),
            schwarz_p_surface(phase_x=0.03),
            schwarz_p_surface(
                width=44.0,
                depth=40.0,
                height=36.0,
                resolution_x=38,
                resolution_y=40,
                resolution_z=36,
            ),
        )
        for request in cases:
            with self.subTest(request=request):
                result = generate_tpms_volume(request)
                self.assertTrue(result.statistics.is_manifold)
                self.assertEqual(result.statistics.degenerate_face_count, 0)
                self.assertEqual(result.statistics.duplicate_face_count, 0)
                if request.boundary_mode is BoundaryMode.CAP:
                    self.assertTrue(result.statistics.is_watertight)

    def test_sample_grid_is_not_mutated_by_symbolic_classification(self):
        request = schwarz_p_surface(preview_quality=PreviewQuality.FINAL)
        estimate = estimate_volume_cost(request)
        field = TPMSFieldFactory.create(
            request.tpms_type,
            request.period,
            request.phase_x,
            request.phase_y,
            request.phase_z,
        )
        from volume.voxel_grid import VoxelGrid
        from volume.iso_surface import extract_isosurface

        grid = VoxelGrid.sample(
            field,
            request.minimum,
            request.maximum,
            estimate.effective_resolution,
        )
        values = grid.values
        first = extract_isosurface(grid, request.iso_value)
        second = extract_isosurface(grid, request.iso_value)
        self.assertIs(grid.values, values)
        self.assertEqual(first, second)
        self.assertEqual(first.statistics().degenerate_face_count, 0)


if __name__ == "__main__":
    unittest.main()
