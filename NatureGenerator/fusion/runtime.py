"""Fusion command registration and event lifecycle for NatureGenerator.

This module owns Autodesk command registration. Outside ``fusion/``, only the
add-in entry point imports ``adsk`` for fatal lifecycle diagnostics.
"""

import traceback
from typing import List


COMMAND_ID = "NatureGeneratorGenerateSponge"
COMMAND_NAME = "Generate Sponge"
COMMAND_DESCRIPTION = "Generate the NatureGenerator Sponge preset as a MeshBody."
WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "SolidScriptsAddinsPanel"

_handlers: List[object] = []


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


def start(context=None) -> None:
    """Register the Generate Sponge command in Fusion's Add-Ins panel."""

    import adsk.core  # type: ignore[import-not-found]

    from commands.generate_sponge import generate_sponge
    from fusion.mesh_body import MeshBodyBuilder

    app = adsk.core.Application.get()
    if app is None:
        raise FusionRuntimeError("Fusion application is unavailable")
    _log(app, "NatureGenerator startup entered")
    ui = app.userInterface if app else None
    if ui is None:
        raise FusionRuntimeError("Fusion user interface is unavailable")
    _log(app, "application and user interface resolved")

    class ExecuteHandler(adsk.core.CommandEventHandler):
        def notify(self, args):
            try:
                result, body = generate_sponge(MeshBodyBuilder().build)
                app.log(
                    "NatureGenerator created {!r}: {} vertices, {} faces, {:.3f}s".format(
                        body.name,
                        result.statistics.vertex_count,
                        result.statistics.face_count,
                        result.elapsed_time,
                    )
                )
            except Exception:
                ui.messageBox(
                    "Generate Sponge failed.\n\n{}".format(traceback.format_exc()),
                    "NatureGenerator",
                )

    class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
        def notify(self, args):
            execute_handler = ExecuteHandler()
            args.command.execute.add(execute_handler)
            _handlers.append(execute_handler)

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

    control = panel.controls.itemById(COMMAND_ID)
    if control is None:
        control = panel.controls.addCommand(command_definition)
    if control is None:
        raise FusionRuntimeError("Fusion failed to add the Generate Sponge control")
    control.isPromotedByDefault = True
    control.isPromoted = True
    _log(app, "toolbar control resolved or created")

    created_handler = CommandCreatedHandler()
    command_definition.commandCreated.add(created_handler)
    _handlers.append(created_handler)
    _log(app, "event handlers retained")
    _log(app, "NatureGenerator startup completed")
    # Temporary development diagnostic: remove after real Fusion validation.
    ui.messageBox(
        "NatureGenerator loaded successfully.\n"
        "Open Design > Utilities > Add-Ins and run Generate Sponge.",
        "NatureGenerator Development Diagnostics",
    )


def stop(context=None) -> None:
    """Remove the command UI and release retained Fusion event handlers."""

    import adsk.core  # type: ignore[import-not-found]

    app = adsk.core.Application.get()
    ui = app.userInterface if app else None
    if ui is not None:
        workspace = ui.workspaces.itemById(WORKSPACE_ID)
        panel = _find_panel(ui, workspace)
        control = panel.controls.itemById(COMMAND_ID) if panel else None
        if control is not None:
            control.deleteMe()
        command_definition = ui.commandDefinitions.itemById(COMMAND_ID)
        if command_definition is not None:
            command_definition.deleteMe()
        app.log("NatureGenerator stopped.")
    _handlers.clear()
