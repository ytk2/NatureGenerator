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
VARIANT_INPUT_ID = "natureVariant"
CUSTOM_VARIANT_LABEL = "Custom"
FAMILY_INPUT_ID = "natureRockFamily"
PREVIEW_INPUT_ID = "naturePreview"
CELL_SIZE_INPUT_ID = "parameter_sponge_cell_size"
THICKNESS_INPUT_ID = "parameter_sponge_thickness"
RESOLUTION_INPUT_ID = "parameter_sponge_resolution"

_handlers: List[object] = []
_command_handler_groups: List[List[object]] = []
_preview_controllers: List[object] = []
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


def _parameter_input_id(preset_id: str, parameter_id: str) -> str:
    return "parameter_{}_{}".format(preset_id, parameter_id)


def _create_parameter_input(inputs, adsk_core, preset, parameter_id, metadata):
    """Create one Fusion input by metadata type, without preset branching."""

    input_id = _parameter_input_id(preset.preset_id, parameter_id)
    if metadata.value_type == "length":
        created = inputs.addValueInput(
            input_id,
            metadata.display_name,
            metadata.unit,
            adsk_core.ValueInput.createByString(
                "{} {}".format(metadata.default_value, metadata.unit)
            ),
        )
    elif metadata.value_type == "float":
        step = max(0.01, (float(metadata.maximum) - float(metadata.minimum)) / 100.0)
        created = inputs.addFloatSpinnerCommandInput(
            input_id, metadata.display_name, metadata.unit,
            float(metadata.minimum), float(metadata.maximum), step,
            float(metadata.default_value),
        )
    elif metadata.value_type in ("integer", "int"):
        step = 2 if parameter_id == "resolution" else 1
        created = inputs.addIntegerSpinnerCommandInput(
            input_id, metadata.display_name,
            int(metadata.minimum), int(metadata.maximum), step,
            int(metadata.default_value),
        )
    else:
        raise ValueError("unsupported parameter type: {}".format(metadata.value_type))
    created.isVisible = False
    return created


def _read_parameter(input_value, metadata):
    value = input_value.value
    # Fusion exposes ValueCommandInput lengths in internal centimetres.
    if metadata.value_type == "length" and metadata.unit == "mm":
        value *= 10.0
    if metadata.value_type in ("integer", "int"):
        value = int(value)
    if metadata.minimum is not None and value < metadata.minimum:
        raise ValueError("{} must be at least {}".format(
            metadata.display_name, metadata.minimum))
    if metadata.maximum is not None and value > metadata.maximum:
        raise ValueError("{} must be at most {}".format(
            metadata.display_name, metadata.maximum))
    return value


def _write_parameter(input_value, metadata, value):
    """Write one metadata value using Fusion's internal unit convention."""

    if metadata.value_type == "length" and metadata.unit == "mm":
        value = float(value) / 10.0
    elif metadata.value_type in ("integer", "int"):
        value = int(value)
    else:
        value = float(value)
    input_value.value = value


def _select_list_item(dropdown, item) -> None:
    """Select a documented ListItem, with assignment support for test doubles."""

    item.isSelected = True
    try:
        dropdown.selectedItem = item
    except (AttributeError, TypeError):
        pass


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
    from fusion.preview import PreviewController, preview_request
    from generators import (
        DEFAULT_RESOLUTION,
        GeneratorError,
        GeneratorFactory,
        GenerationRequest,
    )
    from preset_catalog import PresetCatalog
    from variants import VariantFactory

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

    def read_request(
        preset_input,
        preset_ids,
        parameter_inputs,
        family_input,
        family_state,
    ):
        selected = preset_input.selectedItem
        if selected is None:
            raise ValueError("select a nature preset")
        preset_id = preset_ids[selected.name]
        preset = PresetCatalog.get(preset_id).preset
        if not preset.available:
            raise ValueError("preset {!r} is unavailable: {}".format(
                preset_id, preset.unavailable_reason))
        values = {
            parameter_id: _read_parameter(
                parameter_inputs[(preset_id, parameter_id)], metadata
            )
            for parameter_id, metadata in preset.parameter_metadata.items()
        }
        resolution = values.pop("resolution", DEFAULT_RESOLUTION)
        family_id = family_state.selected_id(family_input, preset_id)
        request = GenerationRequest(preset_id, values, resolution, family_id)
        return preset, request

    class ExecuteHandler(adsk.core.CommandEventHandler):
        def __init__(
            self,
            preset_input,
            preset_ids,
            parameter_inputs,
            family_input,
            family_state,
            controller,
        ):
            super().__init__()
            self._preset_input = preset_input
            self._preset_ids = preset_ids
            self._parameter_inputs = parameter_inputs
            self._family_input = family_input
            self._family_state = family_state
            self._controller = controller

        def notify(self, args):
            try:
                preset, request = read_request(
                    self._preset_input,
                    self._preset_ids,
                    self._parameter_inputs,
                    self._family_input,
                    self._family_state,
                )
                self._controller.cleanup()
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
                self._controller.cleanup()
                app.log("Generate Nature rejected: {}".format(error))
                ui.messageBox(str(error), "Generate Nature")
            except Exception:
                self._controller.cleanup()
                details = traceback.format_exc()
                app.log(details)
                ui.messageBox(
                    "Generate Nature failed.\n\n{}".format(details),
                    "NatureGenerator",
                )

    class PreviewTrigger:
        def __init__(self):
            self.pending = False

    class VariantUiState:
        def __init__(self):
            self.variant_ids = {}
            self.expected_values = {}

        def rebuild(self, variant_input, preset_id):
            self.expected_values.clear()
            self.variant_ids.clear()
            if not variant_input.listItems.clear():
                raise RuntimeError("Fusion failed to rebuild the Variant list")
            variant_input.listItems.add(CUSTOM_VARIANT_LABEL, True, "")
            for variant in VariantFactory.list_for_preset(preset_id):
                variant_input.listItems.add(variant.display_name, False, "")
                self.variant_ids[variant.display_name] = variant.variant_id

        def select_custom(self, variant_input):
            for index in range(variant_input.listItems.count):
                item = variant_input.listItems.item(index)
                if item.name == CUSTOM_VARIANT_LABEL:
                    _select_list_item(variant_input, item)
                    return
            raise RuntimeError("Custom variant list item is unavailable")

    class FamilyUiState:
        def __init__(self, family_input):
            self.preset_id = None
            self.registry = None
            self.family_ids = {}
            self.expected_values = {}
            for definition in PresetCatalog.list_all():
                if definition.families is not None:
                    self.rebuild(family_input, definition.preset_id)
                    break

        def rebuild(self, family_input, preset_id):
            definition = PresetCatalog.get(preset_id)
            registry = definition.families
            if registry is None:
                return
            if self.preset_id == preset_id:
                return
            if not family_input.listItems.clear():
                raise RuntimeError("Fusion failed to rebuild the Family list")
            self.preset_id = preset_id
            self.registry = registry
            self.family_ids.clear()
            self.expected_values.clear()
            for index, family in enumerate(registry.list_all()):
                family_input.listItems.add(
                    family.display_name, index == 0, ""
                )
                self.family_ids[family.display_name] = family.family_id

        def supports(self, preset_id):
            return PresetCatalog.get(preset_id).families is not None

        def selected_id(self, family_input, preset_id):
            if not self.supports(preset_id):
                return ""
            self.rebuild(family_input, preset_id)
            chosen = family_input.selectedItem
            if chosen is None:
                raise ValueError("select a Family")
            return self.family_ids[chosen.name]

        def apply_selected(self, family_input, parameter_inputs, preset_id):
            self.rebuild(family_input, preset_id)
            chosen = family_input.selectedItem
            if chosen is None:
                raise ValueError("select a Family")
            family = self.registry.get(self.family_ids[chosen.name])
            preset = PresetCatalog.get(preset_id).preset
            expected = {}
            for parameter_id, value in family.parameter_values.items():
                input_value = parameter_inputs[(preset_id, parameter_id)]
                _write_parameter(
                    input_value, preset.parameter_metadata[parameter_id], value
                )
                expected[_parameter_input_id(
                    preset_id, parameter_id
                )] = input_value.value
            self.expected_values = expected

    class InputChangedHandler(adsk.core.InputChangedEventHandler):
        def __init__(
            self, preset_input, preset_ids, variant_input, family_input,
            parameter_inputs, preview_input, controller, trigger,
            variant_state, family_state,
        ):
            super().__init__()
            self._preset_input = preset_input
            self._preset_ids = preset_ids
            self._variant_input = variant_input
            self._family_input = family_input
            self._parameter_inputs = parameter_inputs
            self._preview_input = preview_input
            self._controller = controller
            self._trigger = trigger
            self._variant_state = variant_state
            self._family_state = family_state

        def notify(self, args):
            try:
                changed = getattr(args, "input", None)
                changed_id = getattr(changed, "id", None)
                if changed_id == PREVIEW_INPUT_ID:
                    self._trigger.pending = True
                    return

                self._controller.mark_dirty()
                selected = self._preset_input.selectedItem
                selected_id = self._preset_ids[selected.name] if selected else None
                for (preset_id, _), input_value in self._parameter_inputs.items():
                    input_value.isVisible = preset_id == selected_id
                family_supported = self._family_state.supports(selected_id)
                self._family_input.isVisible = family_supported
                self._variant_input.isVisible = not family_supported

                if changed_id == PRESET_INPUT_ID:
                    self._variant_state.rebuild(self._variant_input, selected_id)
                    if family_supported:
                        self._family_state.rebuild(
                            self._family_input, selected_id
                        )
                        self._family_state.apply_selected(
                            self._family_input, self._parameter_inputs, selected_id
                        )
                    return

                if changed_id == FAMILY_INPUT_ID:
                    if not family_supported:
                        return
                    self._family_state.apply_selected(
                        self._family_input, self._parameter_inputs, selected_id
                    )
                    return

                if changed_id == VARIANT_INPUT_ID:
                    chosen = self._variant_input.selectedItem
                    if chosen is None or chosen.name == CUSTOM_VARIANT_LABEL:
                        self._variant_state.expected_values.clear()
                        return
                    variant = VariantFactory.get(
                        self._variant_state.variant_ids[chosen.name]
                    )
                    if variant.preset_id != selected_id:
                        raise ValueError("variant does not belong to selected preset")
                    preset = PresetCatalog.get(selected_id).preset
                    expected = {}
                    for parameter_id, value in variant.parameter_values.items():
                        input_id = _parameter_input_id(selected_id, parameter_id)
                        input_value = self._parameter_inputs[
                            (selected_id, parameter_id)
                        ]
                        _write_parameter(
                            input_value, preset.parameter_metadata[parameter_id], value
                        )
                        expected[input_id] = input_value.value
                    self._variant_state.expected_values = expected
                    return

                parameter_prefix = "parameter_{}_".format(selected_id)
                if changed_id and changed_id.startswith(parameter_prefix):
                    if family_supported:
                        expected = self._family_state.expected_values
                        if (
                            changed_id in expected
                            and changed.value == expected[changed_id]
                        ):
                            expected.pop(changed_id)
                        else:
                            expected.clear()
                        return
                    expected = self._variant_state.expected_values
                    if changed_id in expected and changed.value == expected[changed_id]:
                        expected.pop(changed_id)
                        return
                    expected.clear()
                    self._variant_state.select_custom(self._variant_input)
            except Exception:
                details = traceback.format_exc()
                app.log(details)
                ui.messageBox(
                    "Preview failed: {}".format(details.strip().splitlines()[-1]),
                    "Preview Error",
                )

    class ExecutePreviewHandler(adsk.core.CommandEventHandler):
        def __init__(
            self, preset_input, preset_ids, parameter_inputs, family_input,
            family_state, controller, trigger,
        ):
            super().__init__()
            self._preset_input = preset_input
            self._preset_ids = preset_ids
            self._parameter_inputs = parameter_inputs
            self._family_input = family_input
            self._family_state = family_state
            self._controller = controller
            self._trigger = trigger

        def notify(self, args):
            if not self._trigger.pending:
                return
            self._trigger.pending = False
            if hasattr(args, "isValidResult"):
                args.isValidResult = False
            try:
                preset, request = read_request(
                    self._preset_input, self._preset_ids,
                    self._parameter_inputs,
                    self._family_input,
                    self._family_state,
                )
                metadata = preset.parameter_metadata.get("resolution")
                cap = (
                    int(metadata.default_value)
                    if metadata is not None else request.resolution
                )
                candidates = (
                    metadata.preview_resolutions if metadata is not None else ()
                )
                actual_request = preview_request(request, cap, candidates)
                temporary_name = "NatureGenerator Preview — {}".format(
                    preset.display_name
                )

                def generate_preview_request(pending_request):
                    return GeneratorFactory.generate_request(pending_request)

                def insert_preview(generated):
                    if not generated.mesh.vertices or not generated.mesh.faces:
                        raise ValueError("preview mesh must be non-empty")
                    return MeshBodyBuilder().build(generated.mesh, temporary_name)

                replacing = self._controller.body is not None
                app.log("Preview started: preset={!r}, resolution={}".format(
                    preset.display_name, actual_request.resolution
                ))
                result, body, created = self._controller.generate_preview(
                    request,
                    actual_request,
                    generate_preview_request,
                    insert_preview,
                )
                app.log(
                    "Preview {}: {!r}, {} vertices, {} faces, "
                    "{:.3f}s at resolution {}".format(
                        "replaced" if replacing else "created", body.name,
                        result.statistics.vertex_count,
                        result.statistics.face_count,
                        result.elapsed_time, actual_request.resolution,
                    )
                )
            except Exception:
                details = traceback.format_exc()
                app.log("Preview failed")
                app.log(details)
                ui.messageBox(
                    "Preview failed: {}".format(details.strip().splitlines()[-1]),
                    "Preview Error",
                )

    class ValidateInputsHandler(adsk.core.ValidateInputsEventHandler):
        def __init__(self, preset_input, preset_ids, parameter_inputs):
            super().__init__()
            self._preset_input = preset_input
            self._preset_ids = preset_ids
            self._parameter_inputs = parameter_inputs

        def notify(self, args):
            try:
                selected = self._preset_input.selectedItem
                preset = PresetCatalog.get(
                    self._preset_ids[selected.name]
                ).preset
                if not preset.available:
                    args.areInputsValid = False
                    return
                for parameter_id, metadata in preset.parameter_metadata.items():
                    _read_parameter(
                        self._parameter_inputs[(preset.preset_id, parameter_id)],
                        metadata,
                    )
                args.areInputsValid = True
            except (KeyError, TypeError, ValueError, AttributeError):
                args.areInputsValid = False

    class DestroyHandler(adsk.core.CommandEventHandler):
        def __init__(self, retained, controller):
            super().__init__()
            self._retained = retained
            self._controller = controller

        def notify(self, args):
            self._controller.cleanup()
            if self._controller in _preview_controllers:
                _preview_controllers.remove(self._controller)
            if self._retained in _command_handler_groups:
                _command_handler_groups.remove(self._retained)

    class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
        def notify(self, args):
            command = args.command
            inputs = command.commandInputs
            presets = tuple(
                definition.preset for definition in PresetCatalog.list_all()
            )
            sponge = PresetCatalog.get("sponge").preset
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
            variant_input = inputs.addDropDownCommandInput(
                VARIANT_INPUT_ID,
                "Variant",
                adsk.core.DropDownStyles.TextListDropDownStyle,
            )
            variant_state = VariantUiState()
            variant_state.rebuild(variant_input, sponge.preset_id)
            variant_input.isVisible = True
            family_input = inputs.addDropDownCommandInput(
                FAMILY_INPUT_ID,
                "Family",
                adsk.core.DropDownStyles.TextListDropDownStyle,
            )
            family_state = FamilyUiState(family_input)
            family_input.isVisible = False
            parameter_inputs = {}
            for preset in presets:
                if not preset.available:
                    continue
                for parameter_id, metadata in preset.parameter_metadata.items():
                    parameter_inputs[(preset.preset_id, parameter_id)] = (
                        _create_parameter_input(
                            inputs, adsk.core, preset, parameter_id, metadata
                        )
                    )
            for (preset_id, _), input_value in parameter_inputs.items():
                input_value.isVisible = preset_id == sponge.preset_id

            preview_input = inputs.addBoolValueInput(
                PREVIEW_INPUT_ID, "Preview", False, "", False
            )
            controller = PreviewController(app.log)
            _preview_controllers.append(controller)
            preview_trigger = PreviewTrigger()

            retained = []
            execute_handler = ExecuteHandler(
                preset_input,
                preset_ids,
                parameter_inputs,
                family_input,
                family_state,
                controller,
            )
            input_changed_handler = InputChangedHandler(
                preset_input, preset_ids, variant_input, family_input,
                parameter_inputs, preview_input, controller, preview_trigger,
                variant_state, family_state,
            )
            execute_preview_handler = ExecutePreviewHandler(
                preset_input, preset_ids, parameter_inputs, family_input,
                family_state, controller, preview_trigger,
            )
            validate_handler = ValidateInputsHandler(
                preset_input, preset_ids, parameter_inputs
            )
            destroy_handler = DestroyHandler(retained, controller)
            command.execute.add(execute_handler)
            command.inputChanged.add(input_changed_handler)
            command.executePreview.add(execute_preview_handler)
            command.validateInputs.add(validate_handler)
            command.destroy.add(destroy_handler)
            retained.extend((
                execute_handler, input_changed_handler, execute_preview_handler,
                validate_handler, destroy_handler,
            ))
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

    for controller in tuple(_preview_controllers):
        controller.cleanup()
    _preview_controllers.clear()

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
