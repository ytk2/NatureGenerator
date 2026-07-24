"""Fusion command lifecycle for the independent Procedural Lab surface."""

import traceback
from typing import List


COMMAND_ID = "NatureGeneratorProceduralLab"
COMMAND_NAME = "Procedural Lab"
COMMAND_DESCRIPTION = "Apply procedural operations to an existing body or mesh."
WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "SolidScriptsAddinsPanel"
SOURCE_INPUT_ID = "proceduralSource"
SOURCE_TYPE_INPUT_ID = "proceduralSourceType"
OPERATOR_INPUT_PREFIX = "proceduralOperator_"
NONE_OPERATOR_LABEL = "None"
STACK_SLOT_COUNT = 3
PREVIEW_INPUT_ID = "proceduralPreview"
PARAMETER_INPUT_PREFIX = "proceduralParameter_"
PREVIEW_NAME = "NatureGenerator Procedural Preview — {}"
FINAL_NAME = "NatureGenerator Procedural — {}"

_handlers: List[object] = []
_command_handler_groups: List[List[object]] = []
_preview_controllers: List[object] = []
_started = False


class ProceduralFusionError(RuntimeError):
    pass


def _operator_input_id(slot_index):
    return "{}{}".format(OPERATOR_INPUT_PREFIX, slot_index)


def _parameter_input_id(slot_index, operator_id, parameter_id):
    return "{}{}_{}_{}".format(
        PARAMETER_INPUT_PREFIX, slot_index, operator_id, parameter_id
    )


def _create_parameter_inputs(
    inputs, adsk_core, registry, slot_indices=(1, 2, 3)
):
    """Render independent operator parameters for every stack slot."""

    created = {}
    for slot_index in slot_indices:
        for operator in registry.list_all():
            for definition in operator.parameter_definitions:
                input_id = _parameter_input_id(
                    slot_index, operator.operator_id, definition.parameter_id
                )
                label = "Operator {} — {}".format(
                    slot_index, definition.display_name
                )
                if definition.value_type == "length":
                    value = adsk_core.ValueInput.createByString(
                        "{} {}".format(definition.default_value, definition.unit)
                    )
                    control = inputs.addValueInput(
                        input_id, label, definition.unit, value
                    )
                elif definition.value_type == "integer":
                    control = inputs.addIntegerSpinnerCommandInput(
                        input_id,
                        label,
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
                        label,
                        definition.unit,
                        float(definition.minimum),
                        float(definition.maximum),
                        step,
                        float(definition.default_value),
                    )
                elif definition.value_type == "boolean":
                    control = inputs.addBoolValueInput(
                        input_id,
                        label,
                        True,
                        "",
                        bool(definition.default_value),
                    )
                else:
                    raise ValueError("unsupported procedural parameter type")
                control.isVisible = False
                created[(
                    slot_index, operator.operator_id, definition.parameter_id
                )] = control
    return created


def _set_parameter_visibility(parameter_inputs, slot_index, operator_id):
    for (owner_slot, owner_id, _), control in parameter_inputs.items():
        if owner_slot == slot_index:
            control.isVisible = owner_id == operator_id


def _read_operator_parameters(operator, parameter_inputs, slot_index):
    values = {}
    for definition in operator.parameter_definitions:
        control = parameter_inputs[
            (slot_index, operator.operator_id, definition.parameter_id)
        ]
        value = control.value
        # Fusion stores length command values in internal centimetres.
        if definition.value_type == "length" and definition.unit == "mm":
            value = float(value) * 10.0
        elif definition.value_type == "integer":
            value = int(value)
        elif definition.value_type == "boolean":
            value = bool(value)
        else:
            value = float(value)
        values[definition.parameter_id] = definition.validate(value)
    return values


def _panel(ui, workspace):
    global_panels = getattr(ui, "allToolbarPanels", None)
    found = global_panels.itemById(PANEL_ID) if global_panels else None
    return found or workspace.toolbarPanels.itemById(PANEL_ID)


def _delete_command(ui, panel) -> None:
    control = panel.controls.itemById(COMMAND_ID) if panel else None
    if control is not None:
        control.deleteMe()
    definition = ui.commandDefinitions.itemById(COMMAND_ID)
    if definition is not None:
        definition.deleteMe()


def start(context=None) -> None:
    import adsk.core  # type: ignore[import-not-found]

    from commands.procedural_lab import execute_procedural_stack
    from fusion.mesh_body import MeshBodyBuilder
    from fusion.procedural_preview import ProceduralPreviewController
    from fusion.selection_adapter import FusionSelectionAdapter, FusionSelectionError
    from procedural import (
        DEFAULT_OPERATOR_REGISTRY,
        ExecutionContext,
        OperatorInvocation,
        ProceduralStackRequest,
    )

    global _started
    app = adsk.core.Application.get()
    ui = app.userInterface if app else None
    if ui is None:
        raise ProceduralFusionError("Fusion user interface is unavailable")
    if _started:
        app.log("Procedural Lab startup already completed")
        return

    class Trigger:
        pending = False

    def chosen_operator(operator_input, operator_ids):
        selected = operator_input.selectedItem
        if selected is None:
            raise ValueError("select a procedural operator")
        if selected.name == NONE_OPERATOR_LABEL:
            return None
        try:
            operator_id = operator_ids[selected.name]
            return DEFAULT_OPERATOR_REGISTRY.get(operator_id)
        except KeyError as error:
            raise ValueError("operator lookup failed") from error

    def read_invocations(operator_inputs, operator_ids, parameter_inputs):
        invocations = []
        for slot_index in range(1, STACK_SLOT_COUNT + 1):
            operator = chosen_operator(
                operator_inputs[slot_index], operator_ids[slot_index]
            )
            if operator is None:
                continue
            parameters = _read_operator_parameters(
                operator, parameter_inputs, slot_index
            )
            invocations.append(OperatorInvocation(
                operator.operator_id, parameters
            ))
        if not invocations:
            raise ValueError("select at least one procedural operator")
        return tuple(invocations)

    def stack_display_name(invocations):
        if len(invocations) == 1:
            return DEFAULT_OPERATOR_REGISTRY.get(
                invocations[0].operator_id
            ).display_name
        return "Operator Stack"

    class ExecuteHandler(adsk.core.CommandEventHandler):
        def __init__(
            self, source, operator_inputs, operator_ids, parameter_inputs,
            controller,
        ):
            super().__init__()
            self.source = source
            self.operator_inputs = operator_inputs
            self.operator_ids = operator_ids
            self.parameter_inputs = parameter_inputs
            self.controller = controller

        def notify(self, args):
            self.controller.cleanup()
            try:
                geometry = FusionSelectionAdapter().adapt_selection(
                    self.source, preview=False
                )
                invocations = read_invocations(
                    self.operator_inputs,
                    self.operator_ids,
                    self.parameter_inputs,
                )
                request = ProceduralStackRequest(
                    geometry, invocations,
                    ExecutionContext.FINAL,
                )
                display_name = stack_display_name(invocations)
                result, body = execute_procedural_stack(
                    request,
                    MeshBodyBuilder().build,
                    FINAL_NAME.format(display_name),
                )
                app.log(
                    "Procedural Lab created {!r}: {} vertices, {} faces, digest={}".format(
                        body.name,
                        result.statistics.vertex_count,
                        result.statistics.face_count,
                        result.output_digest,
                    )
                )
            except (FusionSelectionError, KeyError, TypeError, ValueError) as error:
                self.controller.cleanup()
                app.log("Procedural Lab rejected: {}".format(error))
                ui.messageBox(str(error), COMMAND_NAME)
            except Exception:
                self.controller.cleanup()
                details = traceback.format_exc()
                app.log(details)
                ui.messageBox(
                    "Procedural Lab failed.\n\n{}".format(details), COMMAND_NAME
                )

    class InputChangedHandler(adsk.core.InputChangedEventHandler):
        def __init__(
            self, source, source_status, operator_inputs, preview_input,
            operator_ids, parameter_inputs, controller, trigger,
        ):
            super().__init__()
            self.source = source
            self.source_status = source_status
            self.operator_inputs = operator_inputs
            self.preview_input = preview_input
            self.operator_ids = operator_ids
            self.parameter_inputs = parameter_inputs
            self.controller = controller
            self.trigger = trigger

        def notify(self, args):
            changed_id = getattr(getattr(args, "input", None), "id", None)
            if changed_id == PREVIEW_INPUT_ID:
                self.trigger.pending = True
                return
            operator_slots = {
                _operator_input_id(slot_index): slot_index
                for slot_index in range(1, STACK_SLOT_COUNT + 1)
            }
            if (
                changed_id != SOURCE_INPUT_ID
                and changed_id not in operator_slots
                and not (
                    changed_id
                    and changed_id.startswith(PARAMETER_INPUT_PREFIX)
                )
            ):
                return
            self.controller.cleanup()
            if changed_id in operator_slots:
                slot_index = operator_slots[changed_id]
                try:
                    operator = chosen_operator(
                        self.operator_inputs[slot_index],
                        self.operator_ids[slot_index],
                    )
                    _set_parameter_visibility(
                        self.parameter_inputs,
                        slot_index,
                        operator.operator_id if operator is not None else "",
                    )
                except Exception:
                    _set_parameter_visibility(
                        self.parameter_inputs, slot_index, ""
                    )
            try:
                label = FusionSelectionAdapter().source_label(self.source)
                self.source_status.text = label
                self.preview_input.isEnabled = True
            except Exception:
                self.source_status.text = "No valid source selected"
                self.preview_input.isEnabled = False

    class PreviewHandler(adsk.core.CommandEventHandler):
        def __init__(
            self, source, operator_inputs, operator_ids, parameter_inputs,
            controller, trigger,
        ):
            super().__init__()
            self.source = source
            self.operator_inputs = operator_inputs
            self.operator_ids = operator_ids
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
                geometry = FusionSelectionAdapter().adapt_selection(
                    self.source, preview=True
                )
                invocations = read_invocations(
                    self.operator_inputs,
                    self.operator_ids,
                    self.parameter_inputs,
                )
                request = ProceduralStackRequest(
                    geometry, invocations,
                    ExecutionContext.PREVIEW,
                )
                display_name = stack_display_name(invocations)

                def create():
                    result, body = execute_procedural_stack(
                        request,
                        MeshBodyBuilder().build,
                        PREVIEW_NAME.format(display_name),
                    )
                    app.log(
                        "Procedural preview created: {} vertices, {} faces, digest={}".format(
                            result.statistics.vertex_count,
                            result.statistics.face_count,
                            result.output_digest,
                        )
                    )
                    return body

                self.controller.replace(create)
            except Exception as error:
                self.controller.cleanup()
                app.log(traceback.format_exc())
                ui.messageBox(
                    "Preview failed: {}".format(error), "Procedural Lab Preview"
                )

    class ValidateHandler(adsk.core.ValidateInputsEventHandler):
        def __init__(
            self, source, operator_inputs, operator_ids, parameter_inputs
        ):
            super().__init__()
            self.source = source
            self.operator_inputs = operator_inputs
            self.operator_ids = operator_ids
            self.parameter_inputs = parameter_inputs

        def notify(self, args):
            try:
                FusionSelectionAdapter().source_label(self.source)
                read_invocations(
                    self.operator_inputs,
                    self.operator_ids,
                    self.parameter_inputs,
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
            source = inputs.addSelectionInput(
                SOURCE_INPUT_ID, "Input Geometry", "Select one body or mesh"
            )
            source.addSelectionFilter("SolidBodies")
            source.addSelectionFilter("MeshBodies")
            source.setSelectionLimits(0, 1)
            source_status = inputs.addTextBoxCommandInput(
                SOURCE_TYPE_INPUT_ID,
                "Source Type",
                "No valid source selected",
                1,
                True,
            )
            operator_inputs = {}
            operator_ids = {}
            for slot_index in range(1, STACK_SLOT_COUNT + 1):
                operator_input = inputs.addDropDownCommandInput(
                    _operator_input_id(slot_index),
                    "Operator {}".format(slot_index),
                    adsk.core.DropDownStyles.TextListDropDownStyle,
                )
                operator_ids[slot_index] = {}
                operator_input.listItems.add(
                    NONE_OPERATOR_LABEL, slot_index != 1, ""
                )
                for index, operator in enumerate(
                    DEFAULT_OPERATOR_REGISTRY.list_all()
                ):
                    operator_input.listItems.add(
                        operator.display_name,
                        slot_index == 1 and index == 0,
                        "",
                    )
                    operator_ids[slot_index][
                        operator.display_name
                    ] = operator.operator_id
                operator_inputs[slot_index] = operator_input
            parameter_inputs = _create_parameter_inputs(
                inputs, adsk.core, DEFAULT_OPERATOR_REGISTRY
            )
            for slot_index in range(1, STACK_SLOT_COUNT + 1):
                initial_operator_id = (
                    DEFAULT_OPERATOR_REGISTRY.list_all()[0].operator_id
                    if slot_index == 1 else ""
                )
                _set_parameter_visibility(
                    parameter_inputs, slot_index, initial_operator_id
                )
            preview_input = inputs.addBoolValueInput(
                PREVIEW_INPUT_ID, "Preview", False, "", False
            )
            preview_input.isEnabled = False
            controller = ProceduralPreviewController()
            trigger = Trigger()
            retained: List[object] = []
            execute = ExecuteHandler(
                source, operator_inputs, operator_ids, parameter_inputs,
                controller,
            )
            changed = InputChangedHandler(
                source, source_status, operator_inputs, preview_input,
                operator_ids, parameter_inputs, controller, trigger,
            )
            preview = PreviewHandler(
                source, operator_inputs, operator_ids, parameter_inputs,
                controller, trigger,
            )
            validate = ValidateHandler(
                source, operator_inputs, operator_ids, parameter_inputs
            )
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
        raise ProceduralFusionError(
            "Fusion failed to create the Procedural Lab command"
        )
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    if workspace is None:
        raise ProceduralFusionError("Fusion Design workspace is unavailable")
    panel = _panel(ui, workspace)
    if panel is None:
        raise ProceduralFusionError("Fusion Add-Ins panel is unavailable")
    control = panel.controls.itemById(COMMAND_ID)
    if control is None:
        control = panel.controls.addCommand(definition)
    if control is None:
        raise ProceduralFusionError(
            "Fusion failed to add the Procedural Lab control"
        )
    control.isPromotedByDefault = True
    control.isPromoted = True
    handler = CreatedHandler()
    definition.commandCreated.add(handler)
    _handlers.append(handler)
    _started = True
    app.log("Procedural Lab startup completed")


def stop(context=None) -> None:
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
