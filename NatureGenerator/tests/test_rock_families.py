"""Tests for internal Rock families built only from pipeline parameters."""

from collections import Counter
from dataclasses import FrozenInstanceError
import hashlib
import math
import unittest

from generators import GenerationRequest, GeneratorFactory
from generators.rock_families import (
    DEFAULT_ROCK_FAMILY,
    RIVER_STONE_FAMILY,
    RockFamilyRegistry,
)
from generators.rock_generator import RockGenerator, _RockField
from generators.rock_pipeline import RockGenerationContext, build_surface_detail


def _digest(mesh):
    return hashlib.sha256(
        repr((mesh.vertices, mesh.faces)).encode("ascii")
    ).hexdigest()


class RockFamilyDefinitionTests(unittest.TestCase):
    def test_registry_exposes_immutable_parameter_only_families(self):
        self.assertIs(RockFamilyRegistry.get("default"), DEFAULT_ROCK_FAMILY)
        self.assertIs(
            RockFamilyRegistry.get("river_stone"), RIVER_STONE_FAMILY
        )
        self.assertEqual(
            tuple(item.family_id for item in RockFamilyRegistry.list_all()),
            (
                "smooth", "weathered", "rugged", "river_stone",
                "granite", "basalt", "broken_rock",
            ),
        )
        self.assertEqual(
            tuple(item.display_name for item in RockFamilyRegistry.list_all()),
            (
                "Smooth", "Weathered", "Rugged", "River Stone",
                "Granite", "Basalt", "Broken Rock",
            ),
        )
        with self.assertRaises(TypeError):
            RIVER_STONE_FAMILY.parameter_values["seed"] = 2
        with self.assertRaises(FrozenInstanceError):
            RIVER_STONE_FAMILY.display_name = "Changed"
        with self.assertRaises(TypeError):
            RockFamilyRegistry._definitions["changed"] = RIVER_STONE_FAMILY
        with self.assertRaises(KeyError):
            RockFamilyRegistry.get("limestone")

    def test_river_stone_uses_all_three_existing_pipeline_stages(self):
        field = _RockField(40.0, 0.35, 1, RIVER_STONE_FAMILY)
        self.assertEqual(field.context.seed, 1)
        self.assertEqual(len(field.facet_layout.planes), 2)
        self.assertEqual(
            field.surface_detail,
            build_surface_detail(field.context, RIVER_STONE_FAMILY.surface),
        )
        self.assertLess(
            field.surface_detail.fbm_amplitude,
            _RockField(40.0, 0.35, 1).surface_detail.fbm_amplitude,
        )
        self.assertLess(field.macro_shape.radii[2], field.macro_shape.radii[1])

    def test_river_stone_preserves_roughness_scaling(self):
        low = build_surface_detail(
            RockGenerationContext.create(40.0, 0.10, 1),
            RIVER_STONE_FAMILY.surface,
        )
        high = build_surface_detail(
            RockGenerationContext.create(40.0, 0.70, 1),
            RIVER_STONE_FAMILY.surface,
        )
        self.assertGreater(high.fbm_amplitude, low.fbm_amplitude)
        self.assertGreater(high.ridge_amplitude, low.ridge_amplitude)


class RiverStoneGenerationTests(unittest.TestCase):
    _PARAMETERS = {"size": 40.0, "roughness": 0.35, "seed": 1}

    def _generate(self, parameters=None, resolution=25):
        return RockGenerator().generate_family(
            GenerationRequest(
                "rock",
                self._PARAMETERS if parameters is None else parameters,
                resolution,
            ),
            "river_stone",
        )

    def test_output_is_deterministic_and_seed_sensitive(self):
        first = self._generate(resolution=17)
        repeated = self._generate(resolution=17)
        changed = self._generate(
            {"size": 40.0, "roughness": 0.35, "seed": 2}, 17
        )
        self.assertEqual(first, repeated)
        self.assertNotEqual(first.vertices, changed.vertices)

    def test_final_digest_is_stable(self):
        self.assertEqual(
            _digest(self._generate()),
            "61264e6e929229247ac7b4d89f2916f5c5cb875dc985c5c258fa79334c18abd4",
        )

    def test_factory_request_selects_existing_river_family(self):
        request = GenerationRequest(
            "rock", self._PARAMETERS, 25, "river_stone"
        )
        first = GeneratorFactory.generate_request(request)
        repeated = GeneratorFactory.generate_request(request)
        self.assertEqual(_digest(first.mesh), _digest(repeated.mesh))
        self.assertEqual(
            _digest(first.mesh),
            "61264e6e929229247ac7b4d89f2916f5c5cb875dc985c5c258fa79334c18abd4",
        )

    def test_mesh_is_finite_closed_manifold_and_single_component(self):
        mesh = self._generate()
        statistics = mesh.statistics()
        self.assertTrue(statistics.is_watertight)
        self.assertTrue(statistics.is_manifold)
        self.assertEqual(statistics.connected_component_count, 1)
        self.assertEqual(statistics.degenerate_face_count, 0)
        self.assertTrue(all(
            math.isfinite(value)
            for vertex in mesh.vertices
            for value in vertex
        ))

    def test_shape_is_flatter_and_has_no_large_non_ground_planar_region(self):
        river = self._generate()
        smooth = GeneratorFactory.generate_request(GenerationRequest(
            "rock",
            {"size": 40.0, "roughness": 0.10, "seed": 1},
            25,
        ))
        river_stats = river.statistics()
        smooth_stats = smooth.statistics
        river_spans = tuple(
            river_stats.bounds[1][axis] - river_stats.bounds[0][axis]
            for axis in range(3)
        )
        smooth_spans = tuple(
            smooth_stats.bounds[1][axis] - smooth_stats.bounds[0][axis]
            for axis in range(3)
        )
        self.assertLess(
            river_spans[2] / max(river_spans[:2]),
            smooth_spans[2] / max(smooth_spans[:2]),
        )

        normal_counts = Counter(
            tuple(round(value, 5) for value in river.face_normal(index))
            for index in range(len(river.faces))
        )
        ground_faces = normal_counts.pop((0.0, -0.0, -1.0))
        self.assertGreater(ground_faces, 0)
        self.assertLessEqual(max(normal_counts.values()), 4)

    def test_existing_variant_digests_remain_unchanged(self):
        cases = (
            (
                "smooth",
                {"size": 40.0, "roughness": 0.10, "seed": 1},
                17,
                "29d6402a0148637fd00cbc1274d8f6be6c9f8901b2b856e2de75dc43f91bdc3e",
            ),
            (
                "weathered",
                {"size": 40.0, "roughness": 0.35, "seed": 1},
                17,
                "30a709c32fb7dd16b87f0388f21c6e24e12b6ad990b2872dd31f9549956e7c1d",
            ),
            (
                "rugged",
                {"size": 45.0, "roughness": 0.62, "seed": 23},
                25,
                "040bd703ef44549b418fdb5fd6804b9e36ce93e372cbbea00e5e63a8b8ffadde",
            ),
        )
        for family_id, parameters, resolution, expected in cases:
            result = GeneratorFactory.generate_request(GenerationRequest(
                "rock", parameters, resolution, family_id
            ))
            self.assertEqual(_digest(result.mesh), expected)


class DiverseRockFamilyTests(unittest.TestCase):
    _EXPECTED = {
        "granite": "492f9ca68798ff6a7913193677289a6f4a1c525a37cd06eefba1c28c81aea228",
        "basalt": "fb73c7efee28f34fe3f266a9ec68afd266b49b73cab0798d6e854c50b21b84fa",
        "broken_rock": "5a260c62a457b9b0b9782d223f9c9bf6ed9c512490c7c70091443bd5c2623d96",
    }

    @classmethod
    def setUpClass(cls):
        cls.results = {}
        for family_id in cls._EXPECTED:
            family = RockFamilyRegistry.get(family_id)
            parameters = dict(family.parameter_values)
            resolution = parameters.pop("resolution")
            cls.results[family_id] = GeneratorFactory.generate_request(
                GenerationRequest(
                    "rock", parameters, resolution, family_id
                )
            )

    def test_defaults_use_existing_public_parameters(self):
        expected = {
            "granite": (50.0, 0.45, 37, 25),
            "basalt": (50.0, 0.25, 61, 25),
            "broken_rock": (50.0, 0.55, 97, 25),
        }
        for family_id, values in expected.items():
            family = RockFamilyRegistry.get(family_id)
            self.assertEqual(
                tuple(family.parameter_values[key] for key in (
                    "size", "roughness", "seed", "resolution"
                )),
                values,
            )
            self.assertEqual(
                set(family.parameter_values),
                {"size", "roughness", "seed", "resolution"},
            )

    def test_default_meshes_have_stable_digests_and_manufacturable_topology(self):
        for family_id, expected_digest in self._EXPECTED.items():
            result = self.results[family_id]
            statistics = result.statistics
            self.assertEqual(_digest(result.mesh), expected_digest)
            self.assertTrue(statistics.is_watertight)
            self.assertTrue(statistics.is_manifold)
            self.assertEqual(statistics.connected_component_count, 1)
            self.assertEqual(statistics.boundary_edge_count, 0)
            self.assertEqual(statistics.nonmanifold_edge_count, 0)
            self.assertEqual(statistics.nonmanifold_vertex_count, 0)
            self.assertEqual(statistics.inconsistent_winding_edge_count, 0)
            self.assertEqual(statistics.degenerate_face_count, 0)
            self.assertTrue(all(
                math.isfinite(value)
                for vertex in result.mesh.vertices
                for value in vertex
            ))

    def test_seed_and_roughness_change_each_family_deterministically(self):
        for family_id in self._EXPECTED:
            family = RockFamilyRegistry.get(family_id)
            base = dict(family.parameter_values)
            base.pop("resolution")
            first = GeneratorFactory.generate_request(GenerationRequest(
                "rock", base, 17, family_id
            ))
            repeated = GeneratorFactory.generate_request(GenerationRequest(
                "rock", base, 17, family_id
            ))
            changed_seed = dict(base)
            changed_seed["seed"] += 1
            seeded = GeneratorFactory.generate_request(GenerationRequest(
                "rock", changed_seed, 17, family_id
            ))
            changed_roughness = dict(base)
            changed_roughness["roughness"] = max(
                0.0, min(0.7, base["roughness"] - 0.15)
            )
            rough = GeneratorFactory.generate_request(GenerationRequest(
                "rock", changed_roughness, 17, family_id
            ))
            self.assertEqual(first.mesh, repeated.mesh)
            self.assertNotEqual(first.mesh.vertices, seeded.mesh.vertices)
            self.assertNotEqual(first.mesh.vertices, rough.mesh.vertices)

    def test_silhouette_and_planar_metrics_distinguish_new_families(self):
        metrics = {}
        for family_id, result in self.results.items():
            statistics = result.statistics
            spans = tuple(
                statistics.bounds[1][axis] - statistics.bounds[0][axis]
                for axis in range(3)
            )
            normal_counts = Counter(
                tuple(round(value, 5) for value in result.mesh.face_normal(index))
                for index in range(len(result.mesh.faces))
            )
            ground = normal_counts.pop((0.0, -0.0, -1.0), 0)
            metrics[family_id] = {
                "spans": spans,
                "largest_plane": max(normal_counts.values()),
                "planar_faces": sum(
                    count for count in normal_counts.values() if count >= 10
                ),
                "planar_regions": sum(
                    1 for count in normal_counts.values() if count >= 10
                ),
                "ground": ground,
            }

        granite = metrics["granite"]
        basalt = metrics["basalt"]
        broken = metrics["broken_rock"]
        self.assertGreater(granite["spans"][0] / 50.0, 1.10)
        self.assertLess(granite["spans"][2] / granite["spans"][0], 0.70)
        self.assertGreater(basalt["spans"][2] / basalt["spans"][0], 1.20)
        self.assertGreater(basalt["planar_regions"], 4)
        self.assertGreater(broken["planar_regions"], granite["planar_regions"])
        self.assertGreater(broken["planar_faces"], granite["planar_faces"] * 2)
        self.assertGreater(broken["largest_plane"], basalt["largest_plane"] * 2)
        self.assertTrue(all(metrics[key]["ground"] > 0 for key in metrics))


if __name__ == "__main__":
    unittest.main()
