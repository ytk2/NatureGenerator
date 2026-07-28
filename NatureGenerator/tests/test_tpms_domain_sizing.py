"""Focused Sprint 39 tests for TPMS rectangular-domain sizing modes."""

from dataclasses import replace
import math
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fusion.gyroid_volume import (
    _create_domain_diagnostic_inputs,
    _create_parameter_inputs,
    _parameter_input_id,
    _read_parameter_values,
    _update_domain_diagnostics,
    _update_parameter_visibility,
)
from fusion.gyroid_volume_preview import GyroidVolumePreviewController
from tests.test_gyroid_volume import FakeParameterInputs
from volume import (
    BoundaryMode,
    DOMAIN_CELL_COUNT_MAX,
    DomainMode,
    DomainSizingError,
    GeometryMode,
    PreviewQuality,
    TPMSType,
    TPMSVolumeRequest,
    VOLUME_PARAMETER_DEFINITIONS,
    VolumeExecutionContext,
    generate_tpms_volume,
    resolve_domain,
)


def cell_request(**overrides):
    values = {
        "domain_mode": DomainMode.CELL_COUNT,
        "cells_x": 1,
        "cells_y": 1,
        "cells_z": 1,
        "period": 20.0,
        "resolution_x": 12,
        "resolution_y": 12,
        "resolution_z": 12,
        "boundary_mode": BoundaryMode.CAP,
    }
    values.update(overrides)
    return TPMSVolumeRequest(**values)


def fake_adsk_core():
    return SimpleNamespace(
        DropDownStyles=SimpleNamespace(
            TextListDropDownStyle="text-list"
        ),
        ValueInput=SimpleNamespace(
            createByString=lambda expression: SimpleNamespace(
                value=float(expression.split()[0]) / 10.0
            )
        ),
    )


def select(control, display_name):
    control.selectedItem = next(
        item for item in control.listItems.items
        if item.name == display_name
    )


class DomainResolverTests(unittest.TestCase):
    def test_dimensions_preserve_exact_values_and_fractional_cells(self):
        domain = resolve_domain(
            DomainMode.DIMENSIONS,
            65.0,
            40.0,
            25.0,
            1,
            1,
            1,
            20.0,
        )
        self.assertEqual(domain.resolved_dimensions, (65.0, 40.0, 25.0))
        self.assertEqual(domain.effective_cell_counts, (3.25, 2.0, 1.25))
        self.assertEqual(domain.minimum, (-32.5, -20.0, -12.5))
        self.assertEqual(domain.maximum, (32.5, 20.0, 12.5))

    def test_cell_count_uniform_and_nonuniform_resolution(self):
        one = resolve_domain(
            DomainMode.CELL_COUNT, 60, 60, 60, 1, 1, 1, 20
        )
        nonuniform = resolve_domain(
            DomainMode.CELL_COUNT, 60, 60, 60, 3, 2, 4, 20
        )
        self.assertEqual(one.resolved_dimensions, (20.0, 20.0, 20.0))
        self.assertEqual(
            nonuniform.resolved_dimensions, (60.0, 40.0, 80.0)
        )
        self.assertEqual(
            nonuniform.minimum, (-30.0, -20.0, -40.0)
        )
        self.assertEqual(
            nonuniform.maximum, (30.0, 20.0, 40.0)
        )

    def test_resolution_and_phase_do_not_change_domain(self):
        request = cell_request(cells_x=3, cells_y=2, cells_z=4)
        changed = replace(
            request,
            resolution_x=24,
            resolution_y=18,
            resolution_z=30,
            phase_x=0.7,
            phase_y=-0.4,
            phase_z=0.2,
        )
        self.assertEqual(request.domain, changed.domain)
        self.assertEqual(
            request.resolved_dimensions, changed.resolved_dimensions
        )

    def test_domain_is_deterministic_and_immutable(self):
        first = resolve_domain(
            DomainMode.CELL_COUNT, 60, 60, 60, 3, 2, 1, 20
        )
        second = resolve_domain(
            DomainMode.CELL_COUNT, 60, 60, 60, 3, 2, 1, 20
        )
        self.assertEqual(first, second)
        with self.assertRaises(Exception):
            first.resolved_dimensions = (1.0, 1.0, 1.0)

    def test_spacing_and_intervals_per_cell_are_diagnostic_only(self):
        domain = resolve_domain(
            DomainMode.CELL_COUNT, 60, 60, 60, 3, 2, 1, 20
        )
        self.assertEqual(
            domain.sample_spacing((18, 14, 10)),
            (60.0 / 17.0, 40.0 / 13.0, 20.0 / 9.0),
        )
        self.assertEqual(
            domain.intervals_per_cell((18, 14, 10)),
            (17.0 / 3.0, 13.0 / 2.0, 9.0),
        )


class DomainValidationTests(unittest.TestCase):
    def test_invalid_cell_counts_are_rejected(self):
        invalid = (0, -1, 1.5, float("nan"), float("inf"), 51)
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises((TypeError, DomainSizingError)):
                    cell_request(cells_x=value)

    def test_cell_metadata_range_is_explicit(self):
        definitions = {
            item.parameter_id: item
            for item in VOLUME_PARAMETER_DEFINITIONS
        }
        self.assertEqual(definitions["cells_x"].minimum, 1)
        self.assertEqual(
            definitions["cells_x"].maximum, DOMAIN_CELL_COUNT_MAX
        )

    def test_calculated_dimension_limit_has_actionable_context(self):
        with self.assertRaisesRegex(
            DomainSizingError,
            "Cells X = 30.*Period = 20 mm.*Width = 600 mm.*"
            "500 mm domain limit.*Reduce Cells X or Period",
        ):
            cell_request(cells_x=30)

    def test_nonfinite_or_unbounded_products_are_rejected(self):
        for period in (float("nan"), float("inf"), 500.0):
            with self.subTest(period=period):
                with self.assertRaises(ValueError):
                    cell_request(cells_x=50, period=period)

    def test_rejection_occurs_before_scalar_allocation(self):
        with patch("volume.VoxelGrid.sample") as sample:
            with self.assertRaises(DomainSizingError):
                generate_tpms_volume(cell_request(cells_x=30))
        sample.assert_not_called()

    def test_sample_limit_error_includes_resolved_domain_context(self):
        oversized = cell_request(
            execution_context=VolumeExecutionContext.PREVIEW,
            preview_quality=PreviewQuality.FINAL,
            resolution_x=100,
            resolution_y=100,
            resolution_z=100,
        )
        with patch("volume.VoxelGrid.sample") as sample:
            with self.assertRaisesRegex(
                ValueError,
                "Domain Mode cell_count.*Cells 1 × 1 × 1.*Period 20 mm.*"
                "resolved size 20 × 20 × 20 mm.*resolution 100 × 100 × 100.*"
                "1,000,000 scalar samples.*750,000",
            ):
                generate_tpms_volume(oversized)
        sample.assert_not_called()


class DomainCompatibilityAndGeometryTests(unittest.TestCase):
    CELL_DIGESTS = {
        TPMSType.GYROID:
            "fe6a087444169a43085f489146137ed85018ded8fb1fadd1289264d819477b49",
        TPMSType.SCHWARZ_P:
            "2252448fd26fdb441912636bc81d623a841db9060fe81ff801f47b9caecc23c7",
        TPMSType.DIAMOND:
            "351af418f4e30599daeb77ba9bd9e9043b015b404ee41c78fc3a2e935845387b",
        TPMSType.NEOVIUS:
            "11095ec55be8fca20e83adc75719712df99a0d72b8c4f786e21ba5ba8077ed88",
    }

    def test_omitted_mode_is_dimensions_and_preserves_sprint_38_digest(self):
        request = TPMSVolumeRequest(
            resolution_x=16, resolution_y=16, resolution_z=16
        )
        self.assertIs(request.domain_mode, DomainMode.DIMENSIONS)
        self.assertEqual(
            generate_tpms_volume(request).digest,
            "2a762f15dcc93985901ac77d926357ef0b9d0b697137474bd30216c76992a0ba",
        )

    def test_sprint_38_positional_request_order_remains_compatible(self):
        positional = TPMSVolumeRequest(
            PreviewQuality.FINAL,
            TPMSType.GYROID,
            GeometryMode.SURFACE,
            1.0,
            60.0,
            40.0,
            20.0,
            20.0,
            0.0,
            12,
            14,
            16,
            0.1,
            -0.2,
            0.3,
            BoundaryMode.OPEN,
            VolumeExecutionContext.APPLY,
        )
        keyword = TPMSVolumeRequest(
            preview_quality=PreviewQuality.FINAL,
            width=60.0,
            depth=40.0,
            height=20.0,
            resolution_x=12,
            resolution_y=14,
            resolution_z=16,
            phase_x=0.1,
            phase_y=-0.2,
            phase_z=0.3,
        )
        self.assertEqual(positional, keyword)
        self.assertIs(positional.domain_mode, DomainMode.DIMENSIONS)

    def test_equivalent_modes_produce_identical_geometry(self):
        common = {
            "period": 20.0,
            "resolution_x": 12,
            "resolution_y": 12,
            "resolution_z": 12,
            "boundary_mode": BoundaryMode.CAP,
        }
        dimensions = TPMSVolumeRequest(
            width=20.0, depth=20.0, height=20.0, **common
        )
        cells = TPMSVolumeRequest(
            domain_mode=DomainMode.CELL_COUNT,
            cells_x=1,
            cells_y=1,
            cells_z=1,
            **common
        )
        first = generate_tpms_volume(dimensions)
        second = generate_tpms_volume(cells)
        self.assertEqual(first.mesh, second.mesh)
        self.assertEqual(first.digest, second.digest)
        self.assertNotEqual(first.domain.mode, second.domain.mode)
        self.assertEqual(
            first.domain.resolved_dimensions,
            second.domain.resolved_dimensions,
        )

    def test_all_types_have_stable_clean_one_cell_geometry(self):
        for tpms_type, digest in self.CELL_DIGESTS.items():
            with self.subTest(tpms_type=tpms_type):
                first = generate_tpms_volume(
                    cell_request(tpms_type=tpms_type)
                )
                second = generate_tpms_volume(
                    cell_request(tpms_type=tpms_type)
                )
                statistics = first.statistics
                self.assertEqual(first.mesh, second.mesh)
                self.assertEqual(first.digest, digest)
                self.assertEqual(first.digest, second.digest)
                self.assertEqual(statistics.boundary_edge_count, 0)
                self.assertEqual(statistics.nonmanifold_edge_count, 0)
                self.assertEqual(statistics.nonmanifold_vertex_count, 0)
                self.assertEqual(
                    statistics.inconsistent_winding_edge_count, 0
                )
                self.assertEqual(statistics.degenerate_face_count, 0)
                self.assertEqual(statistics.duplicate_face_count, 0)
                self.assertTrue(statistics.is_watertight)
                self.assertTrue(statistics.is_manifold)
                self.assertTrue(math.isfinite(statistics.signed_volume))
                self.assertEqual(
                    statistics.bounds,
                    ((-10.0, -10.0, -10.0), (10.0, 10.0, 10.0)),
                )

    def test_nonuniform_fixture_digest_and_bounds(self):
        result = generate_tpms_volume(cell_request(
            cells_x=3,
            cells_y=2,
            cells_z=1,
            resolution_x=18,
            resolution_y=14,
            resolution_z=10,
        ))
        self.assertEqual(
            result.digest,
            "681ffab54ed8d9ab95c8c16248fff84bba75f0655cc33d0c262e05ad25c7e98a",
        )
        self.assertEqual(
            result.statistics.bounds,
            ((-30.0, -20.0, -10.0), (30.0, 20.0, 10.0)),
        )

    def test_all_types_geometry_and_boundary_modes_work(self):
        for tpms_type in TPMSType:
            for geometry_mode in GeometryMode:
                for boundary_mode in BoundaryMode:
                    with self.subTest(
                        tpms_type=tpms_type,
                        geometry_mode=geometry_mode,
                        boundary_mode=boundary_mode,
                    ):
                        result = generate_tpms_volume(cell_request(
                            tpms_type=tpms_type,
                            geometry_mode=geometry_mode,
                            boundary_mode=boundary_mode,
                            wall_thickness=1.0,
                            resolution_x=8,
                            resolution_y=8,
                            resolution_z=8,
                        ))
                        self.assertTrue(result.statistics.is_manifold)
                        if boundary_mode is BoundaryMode.CAP:
                            self.assertTrue(
                                result.statistics.is_watertight
                            )

    def test_all_preview_qualities_work_for_every_type(self):
        for tpms_type in TPMSType:
            for quality in PreviewQuality:
                with self.subTest(
                    tpms_type=tpms_type, quality=quality
                ):
                    result = generate_tpms_volume(cell_request(
                        tpms_type=tpms_type,
                        preview_quality=quality,
                        execution_context=VolumeExecutionContext.PREVIEW,
                        boundary_mode=BoundaryMode.OPEN,
                        resolution_x=8,
                        resolution_y=8,
                        resolution_z=8,
                    ))
                    self.assertTrue(result.statistics.is_manifold)

    def test_preview_quality_never_changes_resolved_dimensions(self):
        dimensions = []
        for quality in PreviewQuality:
            result = generate_tpms_volume(cell_request(
                preview_quality=quality,
                execution_context=VolumeExecutionContext.PREVIEW,
            ))
            dimensions.append(result.domain.resolved_dimensions)
        self.assertEqual(dimensions, [(20.0, 20.0, 20.0)] * 3)

    def test_result_and_cost_record_domain_diagnostics(self):
        result = generate_tpms_volume(cell_request(
            cells_x=3,
            cells_y=2,
            cells_z=1,
            resolution_x=18,
            resolution_y=14,
            resolution_z=10,
        ))
        self.assertEqual(result.domain, result.cost_estimate.domain)
        self.assertEqual(
            result.domain.requested_cell_counts, (3, 2, 1)
        )
        self.assertEqual(
            result.cost_estimate.sample_spacing,
            (60.0 / 17.0, 40.0 / 13.0, 20.0 / 9.0),
        )
        self.assertEqual(
            result.cost_estimate.intervals_per_cell,
            (17.0 / 3.0, 13.0 / 2.0, 9.0),
        )


class DomainFusionBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.inputs = FakeParameterInputs()
        self.controls = _create_parameter_inputs(
            self.inputs, fake_adsk_core(), VOLUME_PARAMETER_DEFINITIONS
        )
        self.diagnostics = _create_domain_diagnostic_inputs(self.inputs)
        _update_parameter_visibility(
            self.controls, VOLUME_PARAMETER_DEFINITIONS
        )
        _update_domain_diagnostics(
            self.controls,
            self.diagnostics,
            VOLUME_PARAMETER_DEFINITIONS,
        )

    def test_default_visibility_and_effective_cells(self):
        self.assertTrue(self.controls["width"].isVisible)
        self.assertFalse(self.controls["cells_x"].isVisible)
        self.assertEqual(
            self.diagnostics["effective_cells_x"].text, "3"
        )
        self.assertTrue(
            self.diagnostics["effective_cells_x"].isVisible
        )
        self.assertFalse(
            self.diagnostics["calculated_width"].isVisible
        )

    def test_cell_mode_visibility_and_calculated_size(self):
        select(self.controls["domain_mode"], "Cell Count")
        self.controls["cells_x"].value = 3
        self.controls["cells_y"].value = 2
        self.controls["cells_z"].value = 4
        _update_parameter_visibility(
            self.controls, VOLUME_PARAMETER_DEFINITIONS
        )
        domain = _update_domain_diagnostics(
            self.controls,
            self.diagnostics,
            VOLUME_PARAMETER_DEFINITIONS,
        )
        self.assertFalse(self.controls["width"].isVisible)
        self.assertTrue(self.controls["cells_x"].isVisible)
        self.assertEqual(domain.resolved_dimensions, (60.0, 40.0, 80.0))
        self.assertEqual(
            self.diagnostics["calculated_width"].text, "60 mm"
        )
        self.assertEqual(
            self.diagnostics["calculated_height"].text, "80 mm"
        )

    def test_mode_switch_preserves_both_parameter_banks(self):
        self.controls["width"].value = 6.5
        self.controls["depth"].value = 4.0
        self.controls["height"].value = 2.5
        select(self.controls["domain_mode"], "Cell Count")
        self.controls["cells_x"].value = 3
        self.controls["cells_y"].value = 2
        self.controls["cells_z"].value = 1
        _update_parameter_visibility(
            self.controls, VOLUME_PARAMETER_DEFINITIONS
        )
        select(self.controls["domain_mode"], "Dimensions")
        _update_parameter_visibility(
            self.controls, VOLUME_PARAMETER_DEFINITIONS
        )
        self.assertEqual(
            (
                self.controls["width"].value,
                self.controls["depth"].value,
                self.controls["height"].value,
            ),
            (6.5, 4.0, 2.5),
        )
        select(self.controls["domain_mode"], "Cell Count")
        self.assertEqual(
            (
                self.controls["cells_x"].value,
                self.controls["cells_y"].value,
                self.controls["cells_z"].value,
            ),
            (3, 2, 1),
        )

    def test_hidden_dimensions_do_not_drive_cell_request(self):
        select(self.controls["domain_mode"], "Cell Count")
        self.controls["width"].value = 6.5
        self.controls["depth"].value = 4.0
        self.controls["height"].value = 2.5
        values = _read_parameter_values(
            self.controls, VOLUME_PARAMETER_DEFINITIONS
        )
        request = TPMSVolumeRequest(
            domain_mode=DomainMode(values.pop("domain_mode")),
            **{
                key: value for key, value in values.items()
                if key not in (
                    "preview_quality",
                    "tpms_type",
                    "geometry_mode",
                    "boundary_mode",
                )
            }
        )
        self.assertEqual(request.resolved_dimensions, (20.0, 20.0, 20.0))

    def test_domain_change_cleans_owned_preview(self):
        controller = GyroidVolumePreviewController()
        body = SimpleNamespace(isValid=True, deleted=False)
        body.deleteMe = lambda: (
            setattr(body, "deleted", True),
            setattr(body, "isValid", False),
        )
        controller.replace(lambda: body)
        changed_id = _parameter_input_id("domain_mode")
        self.assertTrue(changed_id.startswith("gyroidVolume_"))
        controller.cleanup()
        select(self.controls["domain_mode"], "Cell Count")
        _update_parameter_visibility(
            self.controls, VOLUME_PARAMETER_DEFINITIONS
        )
        self.assertTrue(body.deleted)
        self.assertIsNone(controller.body)


if __name__ == "__main__":
    unittest.main()
