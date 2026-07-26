"""Focused Sprint 38 tests for the generalized TPMS Volume pipeline."""

from dataclasses import replace
import math
import unittest
from unittest.mock import patch

from fusion.gyroid_volume import COMMAND_ID, COMMAND_NAME, _body_name
from volume import (
    AnalyticalTPMSField,
    BoundaryMode,
    GeometryMode,
    GyroidVolumeField,
    GyroidVolumeRequest,
    PreviewQuality,
    TPMSFieldFactory,
    TPMSVolumeRequest,
    TPMS_NORMALIZATION_FACTORS,
    TPMS_TYPE_ORDER,
    TPMSType,
    VOLUME_PARAMETER_DEFINITIONS,
    VolumeExecutionContext,
    VolumeSafetyLimitError,
    estimate_volume_cost,
    generate_gyroid_volume,
    generate_tpms_volume,
)


def request(tpms_type, geometry_mode=GeometryMode.SURFACE,
            boundary_mode=BoundaryMode.OPEN, **overrides):
    values = {
        "tpms_type": tpms_type,
        "geometry_mode": geometry_mode,
        "boundary_mode": boundary_mode,
        "resolution_x": 16,
        "resolution_y": 16,
        "resolution_z": 16,
    }
    values.update(overrides)
    return TPMSVolumeRequest(**values)


class TPMSFieldMathematicsTests(unittest.TestCase):
    def test_ids_order_metadata_and_default_are_stable(self):
        self.assertEqual(
            tuple(item.value for item in TPMS_TYPE_ORDER),
            ("gyroid", "schwarz_p", "diamond", "neovius"),
        )
        definition = next(
            item for item in VOLUME_PARAMETER_DEFINITIONS
            if item.parameter_id == "tpms_type"
        )
        self.assertEqual(
            definition.choices,
            (
                ("gyroid", "Gyroid"),
                ("schwarz_p", "Schwarz P"),
                ("diamond", "Diamond"),
                ("neovius", "Neovius"),
            ),
        )
        self.assertIs(GyroidVolumeRequest().tpms_type, TPMSType.GYROID)

    def test_known_normalized_field_values(self):
        p = TPMSFieldFactory.create(TPMSType.SCHWARZ_P, 2.0 * math.pi)
        d = TPMSFieldFactory.create(TPMSType.DIAMOND, 2.0 * math.pi)
        n = TPMSFieldFactory.create(TPMSType.NEOVIUS, 2.0 * math.pi)
        self.assertAlmostEqual(p.normalized_sample(0.0, 0.0, 0.0), 1.0)
        self.assertAlmostEqual(
            d.normalized_sample(
                math.pi / 2.0, math.pi / 2.0, math.pi / 2.0
            ),
            0.5,
        )
        self.assertAlmostEqual(n.normalized_sample(0.0, 0.0, 0.0), 1.0)

    def test_gyroid_factory_preserves_existing_field_exactly(self):
        field = TPMSFieldFactory.create(TPMSType.GYROID, 20.0, 0.2, -0.3, 0.4)
        legacy = GyroidVolumeField(20.0, 0.2, -0.3, 0.4)
        self.assertIsInstance(field, GyroidVolumeField)
        for point in ((0.0, 0.0, 0.0), (3.1, -4.2, 5.3)):
            self.assertEqual(field(*point), legacy(*point))
            self.assertEqual(field.gradient(*point), legacy.gradient(*point))

    def test_all_fields_are_periodic_and_phase_sensitive(self):
        point = (2.3, -4.7, 6.1)
        for tpms_type in TPMSType:
            with self.subTest(tpms_type=tpms_type):
                field = TPMSFieldFactory.create(tpms_type, 20.0)
                self.assertAlmostEqual(
                    field(*point),
                    field(point[0] + 20.0, point[1], point[2]),
                    places=12,
                )
                shifted = TPMSFieldFactory.create(
                    tpms_type, 20.0, 0.3, -0.2, 0.1
                )
                self.assertNotEqual(field(*point), shifted(*point))

    def test_analytical_world_gradients_match_finite_differences(self):
        point = (2.7, -4.1, 6.3)
        step = 1e-5
        for tpms_type in TPMSType:
            field = TPMSFieldFactory.create(
                tpms_type, 23.0, 0.31, -0.17, 0.23
            )
            analytical = field.gradient(*point)
            numerical = []
            for axis in range(3):
                before, after = list(point), list(point)
                before[axis] -= step
                after[axis] += step
                numerical.append(
                    (field(*after) - field(*before)) / (2.0 * step)
                )
            for actual, expected in zip(analytical, numerical):
                self.assertAlmostEqual(actual, expected, places=8)
                self.assertTrue(math.isfinite(actual))

    def test_period_scaling_and_normalization_apply_to_gradient(self):
        for tpms_type in TPMSType:
            short = TPMSFieldFactory.create(tpms_type, 10.0)
            long = TPMSFieldFactory.create(tpms_type, 20.0)
            normalized = (0.7, -0.4, 1.1)
            short_point = tuple(value * 10.0 / (2.0 * math.pi)
                                for value in normalized)
            long_point = tuple(value * 20.0 / (2.0 * math.pi)
                               for value in normalized)
            self.assertAlmostEqual(short(*short_point), long(*long_point))
            for short_value, long_value in zip(
                short.gradient(*short_point), long.gradient(*long_point)
            ):
                self.assertAlmostEqual(short_value, 2.0 * long_value)
            self.assertGreater(TPMS_NORMALIZATION_FACTORS[tpms_type], 0.0)

    def test_factory_rejects_unknown_type(self):
        with self.assertRaisesRegex(TypeError, "TPMSType"):
            TPMSFieldFactory.create("gyroid", 20.0)


class TPMSGeometryTests(unittest.TestCase):
    EXPECTED_DIGESTS = {
        (TPMSType.SCHWARZ_P, GeometryMode.SURFACE, BoundaryMode.OPEN):
            "28e2cab7c5f2cd2463e656249b132076f8a7a05dd8d804fb29ace4e6f327bcda",
        (TPMSType.SCHWARZ_P, GeometryMode.SURFACE, BoundaryMode.CAP):
            "076f806b037e3092955894eda4aa458b4ead5116262c823ef575dd2233f465a2",
        (TPMSType.SCHWARZ_P, GeometryMode.THICKENED, BoundaryMode.OPEN):
            "9f7236c9b2cacc5486e4d90061e750f5b48a20e36dd96ccfae7d7825e68fa868",
        (TPMSType.SCHWARZ_P, GeometryMode.THICKENED, BoundaryMode.CAP):
            "163be17122504751b39bc19288542c282fc487e50b61cc687b3a672a05999186",
        (TPMSType.DIAMOND, GeometryMode.SURFACE, BoundaryMode.OPEN):
            "ec2127e00408b6abdd21fe001cc8c3047fd864f8207f666ee0da0b9aea27221d",
        (TPMSType.DIAMOND, GeometryMode.SURFACE, BoundaryMode.CAP):
            "60947b54f5a02175d98d0854df11820f0dc09ef3c8c0304b2d8b3a4c3472fc19",
        (TPMSType.DIAMOND, GeometryMode.THICKENED, BoundaryMode.OPEN):
            "802a57fb17bff07f55ff520b153fcbcd8825d32bfb0b8152b7959a8b25d286bd",
        (TPMSType.DIAMOND, GeometryMode.THICKENED, BoundaryMode.CAP):
            "2b158c20bebcb5b1a56f84851060943f60036c221681d8519d5dde6ca92802a7",
        (TPMSType.NEOVIUS, GeometryMode.SURFACE, BoundaryMode.OPEN):
            "d7794d29f525305a1674d4b2b757cee0a3bd8589312c85eceae307375c51cdc2",
        (TPMSType.NEOVIUS, GeometryMode.SURFACE, BoundaryMode.CAP):
            "5d66100c45f2f168acf45de7ab2df2d2c88e113221553358ed2845d5ccb460a8",
        (TPMSType.NEOVIUS, GeometryMode.THICKENED, BoundaryMode.OPEN):
            "7909555effec3ce6d77e004dc7ea8106a8cd2d566b6792d2c09334ec78502830",
        (TPMSType.NEOVIUS, GeometryMode.THICKENED, BoundaryMode.CAP):
            "33fbd1b724bcd5aad386f9287a1c91d51301a159e8b2dcacf4d9b3d5b3912071",
    }
    DEFAULT_40_DIGESTS = {
        (TPMSType.SCHWARZ_P, GeometryMode.SURFACE, BoundaryMode.OPEN):
            "abb49b825925112354da76425fe675a6db3ca2eac700360608a249550c0eb54f",
        (TPMSType.SCHWARZ_P, GeometryMode.SURFACE, BoundaryMode.CAP):
            "385cd6cecbb995ab2bb28cb54f5807ddc013e4bbaf9a5457e2f6e85ef581ef74",
        (TPMSType.SCHWARZ_P, GeometryMode.THICKENED, BoundaryMode.OPEN):
            "cb454fce5840b3899872c5b4927c6505891b12109f440784bc7ba70e8ced05f7",
        (TPMSType.SCHWARZ_P, GeometryMode.THICKENED, BoundaryMode.CAP):
            "e32e329900af6cff18a4f1327796c28c559ef05a485c2f6207411263dc02e662",
        (TPMSType.DIAMOND, GeometryMode.SURFACE, BoundaryMode.OPEN):
            "d00d0d6c0cecba8fb9e513659cfbb57768064fb08f03a6c3faead6e486a3497c",
        (TPMSType.DIAMOND, GeometryMode.SURFACE, BoundaryMode.CAP):
            "7b27544a693bf3a5010aac09b8bb91da5302ea91fce42263326112d4620f7fa7",
        (TPMSType.DIAMOND, GeometryMode.THICKENED, BoundaryMode.OPEN):
            "f4dcab0120b27735136a496e7a66e718c28e54acfa5e061b093e7cd6d988a6e3",
        (TPMSType.DIAMOND, GeometryMode.THICKENED, BoundaryMode.CAP):
            "e7b398beca79a7365bf3d3f7bb1595603ac0975b847d68adc74b774a817d42a5",
        (TPMSType.NEOVIUS, GeometryMode.SURFACE, BoundaryMode.OPEN):
            "95dae538731017e54cd9916370de9c0d5deae89632d69b5a5066a78b1779bb99",
        (TPMSType.NEOVIUS, GeometryMode.SURFACE, BoundaryMode.CAP):
            "52a8f2079ccdada74da01b73580d34b1cc46db8c2dcbdfb6ad527cce97493c5c",
        (TPMSType.NEOVIUS, GeometryMode.THICKENED, BoundaryMode.OPEN):
            "9c6b35ff339cffa63e88d79932bf0f48c26fb6b7d11a2a095f33bb4e163a68d4",
        (TPMSType.NEOVIUS, GeometryMode.THICKENED, BoundaryMode.CAP):
            "04534d7f2de99e7f7cda57078a5fc4fab55aece918ae1d11e15661a494ed1d8c",
    }

    def test_new_default_40_digests_are_stable(self):
        for key, digest in self.DEFAULT_40_DIGESTS.items():
            with self.subTest(key=key):
                result = generate_tpms_volume(
                    TPMSVolumeRequest(
                        tpms_type=key[0],
                        geometry_mode=key[1],
                        boundary_mode=key[2],
                    )
                )
                self.assertEqual(result.digest, digest)

    def test_new_types_all_combinations_have_stable_clean_geometry(self):
        for key, digest in self.EXPECTED_DIGESTS.items():
            tpms_type, geometry_mode, boundary_mode = key
            with self.subTest(key=key):
                first = generate_tpms_volume(
                    request(tpms_type, geometry_mode, boundary_mode)
                )
                second = generate_tpms_volume(
                    request(tpms_type, geometry_mode, boundary_mode)
                )
                stats = first.statistics
                self.assertEqual(first.mesh, second.mesh)
                self.assertEqual(first.digest, digest)
                self.assertEqual(first.digest, second.digest)
                self.assertEqual(stats.degenerate_face_count, 0)
                self.assertEqual(stats.duplicate_face_count, 0)
                self.assertEqual(stats.inconsistent_winding_edge_count, 0)
                self.assertTrue(all(
                    math.isfinite(value)
                    for vertex in first.mesh.vertices for value in vertex
                ))
                if geometry_mode is GeometryMode.THICKENED:
                    self.assertTrue(stats.is_manifold)
                    if boundary_mode is BoundaryMode.OPEN:
                        self.assertGreater(stats.boundary_edge_count, 0)
                    else:
                        self.assertTrue(stats.is_watertight)
                        self.assertEqual(stats.boundary_edge_count, 0)
                        self.assertEqual(stats.nonmanifold_edge_count, 0)
                        self.assertEqual(stats.nonmanifold_vertex_count, 0)
                        self.assertTrue(math.isfinite(stats.signed_volume))
                        self.assertGreater(stats.signed_volume, 0.0)

    def test_types_are_distinct_and_parameters_change_each_type(self):
        baselines = {}
        for tpms_type in TPMSType:
            baseline = generate_tpms_volume(request(tpms_type)).digest
            baselines[tpms_type] = baseline
            for changed in (
                request(tpms_type, period=24.0),
                request(tpms_type, iso_value=0.2),
                request(tpms_type, phase_x=0.3, phase_y=-0.2, phase_z=0.1),
            ):
                self.assertNotEqual(
                    generate_tpms_volume(changed).digest, baseline
                )
        self.assertEqual(len(set(baselines.values())), len(TPMSType))

    def test_thickness_non_cubic_dimensions_and_axis_resolution_work(self):
        for tpms_type in TPMSType:
            base = request(
                tpms_type, GeometryMode.THICKENED, BoundaryMode.CAP,
                width=55.0, depth=48.0, height=42.0,
                resolution_x=14, resolution_y=15, resolution_z=16,
            )
            first = generate_tpms_volume(base)
            thicker = generate_tpms_volume(
                replace(base, wall_thickness=1.5)
            )
            self.assertTrue(first.statistics.is_watertight)
            self.assertTrue(first.statistics.is_manifold)
            self.assertNotEqual(first.digest, thicker.digest)

    def test_backward_compatible_api_uses_single_pipeline(self):
        legacy = GyroidVolumeRequest(
            resolution_x=16, resolution_y=16, resolution_z=16
        )
        self.assertEqual(
            generate_gyroid_volume(legacy),
            generate_tpms_volume(legacy),
        )


class TPMSPreviewSafetyTests(unittest.TestCase):
    def test_command_identity_and_type_aware_names(self):
        self.assertEqual(COMMAND_ID, "NatureGeneratorGyroidVolume")
        self.assertEqual(COMMAND_NAME, "TPMS Volume")
        for tpms_type, label in (
            (TPMSType.GYROID, "Gyroid"),
            (TPMSType.SCHWARZ_P, "Schwarz P"),
            (TPMSType.DIAMOND, "Diamond"),
            (TPMSType.NEOVIUS, "Neovius"),
        ):
            self.assertEqual(
                _body_name(tpms_type, True),
                "NatureGenerator Preview — TPMS — " + label,
            )
            self.assertEqual(
                _body_name(tpms_type, False),
                "NatureGenerator — TPMS — " + label,
            )

    def test_all_types_support_preview_qualities_and_apply_final_resolution(self):
        for tpms_type in TPMSType:
            detail = []
            for quality, effective in (
                (PreviewQuality.DRAFT, (8, 8, 8)),
                (PreviewQuality.STANDARD, (12, 12, 12)),
                (PreviewQuality.FINAL, (16, 16, 16)),
            ):
                value = request(
                    tpms_type,
                    preview_quality=quality,
                    execution_context=VolumeExecutionContext.PREVIEW,
                )
                result = generate_tpms_volume(value)
                self.assertEqual(
                    result.cost_estimate.effective_resolution, effective
                )
                detail.append(result.statistics.face_count)
            self.assertLess(detail[0], detail[1])
            self.assertLess(detail[1], detail[2])
            applied = generate_tpms_volume(
                request(tpms_type, preview_quality=PreviewQuality.DRAFT)
            )
            self.assertEqual(
                applied.cost_estimate.effective_resolution, (16, 16, 16)
            )

    def test_final_preview_and_apply_match_for_every_type(self):
        for tpms_type in TPMSType:
            preview = generate_tpms_volume(
                request(
                    tpms_type,
                    preview_quality=PreviewQuality.FINAL,
                    execution_context=VolumeExecutionContext.PREVIEW,
                )
            )
            apply = generate_tpms_volume(request(tpms_type))
            self.assertEqual(preview.mesh, apply.mesh)
            self.assertEqual(preview.digest, apply.digest)

    def test_cost_identity_and_rejection_include_tpms_context(self):
        value = request(
            TPMSType.DIAMOND,
            GeometryMode.THICKENED,
            BoundaryMode.CAP,
            resolution_x=160,
            resolution_y=160,
            resolution_z=160,
            execution_context=VolumeExecutionContext.PREVIEW,
            preview_quality=PreviewQuality.FINAL,
        )
        estimate = estimate_volume_cost(value)
        self.assertIs(estimate.tpms_type, TPMSType.DIAMOND)
        with patch("volume.sample_thickened_band_grids") as sample:
            with self.assertRaisesRegex(
                VolumeSafetyLimitError,
                "TPMS Type diamond, Geometry Mode thickened, Boundary Mode cap"
                ".*Wall Thickness.*Preview.*Final|Preview.*Final.*TPMS Type diamond",
            ):
                generate_tpms_volume(value)
        sample.assert_not_called()

    def test_type_change_preserves_compatible_values(self):
        original = request(
            TPMSType.GYROID,
            width=51.0,
            period=19.0,
            iso_value=0.2,
            phase_x=0.3,
            resolution_x=17,
        )
        changed = replace(original, tpms_type=TPMSType.NEOVIUS)
        self.assertEqual(changed.width, original.width)
        self.assertEqual(changed.period, original.period)
        self.assertEqual(changed.iso_value, original.iso_value)
        self.assertEqual(changed.phase_x, original.phase_x)
        self.assertEqual(changed.resolution, original.resolution)

    def test_invalid_shared_iso_and_wall_thickness_are_rejected(self):
        for tpms_type in TPMSType:
            with self.assertRaisesRegex(ValueError, "Iso Value"):
                request(tpms_type, iso_value=1.5001)
            with self.assertRaisesRegex(ValueError, "Wall Thickness"):
                request(
                    tpms_type,
                    GeometryMode.THICKENED,
                    wall_thickness=0.0,
                )


if __name__ == "__main__":
    unittest.main()
