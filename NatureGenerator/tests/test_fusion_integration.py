"""Tests for the Fusion boundary that run without Autodesk's Python runtime."""

import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from commands.generate_nature import generate_nature
from core.mesh import TriangleMesh
from fusion.mesh_body import MeshBodyBuilder, triangle_mesh_data
from fusion import runtime
from generators import DEFAULT_RESOLUTION, GenerationRequest, UnavailablePresetError


class FakeEvent:
    def __init__(self):
        self.handlers = []

    def add(self, handler):
        self.handlers.append(handler)


class FakeCollection:
    def __init__(self, items=None):
        self.items = {} if items is None else dict(items)
        self.lookups = []

    def itemById(self, item_id):
        self.lookups.append(item_id)
        return self.items.get(item_id)


class FakeControls(FakeCollection):
    def __init__(self, items=None):
        super().__init__(items)
        self.add_count = 0

    def addCommand(self, definition):
        self.add_count += 1
        control = SimpleNamespace(isPromoted=False, isPromotedByDefault=False)
        control.deleteMe = lambda: self.items.pop(runtime.COMMAND_ID, None)
        self.items[runtime.COMMAND_ID] = control
        return control


class FakeCommandDefinitions(FakeCollection):
    def __init__(self, items=None):
        super().__init__(items)
        self.add_count = 0

    def addButtonDefinition(self, command_id, name, description):
        self.add_count += 1
        definition = SimpleNamespace(commandCreated=FakeEvent())
        definition.deleteMe = lambda: self.items.pop(command_id, None)
        self.items[command_id] = definition
        return definition


class FakeListItems:
    def __init__(self, dropdown):
        self.dropdown = dropdown
        self.items = []

    def add(self, name, is_selected, icon):
        item = SimpleNamespace(name=name, isSelected=is_selected)
        self.items.append(item)
        if is_selected:
            self.dropdown.selectedItem = item
        return item


class FakeCommandInputs:
    def __init__(self):
        self.items = {}

    def addDropDownCommandInput(self, input_id, name, style):
        result = SimpleNamespace(id=input_id, name=name, selectedItem=None)
        result.listItems = FakeListItems(result)
        self.items[input_id] = result
        return result

    def addValueInput(self, input_id, name, unit, initial):
        result = SimpleNamespace(
            id=input_id, name=name, unit=unit, value=initial.value
        )
        self.items[input_id] = result
        return result

    def addFloatSpinnerCommandInput(
        self, input_id, name, unit, minimum, maximum, step, initial
    ):
        result = SimpleNamespace(
            id=input_id,
            name=name,
            unit=unit,
            minimumValue=minimum,
            maximumValue=maximum,
            spinStep=step,
            value=initial,
        )
        self.items[input_id] = result
        return result

    def addIntegerSpinnerCommandInput(
        self, input_id, name, minimum, maximum, step, initial
    ):
        result = self.addFloatSpinnerCommandInput(
            input_id, name, "", minimum, maximum, step, initial
        )
        return result


class FakeCommand:
    def __init__(self):
        self.commandInputs = FakeCommandInputs()
        self.execute = FakeEvent()
        self.inputChanged = FakeEvent()
        self.validateInputs = FakeEvent()
        self.destroy = FakeEvent()


def fake_adsk_modules(app):
    adsk = ModuleType("adsk")
    core = ModuleType("adsk.core")
    core.Application = SimpleNamespace(get=lambda: app)
    core.CommandEventHandler = object
    core.CommandCreatedEventHandler = object
    core.InputChangedEventHandler = object
    core.ValidateInputsEventHandler = object
    core.DropDownStyles = SimpleNamespace(TextListDropDownStyle="text-list")
    core.ValueInput = SimpleNamespace(
        createByString=lambda expression: SimpleNamespace(
            value=float(expression.split()[0]) / 10.0
        )
    )
    adsk.core = core
    return {"adsk": adsk, "adsk.core": core}


def fake_fusion_ui(global_panel=True, workspace_panel=True):
    panel = SimpleNamespace(controls=FakeControls())
    workspace_panels = FakeCollection(
        {runtime.PANEL_ID: panel} if workspace_panel else {}
    )
    workspace = SimpleNamespace(
        id=runtime.WORKSPACE_ID,
        name="Design",
        toolbarPanels=workspace_panels,
    )
    ui = SimpleNamespace(
        commandDefinitions=FakeCommandDefinitions(),
        workspaces=FakeCollection({runtime.WORKSPACE_ID: workspace}),
        allToolbarPanels=FakeCollection(
            {runtime.PANEL_ID: panel} if global_panel else {}
        ),
        activeWorkspace=workspace,
        messages=[],
    )
    ui.messageBox = lambda message, title: ui.messages.append((message, title))
    app = SimpleNamespace(userInterface=ui, logs=[])
    app.log = app.logs.append
    return app, ui, workspace, panel


class GenerateNatureCommandTests(unittest.TestCase):
    def test_command_runs_runtime_and_passes_mesh_to_adapter(self):
        received = []
        sentinel_body = object()

        def insert_mesh(mesh, name):
            received.append((mesh, name))
            return sentinel_body

        request = GenerationRequest(
            "sponge", {"cell_size": 10.0, "thickness": 0.2}, 17
        )
        result, body = generate_nature(request, insert_mesh)

        self.assertIs(body, sentinel_body)
        self.assertEqual(result.preset_id, "sponge")
        self.assertEqual(result.generator_id, "gyroid")
        self.assertEqual(received, [(result.mesh, "NatureGenerator Sponge")])

    def test_command_rejects_missing_mesh_body(self):
        with self.assertRaisesRegex(RuntimeError, "did not return"):
            generate_nature(
                GenerationRequest("sponge", {}, DEFAULT_RESOLUTION),
                lambda mesh, name: None,
            )

    def test_unavailable_preset_never_calls_adapter(self):
        calls = []
        with self.assertRaises(UnavailablePresetError):
            generate_nature(
                GenerationRequest("bone", {}, DEFAULT_RESOLUTION),
                lambda mesh, name: calls.append(mesh),
            )
        self.assertEqual(calls, [])


class MeshBodyAdapterTests(unittest.TestCase):
    def test_triangle_mesh_data_flattens_indexed_mesh(self):
        mesh = TriangleMesh(
            vertices=((0, 0, 0), (1, 0, 0), (0, 1, 0)),
            faces=((0, 1, 2),),
        )
        coordinates, indices = triangle_mesh_data(mesh)
        self.assertEqual(
            coordinates,
            [0.0, 0.0, 0.0, 0.1, 0.0, 0.0, 0.0, 0.1, 0.0],
        )
        self.assertEqual(indices, [0, 1, 2])

    def test_triangle_mesh_data_rejects_empty_mesh(self):
        with self.assertRaisesRegex(ValueError, "at least one triangle"):
            triangle_mesh_data(TriangleMesh(vertices=(), faces=()))

    def test_builder_inserts_data_into_supplied_design(self):
        mesh = TriangleMesh(
            vertices=((0, 0, 0), (1, 0, 0), (0, 1, 0)),
            faces=((0, 1, 2),),
        )
        calls = []
        body = SimpleNamespace(name="")

        class MeshBodies:
            def addByTriangleMeshData(
                self, coordinates, indices, normals, normal_indices
            ):
                calls.append((coordinates, indices, normals, normal_indices))
                return body

        design = SimpleNamespace(
            rootComponent=SimpleNamespace(meshBodies=MeshBodies())
        )
        adsk = ModuleType("adsk")
        adsk.core = ModuleType("adsk.core")
        adsk.fusion = ModuleType("adsk.fusion")
        with patch.dict(
            sys.modules,
            {"adsk": adsk, "adsk.core": adsk.core, "adsk.fusion": adsk.fusion},
        ):
            created = MeshBodyBuilder().build(mesh, "Test Sponge", design)

        self.assertIs(created, body)
        self.assertEqual(body.name, "Test Sponge")
        self.assertEqual(calls[0][1], [0, 1, 2])
        self.assertEqual(calls[0][2:], ([], []))


class FusionDependencyBoundaryTests(unittest.TestCase):
    def test_command_and_fusion_layers_do_not_reference_concrete_rock_generator(self):
        package_root = Path(__file__).parents[1]
        for folder in ("commands", "fusion"):
            for module in (package_root / folder).glob("*.py"):
                self.assertNotIn("RockGenerator", module.read_text(encoding="utf-8"))

    def test_command_and_fusion_layers_do_not_reference_concrete_bark_generator(self):
        package_root = Path(__file__).parents[1]
        for folder in ("commands", "fusion"):
            for module in (package_root / folder).glob("*.py"):
                self.assertNotIn("BarkGenerator", module.read_text(encoding="utf-8"))

    def test_geometry_runtime_presets_and_commands_have_no_adsk_imports(self):
        package_root = Path(__file__).parents[1]
        for folder in ("core", "generators", "presets", "commands"):
            for module in (package_root / folder).glob("*.py"):
                self.assertNotIn("import adsk", module.read_text(encoding="utf-8"))
        fusion_sources = "\n".join(
            module.read_text(encoding="utf-8")
            for module in (package_root / "fusion").glob("*.py")
        )
        self.assertIn("import adsk", fusion_sources)

    def test_only_entry_point_modifies_sys_path(self):
        package_root = Path(__file__).parents[1]
        for folder in ("core", "generators", "presets", "commands", "fusion"):
            for module in (package_root / folder).glob("*.py"):
                self.assertNotIn("sys.path", module.read_text(encoding="utf-8"))
        entry_source = (package_root / "NatureGenerator.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("sys.path.insert", entry_source)

    def test_entry_point_imports_without_autodesk_runtime(self):
        entry_path = Path(__file__).parents[1] / "NatureGenerator.py"
        spec = importlib.util.spec_from_file_location("addin_entry", str(entry_path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(callable(module.run))
        self.assertTrue(callable(module.stop))

    def test_entry_point_bootstrap_imports_fusion_and_is_idempotent(self):
        entry_path = Path(__file__).parents[1] / "NatureGenerator.py"
        addin_root = str(entry_path.resolve().parent)
        original_path = list(sys.path)
        saved_fusion_modules = {
            name: module
            for name, module in list(sys.modules.items())
            if name == "fusion" or name.startswith("fusion.")
        }
        try:
            sys.path[:] = [path for path in sys.path if path != addin_root]
            for name in saved_fusion_modules:
                sys.modules.pop(name, None)

            spec = importlib.util.spec_from_file_location(
                "bootstrap_addin_entry", str(entry_path)
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            self.assertNotIn(addin_root, sys.path)
            self.assertEqual(module._bootstrap_addin_path(), addin_root)
            imported = importlib.import_module("fusion.runtime")
            self.assertEqual(imported.COMMAND_ID, runtime.COMMAND_ID)
            module._bootstrap_addin_path()
            self.assertEqual(sys.path.count(addin_root), 1)
        finally:
            sys.path[:] = original_path
            for name in list(sys.modules):
                if name == "fusion" or name.startswith("fusion."):
                    sys.modules.pop(name, None)
            sys.modules.update(saved_fusion_modules)

    def test_run_and_stop_bootstrap_when_addin_root_is_absent(self):
        entry_path = Path(__file__).parents[1] / "NatureGenerator.py"
        addin_root = str(entry_path.resolve().parent)
        original_path = list(sys.path)
        saved_fusion_modules = {
            name: module
            for name, module in list(sys.modules.items())
            if name == "fusion" or name.startswith("fusion.")
        }
        app, ui, _, _ = fake_fusion_ui()
        try:
            sys.path[:] = [path for path in sys.path if path != addin_root]
            for name in saved_fusion_modules:
                sys.modules.pop(name, None)

            spec = importlib.util.spec_from_file_location(
                "direct_addin_entry", str(entry_path)
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            with patch.dict(sys.modules, fake_adsk_modules(app)):
                module.run(None)
                module.stop(None)

            self.assertEqual(sys.path.count(addin_root), 1)
            self.assertEqual(ui.messages, [])
            self.assertIn("NatureGenerator startup completed", app.logs)
            self.assertIn("NatureGenerator stopped.", app.logs)
        finally:
            sys.path[:] = original_path
            for name in list(sys.modules):
                if name == "fusion" or name.startswith("fusion."):
                    sys.modules.pop(name, None)
            sys.modules.update(saved_fusion_modules)

    def test_entry_point_reports_and_reraises_startup_exception(self):
        entry_path = Path(__file__).parents[1] / "NatureGenerator.py"
        spec = importlib.util.spec_from_file_location(
            "failing_addin_entry", str(entry_path)
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        app, ui, _, _ = fake_fusion_ui()
        failing_runtime = ModuleType("fusion.runtime")
        failing_runtime.start = lambda context: (_ for _ in ()).throw(
            RuntimeError("startup exploded")
        )
        failing_runtime.stop = lambda context: None
        modules = fake_adsk_modules(app)
        modules["fusion.runtime"] = failing_runtime
        with patch.dict(sys.modules, modules):
            with self.assertRaisesRegex(RuntimeError, "startup exploded"):
                module.run(None)

        self.assertIn("RuntimeError: startup exploded", app.logs[0])
        self.assertIn("RuntimeError: startup exploded", ui.messages[0][0])
        self.assertEqual(ui.messages[0][1], "NatureGenerator Startup Error")

    def test_entry_point_reports_and_reraises_stop_exception(self):
        entry_path = Path(__file__).parents[1] / "NatureGenerator.py"
        spec = importlib.util.spec_from_file_location(
            "stopping_addin_entry", str(entry_path)
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        app, ui, _, _ = fake_fusion_ui()
        failing_runtime = ModuleType("fusion.runtime")
        failing_runtime.start = lambda context: None
        failing_runtime.stop = lambda context: (_ for _ in ()).throw(
            RuntimeError("stop exploded")
        )
        modules = fake_adsk_modules(app)
        modules["fusion.runtime"] = failing_runtime
        with patch.dict(sys.modules, modules):
            with self.assertRaisesRegex(RuntimeError, "stop exploded"):
                module.stop(None)

        self.assertIn("RuntimeError: stop exploded", app.logs[0])
        self.assertIn("RuntimeError: stop exploded", ui.messages[0][0])
        self.assertEqual(ui.messages[0][1], "NatureGenerator Stop Error")


class FusionRuntimeStartupTests(unittest.TestCase):
    def setUp(self):
        runtime._handlers.clear()
        runtime._command_handler_groups.clear()
        runtime._started = False

    def tearDown(self):
        runtime._handlers.clear()
        runtime._command_handler_groups.clear()
        runtime._started = False

    def _start(self, global_panel=True, workspace_panel=True):
        app, ui, workspace, panel = fake_fusion_ui(
            global_panel=global_panel,
            workspace_panel=workspace_panel,
        )
        with patch.dict(sys.modules, fake_adsk_modules(app)):
            runtime.start()
        return app, ui, workspace, panel

    def test_prefers_all_toolbar_panels_lookup(self):
        app, ui, workspace, panel = self._start(
            global_panel=True, workspace_panel=True
        )
        self.assertEqual(ui.allToolbarPanels.lookups, [runtime.PANEL_ID])
        self.assertEqual(workspace.toolbarPanels.lookups, [])

    def test_falls_back_to_workspace_panel_lookup(self):
        app, ui, workspace, panel = self._start(
            global_panel=False, workspace_panel=True
        )
        self.assertEqual(ui.allToolbarPanels.lookups, [runtime.PANEL_ID])
        self.assertEqual(workspace.toolbarPanels.lookups, [runtime.PANEL_ID])

    def test_missing_panel_error_includes_ids_and_active_workspace(self):
        app, ui, workspace, panel = fake_fusion_ui(
            global_panel=False, workspace_panel=False
        )
        with patch.dict(sys.modules, fake_adsk_modules(app)):
            with self.assertRaises(runtime.FusionRuntimeError) as raised:
                runtime.start()
        message = str(raised.exception)
        self.assertIn(runtime.PANEL_ID, message)
        self.assertIn(runtime.WORKSPACE_ID, message)
        self.assertIn("active workspace", message)
        self.assertIn("Design", message)

    def test_successful_registration_logs_checkpoints(self):
        app, ui, workspace, panel = self._start()
        self.assertEqual(
            app.logs,
            [
                "NatureGenerator startup entered",
                "application and user interface resolved",
                "command definition resolved or created",
                "workspace resolved",
                "toolbar panel resolved",
                "toolbar control resolved or created",
                "event handlers retained",
                "NatureGenerator startup completed",
            ],
        )
        self.assertEqual(len(runtime._handlers), 1)
        control = panel.controls.items[runtime.COMMAND_ID]
        self.assertTrue(control.isPromoted)
        self.assertTrue(control.isPromotedByDefault)
        self.assertEqual(ui.messages, [])

    def test_command_creation_populates_interactive_inputs(self):
        app, ui, workspace, panel = self._start()
        definition = ui.commandDefinitions.items[runtime.COMMAND_ID]
        command = FakeCommand()
        definition.commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )

        inputs = command.commandInputs.items
        preset_input = inputs[runtime.PRESET_INPUT_ID]
        labels = [item.name for item in preset_input.listItems.items]
        self.assertIn("Sponge", labels)
        self.assertIn("Coral", labels)
        for name in ("Bone",):
            self.assertIn("{} — Coming Soon".format(name), labels)
        self.assertIn("Bark", labels)
        self.assertIn("Rock", labels)
        self.assertNotIn("Coral — Coming Soon", labels)
        self.assertEqual(preset_input.selectedItem.name, "Sponge")
        self.assertEqual(inputs[runtime.CELL_SIZE_INPUT_ID].unit, "mm")
        self.assertEqual(inputs[runtime.CELL_SIZE_INPUT_ID].value, 1.0)
        self.assertEqual(inputs[runtime.THICKNESS_INPUT_ID].unit, "")
        self.assertEqual(inputs[runtime.THICKNESS_INPUT_ID].value, 0.2)
        self.assertEqual(
            inputs[runtime.RESOLUTION_INPUT_ID].value, DEFAULT_RESOLUTION
        )
        self.assertEqual(len(command.execute.handlers), 1)
        self.assertEqual(len(command.inputChanged.handlers), 1)
        self.assertEqual(len(command.validateInputs.handlers), 1)
        self.assertEqual(len(command.destroy.handlers), 1)

    def test_preset_switching_updates_visible_metadata_inputs(self):
        app, ui, workspace, panel = self._start()
        definition = ui.commandDefinitions.items[runtime.COMMAND_ID]
        command = FakeCommand()
        definition.commandCreated.handlers[0].notify(SimpleNamespace(command=command))
        preset_input = command.commandInputs.items[runtime.PRESET_INPUT_ID]

        rock_item = next(item for item in preset_input.listItems.items if item.name == "Rock")
        preset_input.selectedItem = rock_item
        command.inputChanged.handlers[0].notify(SimpleNamespace(input=preset_input))

        rock_ids = {
            runtime._parameter_input_id("rock", key)
            for key in ("size", "roughness", "seed", "resolution")
        }
        self.assertTrue(all(command.commandInputs.items[key].isVisible for key in rock_ids))
        self.assertFalse(command.commandInputs.items[runtime.CELL_SIZE_INPUT_ID].isVisible)
        self.assertEqual(command.commandInputs.items[
            runtime._parameter_input_id("rock", "size")].name, "Size")

        bark_item = next(item for item in preset_input.listItems.items if item.name == "Bark")
        preset_input.selectedItem = bark_item
        command.inputChanged.handlers[0].notify(SimpleNamespace(input=preset_input))
        bark_keys = (
            "diameter", "height", "bark_depth", "groove_scale", "twist",
            "seed", "resolution",
        )
        self.assertTrue(all(
            command.commandInputs.items[
                runtime._parameter_input_id("bark", key)
            ].isVisible
            for key in bark_keys
        ))
        preset_input.selectedItem = rock_item
        command.inputChanged.handlers[0].notify(SimpleNamespace(input=preset_input))
        preset_input.selectedItem = bark_item
        command.inputChanged.handlers[0].notify(SimpleNamespace(input=preset_input))
        self.assertEqual(
            len([key for key in command.commandInputs.items if key.startswith("parameter_bark_")]),
            len(bark_keys),
        )

    def test_bark_selection_builds_metadata_driven_request(self):
        captured = []
        result = SimpleNamespace(
            statistics=SimpleNamespace(vertex_count=10, face_count=20), elapsed_time=0.25
        )
        body = SimpleNamespace(name="NatureGenerator Bark")
        app, ui, workspace, panel = fake_fusion_ui()
        with patch(
            "commands.generate_nature.generate_nature",
            lambda request, inserter: (captured.append(request) or (result, body)),
        ):
            with patch.dict(sys.modules, fake_adsk_modules(app)):
                runtime.start()
        command = FakeCommand()
        ui.commandDefinitions.items[runtime.COMMAND_ID].commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )
        preset_input = command.commandInputs.items[runtime.PRESET_INPUT_ID]
        preset_input.selectedItem = next(
            item for item in preset_input.listItems.items if item.name == "Bark"
        )
        command.execute.handlers[0].notify(SimpleNamespace(command=command))
        self.assertEqual(captured[0].preset_id, "bark")
        self.assertEqual(set(captured[0].parameter_overrides), {
            "diameter", "height", "bark_depth", "groove_scale", "twist", "seed",
        })
        self.assertEqual(captured[0].resolution, 33)

    def test_rock_selection_builds_metadata_driven_request(self):
        captured = []
        result = SimpleNamespace(
            statistics=SimpleNamespace(vertex_count=10, face_count=20), elapsed_time=0.25
        )
        body = SimpleNamespace(name="NatureGenerator Rock")
        app, ui, workspace, panel = fake_fusion_ui()
        with patch(
            "commands.generate_nature.generate_nature",
            lambda request, inserter: (captured.append(request) or (result, body)),
        ):
            with patch.dict(sys.modules, fake_adsk_modules(app)):
                runtime.start()
        command = FakeCommand()
        ui.commandDefinitions.items[runtime.COMMAND_ID].commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )
        preset_input = command.commandInputs.items[runtime.PRESET_INPUT_ID]
        preset_input.selectedItem = next(
            item for item in preset_input.listItems.items if item.name == "Rock"
        )
        command.execute.handlers[0].notify(SimpleNamespace(command=command))

        self.assertEqual(captured[0].preset_id, "rock")
        self.assertEqual(set(captured[0].parameter_overrides), {"size", "roughness", "seed"})
        self.assertEqual(captured[0].resolution, DEFAULT_RESOLUTION)

    def test_command_execute_builds_request_from_input_values(self):
        captured = []
        result = SimpleNamespace(
            statistics=SimpleNamespace(vertex_count=10, face_count=20),
            elapsed_time=0.25,
        )
        body = SimpleNamespace(name="NatureGenerator Sponge")

        def execute_request(request, inserter):
            captured.append(request)
            return result, body

        app, ui, workspace, panel = fake_fusion_ui()
        with patch("commands.generate_nature.generate_nature", execute_request):
            with patch.dict(sys.modules, fake_adsk_modules(app)):
                runtime.start()
        definition = ui.commandDefinitions.items[runtime.COMMAND_ID]
        command = FakeCommand()
        definition.commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )
        inputs = command.commandInputs.items
        inputs[runtime.CELL_SIZE_INPUT_ID].value = 1.2
        inputs[runtime.THICKNESS_INPUT_ID].value = 0.3
        inputs[runtime.RESOLUTION_INPUT_ID].value = 19
        command.execute.handlers[0].notify(SimpleNamespace(command=command))

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0].preset_id, "sponge")
        self.assertEqual(captured[0].parameter_overrides["cell_size"], 12.0)
        self.assertEqual(captured[0].parameter_overrides["thickness"], 0.3)
        self.assertEqual(captured[0].resolution, 19)

    def test_cancel_creates_no_geometry_and_releases_command_handlers(self):
        calls = []
        app, ui, workspace, panel = fake_fusion_ui()
        with patch(
            "commands.generate_nature.generate_nature",
            lambda request, inserter: calls.append(request),
        ):
            with patch.dict(sys.modules, fake_adsk_modules(app)):
                runtime.start()
        definition = ui.commandDefinitions.items[runtime.COMMAND_ID]
        command = FakeCommand()
        definition.commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )

        self.assertEqual(calls, [])
        self.assertEqual(len(runtime._command_handler_groups), 1)
        command.destroy.handlers[0].notify(SimpleNamespace(command=command))
        self.assertEqual(calls, [])
        self.assertEqual(runtime._command_handler_groups, [])

    def test_unavailable_selection_is_non_destructive(self):
        app, ui, workspace, panel = self._start()
        definition = ui.commandDefinitions.items[runtime.COMMAND_ID]
        command = FakeCommand()
        definition.commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )
        preset_input = command.commandInputs.items[runtime.PRESET_INPUT_ID]
        preset_input.selectedItem = next(
            item
            for item in preset_input.listItems.items
            if item.name.startswith("Bone")
        )
        command.execute.handlers[0].notify(SimpleNamespace(command=command))

        self.assertEqual(len(ui.messages), 1)
        self.assertIn("unavailable", ui.messages[0][0])
        self.assertEqual(ui.messages[0][1], "Generate Nature")

    def test_coral_selection_builds_a_coral_request(self):
        captured = []
        result = SimpleNamespace(
            statistics=SimpleNamespace(vertex_count=10, face_count=20),
            elapsed_time=0.25,
        )
        body = SimpleNamespace(name="NatureGenerator Coral")

        app, ui, workspace, panel = fake_fusion_ui()
        with patch(
            "commands.generate_nature.generate_nature",
            lambda request, inserter: (captured.append(request) or (result, body)),
        ):
            with patch.dict(sys.modules, fake_adsk_modules(app)):
                runtime.start()
        definition = ui.commandDefinitions.items[runtime.COMMAND_ID]
        command = FakeCommand()
        definition.commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )
        preset_input = command.commandInputs.items[runtime.PRESET_INPUT_ID]
        preset_input.selectedItem = next(
            item for item in preset_input.listItems.items if item.name == "Coral"
        )
        command.execute.handlers[0].notify(SimpleNamespace(command=command))

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0].preset_id, "coral")
        self.assertEqual(
            set(captured[0].parameter_overrides), {"cell_size", "thickness"}
        )

    def test_invalid_cell_size_is_reported_without_geometry(self):
        app, ui, workspace, panel = self._start()
        definition = ui.commandDefinitions.items[runtime.COMMAND_ID]
        command = FakeCommand()
        definition.commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )
        command.commandInputs.items[runtime.CELL_SIZE_INPUT_ID].value = 0.0
        command.execute.handlers[0].notify(SimpleNamespace(command=command))

        self.assertEqual(len(ui.messages), 1)
        self.assertIn("Cell Size", ui.messages[0][0])
        self.assertEqual(ui.messages[0][1], "Generate Nature")

    def test_invalid_values_disable_execution_validation(self):
        app, ui, workspace, panel = self._start()
        command = FakeCommand()
        ui.commandDefinitions.items[runtime.COMMAND_ID].commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )
        command.commandInputs.items[runtime.CELL_SIZE_INPUT_ID].value = 0.0
        args = SimpleNamespace(areInputsValid=True)
        command.validateInputs.handlers[0].notify(args)
        self.assertFalse(args.areInputsValid)

    def test_invalid_bark_depth_ratio_prevents_geometry(self):
        app, ui, workspace, panel = fake_fusion_ui()
        with patch.dict(sys.modules, fake_adsk_modules(app)):
            runtime.start()
        command = FakeCommand()
        ui.commandDefinitions.items[runtime.COMMAND_ID].commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )
        preset_input = command.commandInputs.items[runtime.PRESET_INPUT_ID]
        preset_input.selectedItem = next(
            item for item in preset_input.listItems.items if item.name == "Bark"
        )
        command.commandInputs.items[
            runtime._parameter_input_id("bark", "diameter")
        ].value = 3.0
        command.commandInputs.items[
            runtime._parameter_input_id("bark", "bark_depth")
        ].value = 1.5
        command.execute.handlers[0].notify(SimpleNamespace(command=command))
        self.assertIn("25%", ui.messages[0][0])

    def test_repeated_start_stop_does_not_duplicate_ui_or_handlers(self):
        app, ui, workspace, panel = fake_fusion_ui()
        with patch.dict(sys.modules, fake_adsk_modules(app)):
            runtime.start()
            runtime.start()
            self.assertEqual(ui.commandDefinitions.add_count, 1)
            self.assertEqual(panel.controls.add_count, 1)
            self.assertEqual(len(runtime._handlers), 1)
            runtime.stop()
            self.assertNotIn(runtime.COMMAND_ID, ui.commandDefinitions.items)
            self.assertNotIn(runtime.COMMAND_ID, panel.controls.items)
            self.assertEqual(runtime._handlers, [])
            runtime.start()
            self.assertEqual(ui.commandDefinitions.add_count, 2)
            self.assertEqual(panel.controls.add_count, 2)


if __name__ == "__main__":
    unittest.main()
