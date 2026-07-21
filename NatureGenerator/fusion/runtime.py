"""Fusion command registration and event lifecycle for NatureGenerator.

This module is the Autodesk boundary. No module outside ``fusion/`` imports
``adsk``.
"""

import traceback
from typing import List


COMMAND_ID = "NatureGeneratorGenerateSponge"
COMMAND_NAME = "Generate Sponge"
COMMAND_DESCRIPTION = "Generate the NatureGenerator Sponge preset as a MeshBody."
WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "SolidScriptsAddinsPanel"

_handlers: List[object] = []


def start(context=None) -> None:
    """Register the Generate Sponge command in Fusion's Add-Ins panel."""

    import adsk.core  # type: ignore[import-not-found]

    from commands.generate_sponge import generate_sponge
    from fusion.mesh_body import MeshBodyBuilder

    app = adsk.core.Application.get()
    ui = app.userInterface if app else None
    if ui is None:
        raise RuntimeError("Fusion user interface is unavailable")

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
        raise RuntimeError("Fusion failed to create the command definition")

    created_handler = CommandCreatedHandler()
    command_definition.commandCreated.add(created_handler)
    _handlers.append(created_handler)

    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID) if workspace else None
    if panel is None:
        raise RuntimeError("Fusion Design Add-Ins panel is unavailable")
    control = panel.controls.itemById(COMMAND_ID)
    if control is None:
        control = panel.controls.addCommand(command_definition)
    if control is None:
        raise RuntimeError("Fusion failed to add the Generate Sponge control")
    control.isPromotedByDefault = True
    control.isPromoted = True
    app.log("NatureGenerator loaded; Generate Sponge is available.")


def stop(context=None) -> None:
    """Remove the command UI and release retained Fusion event handlers."""

    import adsk.core  # type: ignore[import-not-found]

    app = adsk.core.Application.get()
    ui = app.userInterface if app else None
    if ui is not None:
        workspace = ui.workspaces.itemById(WORKSPACE_ID)
        panel = workspace.toolbarPanels.itemById(PANEL_ID) if workspace else None
        control = panel.controls.itemById(COMMAND_ID) if panel else None
        if control is not None:
            control.deleteMe()
        command_definition = ui.commandDefinitions.itemById(COMMAND_ID)
        if command_definition is not None:
            command_definition.deleteMe()
        app.log("NatureGenerator stopped.")
    _handlers.clear()
