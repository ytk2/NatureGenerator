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
OPERATOR_INPUT_ID = "proceduralOperator"
PREVIEW_INPUT_ID = "proceduralPreview"
PREVIEW_NAME = "NatureGenerator Procedural Preview — {}"
FINAL_NAME = "NatureGenerator Procedural — {}"

_handlers: List[object] = []
_command_handler_groups: List[List[object]] = []
_preview_controllers: List[object] = []
_started = False


class ProceduralFusionError(RuntimeError):
    pass


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

    from commands.procedural_lab import execute_procedural
    from fusion.mesh_body import MeshBodyBuilder
    from fusion.procedural_preview import ProceduralPreviewController
    from fusion.selection_adapter import FusionSelectionAdapter, FusionSelectionError
    from procedural import (
        DEFAULT_OPERATOR_REGISTRY,
        ExecutionContext,
        ProceduralRequest,
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
        try:
            operator_id = operator_ids[selected.name]
            return DEFAULT_OPERATOR_REGISTRY.get(operator_id)
        except KeyError as error:
            raise ValueError("operator lookup failed") from error

    class ExecuteHandler(adsk.core.CommandEventHandler):
        def __init__(self, source, operator_input, operator_ids, controller):
            super().__init__()
            self.source = source
            self.operator_input = operator_input
            self.operator_ids = operator_ids
            self.controller = controller

        def notify(self, args):
            self.controller.cleanup()
            try:
                geometry = FusionSelectionAdapter().adapt_selection(
                    self.source, preview=False
                )
                operator = chosen_operator(self.operator_input, self.operator_ids)
                request = ProceduralRequest(
                    geometry, operator.operator_id, {},
                    ExecutionContext.FINAL,
                )
                result, body = execute_procedural(
                    request,
                    MeshBodyBuilder().build,
                    FINAL_NAME.format(operator.display_name),
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
            self, source, source_status, operator_input, preview_input,
            controller, trigger,
        ):
            super().__init__()
            self.source = source
            self.source_status = source_status
            self.operator_input = operator_input
            self.preview_input = preview_input
            self.controller = controller
            self.trigger = trigger

        def notify(self, args):
            changed_id = getattr(getattr(args, "input", None), "id", None)
            if changed_id == PREVIEW_INPUT_ID:
                self.trigger.pending = True
                return
            if changed_id not in (SOURCE_INPUT_ID, OPERATOR_INPUT_ID):
                return
            self.controller.cleanup()
            try:
                label = FusionSelectionAdapter().source_label(self.source)
                self.source_status.text = label
                self.preview_input.isEnabled = True
            except Exception:
                self.source_status.text = "No valid source selected"
                self.preview_input.isEnabled = False

    class PreviewHandler(adsk.core.CommandEventHandler):
        def __init__(
            self, source, operator_input, operator_ids, controller, trigger
        ):
            super().__init__()
            self.source = source
            self.operator_input = operator_input
            self.operator_ids = operator_ids
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
                operator = chosen_operator(self.operator_input, self.operator_ids)
                request = ProceduralRequest(
                    geometry, operator.operator_id, {},
                    ExecutionContext.PREVIEW,
                )

                def create():
                    result, body = execute_procedural(
                        request,
                        MeshBodyBuilder().build,
                        PREVIEW_NAME.format(operator.display_name),
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
        def __init__(self, source, operator_input, operator_ids):
            super().__init__()
            self.source = source
            self.operator_input = operator_input
            self.operator_ids = operator_ids

        def notify(self, args):
            try:
                FusionSelectionAdapter().source_label(self.source)
                chosen_operator(self.operator_input, self.operator_ids)
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
            operator_input = inputs.addDropDownCommandInput(
                OPERATOR_INPUT_ID,
                "Operator",
                adsk.core.DropDownStyles.TextListDropDownStyle,
            )
            operator_ids = {}
            for index, operator in enumerate(DEFAULT_OPERATOR_REGISTRY.list_all()):
                operator_input.listItems.add(
                    operator.display_name, index == 0, ""
                )
                operator_ids[operator.display_name] = operator.operator_id
            preview_input = inputs.addBoolValueInput(
                PREVIEW_INPUT_ID, "Preview", False, "", False
            )
            preview_input.isEnabled = False
            controller = ProceduralPreviewController()
            trigger = Trigger()
            retained: List[object] = []
            execute = ExecuteHandler(
                source, operator_input, operator_ids, controller
            )
            changed = InputChangedHandler(
                source, source_status, operator_input, preview_input,
                controller, trigger,
            )
            preview = PreviewHandler(
                source, operator_input, operator_ids, controller, trigger
            )
            validate = ValidateHandler(source, operator_input, operator_ids)
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
