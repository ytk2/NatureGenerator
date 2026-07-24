"""Tests for Procedural Lab Fusion adapters without Autodesk runtime."""

from types import SimpleNamespace
import unittest

from fusion.procedural_preview import ProceduralPreviewController
from fusion.procedural_runtime import (
    _create_parameter_inputs,
    _read_operator_parameters,
    _set_parameter_visibility,
)
from fusion.selection_adapter import (
    FusionSelectionError,
    _brep_polygon_mesh,
    _mesh_body_polygon_mesh,
    _polygon_mesh_data,
    selection_entities,
)
from procedural import DEFAULT_OPERATOR_REGISTRY


class FakeSelection:
    def __init__(self, entities):
        self.entities = entities
        self.selectionCount = len(entities)

    def selection(self, index):
        return SimpleNamespace(entity=self.entities[index])


class FusionSelectionTests(unittest.TestCase):
    def test_rejects_empty_and_multiple_selection(self):
        with self.assertRaisesRegex(FusionSelectionError, "exactly one"):
            selection_entities(FakeSelection([]))
        with self.assertRaisesRegex(FusionSelectionError, "multiple"):
            selection_entities(FakeSelection([object(), object()]))

    def test_polygon_mesh_converts_fusion_centimeters_to_millimeters(self):
        polygon = SimpleNamespace(
            nodeCoordinates=(
                SimpleNamespace(x=0, y=0, z=0),
                SimpleNamespace(x=1, y=0, z=0),
                SimpleNamespace(x=0, y=1, z=0),
            ),
            nodeIndices=(0, 1, 2),
        )
        mesh = _polygon_mesh_data(polygon)
        self.assertEqual(
            mesh.vertices, ((0, 0, 0), (10, 0, 0), (0, 10, 0))
        )
        self.assertEqual(mesh.faces, ((0, 1, 2),))

    def test_brep_calculator_tuple_and_flat_coordinates_are_supported(self):
        calculated = SimpleNamespace(
            nodeCoordinates=None,
            nodeCoordinatesAsDouble=(0, 0, 0, 1, 0, 0, 0, 1, 0),
            nodeIndices=(0, 1, 2),
        )
        calculator = SimpleNamespace(surfaceTolerance=0.0)
        calculator.calculate = lambda: (True, calculated)
        manager = SimpleNamespace(
            createMeshCalculator=lambda: calculator
        )
        body = SimpleNamespace(meshManager=manager)

        result = _brep_polygon_mesh(body, preview=True)
        mesh = _polygon_mesh_data(result)

        self.assertIs(result, calculated)
        self.assertEqual(
            mesh.vertices, ((0, 0, 0), (10, 0, 0), (0, 10, 0))
        )
        self.assertEqual(mesh.faces, ((0, 1, 2),))
        self.assertEqual(calculator.surfaceTolerance, 0.02)

    def test_mesh_body_prefers_triangular_display_mesh(self):
        display = SimpleNamespace(
            nodeCoordinates=(
                SimpleNamespace(x=0, y=0, z=0),
                SimpleNamespace(x=1, y=0, z=0),
                SimpleNamespace(x=0, y=1, z=0),
            ),
            nodeIndices=(0, 1, 2),
        )
        original_polygon = SimpleNamespace()
        body = SimpleNamespace(displayMesh=display, mesh=original_polygon)
        self.assertIs(_mesh_body_polygon_mesh(body), display)

    def test_polygon_mesh_quads_and_polygons_are_triangulated(self):
        points = tuple(
            SimpleNamespace(x=value[0], y=value[1], z=value[2])
            for value in (
                (0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
                (2, 0, 0), (3, 0, 0), (3, 1, 0), (2.5, 2, 0), (2, 1, 0),
            )
        )
        polygon = SimpleNamespace(
            nodeCoordinates=points,
            triangleNodeIndices=(),
            quadNodeIndices=(0, 1, 2, 3),
            polygonNodeIndices=(4, 5, 6, 7, 8),
            nodeCountPerPolygon=(5,),
        )
        mesh = _polygon_mesh_data(polygon)
        self.assertEqual(
            mesh.faces,
            ((0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7), (4, 7, 8)),
        )

    def test_rejects_empty_invalid_and_non_finite_tessellation(self):
        with self.assertRaisesRegex(FusionSelectionError, "empty"):
            _polygon_mesh_data(SimpleNamespace(
                nodeCoordinates=(), nodeIndices=()
            ))
        with self.assertRaisesRegex(FusionSelectionError, "not triangular"):
            _polygon_mesh_data(SimpleNamespace(
                nodeCoordinates=(SimpleNamespace(x=0, y=0, z=0),),
                nodeIndices=(0,),
            ))
        with self.assertRaisesRegex(FusionSelectionError, "invalid geometry"):
            _polygon_mesh_data(SimpleNamespace(
                nodeCoordinates=(
                    SimpleNamespace(x=float("nan"), y=0, z=0),
                    SimpleNamespace(x=1, y=0, z=0),
                    SimpleNamespace(x=0, y=1, z=0),
                ),
                nodeIndices=(0, 1, 2),
            ))


class PreviewOwnershipTests(unittest.TestCase):
    def test_repeated_preview_replaces_only_owned_body(self):
        first = SimpleNamespace(isValid=True, deleted=False)
        first.deleteMe = lambda: setattr(first, "deleted", True)
        second = SimpleNamespace(isValid=True, deleted=False)
        second.deleteMe = lambda: setattr(second, "deleted", True)
        unrelated = SimpleNamespace(isValid=True, deleted=False)
        controller = ProceduralPreviewController()

        controller.replace(lambda: first)
        controller.replace(lambda: second)
        self.assertTrue(first.deleted)
        self.assertFalse(second.deleted)
        self.assertFalse(unrelated.deleted)
        controller.cleanup()
        self.assertTrue(second.deleted)
        self.assertFalse(unrelated.deleted)

    def test_failed_replacement_leaves_no_partial_ownership(self):
        controller = ProceduralPreviewController()
        with self.assertRaisesRegex(RuntimeError, "failed"):
            controller.replace(
                lambda: (_ for _ in ()).throw(RuntimeError("failed"))
            )
        self.assertIsNone(controller.body)


class FakeParameterInputs:
    def __init__(self):
        self.created = {}

    def addValueInput(self, input_id, name, unit, initial):
        control = SimpleNamespace(
            id=input_id, name=name, unit=unit, value=initial.value
        )
        self.created[input_id] = control
        return control

    def addIntegerSpinnerCommandInput(
        self, input_id, name, minimum, maximum, step, initial
    ):
        control = SimpleNamespace(
            id=input_id, name=name, value=initial,
            minimumValue=minimum, maximumValue=maximum,
        )
        self.created[input_id] = control
        return control

    def addFloatSpinnerCommandInput(
        self, input_id, name, unit, minimum, maximum, step, initial
    ):
        control = SimpleNamespace(
            id=input_id, name=name, unit=unit, value=initial,
            minimumValue=minimum, maximumValue=maximum,
        )
        self.created[input_id] = control
        return control

    def addBoolValueInput(
        self, input_id, name, is_checkbox, resource_folder, initial
    ):
        control = SimpleNamespace(
            id=input_id, name=name, value=initial, isCheckBox=is_checkbox
        )
        self.created[input_id] = control
        return control


class RegistryDrivenParameterUiTests(unittest.TestCase):
    def setUp(self):
        self.inputs = FakeParameterInputs()
        adsk_core = SimpleNamespace(
            ValueInput=SimpleNamespace(
                createByString=lambda expression: SimpleNamespace(
                    value=float(expression.split()[0]) / 10.0
                )
            )
        )
        self.controls = _create_parameter_inputs(
            self.inputs, adsk_core, DEFAULT_OPERATOR_REGISTRY
        )

    def test_registry_renders_noise_controls_and_pass_through_has_none(self):
        noise = DEFAULT_OPERATOR_REGISTRY.get("noise_displacement")
        self.assertEqual(
            tuple(item.parameter_id for item in noise.parameter_definitions),
            (
                "amplitude", "scale", "octaves",
                "persistence", "lacunarity", "seed",
            ),
        )
        self.assertFalse(
            DEFAULT_OPERATOR_REGISTRY.get("pass_through").parameter_definitions
        )
        self.assertEqual(len(self.controls), 63)

    def test_visibility_tracks_operator_without_noise_specific_branch(self):
        _set_parameter_visibility(self.controls, 2, "noise_displacement")
        for (slot_index, operator_id, _), control in self.controls.items():
            self.assertEqual(
                control.isVisible,
                slot_index == 2 and operator_id == "noise_displacement",
            )
        _set_parameter_visibility(self.controls, 2, "pass_through")
        self.assertFalse(any(
            control.isVisible for control in self.controls.values()
        ))

    def test_subdivision_level_is_rendered_and_other_controls_are_hidden(self):
        subdivision = DEFAULT_OPERATOR_REGISTRY.get("subdivision")
        _set_parameter_visibility(self.controls, 1, "subdivision")
        visible = [
            key for key, control in self.controls.items()
            if control.isVisible
        ]
        self.assertEqual(visible, [(1, "subdivision", "level")])
        self.assertEqual(
            _read_operator_parameters(subdivision, self.controls, 1),
            {"level": 1},
        )
        level_control = self.controls[(1, "subdivision", "level")]
        self.assertEqual(level_control.minimumValue, 1)
        self.assertEqual(level_control.maximumValue, 5)

    def test_voronoi_parameters_render_and_hide_unrelated_controls(self):
        voronoi = DEFAULT_OPERATOR_REGISTRY.get("voronoi_surface")
        _set_parameter_visibility(self.controls, 3, "voronoi_surface")
        visible = [
            key for key, control in self.controls.items()
            if control.isVisible
        ]
        self.assertEqual(
            visible,
            [
                (3, "voronoi_surface", "cell_size"),
                (3, "voronoi_surface", "depth"),
                (3, "voronoi_surface", "edge_width"),
                (3, "voronoi_surface", "falloff"),
                (3, "voronoi_surface", "jitter"),
                (3, "voronoi_surface", "seed"),
            ],
        )
        self.assertEqual(
            _read_operator_parameters(voronoi, self.controls, 3),
            {
                "cell_size": 20.0,
                "depth": 2.0,
                "edge_width": 3.0,
                "falloff": 2.0,
                "jitter": 0.75,
                "seed": 0,
            },
        )

    def test_gyroid_parameters_are_metadata_driven_in_every_slot(self):
        gyroid = DEFAULT_OPERATOR_REGISTRY.get("gyroid_surface")
        expected_ids = (
            "period", "amplitude", "threshold", "band_width",
            "phase_x", "phase_y", "phase_z", "invert",
        )
        self.assertEqual(
            tuple(item.parameter_id for item in gyroid.parameter_definitions),
            expected_ids,
        )
        for slot_index in (1, 2, 3):
            _set_parameter_visibility(
                self.controls, slot_index, "gyroid_surface"
            )
            visible = [
                key for key, control in self.controls.items()
                if control.isVisible
            ]
            self.assertEqual(
                visible,
                [
                    (slot_index, "gyroid_surface", parameter_id)
                    for parameter_id in expected_ids
                ],
            )
            values = _read_operator_parameters(
                gyroid, self.controls, slot_index
            )
            self.assertEqual(values["period"], 20.0)
            self.assertEqual(values["amplitude"], 2.0)
            self.assertFalse(values["invert"])
            _set_parameter_visibility(self.controls, slot_index, "")

    def test_fusion_length_values_are_read_back_in_millimeters(self):
        noise = DEFAULT_OPERATOR_REGISTRY.get("noise_displacement")
        values = _read_operator_parameters(noise, self.controls, 1)
        self.assertEqual(values["amplitude"], 2.0)
        self.assertEqual(values["scale"], 20.0)
        self.assertEqual(values["octaves"], 3)

    def test_slot_parameters_are_independent_and_visibility_is_isolated(self):
        noise = DEFAULT_OPERATOR_REGISTRY.get("noise_displacement")
        self.controls[(1, "noise_displacement", "amplitude")].value = 0.4
        self.controls[(2, "noise_displacement", "amplitude")].value = 0.7
        _set_parameter_visibility(self.controls, 1, "noise_displacement")
        _set_parameter_visibility(self.controls, 2, "voronoi_surface")

        self.assertEqual(
            _read_operator_parameters(noise, self.controls, 1)["amplitude"],
            4.0,
        )
        self.assertEqual(
            _read_operator_parameters(noise, self.controls, 2)["amplitude"],
            7.0,
        )
        self.assertTrue(
            self.controls[(1, "noise_displacement", "amplitude")].isVisible
        )
        self.assertTrue(
            self.controls[(2, "voronoi_surface", "depth")].isVisible
        )
        self.assertFalse(
            self.controls[(3, "noise_displacement", "amplitude")].isVisible
        )
