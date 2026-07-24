"""Tests for Procedural Lab Fusion adapters without Autodesk runtime."""

from types import SimpleNamespace
import unittest

from fusion.procedural_preview import ProceduralPreviewController
from fusion.selection_adapter import (
    FusionSelectionError,
    _polygon_mesh_data,
    selection_entities,
)


class FakeSelection:
    def __init__(self, entities):
        self.entities = entities
        self.selectionCount = len(entities)

    def selection(self, index):
        return SimpleNamespace(entity=self.entities[index])


class FusionSelectionTests(unittest.TestCase):
    def test_rejects_empty_and_multiple_selection(self):
        with self.assertRaisesRegex(FusionSelectionError, "exactly one"):
            selection_entities(FakeSelection([]))
        with self.assertRaisesRegex(FusionSelectionError, "multiple"):
            selection_entities(FakeSelection([object(), object()]))

    def test_polygon_mesh_converts_fusion_centimeters_to_millimeters(self):
        polygon = SimpleNamespace(
            nodeCoordinates=(
                SimpleNamespace(x=0, y=0, z=0),
                SimpleNamespace(x=1, y=0, z=0),
                SimpleNamespace(x=0, y=1, z=0),
            ),
            nodeIndices=(0, 1, 2),
        )
        mesh = _polygon_mesh_data(polygon)
        self.assertEqual(
            mesh.vertices, ((0, 0, 0), (10, 0, 0), (0, 10, 0))
        )
        self.assertEqual(mesh.faces, ((0, 1, 2),))

    def test_rejects_empty_invalid_and_non_finite_tessellation(self):
        with self.assertRaisesRegex(FusionSelectionError, "empty"):
            _polygon_mesh_data(SimpleNamespace(
                nodeCoordinates=(), nodeIndices=()
            ))
        with self.assertRaisesRegex(FusionSelectionError, "not triangular"):
            _polygon_mesh_data(SimpleNamespace(
                nodeCoordinates=(SimpleNamespace(x=0, y=0, z=0),),
                nodeIndices=(0,),
            ))
        with self.assertRaisesRegex(FusionSelectionError, "invalid geometry"):
            _polygon_mesh_data(SimpleNamespace(
                nodeCoordinates=(
                    SimpleNamespace(x=float("nan"), y=0, z=0),
                    SimpleNamespace(x=1, y=0, z=0),
                    SimpleNamespace(x=0, y=1, z=0),
                ),
                nodeIndices=(0, 1, 2),
            ))


class PreviewOwnershipTests(unittest.TestCase):
    def test_repeated_preview_replaces_only_owned_body(self):
        first = SimpleNamespace(isValid=True, deleted=False)
        first.deleteMe = lambda: setattr(first, "deleted", True)
        second = SimpleNamespace(isValid=True, deleted=False)
        second.deleteMe = lambda: setattr(second, "deleted", True)
        unrelated = SimpleNamespace(isValid=True, deleted=False)
        controller = ProceduralPreviewController()

        controller.replace(lambda: first)
        controller.replace(lambda: second)
        self.assertTrue(first.deleted)
        self.assertFalse(second.deleted)
        self.assertFalse(unrelated.deleted)
        controller.cleanup()
        self.assertTrue(second.deleted)
        self.assertFalse(unrelated.deleted)

    def test_failed_replacement_leaves_no_partial_ownership(self):
        controller = ProceduralPreviewController()
        with self.assertRaisesRegex(RuntimeError, "failed"):
            controller.replace(
                lambda: (_ for _ in ()).throw(RuntimeError("failed"))
            )
        self.assertIsNone(controller.body)
