"""Fusion command registration and event lifecycle for NatureGenerator.

This module owns Autodesk command registration. Outside ``fusion/``, only the
add-in entry point imports ``adsk`` for fatal lifecycle diagnostics.
"""

import traceback
from typing import List


COMMAND_ID = "NatureGeneratorGenerateNature"
COMMAND_NAME = "Generate Nature"
COMMAND_DESCRIPTION = "Generate a natural form as a MeshBody."
LEGACY_COMMAND_ID = "NatureGeneratorGenerateSponge"
WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "SolidScriptsAddinsPanel"
PRESET_INPUT_ID = "naturePreset"
CELL_SIZE_INPUT_ID = "cellSize"
THICKNESS_INPUT_ID = "thickness"
RESOLUTION_INPUT_ID = "resolution"

_handlers: List[object] = []
_command_handler_groups: List[List[object]] = []
_started = False


class FusionRuntimeError(RuntimeError):
    """Raised when Fusion cannot register the NatureGenerator command."""


def _log(app, message: str) -> None:
    app.log(message)


def _find_panel(ui, workspace):
    """Resolve the Add-Ins panel globally, then through the Design workspace."""
    all_panels = getattr(ui, "allToolbarPanels", None)
    panel = all_panels.itemById(PANEL_ID) if all_panels else None
    if panel is None and workspace is not None:
        panel = workspace.toolbarPanels.itemById(PANEL_ID)
    return panel


def _active_workspace_description(ui) -> str:
    active = getattr(ui, "activeWorkspace", None)
    if active is None:
        return "active workspace unavailable"
    return "active workspace id={!r}, name={!r}".format(
        getattr(active, "id", "<unknown>"),
        getattr(active, "name", "<unknown>"),
    )


def _preset_label(preset) -> str:
    if preset.available:
        return preset.display_name
    return "{} — Coming Soon".format(preset.display_name)


def _delete_command(ui, panel, command_id: str) -> None:
    control = panel.controls.itemById(command_id) if panel else None
    if control is not None:
        control.deleteMe()
    definition = ui.commandDefinitions.itemById(command_id)
    if definition is not None:
        definition.deleteMe()


def start(context=None) -> None:
    """Register the Generate Nature command in Fusion's Add-Ins panel."""

    import adsk.core  # type: ignore[import-not-found]

    from commands.generate_nature import generate_nature
    from fusion.mesh_body import MeshBodyBuilder
    from generators import (
        DEFAULT_RESOLUTION,
        GeneratorError,
        GenerationRequest,
        MAX_RESOLUTION,
        MIN_RESOLUTION,
    )
    from presets import PresetFactory

    global _started

    app = adsk.core.Application.get()
    if app is None:
        raise FusionRuntimeError("Fusion application is unavailable")
    _log(app, "NatureGenerator startup entered")
    ui = app.userInterface if app else None
    if ui is None:
        raise FusionRuntimeError("Fusion user interface is unavailable")
    _log(app, "application and user interface resolved")
    if _started:
        _log(app, "NatureGenerator startup already completed")
        return

    class ExecuteHandler(adsk.core.CommandEventHandler):
        def __init__(
            self,
            preset_input,
            preset_ids,
            cell_size_input,
            thickness_input,
            resolution_input,
        ):
            super().__init__()
            self._preset_input = preset_input
            self._preset_ids = preset_ids
            self._cell_size_input = cell_size_input
            self._thickness_input = thickness_input
            self._resolution_input = resolution_input

        def notify(self, args):
            try:
                selected = self._preset_input.selectedItem
                if selected is None:
                    raise ValueError("select a nature preset")
                preset_id = self._preset_ids[selected.name]
                request = GenerationRequest(
                    preset_id=preset_id,
                    parameter_overrides={
                        "cell_size": self._cell_size_input.value * 10.0,
                        "thickness": self._thickness_input.value,
                    },
                    resolution=self._resolution_input.value,
                )
                result, body = generate_nature(request, MeshBodyBuilder().build)
                app.log(
                    "NatureGenerator created {!r}: {} vertices, {} faces, {:.3f}s".format(
                        body.name,
                        result.statistics.vertex_count,
                        result.statistics.face_count,
                        result.elapsed_time,
                    )
                )
            except (GeneratorError, KeyError, TypeError, ValueError) as error:
                app.log("Generate Nature rejected: {}".format(error))
                ui.messageBox(str(error), "Generate Nature")
            except Exception:
                details = traceback.format_exc()
                app.log(details)
                ui.messageBox(
                    "Generate Nature failed.\n\n{}".format(details),
                    "NatureGenerator",
                )

    class DestroyHandler(adsk.core.CommandEventHandler):
        def __init__(self, retained):
            super().__init__()
            self._retained = retained

        def notify(self, args):
            if self._retained in _command_handler_groups:
                _command_handler_groups.remove(self._retained)

    class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
        def notify(self, args):
            command = args.command
            inputs = command.commandInputs
            presets = PresetFactory.list_all()
            sponge = PresetFactory.get("sponge")
            preset_input = inputs.addDropDownCommandInput(
                PRESET_INPUT_ID,
                "Preset",
                adsk.core.DropDownStyles.TextListDropDownStyle,
            )
            preset_ids = {}
            for preset in presets:
                label = _preset_label(preset)
                preset_input.listItems.add(
                    label, preset.preset_id == sponge.preset_id, ""
                )
                preset_ids[label] = preset.preset_id

            cell_metadata = sponge.parameter_metadata["cell_size"]
            cell_size_input = inputs.addValueInput(
                CELL_SIZE_INPUT_ID,
                "Cell Size",
                "mm",
                adsk.core.ValueInput.createByString(
                    "{} mm".format(cell_metadata.default_value)
                ),
            )
            thickness_metadata = sponge.parameter_metadata["thickness"]
            thickness_input = inputs.addFloatSpinnerCommandInput(
                THICKNESS_INPUT_ID,
                "Thickness",
                "",
                float(thickness_metadata.minimum),
                float(thickness_metadata.maximum),
                0.01,
                float(thickness_metadata.default_value),
            )
            resolution_input = inputs.addIntegerSpinnerCommandInput(
                RESOLUTION_INPUT_ID,
                "Resolution",
                MIN_RESOLUTION,
                MAX_RESOLUTION,
                2,
                DEFAULT_RESOLUTION,
            )

            retained = []
            execute_handler = ExecuteHandler(
                preset_input,
                preset_ids,
                cell_size_input,
                thickness_input,
                resolution_input,
            )
            destroy_handler = DestroyHandler(retained)
            command.execute.add(execute_handler)
            command.destroy.add(destroy_handler)
            retained.extend((execute_handler, destroy_handler))
            _command_handler_groups.append(retained)

    command_definition = ui.commandDefinitions.itemById(COMMAND_ID)
    if command_definition is None:
        command_definition = ui.commandDefinitions.addButtonDefinition(
            COMMAND_ID, COMMAND_NAME, COMMAND_DESCRIPTION
        )
    if command_definition is None:
        raise FusionRuntimeError("Fusion failed to create the command definition")
    _log(app, "command definition resolved or created")

    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    if workspace is None:
        raise FusionRuntimeError(
            "Fusion workspace {!r} is unavailable; {}".format(
                WORKSPACE_ID, _active_workspace_description(ui)
            )
        )
    _log(app, "workspace resolved")

    panel = _find_panel(ui, workspace)
    if panel is None:
        raise FusionRuntimeError(
            "Fusion toolbar panel {!r} was not found globally or in workspace "
            "{!r}; {}".format(
                PANEL_ID, WORKSPACE_ID, _active_workspace_description(ui)
            )
        )
    _log(app, "toolbar panel resolved")

    _delete_command(ui, panel, LEGACY_COMMAND_ID)

    control = panel.controls.itemById(COMMAND_ID)
    if control is None:
        control = panel.controls.addCommand(command_definition)
    if control is None:
        raise FusionRuntimeError("Fusion failed to add the Generate Nature control")
    control.isPromotedByDefault = True
    control.isPromoted = True
    _log(app, "toolbar control resolved or created")

    created_handler = CommandCreatedHandler()
    command_definition.commandCreated.add(created_handler)
    _handlers.append(created_handler)
    _log(app, "event handlers retained")
    _started = True
    _log(app, "NatureGenerator startup completed")


def stop(context=None) -> None:
    """Remove the command UI and release retained Fusion event handlers."""

    import adsk.core  # type: ignore[import-not-found]

    global _started

    app = adsk.core.Application.get()
    ui = app.userInterface if app else None
    if ui is not None:
        workspace = ui.workspaces.itemById(WORKSPACE_ID)
        panel = _find_panel(ui, workspace)
        _delete_command(ui, panel, COMMAND_ID)
        _delete_command(ui, panel, LEGACY_COMMAND_ID)
        app.log("NatureGenerator stopped.")
    _handlers.clear()
    _command_handler_groups.clear()
    _started = False
