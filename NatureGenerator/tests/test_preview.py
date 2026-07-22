"""Pure tests for command-instance preview state and ownership."""

from pathlib import Path
from types import SimpleNamespace
import unittest

from fusion.preview import PreviewController, preview_request, request_signature
from generators import GenerationRequest


class FakeBody:
    def __init__(self, name="preview"):
        self.name = name
        self.isValid = True
        self.delete_count = 0

    def deleteMe(self):
        self.delete_count += 1
        self.isValid = False


class PreviewControllerTests(unittest.TestCase):
    def setUp(self):
        self.request = GenerationRequest(
            "sponge", {"cell_size": 10.0, "thickness": 0.2}, 17
        )
        self.result = SimpleNamespace(mesh=object())

    def test_initial_state_and_signature_are_deterministic_without_hash(self):
        controller = PreviewController()
        reordered = GenerationRequest(
            "sponge", {"thickness": 0.2, "cell_size": 10.0}, 17
        )
        self.assertEqual(controller.state, "idle")
        self.assertIsNone(controller.body)
        self.assertEqual(request_signature(self.request), request_signature(reordered))
        source = (Path(__file__).parents[1] / "fusion" / "preview.py").read_text()
        self.assertNotIn("hash(", source)

    def test_preview_cap_is_generic_and_preserves_values(self):
        capped = preview_request(
            GenerationRequest("sponge", self.request.parameter_overrides, 41), 17
        )
        self.assertEqual(capped.resolution, 17)
        self.assertEqual(capped.parameter_overrides, self.request.parameter_overrides)

    def test_adaptive_preview_resolution_is_deterministic_and_bounded(self):
        candidates = (17, 21, 25)
        expected = ((17, 17), (25, 21), (41, 25))
        parameters = {"size": 45.0, "roughness": 0.62, "seed": 23}
        for requested, preview in expected:
            with self.subTest(requested=requested):
                source = GenerationRequest("rock", parameters, requested)
                first = preview_request(source, 17, candidates)
                repeated = preview_request(source, 17, candidates)
                self.assertEqual(first, repeated)
                self.assertEqual(first.resolution, preview)
                self.assertLessEqual(first.resolution, source.resolution)
                self.assertEqual(first.parameter_overrides, source.parameter_overrides)

    def test_invalid_adaptive_preview_candidates_are_rejected(self):
        source = GenerationRequest("rock", {"seed": 1}, 41)
        for candidates in ((21, 17), (17, 17), (17, 0), (17, 21.0)):
            with self.subTest(candidates=candidates):
                with self.assertRaises((TypeError, ValueError)):
                    preview_request(source, 17, candidates)

    def test_same_request_reuses_and_changed_request_replaces_preview(self):
        controller = PreviewController()
        generated = []
        bodies = []

        def generate(request):
            generated.append(request)
            return self.result

        def insert(result):
            body = FakeBody()
            bodies.append(body)
            return body

        first = controller.generate_preview(
            self.request, self.request, generate, insert
        )
        repeated = controller.generate_preview(
            self.request, self.request, generate, insert
        )
        self.assertTrue(first[2])
        self.assertFalse(repeated[2])
        self.assertEqual(len(generated), 1)
        controller.mark_dirty()
        self.assertEqual(controller.state, "stale")

        changed = GenerationRequest(
            "sponge", {"cell_size": 12.0, "thickness": 0.2}, 17
        )
        controller.generate_preview(changed, changed, generate, insert)
        self.assertEqual(bodies[0].delete_count, 1)
        self.assertEqual(len(generated), 2)
        self.assertTrue(controller.is_current_for(changed))

    def test_cleanup_is_idempotent_and_does_not_delete_unowned_body(self):
        controller = PreviewController()
        owned = FakeBody()
        unrelated = FakeBody("user body")
        controller.generate_preview(
            self.request, self.request, lambda request: self.result,
            lambda result: owned,
        )
        controller.cleanup()
        controller.cleanup()
        self.assertEqual(owned.delete_count, 1)
        self.assertEqual(unrelated.delete_count, 0)
        self.assertEqual(controller.state, "idle")

    def test_promotion_relinquishes_ownership(self):
        controller = PreviewController()
        body = FakeBody("NatureGenerator Preview — Sponge")
        controller.generate_preview(
            self.request, self.request, lambda request: self.result,
            lambda result: body,
        )
        result, promoted = controller.promote(
            self.request, "NatureGenerator Sponge"
        )
        self.assertEqual(controller.state, "finalized")
        controller.cleanup()
        self.assertIs(result, self.result)
        self.assertIs(promoted, body)
        self.assertEqual(body.name, "NatureGenerator Sponge")
        self.assertEqual(body.delete_count, 0)
        self.assertEqual(controller.state, "idle")

    def test_capped_preview_cannot_be_promoted_as_higher_resolution_final(self):
        controller = PreviewController()
        source = GenerationRequest(
            "sponge", self.request.parameter_overrides, 41
        )
        actual = preview_request(source, 17)
        body = FakeBody()
        controller.generate_preview(
            source, actual, lambda request: self.result, lambda result: body
        )
        self.assertTrue(controller.is_current_for(source))
        self.assertFalse(controller.can_promote(source))

    def test_failed_generation_is_recoverable(self):
        controller = PreviewController()
        with self.assertRaisesRegex(RuntimeError, "failed"):
            controller.generate_preview(
                self.request, self.request,
                lambda request: (_ for _ in ()).throw(RuntimeError("failed")),
                lambda result: FakeBody(),
            )
        self.assertEqual(controller.state, "failed")
        body = FakeBody()
        controller.generate_preview(
            self.request, self.request, lambda request: self.result,
            lambda result: body,
        )
        self.assertEqual(controller.state, "current")


if __name__ == "__main__":
    unittest.main()
