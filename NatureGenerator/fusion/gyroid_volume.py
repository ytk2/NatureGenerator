"""Fusion lifecycle for the independent Gyroid Volume command."""

import traceback
from typing import List


COMMAND_ID = "NatureGeneratorGyroidVolume"
COMMAND_NAME = "Gyroid Volume"
COMMAND_DESCRIPTION = "Generate a volumetric Gyroid iso-surface MeshBody."
WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "SolidScriptsAddinsPanel"
PARAMETER_PREFIX = "gyroidVolume_"
PREVIEW_INPUT_ID = "gyroidVolumePreview"
PREVIEW_NAME = "NatureGenerator Preview — Gyroid Volume"
FINAL_NAME = "NatureGenerator — Gyroid Volume"

_handlers: List[object] = []
_command_handler_groups: List[List[object]] = []
_preview_controllers: List[object] = []
_started = False


class GyroidVolumeFusionError(RuntimeError):
    pass


def _parameter_input_id(parameter_id):
    return "{}{}".format(PARAMETER_PREFIX, parameter_id)


def _create_parameter_inputs(inputs, adsk_core, definitions):
    created = {}
    for definition in definitions:
        input_id = _parameter_input_id(definition.parameter_id)
        if definition.value_type == "length":
            control = inputs.addValueInput(
                input_id,
                definition.display_name,
                definition.unit,
                adsk_core.ValueInput.createByString(
                    "{} {}".format(
                        definition.default_value, definition.unit
                    )
                ),
            )
        elif definition.value_type == "integer":
            control = inputs.addIntegerSpinnerCommandInput(
                input_id,
                definition.display_name,
                int(definition.minimum),
                int(definition.maximum),
                1,
                int(definition.default_value),
            )
        elif definition.value_type == "float":
            step = max(
                0.01,
                (
                    float(definition.maximum)
                    - float(definition.minimum)
                ) / 100.0,
            )
            control = inputs.addFloatSpinnerCommandInput(
                input_id,
                definition.display_name,
                definition.unit,
                float(definition.minimum),
                float(definition.maximum),
                step,
                float(definition.default_value),
            )
        elif definition.value_type == "enum":
            control = inputs.addDropDownCommandInput(
                input_id,
                definition.display_name,
                adsk_core.DropDownStyles.TextListDropDownStyle,
            )
            for value, display_name in definition.choices:
                control.listItems.add(
                    display_name, value == definition.default_value, ""
                )
        else:
            raise ValueError("unsupported volume parameter type")
        created[definition.parameter_id] = control
    return created


def _read_parameter_values(parameter_inputs, definitions):
    values = {}
    for definition in definitions:
        control = parameter_inputs[definition.parameter_id]
        if definition.value_type == "enum":
            selected = control.selectedItem
            if selected is None:
                raise ValueError(
                    "select {}".format(definition.display_name)
                )
            labels = {
                display_name: value
                for value, display_name in definition.choices
            }
            try:
                value = labels[selected.name]
            except KeyError as error:
                raise ValueError(
                    "unsupported {}".format(definition.display_name)
                ) from error
        else:
            value = control.value
        if definition.value_type == "length" and definition.unit == "mm":
            value = float(value) * 10.0
        elif definition.value_type == "integer":
            value = int(value)
        elif definition.value_type != "enum":
            value = float(value)
        values[definition.parameter_id] = definition.validate(value)
    return values


def _selected_enum_value(control, definition):
    selected = control.selectedItem
    if selected is None:
        return None
    labels = {
        display_name: value
        for value, display_name in definition.choices
    }
    return labels.get(selected.name)


def _update_parameter_visibility(parameter_inputs, definitions):
    """Apply generic metadata visibility without resetting control values."""

    by_id = {
        definition.parameter_id: definition for definition in definitions
    }
    for definition in definitions:
        visible = True
        if definition.visible_when:
            source_id, allowed_values = definition.visible_when
            source_definition = by_id[source_id]
            source_value = _selected_enum_value(
                parameter_inputs[source_id], source_definition
            )
            visible = source_value in allowed_values
        parameter_inputs[definition.parameter_id].isVisible = visible


def _panel(ui, workspace):
    global_panels = getattr(ui, "allToolbarPanels", None)
    found = global_panels.itemById(PANEL_ID) if global_panels else None
    return found or workspace.toolbarPanels.itemById(PANEL_ID)


def _delete_command(ui, panel):
    control = panel.controls.itemById(COMMAND_ID) if panel else None
    if control is not None:
        control.deleteMe()
    definition = ui.commandDefinitions.itemById(COMMAND_ID)
    if definition is not None:
        definition.deleteMe()


def start(context=None):
    import adsk.core  # type: ignore[import-not-found]

    from commands.gyroid_volume import execute_gyroid_volume
    from fusion.gyroid_volume_preview import GyroidVolumePreviewController
    from fusion.volume_mesh_builder import VolumeMeshBuilder
    from volume import (
        BoundaryMode,
        GeometryMode,
        GyroidVolumeRequest,
        PreviewQuality,
        VOLUME_PARAMETER_DEFINITIONS,
        VolumeExecutionContext,
    )

    global _started
    app = adsk.core.Application.get()
    ui = app.userInterface if app else None
    if ui is None:
        raise GyroidVolumeFusionError("Fusion user interface is unavailable")
    if _started:
        app.log("Gyroid Volume startup already completed")
        return

    class Trigger:
        pending = False

    def read_request(parameter_inputs, execution_context):
        values = _read_parameter_values(
            parameter_inputs, VOLUME_PARAMETER_DEFINITIONS
        )
        return GyroidVolumeRequest(
            execution_context=execution_context,
            boundary_mode=BoundaryMode(values.pop("boundary_mode")),
            geometry_mode=GeometryMode(values.pop("geometry_mode")),
            preview_quality=PreviewQuality(values.pop("preview_quality")),
            **values
        )

    def log_completion(label, result, insertion_time):
        estimate = result.cost_estimate
        resolution = estimate.effective_resolution
        quality = (
            "\nQuality: {}".format(
                estimate.preview_quality.value.title()
            )
            if estimate.preview_quality is not None
            else ""
        )
        app.log(
            "{}{}\nResolution: {} × {} × {}\nSamples: {:,}\n"
            "Faces: {:,}\nCore generation: {:.3f}s\n"
            "Fusion insertion: {:.3f}s\nTotal: {:.3f}s".format(
                label,
                quality,
                resolution[0],
                resolution[1],
                resolution[2],
                estimate.total_scalar_samples,
                result.statistics.face_count,
                result.timings.total_core,
                insertion_time,
                result.timings.total_core + insertion_time,
            )
        )

    class ExecuteHandler(adsk.core.CommandEventHandler):
        def __init__(self, parameter_inputs, controller):
            super().__init__()
            self.parameter_inputs = parameter_inputs
            self.controller = controller

        def notify(self, args):
            try:
                request = read_request(
                    self.parameter_inputs, VolumeExecutionContext.APPLY
                )
                self.controller.cleanup()
                insertion = []
                result, body = execute_gyroid_volume(
                    request,
                    VolumeMeshBuilder().build,
                    FINAL_NAME,
                    insertion.append,
                )
                log_completion(
                    "Gyroid Volume Apply — {!r}".format(body.name),
                    result,
                    insertion[0],
                )
            except Exception as error:
                self.controller.cleanup()
                app.log(traceback.format_exc())
                ui.messageBox(
                    "Gyroid Volume failed: {}".format(error),
                    "Gyroid Volume",
                )

    class InputChangedHandler(adsk.core.InputChangedEventHandler):
        def __init__(
            self, parameter_inputs, preview_input, controller, trigger
        ):
            super().__init__()
            self.parameter_inputs = parameter_inputs
            self.preview_input = preview_input
            self.controller = controller
            self.trigger = trigger

        def notify(self, args):
            changed = getattr(args, "input", None)
            changed_id = getattr(changed, "id", None)
            if changed_id == PREVIEW_INPUT_ID:
                self.trigger.pending = True
                return
            if not (
                changed_id and changed_id.startswith(PARAMETER_PREFIX)
            ):
                return
            self.controller.cleanup()
            _update_parameter_visibility(
                self.parameter_inputs, VOLUME_PARAMETER_DEFINITIONS
            )
            try:
                read_request(
                    self.parameter_inputs, VolumeExecutionContext.PREVIEW
                )
                self.preview_input.isEnabled = True
            except Exception:
                self.preview_input.isEnabled = False

    class PreviewHandler(adsk.core.CommandEventHandler):
        def __init__(self, parameter_inputs, controller, trigger):
            super().__init__()
            self.parameter_inputs = parameter_inputs
            self.controller = controller
            self.trigger = trigger

        def notify(self, args):
            if not self.trigger.pending:
                return
            self.trigger.pending = False
            if hasattr(args, "isValidResult"):
                args.isValidResult = False
            try:
                request = read_request(
                    self.parameter_inputs, VolumeExecutionContext.PREVIEW
                )

                def create():
                    insertion = []
                    result, body = execute_gyroid_volume(
                        request,
                        VolumeMeshBuilder().build,
                        PREVIEW_NAME,
                        insertion.append,
                    )
                    log_completion(
                        "Gyroid Volume Preview", result, insertion[0]
                    )
                    return body

                self.controller.replace(create)
            except Exception as error:
                self.controller.cleanup()
                app.log(traceback.format_exc())
                ui.messageBox(
                    "Preview failed: {}".format(error),
                    "Gyroid Volume Preview",
                )

    class ValidateHandler(adsk.core.ValidateInputsEventHandler):
        def __init__(self, parameter_inputs):
            super().__init__()
            self.parameter_inputs = parameter_inputs

        def notify(self, args):
            try:
                read_request(
                    self.parameter_inputs, VolumeExecutionContext.APPLY
                )
                args.areInputsValid = True
            except Exception:
                args.areInputsValid = False

    class DestroyHandler(adsk.core.CommandEventHandler):
        def __init__(self, retained, controller):
            super().__init__()
            self.retained = retained
            self.controller = controller

        def notify(self, args):
            self.controller.cleanup()
            if self.controller in _preview_controllers:
                _preview_controllers.remove(self.controller)
            if self.retained in _command_handler_groups:
                _command_handler_groups.remove(self.retained)

    class CreatedHandler(adsk.core.CommandCreatedEventHandler):
        def notify(self, args):
            command = args.command
            inputs = command.commandInputs
            parameter_inputs = _create_parameter_inputs(
                inputs, adsk.core, VOLUME_PARAMETER_DEFINITIONS
            )
            _update_parameter_visibility(
                parameter_inputs, VOLUME_PARAMETER_DEFINITIONS
            )
            preview_input = inputs.addBoolValueInput(
                PREVIEW_INPUT_ID, "Preview", False, "", False
            )
            preview_input.isEnabled = True
            controller = GyroidVolumePreviewController()
            trigger = Trigger()
            retained = []
            execute = ExecuteHandler(parameter_inputs, controller)
            changed = InputChangedHandler(
                parameter_inputs, preview_input, controller, trigger
            )
            preview = PreviewHandler(
                parameter_inputs, controller, trigger
            )
            validate = ValidateHandler(parameter_inputs)
            destroy = DestroyHandler(retained, controller)
            command.execute.add(execute)
            command.inputChanged.add(changed)
            command.executePreview.add(preview)
            command.validateInputs.add(validate)
            command.destroy.add(destroy)
            retained.extend((execute, changed, preview, validate, destroy))
            _preview_controllers.append(controller)
            _command_handler_groups.append(retained)

    definition = ui.commandDefinitions.itemById(COMMAND_ID)
    if definition is None:
        definition = ui.commandDefinitions.addButtonDefinition(
            COMMAND_ID, COMMAND_NAME, COMMAND_DESCRIPTION
        )
    if definition is None:
        raise GyroidVolumeFusionError(
            "Fusion failed to create the Gyroid Volume command"
        )
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    if workspace is None:
        raise GyroidVolumeFusionError(
            "Fusion Design workspace is unavailable"
        )
    panel = _panel(ui, workspace)
    if panel is None:
        raise GyroidVolumeFusionError(
            "Fusion Add-Ins panel is unavailable"
        )
    control = panel.controls.itemById(COMMAND_ID)
    if control is None:
        control = panel.controls.addCommand(definition)
    if control is None:
        raise GyroidVolumeFusionError(
            "Fusion failed to add the Gyroid Volume control"
        )
    control.isPromotedByDefault = True
    control.isPromoted = True
    handler = CreatedHandler()
    definition.commandCreated.add(handler)
    _handlers.append(handler)
    _started = True
    app.log("Gyroid Volume startup completed")


def stop(context=None):
    import adsk.core  # type: ignore[import-not-found]

    global _started
    for controller in tuple(_preview_controllers):
        controller.cleanup()
    _preview_controllers.clear()
    app = adsk.core.Application.get()
    ui = app.userInterface if app else None
    if ui is not None:
        workspace = ui.workspaces.itemById(WORKSPACE_ID)
        panel = _panel(ui, workspace) if workspace else None
        _delete_command(ui, panel)
    _handlers.clear()
    _command_handler_groups.clear()
    _started = False
