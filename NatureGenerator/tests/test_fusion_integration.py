"""Tests for the Fusion boundary that run without Autodesk's Python runtime."""

import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from commands.generate_sponge import generate_sponge
from core.mesh import TriangleMesh
from fusion.mesh_body import MeshBodyBuilder, triangle_mesh_data
from fusion import runtime


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
    def addCommand(self, definition):
        control = SimpleNamespace(
            isPromoted=False,
            isPromotedByDefault=False,
            deleteMe=lambda: None,
        )
        self.items[runtime.COMMAND_ID] = control
        return control


class FakeCommandDefinitions(FakeCollection):
    def addButtonDefinition(self, command_id, name, description):
        definition = SimpleNamespace(
            commandCreated=FakeEvent(),
            deleteMe=lambda: None,
        )
        self.items[command_id] = definition
        return definition


def fake_adsk_modules(app):
    adsk = ModuleType("adsk")
    core = ModuleType("adsk.core")
    core.Application = SimpleNamespace(get=lambda: app)
    core.CommandEventHandler = object
    core.CommandCreatedEventHandler = object
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


class GenerateSpongeCommandTests(unittest.TestCase):
    def test_command_runs_runtime_and_passes_mesh_to_adapter(self):
        received = []
        sentinel_body = object()

        def insert_mesh(mesh, name):
            received.append((mesh, name))
            return sentinel_body

        result, body = generate_sponge(insert_mesh)

        self.assertIs(body, sentinel_body)
        self.assertEqual(result.preset_id, "sponge")
        self.assertEqual(result.generator_id, "gyroid")
        self.assertEqual(received, [(result.mesh, "NatureGenerator Sponge")])

    def test_command_rejects_missing_mesh_body(self):
        with self.assertRaisesRegex(RuntimeError, "did not return"):
            generate_sponge(lambda mesh, name: None)


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

    def test_entry_point_imports_without_autodesk_runtime(self):
        entry_path = Path(__file__).parents[1] / "NatureGenerator.py"
        spec = importlib.util.spec_from_file_location("addin_entry", str(entry_path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(callable(module.run))
        self.assertTrue(callable(module.stop))

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

    def tearDown(self):
        runtime._handlers.clear()

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

    def test_successful_registration_logs_checkpoints_and_confirms(self):
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
        self.assertEqual(
            ui.messages,
            [
                (
                    "NatureGenerator loaded successfully.\n"
                    "Open Design > Utilities > Add-Ins and run Generate Sponge.",
                    "NatureGenerator Development Diagnostics",
                )
            ],
        )


if __name__ == "__main__":
    unittest.main()
