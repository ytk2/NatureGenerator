"""Focused tests for Classic Crystal geometry and Family integration."""

from dataclasses import FrozenInstanceError
import hashlib
import math
import unittest

from generators import GenerationRequest, GeneratorFactory
from generators.crystal_families import (
    CLASSIC_CRYSTAL_FAMILY,
    CrystalFamilyDefinition,
    CrystalFamilyRegistry,
)
from generators.generator import InvalidGeneratorParameters


CLASSIC_CRYSTAL_DIGEST = (
    "3f66098eaae05c74e20635c320c32b0c2b37a50febd0ef2dd6b8a273fb66f974"
)


def _generate(overrides=None, resolution=33, family_id="classic_crystal"):
    return GeneratorFactory.generate_request(GenerationRequest(
        "crystal", {} if overrides is None else overrides, resolution, family_id
    ))


class CrystalFamilyTests(unittest.TestCase):
    def test_classic_definition_and_registry_are_immutable(self):
        self.assertIsInstance(CLASSIC_CRYSTAL_FAMILY, CrystalFamilyDefinition)
        self.assertEqual(CLASSIC_CRYSTAL_FAMILY.family_id, "classic_crystal")
        self.assertEqual(CLASSIC_CRYSTAL_FAMILY.display_name, "Classic Crystal")
        self.assertIs(
            CrystalFamilyRegistry.get("classic_crystal"),
            CLASSIC_CRYSTAL_FAMILY,
        )
        self.assertEqual(
            CrystalFamilyRegistry.list_all(), (CLASSIC_CRYSTAL_FAMILY,)
        )
        with self.assertRaises(TypeError):
            CLASSIC_CRYSTAL_FAMILY.parameter_values["seed"] = 14
        with self.assertRaises(FrozenInstanceError):
            CLASSIC_CRYSTAL_FAMILY.display_name = "Changed"
        with self.assertRaises(KeyError):
            CrystalFamilyRegistry.get("missing_crystal")

    def test_classic_family_contains_all_visual_parameters(self):
        self.assertEqual(
            tuple(CLASSIC_CRYSTAL_FAMILY.parameter_values),
            (
                "length", "width", "facet_count", "taper", "irregularity",
                "seed", "resolution",
            ),
        )


class ClassicCrystalGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = _generate()

    def test_digest_is_stable_and_legacy_request_is_identical(self):
        digest = hashlib.sha256(repr((
            self.result.mesh.vertices, self.result.mesh.faces
        )).encode("ascii")).hexdigest()
        self.assertEqual(digest, CLASSIC_CRYSTAL_DIGEST)
        legacy = _generate(family_id="")
        self.assertEqual(legacy.mesh, self.result.mesh)

    def test_mesh_is_finite_closed_manifold_and_single_component(self):
        statistics = self.result.statistics
        self.assertTrue(statistics.is_watertight)
        self.assertTrue(statistics.is_manifold)
        self.assertEqual(statistics.connected_component_count, 1)
        self.assertEqual(statistics.boundary_edge_count, 0)
        self.assertEqual(statistics.nonmanifold_edge_count, 0)
        self.assertEqual(statistics.nonmanifold_vertex_count, 0)
        self.assertEqual(statistics.degenerate_face_count, 0)
        self.assertEqual(statistics.inconsistent_winding_edge_count, 0)
        self.assertTrue(all(
            math.isfinite(value)
            for vertex in self.result.mesh.vertices for value in vertex
        ))

    def test_shape_is_an_elongated_faceted_prism_with_termination(self):
        minimum, maximum = self.result.statistics.bounds
        width = max(
            maximum[0] - minimum[0],
            maximum[1] - minimum[1],
        )
        height = maximum[2] - minimum[2]
        self.assertGreater(height / width, 2.5)
        top_vertices = [
            vertex for vertex in self.result.mesh.vertices
            if abs(vertex[2] - maximum[2]) < 1e-9
        ]
        bottom_vertices = [
            vertex for vertex in self.result.mesh.vertices
            if abs(vertex[2] - minimum[2]) < 1e-9
        ]
        self.assertEqual(len(top_vertices), 1)
        self.assertEqual(
            len(bottom_vertices),
            CLASSIC_CRYSTAL_FAMILY.parameter_values["facet_count"] + 1,
        )

    def test_seed_and_each_shape_parameter_have_deterministic_effects(self):
        repeated = _generate()
        self.assertEqual(repeated.mesh, self.result.mesh)
        for overrides in (
            {"seed": 14},
            {"length": 120.0},
            {"width": 40.0},
            {"facet_count": 8},
            {"taper": 0.45},
            {"irregularity": 0.40},
        ):
            self.assertNotEqual(_generate(overrides).mesh, self.result.mesh)

    def test_resolution_changes_axial_detail_without_changing_major_shape(self):
        preview = _generate(resolution=25)
        self.assertNotEqual(len(preview.mesh.vertices), len(self.result.mesh.vertices))
        for axis in range(3):
            preview_span = (
                preview.statistics.bounds[1][axis]
                - preview.statistics.bounds[0][axis]
            )
            final_span = (
                self.result.statistics.bounds[1][axis]
                - self.result.statistics.bounds[0][axis]
            )
            self.assertAlmostEqual(preview_span / final_span, 1.0, delta=0.03)

    def test_generated_asset_defaults_and_identity(self):
        asset = self.result.asset
        self.assertIs(asset.mesh, self.result.mesh)
        self.assertEqual(asset.metadata.family_id, "classic_crystal")
        self.assertEqual(asset.material.material_id, "natural_crystal")
        self.assertEqual(asset.material.base_color, (0.68, 0.82, 0.88, 1.0))
        self.assertEqual(asset.material.metallic, 0.0)
        self.assertEqual(asset.material.roughness, 0.28)
        self.assertEqual(asset.mapping.mode.value, "object_space")
        self.assertEqual(asset.textures.resources, ())

    def test_invalid_parameters_and_family_fail_clearly(self):
        for overrides in (
            {"length": 20.0},
            {"width": 5.0},
            {"facet_count": 4},
            {"facet_count": 6.5},
            {"taper": 0.8},
            {"irregularity": -0.1},
            {"seed": 1.5},
            {"unknown": 1},
        ):
            with self.assertRaises(InvalidGeneratorParameters):
                _generate(overrides)
        with self.assertRaises(InvalidGeneratorParameters):
            _generate(resolution=17)
        with self.assertRaises(ValueError):
            _generate(resolution=45)
        with self.assertRaisesRegex(
            InvalidGeneratorParameters, "unknown crystal family"
        ):
            _generate(family_id="missing_crystal")

    def test_supported_parameter_extremes_remain_closed_solids(self):
        cases = (
            {
                "length": 180.0, "width": 12.0, "facet_count": 5,
                "taper": 0.15, "irregularity": 0.50, "seed": 2147483647,
            },
            {
                "length": 40.0, "width": 70.0, "facet_count": 10,
                "taper": 0.50, "irregularity": 0.0, "seed": 0,
            },
        )
        for parameters in cases:
            result = _generate(parameters, resolution=21)
            self.assertTrue(result.statistics.is_watertight)
            self.assertTrue(result.statistics.is_manifold)
            self.assertEqual(result.statistics.connected_component_count, 1)
            self.assertEqual(result.statistics.degenerate_face_count, 0)


if __name__ == "__main__":
    unittest.main()
