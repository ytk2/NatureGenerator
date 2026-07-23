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

    @property
    def count(self):
        return len(self.items)

    def item(self, index):
        return self.items[index]

    def clear(self):
        self.items.clear()
        self.dropdown.selectedItem = None
        return True


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

    def addBoolValueInput(self, input_id, name, is_checkbox, resource, initial):
        result = SimpleNamespace(
            id=input_id, name=name, value=initial, isCheckBox=is_checkbox
        )
        self.items[input_id] = result
        return result


class FakeCommand:
    def __init__(self):
        self.commandInputs = FakeCommandInputs()
        self.execute = FakeEvent()
        self.executePreview = FakeEvent()
        self.inputChanged = FakeEvent()
        self.validateInputs = FakeEvent()
        self.destroy = FakeEvent()


def fire_preview(command, changed_input=None):
    """Simulate Fusion firing executePreview after a Preview input change."""

    changed = changed_input or SimpleNamespace(id=runtime.PREVIEW_INPUT_ID)
    command.inputChanged.handlers[0].notify(SimpleNamespace(input=changed))
    args = SimpleNamespace(command=command, isValidResult=None)
    command.executePreview.handlers[0].notify(args)
    return args


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

    def test_builder_removes_partially_inserted_body_if_naming_fails(self):
        mesh = TriangleMesh(
            vertices=((0, 0, 0), (1, 0, 0), (0, 1, 0)),
            faces=((0, 1, 2),),
        )

        class Body:
            deleted = 0

            @property
            def name(self):
                return ""

            @name.setter
            def name(self, value):
                raise RuntimeError("name failed")

            def deleteMe(self):
                self.deleted += 1

        body = Body()
        mesh_bodies = SimpleNamespace(
            addByTriangleMeshData=lambda *args: body
        )
        design = SimpleNamespace(
            rootComponent=SimpleNamespace(meshBodies=mesh_bodies)
        )
        adsk = ModuleType("adsk")
        adsk.core = ModuleType("adsk.core")
        adsk.fusion = ModuleType("adsk.fusion")
        with patch.dict(sys.modules, {
            "adsk": adsk, "adsk.core": adsk.core, "adsk.fusion": adsk.fusion,
        }):
            with self.assertRaisesRegex(RuntimeError, "name failed"):
                MeshBodyBuilder().build(mesh, "preview", design)
        self.assertEqual(body.deleted, 1)

    def test_builder_inserts_into_root_sets_visibility_and_refreshes(self):
        mesh = TriangleMesh(
            vertices=((0, 0, 0), (1, 0, 0), (0, 1, 0)),
            faces=((0, 1, 2),),
        )
        root = SimpleNamespace(name="Root Component")
        active = SimpleNamespace(name="Active Component")

        class Body:
            name = ""
            parentComponent = root
            assemblyContext = None
            entityToken = "preview-token"
            isVisible = True
            isLightBulbOn = False
            objectType = "adsk::fusion::MeshBody"

            def classType(self):
                return "adsk::fusion::MeshBody"

        body = Body()

        class MeshBodies:
            def __init__(self):
                self.items = []

            @property
            def count(self):
                return len(self.items)

            def addByTriangleMeshData(self, *args):
                self.items.append(body)
                return body

        root.meshBodies = MeshBodies()
        design = SimpleNamespace(rootComponent=root, activeComponent=active)
        refreshes = []
        app = SimpleNamespace(
            activeProduct=design,
            activeViewport=SimpleNamespace(refresh=lambda: refreshes.append(True)),
        )
        adsk = ModuleType("adsk")
        adsk.core = ModuleType("adsk.core")
        adsk.fusion = ModuleType("adsk.fusion")
        adsk.core.Application = SimpleNamespace(get=lambda: app)
        adsk.fusion.Design = SimpleNamespace(cast=lambda product: product)
        with patch.dict(sys.modules, {
            "adsk": adsk, "adsk.core": adsk.core, "adsk.fusion": adsk.fusion,
        }):
            created = MeshBodyBuilder().build(mesh, "Preview")

        self.assertIs(created, body)
        self.assertTrue(body.isLightBulbOn)
        self.assertEqual(refreshes, [True])
        self.assertEqual(root.meshBodies.count, 1)
        self.assertIs(body.parentComponent, root)
        self.assertIsNone(body.assemblyContext)


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

    def test_command_and_fusion_layers_do_not_reference_concrete_root_generator(self):
        package_root = Path(__file__).parents[1]
        for folder in ("commands", "fusion"):
            for module in (package_root / folder).glob("*.py"):
                self.assertNotIn("RootGenerator", module.read_text(encoding="utf-8"))

    def test_fusion_uses_preset_catalog_without_rock_registry_assumptions(self):
        source = (Path(__file__).parents[1] / "fusion" / "runtime.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("PresetCatalog", source)
        self.assertNotIn("PresetFactory", source)
        self.assertNotIn("RockFamilyRegistry", source)

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
        runtime._preview_controllers.clear()
        runtime._started = False

    def tearDown(self):
        runtime._handlers.clear()
        runtime._command_handler_groups.clear()
        runtime._preview_controllers.clear()
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
        self.assertIn("Root", labels)
        self.assertNotIn("Coral — Coming Soon", labels)
        self.assertEqual(preset_input.selectedItem.name, "Sponge")
        variant_input = inputs[runtime.VARIANT_INPUT_ID]
        self.assertEqual(
            [item.name for item in variant_input.listItems.items],
            [runtime.CUSTOM_VARIANT_LABEL, "Fine", "Balanced", "Bold"],
        )
        self.assertEqual(variant_input.selectedItem.name, runtime.CUSTOM_VARIANT_LABEL)
        family_input = inputs[runtime.FAMILY_INPUT_ID]
        self.assertEqual(
            [item.name for item in family_input.listItems.items],
            [
                "Smooth", "Weathered", "Rugged", "River Stone",
                "Granite", "Basalt", "Broken Rock",
            ],
        )
        self.assertFalse(family_input.isVisible)
        self.assertTrue(variant_input.isVisible)
        self.assertEqual(inputs[runtime.CELL_SIZE_INPUT_ID].unit, "mm")
        self.assertEqual(inputs[runtime.CELL_SIZE_INPUT_ID].value, 1.0)
        self.assertEqual(inputs[runtime.THICKNESS_INPUT_ID].unit, "")
        self.assertEqual(inputs[runtime.THICKNESS_INPUT_ID].value, 0.2)
        self.assertEqual(
            inputs[runtime.RESOLUTION_INPUT_ID].value, DEFAULT_RESOLUTION
        )
        self.assertEqual(len(command.execute.handlers), 1)
        self.assertEqual(len(command.executePreview.handlers), 1)
        self.assertEqual(len(command.inputChanged.handlers), 1)
        self.assertEqual(len(command.validateInputs.handlers), 1)
        self.assertEqual(len(command.destroy.handlers), 1)
        self.assertIn(runtime.PREVIEW_INPUT_ID, inputs)
        self.assertEqual(len(runtime._preview_controllers), 1)
        retained = runtime._command_handler_groups[0]
        self.assertIs(retained[0], command.execute.handlers[0])
        self.assertIs(retained[1], command.inputChanged.handlers[0])
        self.assertIs(retained[2], command.executePreview.handlers[0])
        self.assertIs(retained[3], command.validateInputs.handlers[0])
        self.assertIs(retained[4], command.destroy.handlers[0])

    def test_preview_create_replace_finalize_cancel_destroy_and_stop(self):
        app, ui, workspace, panel = self._start()
        command = FakeCommand()
        ui.commandDefinitions.items[runtime.COMMAND_ID].commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )
        preview_input = command.commandInputs.items[runtime.PREVIEW_INPUT_ID]
        created = []

        class Body:
            def __init__(self, name):
                self.name = name
                self.isValid = True
                self.deleted = 0

            def deleteMe(self):
                self.deleted += 1
                self.isValid = False

        def build(mesh, name):
            body = Body(name)
            created.append(body)
            return body

        result = SimpleNamespace(
            mesh=TriangleMesh(((0, 0, 0), (1, 0, 0), (0, 1, 0)), ((0, 1, 2),)),
            statistics=SimpleNamespace(vertex_count=3, face_count=1),
            elapsed_time=0.01,
        )
        with patch("generators.GeneratorFactory.generate_request", return_value=result):
            with patch("fusion.mesh_body.MeshBodyBuilder.build", side_effect=build):
                preview_input.value = True
                fire_preview(command)
                self.assertEqual(created[0].name, "NatureGenerator Preview — Sponge")
                self.assertTrue(created[0].isValid)
                self.assertIs(runtime._preview_controllers[0].body, created[0])
                command.commandInputs.items[runtime.THICKNESS_INPUT_ID].value = 0.3
                command.inputChanged.handlers[0].notify(SimpleNamespace(
                    input=command.commandInputs.items[runtime.THICKNESS_INPUT_ID]
                ))
                preview_input.value = True
                fire_preview(command, preview_input)
                self.assertEqual(created[0].deleted, 1)
                self.assertEqual(len(created), 2)
                command.execute.handlers[0].notify(SimpleNamespace(command=command))
                self.assertEqual(created[1].deleted, 1)
                self.assertEqual(created[2].name, "NatureGenerator Sponge")
                self.assertEqual(created[2].deleted, 0)

        command.destroy.handlers[0].notify(SimpleNamespace(command=command))
        self.assertEqual(created[2].deleted, 0)
        self.assertEqual(runtime._preview_controllers, [])

        second = FakeCommand()
        ui.commandDefinitions.items[runtime.COMMAND_ID].commandCreated.handlers[0].notify(
            SimpleNamespace(command=second)
        )
        second_preview = second.commandInputs.items[runtime.PREVIEW_INPUT_ID]
        with patch("generators.GeneratorFactory.generate_request", return_value=result):
            with patch("fusion.mesh_body.MeshBodyBuilder.build", side_effect=build):
                fire_preview(second, second_preview)
        pending = created[-1]
        with patch.dict(sys.modules, fake_adsk_modules(app)):
            runtime.stop()
        self.assertEqual(pending.deleted, 1)

    def test_preview_failure_reports_traceback_and_command_remains_usable(self):
        app, ui, workspace, panel = self._start()
        command = FakeCommand()
        ui.commandDefinitions.items[runtime.COMMAND_ID].commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )
        changed = SimpleNamespace(id=runtime.PREVIEW_INPUT_ID)
        with patch(
            "generators.GeneratorFactory.generate_request",
            side_effect=RuntimeError("preview exploded"),
        ):
            fire_preview(command, changed)
        self.assertEqual(ui.messages[-1][1], "Preview Error")
        self.assertIn("preview exploded", ui.messages[-1][0])
        self.assertTrue(any("Traceback" in message for message in app.logs))
        self.assertEqual(runtime._preview_controllers[0].state, "failed")

        result = SimpleNamespace(
            mesh=TriangleMesh(((0, 0, 0), (1, 0, 0), (0, 1, 0)), ((0, 1, 2),)),
            statistics=SimpleNamespace(vertex_count=3, face_count=1),
            elapsed_time=0.01,
        )
        body = SimpleNamespace(
            name="NatureGenerator Preview — Sponge", isValid=True,
            deleteMe=lambda: None,
        )
        with patch("generators.GeneratorFactory.generate_request", return_value=result):
            with patch("fusion.mesh_body.MeshBodyBuilder.build", return_value=body):
                fire_preview(command, changed)
        self.assertIs(runtime._preview_controllers[0].body, body)

    def test_preview_operational_lifecycle_is_logged_concisely(self):
        app, ui, workspace, panel = self._start()
        command = FakeCommand()
        ui.commandDefinitions.items[runtime.COMMAND_ID].commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )
        result = SimpleNamespace(
            mesh=TriangleMesh(((0, 0, 0), (1, 0, 0), (0, 1, 0)), ((0, 1, 2),)),
            statistics=SimpleNamespace(vertex_count=3, face_count=1),
            elapsed_time=0.01,
        )
        body = SimpleNamespace(
            name="NatureGenerator Preview — Sponge", isValid=True,
            deleteMe=lambda: None,
        )
        with patch("generators.GeneratorFactory.generate_request", return_value=result):
            with patch("fusion.mesh_body.MeshBodyBuilder.build", return_value=body):
                fire_preview(command)
        expected = (
            "Preview started:",
            "Preview created:",
        )
        position = -1
        for fragment in expected:
            position = next(
                index for index in range(position + 1, len(app.logs))
                if fragment in app.logs[index]
            )
        self.assertFalse(any("entityToken" in item for item in app.logs))
        self.assertFalse(any("objectType" in item for item in app.logs))

    def test_destroy_removes_successful_preview_without_touching_unrelated_body(self):
        app, ui, workspace, panel = self._start()
        command = FakeCommand()
        ui.commandDefinitions.items[runtime.COMMAND_ID].commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )

        class Body:
            def __init__(self):
                self.name = ""
                self.isValid = True
                self.deleted = 0

            def deleteMe(self):
                self.deleted += 1
                self.isValid = False

        preview = Body()
        unrelated = Body()
        result = SimpleNamespace(
            mesh=TriangleMesh(((0, 0, 0), (1, 0, 0), (0, 1, 0)), ((0, 1, 2),)),
            statistics=SimpleNamespace(vertex_count=3, face_count=1),
            elapsed_time=0.01,
        )
        with patch("generators.GeneratorFactory.generate_request", return_value=result):
            with patch("fusion.mesh_body.MeshBodyBuilder.build", return_value=preview):
                fire_preview(command)
        self.assertEqual(preview.deleted, 0)
        command.destroy.handlers[0].notify(SimpleNamespace(command=command))
        self.assertEqual(preview.deleted, 1)
        self.assertEqual(unrelated.deleted, 0)

    def test_stale_preview_is_deleted_and_current_final_is_regenerated(self):
        class Body:
            def __init__(self, name):
                self.name = name
                self.isValid = True
                self.deleted = 0

            def deleteMe(self):
                self.deleted += 1
                self.isValid = False

        result = SimpleNamespace(
            mesh=TriangleMesh(((0, 0, 0), (1, 0, 0), (0, 1, 0)), ((0, 1, 2),)),
            statistics=SimpleNamespace(vertex_count=3, face_count=1),
            elapsed_time=0.01,
        )
        preview = Body("preview")
        final = Body("NatureGenerator Sponge")
        final_requests = []
        with patch(
            "commands.generate_nature.generate_nature",
            side_effect=lambda request, insert: (
                final_requests.append(request) or (result, final)
            ),
        ):
            app, ui, workspace, panel = self._start()
        command = FakeCommand()
        ui.commandDefinitions.items[runtime.COMMAND_ID].commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )
        with patch("generators.GeneratorFactory.generate_request", return_value=result):
            with patch("fusion.mesh_body.MeshBodyBuilder.build", return_value=preview):
                fire_preview(command)
        thickness = command.commandInputs.items[runtime.THICKNESS_INPUT_ID]
        thickness.value = 0.3
        command.inputChanged.handlers[0].notify(SimpleNamespace(input=thickness))
        command.execute.handlers[0].notify(SimpleNamespace(command=command))
        self.assertEqual(preview.deleted, 1)
        self.assertEqual(final.deleted, 0)
        self.assertEqual(final_requests[0].parameter_overrides["thickness"], 0.3)

    def test_invalid_or_unavailable_preview_creates_no_body(self):
        app, ui, workspace, panel = self._start()
        command = FakeCommand()
        ui.commandDefinitions.items[runtime.COMMAND_ID].commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )
        preview_input = command.commandInputs.items[runtime.PREVIEW_INPUT_ID]
        command.commandInputs.items[runtime.CELL_SIZE_INPUT_ID].value = 0.0
        with patch("generators.GeneratorFactory.generate_request") as generate:
            fire_preview(command, preview_input)
        generate.assert_not_called()

        preset_input = command.commandInputs.items[runtime.PRESET_INPUT_ID]
        preset_input.selectedItem = next(
            item for item in preset_input.listItems.items if item.name.startswith("Bone")
        )
        with patch("generators.GeneratorFactory.generate_request") as generate:
            fire_preview(command, preview_input)
        generate.assert_not_called()

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

        root_item = next(item for item in preset_input.listItems.items if item.name == "Root")
        preset_input.selectedItem = root_item
        command.inputChanged.handlers[0].notify(SimpleNamespace(input=preset_input))
        root_keys = (
            "length", "root_radius", "branch_count", "branching", "spread",
            "taper", "gravity", "seed", "resolution",
        )
        self.assertTrue(all(
            command.commandInputs.items[
                runtime._parameter_input_id("root", key)
            ].isVisible
            for key in root_keys
        ))
        self.assertEqual(
            len([key for key in command.commandInputs.items if key.startswith("parameter_root_")]),
            len(root_keys),
        )

    def test_family_replaces_variant_for_rock_and_other_presets_keep_variants(self):
        app, ui, workspace, panel = self._start()
        command = FakeCommand()
        ui.commandDefinitions.items[runtime.COMMAND_ID].commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )
        inputs = command.commandInputs.items
        preset_input = inputs[runtime.PRESET_INPUT_ID]
        variant_input = inputs[runtime.VARIANT_INPUT_ID]
        family_input = inputs[runtime.FAMILY_INPUT_ID]
        sponge_cell = inputs[runtime.CELL_SIZE_INPUT_ID]
        sponge_cell.value = 1.3
        command.inputChanged.handlers[0].notify(SimpleNamespace(input=sponge_cell))

        rock_item = next(item for item in preset_input.listItems.items if item.name == "Rock")
        preset_input.selectedItem = rock_item
        command.inputChanged.handlers[0].notify(SimpleNamespace(input=preset_input))
        self.assertFalse(variant_input.isVisible)
        self.assertTrue(family_input.isVisible)
        self.assertEqual(
            [item.name for item in family_input.listItems.items],
            [
                "Smooth", "Weathered", "Rugged", "River Stone",
                "Granite", "Basalt", "Broken Rock",
            ],
        )
        self.assertEqual(family_input.selectedItem.name, "Smooth")

        sponge_item = next(
            item for item in preset_input.listItems.items if item.name == "Sponge"
        )
        preset_input.selectedItem = sponge_item
        command.inputChanged.handlers[0].notify(SimpleNamespace(input=preset_input))
        self.assertEqual(sponge_cell.value, 1.3)
        self.assertTrue(variant_input.isVisible)
        self.assertFalse(family_input.isVisible)
        self.assertEqual(variant_input.selectedItem.name, runtime.CUSTOM_VARIANT_LABEL)

    def test_named_rock_family_applies_values_and_manual_edit_retains_family(self):
        app, ui, workspace, panel = self._start()
        command = FakeCommand()
        ui.commandDefinitions.items[runtime.COMMAND_ID].commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )
        inputs = command.commandInputs.items
        preset_input = inputs[runtime.PRESET_INPUT_ID]
        family_input = inputs[runtime.FAMILY_INPUT_ID]
        preset_input.selectedItem = next(
            item for item in preset_input.listItems.items if item.name == "Rock"
        )
        command.inputChanged.handlers[0].notify(SimpleNamespace(input=preset_input))
        family_input.selectedItem = next(
            item for item in family_input.listItems.items if item.name == "Rugged"
        )
        command.inputChanged.handlers[0].notify(SimpleNamespace(input=family_input))

        size = inputs[runtime._parameter_input_id("rock", "size")]
        roughness = inputs[runtime._parameter_input_id("rock", "roughness")]
        seed = inputs[runtime._parameter_input_id("rock", "seed")]
        resolution = inputs[runtime._parameter_input_id("rock", "resolution")]
        self.assertEqual((size.value, roughness.value, seed.value, resolution.value),
                         (4.5, 0.62, 23, 25))
        self.assertEqual(family_input.selectedItem.name, "Rugged")

        roughness.value = 0.5
        command.inputChanged.handlers[0].notify(SimpleNamespace(input=roughness))
        self.assertEqual(family_input.selectedItem.name, "Rugged")

    def test_variant_selection_marks_existing_preview_stale_without_generating(self):
        app, ui, workspace, panel = self._start()
        command = FakeCommand()
        ui.commandDefinitions.items[runtime.COMMAND_ID].commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )
        result = SimpleNamespace(
            mesh=TriangleMesh(((0, 0, 0), (1, 0, 0), (0, 1, 0)), ((0, 1, 2),)),
            statistics=SimpleNamespace(vertex_count=3, face_count=1),
            elapsed_time=0.01,
        )
        body = SimpleNamespace(
            name="NatureGenerator Preview — Sponge", isValid=True,
            deleteMe=lambda: None,
        )
        with patch("generators.GeneratorFactory.generate_request", return_value=result) as generate:
            with patch("fusion.mesh_body.MeshBodyBuilder.build", return_value=body):
                fire_preview(command)
        controller = runtime._preview_controllers[0]
        self.assertEqual(controller.state, "current")
        variant_input = command.commandInputs.items[runtime.VARIANT_INPUT_ID]
        variant_input.selectedItem = next(
            item for item in variant_input.listItems.items if item.name == "Fine"
        )
        command.inputChanged.handlers[0].notify(SimpleNamespace(input=variant_input))
        self.assertEqual(controller.state, "stale")
        self.assertEqual(generate.call_count, 1)

    def test_named_variant_builds_fresh_preview_request(self):
        app, ui, workspace, panel = self._start()
        command = FakeCommand()
        ui.commandDefinitions.items[runtime.COMMAND_ID].commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )
        variant_input = command.commandInputs.items[runtime.VARIANT_INPUT_ID]
        variant_input.selectedItem = next(
            item for item in variant_input.listItems.items if item.name == "Fine"
        )
        command.inputChanged.handlers[0].notify(SimpleNamespace(input=variant_input))
        result = SimpleNamespace(
            mesh=TriangleMesh(((0, 0, 0), (1, 0, 0), (0, 1, 0)), ((0, 1, 2),)),
            statistics=SimpleNamespace(vertex_count=3, face_count=1),
            elapsed_time=0.01,
        )
        body = SimpleNamespace(name="preview", isValid=True, deleteMe=lambda: None)
        with patch("generators.GeneratorFactory.generate_request", return_value=result) as generate:
            with patch("fusion.mesh_body.MeshBodyBuilder.build", return_value=body):
                fire_preview(command)
        request = generate.call_args.args[0]
        self.assertEqual(request.preset_id, "sponge")
        self.assertEqual(request.parameter_overrides["cell_size"], 7.0)
        self.assertEqual(request.parameter_overrides["thickness"], 0.14)
        self.assertEqual(request.resolution, 17)

    def test_rugged_rock_preview_uses_adaptive_resolution_and_same_values(self):
        app, ui, workspace, panel = self._start()
        command = FakeCommand()
        ui.commandDefinitions.items[runtime.COMMAND_ID].commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )
        inputs = command.commandInputs.items
        preset_input = inputs[runtime.PRESET_INPUT_ID]
        preset_input.selectedItem = next(
            item for item in preset_input.listItems.items if item.name == "Rock"
        )
        command.inputChanged.handlers[0].notify(SimpleNamespace(input=preset_input))
        family_input = inputs[runtime.FAMILY_INPUT_ID]
        family_input.selectedItem = next(
            item for item in family_input.listItems.items if item.name == "Rugged"
        )
        command.inputChanged.handlers[0].notify(SimpleNamespace(input=family_input))

        result = SimpleNamespace(
            mesh=TriangleMesh(((0, 0, 0), (1, 0, 0), (0, 1, 0)), ((0, 1, 2),)),
            statistics=SimpleNamespace(vertex_count=3, face_count=1),
            elapsed_time=0.01,
        )
        body = SimpleNamespace(name="preview", isValid=True, deleteMe=lambda: None)
        with patch("generators.GeneratorFactory.generate_request", return_value=result) as generate:
            with patch("fusion.mesh_body.MeshBodyBuilder.build", return_value=body):
                fire_preview(command)
        request = generate.call_args.args[0]
        self.assertEqual(request.resolution, 21)
        self.assertEqual(request.family_id, "rugged")
        self.assertEqual(
            request.parameter_overrides,
            {"size": 45.0, "roughness": 0.62, "seed": 23},
        )

    def test_river_stone_family_builds_existing_family_preview_request(self):
        app, ui, workspace, panel = self._start()
        command = FakeCommand()
        ui.commandDefinitions.items[runtime.COMMAND_ID].commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )
        inputs = command.commandInputs.items
        preset_input = inputs[runtime.PRESET_INPUT_ID]
        preset_input.selectedItem = next(
            item for item in preset_input.listItems.items if item.name == "Rock"
        )
        command.inputChanged.handlers[0].notify(SimpleNamespace(input=preset_input))
        family_input = inputs[runtime.FAMILY_INPUT_ID]
        family_input.selectedItem = next(
            item for item in family_input.listItems.items
            if item.name == "River Stone"
        )
        command.inputChanged.handlers[0].notify(SimpleNamespace(input=family_input))

        result = SimpleNamespace(
            mesh=TriangleMesh(((0, 0, 0), (1, 0, 0), (0, 1, 0)), ((0, 1, 2),)),
            statistics=SimpleNamespace(vertex_count=3, face_count=1),
            elapsed_time=0.01,
        )
        body = SimpleNamespace(name="preview", isValid=True, deleteMe=lambda: None)
        with patch(
            "generators.GeneratorFactory.generate_request", return_value=result
        ) as generate:
            with patch("fusion.mesh_body.MeshBodyBuilder.build", return_value=body):
                fire_preview(command)
        request = generate.call_args.args[0]
        self.assertEqual(request.family_id, "river_stone")
        self.assertEqual(request.resolution, 21)
        self.assertEqual(
            request.parameter_overrides,
            {"size": 40.0, "roughness": 0.35, "seed": 1},
        )

    def test_new_family_selections_apply_registry_defaults(self):
        app, ui, workspace, panel = self._start()
        command = FakeCommand()
        ui.commandDefinitions.items[runtime.COMMAND_ID].commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )
        inputs = command.commandInputs.items
        preset_input = inputs[runtime.PRESET_INPUT_ID]
        preset_input.selectedItem = next(
            item for item in preset_input.listItems.items if item.name == "Rock"
        )
        command.inputChanged.handlers[0].notify(SimpleNamespace(input=preset_input))
        family_input = inputs[runtime.FAMILY_INPUT_ID]
        expected = {
            "Granite": (5.0, 0.45, 37, 25),
            "Basalt": (5.0, 0.25, 61, 25),
            "Broken Rock": (5.0, 0.55, 97, 25),
        }
        for family_name, values in expected.items():
            with self.subTest(family=family_name):
                family_input.selectedItem = next(
                    item for item in family_input.listItems.items
                    if item.name == family_name
                )
                command.inputChanged.handlers[0].notify(
                    SimpleNamespace(input=family_input)
                )
                actual = tuple(
                    inputs[runtime._parameter_input_id("rock", key)].value
                    for key in ("size", "roughness", "seed", "resolution")
                )
                self.assertEqual(actual, values)

    def test_new_families_use_adaptive_preview_and_retain_final_resolution_input(self):
        captured = []
        result = SimpleNamespace(
            mesh=TriangleMesh(((0, 0, 0), (1, 0, 0), (0, 1, 0)), ((0, 1, 2),)),
            statistics=SimpleNamespace(vertex_count=3, face_count=1),
            elapsed_time=0.01,
        )
        body = SimpleNamespace(
            name="preview", isValid=True, deleteMe=lambda: None
        )
        app, ui, workspace, panel = self._start()
        command = FakeCommand()
        ui.commandDefinitions.items[runtime.COMMAND_ID].commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )
        inputs = command.commandInputs.items
        preset_input = inputs[runtime.PRESET_INPUT_ID]
        preset_input.selectedItem = next(
            item for item in preset_input.listItems.items if item.name == "Rock"
        )
        command.inputChanged.handlers[0].notify(SimpleNamespace(input=preset_input))
        family_input = inputs[runtime.FAMILY_INPUT_ID]
        with patch(
            "generators.GeneratorFactory.generate_request",
            side_effect=lambda request: (captured.append(request) or result),
        ):
            with patch("fusion.mesh_body.MeshBodyBuilder.build", return_value=body):
                for family_name in ("Granite", "Basalt", "Broken Rock"):
                    family_input.selectedItem = next(
                        item for item in family_input.listItems.items
                        if item.name == family_name
                    )
                    command.inputChanged.handlers[0].notify(
                        SimpleNamespace(input=family_input)
                    )
                    fire_preview(command)

        self.assertEqual(
            tuple(request.family_id for request in captured),
            ("granite", "basalt", "broken_rock"),
        )
        self.assertTrue(all(request.resolution == 21 for request in captured))
        self.assertTrue(all(
            inputs[runtime._parameter_input_id("rock", "resolution")].value == 25
            for _ in captured
        ))

    def test_family_change_marks_preview_stale_and_replaces_owned_body(self):
        app, ui, workspace, panel = self._start()
        command = FakeCommand()
        ui.commandDefinitions.items[runtime.COMMAND_ID].commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )
        inputs = command.commandInputs.items
        preset_input = inputs[runtime.PRESET_INPUT_ID]
        preset_input.selectedItem = next(
            item for item in preset_input.listItems.items if item.name == "Rock"
        )
        command.inputChanged.handlers[0].notify(SimpleNamespace(input=preset_input))

        class Body:
            def __init__(self):
                self.name = "preview"
                self.isValid = True
                self.deleted = 0

            def deleteMe(self):
                self.deleted += 1
                self.isValid = False

        result = SimpleNamespace(
            mesh=TriangleMesh(((0, 0, 0), (1, 0, 0), (0, 1, 0)), ((0, 1, 2),)),
            statistics=SimpleNamespace(vertex_count=3, face_count=1),
            elapsed_time=0.01,
        )
        bodies = []

        def build(mesh, name):
            body = Body()
            body.name = name
            bodies.append(body)
            return body

        with patch(
            "generators.GeneratorFactory.generate_request", return_value=result
        ) as generate:
            with patch("fusion.mesh_body.MeshBodyBuilder.build", side_effect=build):
                fire_preview(command)
                family_input = inputs[runtime.FAMILY_INPUT_ID]
                family_input.selectedItem = next(
                    item for item in family_input.listItems.items
                    if item.name == "River Stone"
                )
                command.inputChanged.handlers[0].notify(
                    SimpleNamespace(input=family_input)
                )
                self.assertEqual(runtime._preview_controllers[0].state, "stale")
                fire_preview(command)

        self.assertEqual(generate.call_count, 2)
        self.assertEqual(generate.call_args_list[0].args[0].family_id, "smooth")
        self.assertEqual(generate.call_args_list[1].args[0].family_id, "river_stone")
        self.assertEqual(bodies[0].deleted, 1)
        self.assertEqual(bodies[1].deleted, 0)

    def test_river_stone_final_uses_fresh_full_resolution_request(self):
        captured = []
        result = SimpleNamespace(
            statistics=SimpleNamespace(vertex_count=3, face_count=1),
            elapsed_time=0.01,
        )
        body = SimpleNamespace(name="NatureGenerator Rock")
        app, ui, workspace, panel = fake_fusion_ui()
        with patch(
            "commands.generate_nature.generate_nature",
            lambda request, insert: (captured.append(request) or (result, body)),
        ):
            with patch.dict(sys.modules, fake_adsk_modules(app)):
                runtime.start()
        command = FakeCommand()
        ui.commandDefinitions.items[runtime.COMMAND_ID].commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )
        inputs = command.commandInputs.items
        preset_input = inputs[runtime.PRESET_INPUT_ID]
        preset_input.selectedItem = next(
            item for item in preset_input.listItems.items if item.name == "Rock"
        )
        command.inputChanged.handlers[0].notify(SimpleNamespace(input=preset_input))
        family_input = inputs[runtime.FAMILY_INPUT_ID]
        family_input.selectedItem = next(
            item for item in family_input.listItems.items
            if item.name == "River Stone"
        )
        command.inputChanged.handlers[0].notify(SimpleNamespace(input=family_input))
        command.execute.handlers[0].notify(SimpleNamespace(command=command))
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0].family_id, "river_stone")
        self.assertEqual(captured[0].resolution, 25)
        self.assertEqual(
            captured[0].parameter_overrides,
            {"size": 40.0, "roughness": 0.35, "seed": 1},
        )

    def test_named_variant_builds_fresh_final_request(self):
        captured = []
        result = SimpleNamespace(
            statistics=SimpleNamespace(vertex_count=3, face_count=1),
            elapsed_time=0.01,
        )
        body = SimpleNamespace(name="NatureGenerator Sponge")
        app, ui, workspace, panel = fake_fusion_ui()
        with patch(
            "commands.generate_nature.generate_nature",
            lambda request, insert: (captured.append(request) or (result, body)),
        ):
            with patch.dict(sys.modules, fake_adsk_modules(app)):
                runtime.start()
        command = FakeCommand()
        ui.commandDefinitions.items[runtime.COMMAND_ID].commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )
        variant_input = command.commandInputs.items[runtime.VARIANT_INPUT_ID]
        variant_input.selectedItem = next(
            item for item in variant_input.listItems.items if item.name == "Bold"
        )
        command.inputChanged.handlers[0].notify(SimpleNamespace(input=variant_input))
        command.execute.handlers[0].notify(SimpleNamespace(command=command))
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0].parameter_overrides["cell_size"], 16.0)
        self.assertEqual(captured[0].parameter_overrides["thickness"], 0.32)
        self.assertEqual(captured[0].resolution, 17)

    def test_root_selection_builds_metadata_driven_request(self):
        captured = []
        result = SimpleNamespace(
            statistics=SimpleNamespace(vertex_count=10, face_count=20), elapsed_time=0.25
        )
        body = SimpleNamespace(name="NatureGenerator Root")
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
            item for item in preset_input.listItems.items if item.name == "Root"
        )
        command.execute.handlers[0].notify(SimpleNamespace(command=command))
        self.assertEqual(captured[0].preset_id, "root")
        self.assertEqual(set(captured[0].parameter_overrides), {
            "length", "root_radius", "branch_count", "branching", "spread",
            "taper", "gravity", "seed",
        })
        self.assertEqual(captured[0].resolution, 37)

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
        command.inputChanged.handlers[0].notify(SimpleNamespace(input=preset_input))
        command.execute.handlers[0].notify(SimpleNamespace(command=command))

        self.assertEqual(captured[0].preset_id, "rock")
        self.assertEqual(set(captured[0].parameter_overrides), {"size", "roughness", "seed"})
        self.assertEqual(captured[0].resolution, DEFAULT_RESOLUTION)
        self.assertEqual(captured[0].family_id, "smooth")

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

    def test_invalid_root_radius_ratio_prevents_geometry(self):
        app, ui, workspace, panel = fake_fusion_ui()
        with patch.dict(sys.modules, fake_adsk_modules(app)):
            runtime.start()
        command = FakeCommand()
        ui.commandDefinitions.items[runtime.COMMAND_ID].commandCreated.handlers[0].notify(
            SimpleNamespace(command=command)
        )
        preset_input = command.commandInputs.items[runtime.PRESET_INPUT_ID]
        preset_input.selectedItem = next(
            item for item in preset_input.listItems.items if item.name == "Root"
        )
        command.commandInputs.items[
            runtime._parameter_input_id("root", "length")
        ].value = 4.0
        command.commandInputs.items[
            runtime._parameter_input_id("root", "root_radius")
        ].value = 2.0
        command.execute.handlers[0].notify(SimpleNamespace(command=command))
        self.assertIn("20%", ui.messages[0][0])

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
