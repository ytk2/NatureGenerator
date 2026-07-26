"""Focused tests for the Fusion-independent Gyroid Volume pipeline."""

import math
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

from commands.gyroid_volume import execute_gyroid_volume
from fusion.gyroid_volume import (
    _create_parameter_inputs,
    _read_parameter_values,
    _update_parameter_visibility,
)
from fusion.gyroid_volume_preview import GyroidVolumePreviewController
from fusion import gyroid_volume as volume_runtime
from tests.test_fusion_integration import (
    FakeCommand,
    fake_adsk_modules,
    fake_fusion_ui,
)
from volume import (
    BoundaryMode,
    GeometryMode,
    GyroidVolumeField,
    GyroidVolumeRequest,
    VOLUME_APPLY_MAX_SAMPLES,
    VOLUME_PARAMETER_DEFINITIONS,
    VOLUME_PREVIEW_MAX_SAMPLES,
    VolumeExecutionContext,
    VolumeSafetyLimitError,
    enforce_volume_sample_limit,
    estimate_volume_size,
    generate_gyroid_volume,
    validate_volume_size,
)


def request(**overrides):
    values = {
        "resolution_x": 16,
        "resolution_y": 16,
        "resolution_z": 16,
    }
    values.update(overrides)
    return GyroidVolumeRequest(**values)


class GyroidVolumeFieldTests(unittest.TestCase):
    def test_field_is_deterministic_and_periodic(self):
        field = GyroidVolumeField(20.0, 0.2, -0.4, 0.7)
        point = (3.25, -7.5, 11.75)
        self.assertEqual(field(*point), field(*point))
        self.assertAlmostEqual(
            field(*point),
            field(point[0] + 20.0, point[1], point[2]),
        )
        self.assertAlmostEqual(
            field(*point),
            field(point[0], point[1] - 20.0, point[2]),
        )

    def test_phase_changes_field(self):
        point = (3.0, 5.0, 7.0)
        baseline = GyroidVolumeField(20.0)(*point)
        self.assertNotEqual(
            baseline, GyroidVolumeField(20.0, phase_x=0.8)(*point)
        )
        self.assertNotEqual(
            baseline, GyroidVolumeField(20.0, phase_y=-0.6)(*point)
        )
        self.assertNotEqual(
            baseline, GyroidVolumeField(20.0, phase_z=1.2)(*point)
        )


class GyroidVolumeRequestTests(unittest.TestCase):
    def test_metadata_defaults_ranges_types_and_units(self):
        definitions = {
            item.parameter_id: item
            for item in VOLUME_PARAMETER_DEFINITIONS
        }
        self.assertEqual(len(definitions), 14)
        self.assertEqual(
            definitions["geometry_mode"].choices,
            (("surface", "Surface"), ("thickened", "Thickened")),
        )
        self.assertEqual(definitions["geometry_mode"].default_value, "surface")
        self.assertEqual(definitions["wall_thickness"].default_value, 1.0)
        self.assertEqual(definitions["wall_thickness"].minimum, 0.1)
        self.assertEqual(definitions["wall_thickness"].maximum, 20.0)
        self.assertEqual(
            definitions["wall_thickness"].visible_when,
            ("geometry_mode", ("thickened",)),
        )
        self.assertEqual(definitions["width"].default_value, 60.0)
        self.assertEqual(definitions["period"].unit, "mm")
        self.assertEqual(definitions["iso_value"].minimum, -1.5)
        self.assertEqual(definitions["resolution_x"].minimum, 8)
        self.assertEqual(definitions["resolution_x"].maximum, 160)
        self.assertEqual(definitions["phase_z"].unit, "rad")
        self.assertEqual(
            definitions["boundary_mode"].choices,
            (("open", "Open"), ("cap", "Cap")),
        )

    def test_request_is_centered_and_validated(self):
        value = GyroidVolumeRequest()
        self.assertEqual(value.minimum, (-30.0, -30.0, -30.0))
        self.assertEqual(value.maximum, (30.0, 30.0, 30.0))
        self.assertEqual(value.resolution, (40, 40, 40))
        self.assertIs(value.boundary_mode, BoundaryMode.OPEN)
        self.assertIs(value.geometry_mode, GeometryMode.SURFACE)
        with self.assertRaisesRegex(ValueError, "Width"):
            GyroidVolumeRequest(width=0.0)
        with self.assertRaisesRegex(ValueError, "Resolution X"):
            GyroidVolumeRequest(resolution_x=7)
        with self.assertRaisesRegex(TypeError, "Resolution X"):
            GyroidVolumeRequest(resolution_x=40.0)


class VolumeSafetyPolicyTests(unittest.TestCase):
    def test_estimate_uses_checked_integer_products(self):
        estimate = estimate_volume_size(40, 50, 60)
        self.assertEqual(estimate.sample_count, 120_000)
        self.assertEqual(estimate.cell_count, 39 * 49 * 59)
        self.assertEqual(estimate.scalar_bytes, 960_000)
        self.assertIsInstance(estimate.sample_count, int)

    def test_preview_limit_accepts_exact_boundary_and_rejects_next(self):
        self.assertEqual(
            enforce_volume_sample_limit(
                750_000, (100, 100, 75),
                VolumeExecutionContext.PREVIEW,
            ),
            VOLUME_PREVIEW_MAX_SAMPLES,
        )
        with self.assertRaisesRegex(
            VolumeSafetyLimitError,
            "750,001 scalar samples.*Preview limit of 750,000",
        ):
            enforce_volume_sample_limit(
                750_001, (100, 100, 76),
                VolumeExecutionContext.PREVIEW,
            )

    def test_apply_limit_accepts_exact_boundary_and_rejects_next(self):
        self.assertEqual(
            enforce_volume_sample_limit(
                2_000_000, (125, 100, 160),
                VolumeExecutionContext.APPLY,
            ),
            VOLUME_APPLY_MAX_SAMPLES,
        )
        with self.assertRaisesRegex(
            VolumeSafetyLimitError,
            "2,000,001 scalar samples.*Apply limit of 2,000,000",
        ):
            enforce_volume_sample_limit(
                2_000_001, (125, 101, 160),
                VolumeExecutionContext.APPLY,
            )

    def test_validation_uses_resolution_product(self):
        self.assertEqual(
            validate_volume_size(
                100, 100, 75, VolumeExecutionContext.PREVIEW
            ).sample_count,
            750_000,
        )
        with self.assertRaises(VolumeSafetyLimitError):
            validate_volume_size(
                100, 100, 76, VolumeExecutionContext.PREVIEW
            )

    def test_oversized_request_is_rejected_before_sampling(self):
        oversized = request(
            resolution_x=100,
            resolution_y=100,
            resolution_z=100,
            execution_context=VolumeExecutionContext.PREVIEW,
        )
        with patch("volume.VoxelGrid.sample") as sample:
            with self.assertRaises(VolumeSafetyLimitError):
                generate_gyroid_volume(oversized)
            sample.assert_not_called()


class GyroidVolumeGeometryTests(unittest.TestCase):
    def test_default_focused_fixture_has_stable_digest(self):
        first = generate_gyroid_volume(request())
        second = generate_gyroid_volume(request())
        self.assertEqual(first.mesh, second.mesh)
        self.assertEqual(
            first.digest,
            "2a762f15dcc93985901ac77d926357ef0b9d0b697137474bd30216c76992a0ba",
        )
        self.assertEqual(first.digest, second.digest)

    def test_iso_resolution_dimensions_and_phases_change_mesh(self):
        baseline = generate_gyroid_volume(request()).digest
        alternatives = (
            request(iso_value=0.35),
            request(resolution_x=17),
            request(width=55.0),
            request(depth=52.0),
            request(height=48.0),
            request(phase_x=0.5),
            request(phase_y=-0.7),
            request(phase_z=0.9),
        )
        for changed in alternatives:
            with self.subTest(changed=changed):
                self.assertNotEqual(
                    generate_gyroid_volume(changed).digest, baseline
                )

    def test_geometry_is_finite_oriented_nondegenerate_and_measured_open(self):
        result = generate_gyroid_volume(request())
        statistics = result.statistics
        self.assertTrue(all(
            math.isfinite(coordinate)
            for vertex in result.mesh.vertices
            for coordinate in vertex
        ))
        self.assertEqual(statistics.degenerate_face_count, 0)
        self.assertEqual(statistics.inconsistent_winding_edge_count, 0)
        self.assertEqual(statistics.nonmanifold_edge_count, 0)
        self.assertGreater(statistics.boundary_edge_count, 0)
        self.assertFalse(statistics.is_watertight)
        self.assertTrue(statistics.is_manifold)
        self.assertEqual(result.boundary_behavior, "open_at_bounds")
        self.assertEqual(
            statistics.bounds,
            ((-30.0, -30.0, -30.0), (30.0, 30.0, 30.0)),
        )
        self.assertGreater(statistics.surface_area, 0.0)


class FakeParameterInputs:
    def __init__(self):
        self.created = {}

    def addValueInput(self, input_id, name, unit, initial):
        value = SimpleNamespace(
            id=input_id, name=name, unit=unit, value=initial.value
        )
        self.created[input_id] = value
        return value

    def addFloatSpinnerCommandInput(
        self, input_id, name, unit, minimum, maximum, step, initial
    ):
        value = SimpleNamespace(
            id=input_id, name=name, unit=unit, value=initial,
            minimumValue=minimum, maximumValue=maximum,
        )
        self.created[input_id] = value
        return value

    def addIntegerSpinnerCommandInput(
        self, input_id, name, minimum, maximum, step, initial
    ):
        return self.addFloatSpinnerCommandInput(
            input_id, name, "", minimum, maximum, step, initial
        )

    def addDropDownCommandInput(self, input_id, name, style):
        control = SimpleNamespace(
            id=input_id, name=name, selectedItem=None
        )
        items = []

        def add(display_name, selected, icon):
            item = SimpleNamespace(name=display_name)
            items.append(item)
            if selected:
                control.selectedItem = item
            return item

        control.listItems = SimpleNamespace(add=add, items=items)
        self.created[input_id] = control
        return control


class VolumeFusionBoundaryTests(unittest.TestCase):
    def test_metadata_drives_all_ui_parameters(self):
        inputs = FakeParameterInputs()
        adsk_core = SimpleNamespace(
            DropDownStyles=SimpleNamespace(
                TextListDropDownStyle="text-list"
            ),
            ValueInput=SimpleNamespace(
                createByString=lambda expression: SimpleNamespace(
                    value=float(expression.split()[0]) / 10.0
                )
            )
        )
        controls = _create_parameter_inputs(
            inputs, adsk_core, VOLUME_PARAMETER_DEFINITIONS
        )
        self.assertEqual(
            tuple(controls),
            tuple(
                definition.parameter_id
                for definition in VOLUME_PARAMETER_DEFINITIONS
            ),
        )
        values = _read_parameter_values(
            controls, VOLUME_PARAMETER_DEFINITIONS
        )
        _update_parameter_visibility(
            controls, VOLUME_PARAMETER_DEFINITIONS
        )
        self.assertFalse(controls["wall_thickness"].isVisible)
        controls["geometry_mode"].selectedItem = next(
            item for item in controls["geometry_mode"].listItems.items
            if item.name == "Thickened"
        )
        _update_parameter_visibility(
            controls, VOLUME_PARAMETER_DEFINITIONS
        )
        self.assertTrue(controls["wall_thickness"].isVisible)
        self.assertEqual(controls["wall_thickness"].value, 0.1)
        self.assertEqual(values["width"], 60.0)
        self.assertEqual(values["resolution_z"], 40)
        self.assertEqual(values["phase_x"], 0.0)
        self.assertEqual(values["boundary_mode"], "open")
        self.assertEqual(values["geometry_mode"], "surface")

    def test_apply_inserts_exactly_one_final_mesh(self):
        inserted = []
        sentinel = object()
        result, body = execute_gyroid_volume(
            request(),
            lambda mesh, name: inserted.append((mesh, name)) or sentinel,
            "NatureGenerator — Gyroid Volume",
        )
        self.assertIs(body, sentinel)
        self.assertEqual(
            inserted, [(result.mesh, "NatureGenerator — Gyroid Volume")]
        )

    def test_preview_replacement_cancel_and_stop_cleanup_are_owned(self):
        controller = GyroidVolumePreviewController()
        first = SimpleNamespace(isValid=True, deleted=False)
        first.deleteMe = lambda: setattr(first, "deleted", True)
        second = SimpleNamespace(isValid=True, deleted=False)
        second.deleteMe = lambda: setattr(second, "deleted", True)
        unrelated = SimpleNamespace(isValid=True, deleted=False)

        controller.replace(lambda: first)
        controller.replace(lambda: second)
        self.assertTrue(first.deleted)
        self.assertFalse(unrelated.deleted)
        controller.cleanup()
        self.assertTrue(second.deleted)
        self.assertFalse(unrelated.deleted)

    def test_oversized_preview_rejection_leaves_no_stale_preview(self):
        controller = GyroidVolumePreviewController()
        previous = SimpleNamespace(isValid=True, deleted=False)
        previous.deleteMe = lambda: setattr(previous, "deleted", True)
        controller.replace(lambda: previous)

        def reject():
            enforce_volume_sample_limit(
                750_001,
                (100, 100, 76),
                VolumeExecutionContext.PREVIEW,
            )

        with self.assertRaises(VolumeSafetyLimitError):
            controller.replace(reject)
        self.assertTrue(previous.deleted)
        self.assertIsNone(controller.body)

    def test_independent_command_preview_apply_cancel_and_stop_lifecycle(self):
        app, ui, _, _ = fake_fusion_ui()
        bodies = []

        def build(mesh, name):
            body = SimpleNamespace(
                name=name, isValid=True, deleted=False, mesh=mesh
            )
            body.deleteMe = lambda: (
                setattr(body, "deleted", True),
                setattr(body, "isValid", False),
            )
            bodies.append(body)
            return body

        volume_runtime._started = False
        volume_runtime._handlers.clear()
        volume_runtime._command_handler_groups.clear()
        volume_runtime._preview_controllers.clear()
        with patch.dict(sys.modules, fake_adsk_modules(app)):
            with patch(
                "fusion.volume_mesh_builder.VolumeMeshBuilder.build",
                side_effect=build,
            ):
                volume_runtime.start()
                definition = ui.commandDefinitions.itemById(
                    volume_runtime.COMMAND_ID
                )
                command = FakeCommand()
                definition.commandCreated.handlers[0].notify(
                    SimpleNamespace(command=command)
                )
                for axis in ("x", "y", "z"):
                    command.commandInputs.items[
                        volume_runtime._parameter_input_id(
                            "resolution_{}".format(axis)
                        )
                    ].value = 8

                preview_input = command.commandInputs.items[
                    volume_runtime.PREVIEW_INPUT_ID
                ]
                command.inputChanged.handlers[0].notify(
                    SimpleNamespace(input=preview_input)
                )
                command.executePreview.handlers[0].notify(
                    SimpleNamespace(isValidResult=None)
                )
                self.assertEqual(len(bodies), 1)
                self.assertFalse(bodies[0].deleted)

                phase_values = {
                    "phase_x": 0.31,
                    "phase_y": -0.17,
                    "phase_z": 0.23,
                }
                for parameter_id, value in phase_values.items():
                    command.commandInputs.items[
                        volume_runtime._parameter_input_id(parameter_id)
                    ].value = value
                boundary_mode = command.commandInputs.items[
                    volume_runtime._parameter_input_id("boundary_mode")
                ]
                boundary_mode.selectedItem = next(
                    item for item in boundary_mode.listItems.items
                    if item.name == "Cap"
                )
                command.inputChanged.handlers[0].notify(
                    SimpleNamespace(input=boundary_mode)
                )
                self.assertTrue(bodies[0].deleted)
                command.inputChanged.handlers[0].notify(
                    SimpleNamespace(input=preview_input)
                )
                command.executePreview.handlers[0].notify(
                    SimpleNamespace(isValidResult=None)
                )
                self.assertEqual(len(bodies), 2)
                self.assertTrue(bodies[1].mesh.statistics().is_watertight)

                geometry_mode = command.commandInputs.items[
                    volume_runtime._parameter_input_id("geometry_mode")
                ]
                wall_thickness = command.commandInputs.items[
                    volume_runtime._parameter_input_id("wall_thickness")
                ]
                geometry_mode.selectedItem = next(
                    item for item in geometry_mode.listItems.items
                    if item.name == "Thickened"
                )
                command.inputChanged.handlers[0].notify(
                    SimpleNamespace(input=geometry_mode)
                )
                self.assertTrue(bodies[1].deleted)
                self.assertTrue(wall_thickness.isVisible)
                command.inputChanged.handlers[0].notify(
                    SimpleNamespace(input=preview_input)
                )
                command.executePreview.handlers[0].notify(
                    SimpleNamespace(isValidResult=None)
                )
                self.assertEqual(len(bodies), 3)
                self.assertTrue(bodies[2].mesh.statistics().is_watertight)

                wall_thickness.value = 0.15
                command.inputChanged.handlers[0].notify(
                    SimpleNamespace(input=wall_thickness)
                )
                self.assertTrue(bodies[2].deleted)
                command.inputChanged.handlers[0].notify(
                    SimpleNamespace(input=preview_input)
                )
                command.executePreview.handlers[0].notify(
                    SimpleNamespace(isValidResult=None)
                )
                self.assertEqual(len(bodies), 4)
                self.assertTrue(bodies[3].mesh.statistics().is_watertight)

                command.execute.handlers[0].notify(SimpleNamespace())
                self.assertTrue(bodies[3].deleted)
                self.assertEqual(len(bodies), 5)
                self.assertEqual(
                    bodies[4].name, "NatureGenerator — Gyroid Volume"
                )

                command.destroy.handlers[0].notify(SimpleNamespace())
                self.assertFalse(bodies[4].deleted)

                second_command = FakeCommand()
                definition.commandCreated.handlers[0].notify(
                    SimpleNamespace(command=second_command)
                )
                for axis in ("x", "y", "z"):
                    second_command.commandInputs.items[
                        volume_runtime._parameter_input_id(
                            "resolution_{}".format(axis)
                        )
                    ].value = 8
                second_preview = second_command.commandInputs.items[
                    volume_runtime.PREVIEW_INPUT_ID
                ]
                second_command.inputChanged.handlers[0].notify(
                    SimpleNamespace(input=second_preview)
                )
                second_command.executePreview.handlers[0].notify(
                    SimpleNamespace(isValidResult=None)
                )
                stop_owned = bodies[-1]
                volume_runtime.stop()
                self.assertTrue(stop_owned.deleted)
