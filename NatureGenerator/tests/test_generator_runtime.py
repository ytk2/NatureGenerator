"""End-to-end tests for the preset-to-mesh generator runtime."""

from dataclasses import FrozenInstanceError
from collections import Counter
from pathlib import Path
import hashlib
import math
import unittest
from unittest.mock import patch

from core.mesh import TriangleMesh
from generators.coral_generator import _CoralField
from generators.sponge_generator import _SpongeField
from generators import (
    DEFAULT_RESOLUTION,
    MAX_RESOLUTION,
    MIN_RESOLUTION,
    Generator,
    GeneratorFactory,
    GeneratorResult,
    GenerationRequest,
    CoralGenerator,
    BarkGenerator,
    RockGenerator,
    RootGenerator,
    build_root_skeleton,
    SpongeGenerator,
    GyroidGenerator,
    InvalidGeneratorParameters,
    MeshExtractionError,
    UnavailablePresetError,
    UnknownGeneratorError,
    UnknownPresetError,
)
from presets import NaturePreset, PresetFactory


class GeneratorFactoryTests(unittest.TestCase):
    def test_resolves_gyroid_by_stable_id(self):
        generator = GeneratorFactory.create("gyroid")
        self.assertIsInstance(generator, GyroidGenerator)
        self.assertEqual(generator.generator_id, "gyroid")

    def test_unknown_generator_has_meaningful_error(self):
        with self.assertRaisesRegex(UnknownGeneratorError, "unknown generator_id"):
            GeneratorFactory.create("missing")

    def test_resolves_coral_by_preset_id(self):
        generator = GeneratorFactory.create_for_preset("coral")
        self.assertIsInstance(generator, CoralGenerator)
        self.assertEqual(generator.generator_id, "coral")

    def test_request_generators_return_triangle_mesh(self):
        for preset_id, expected_type in (
            ("sponge", SpongeGenerator),
            ("coral", CoralGenerator),
            ("rock", RockGenerator),
            ("bark", BarkGenerator),
            ("root", RootGenerator),
        ):
            generator = GeneratorFactory.create_for_preset(preset_id)
            self.assertIsInstance(generator, expected_type)
            mesh = generator.generate(
                GenerationRequest(
                    preset_id, {},
                    PresetFactory.get(preset_id).default_parameters.get(
                        "resolution", DEFAULT_RESOLUTION
                    ),
                )
            )
            self.assertIsInstance(mesh, TriangleMesh)
            self.assertGreater(len(mesh.faces), 0)

    def test_preset_registration_rejects_duplicates(self):
        GeneratorFactory.create_for_preset("sponge")
        with self.assertRaisesRegex(ValueError, "duplicate preset id"):
            GeneratorFactory.register_preset("sponge", SpongeGenerator)

    def test_request_rejects_unavailable_preset(self):
        request = GenerationRequest("bone", {}, DEFAULT_RESOLUTION)
        with self.assertRaisesRegex(UnavailablePresetError, "not implemented"):
            GeneratorFactory.generate_request(request)

    def test_request_rejects_unknown_preset(self):
        request = GenerationRequest("missing", {}, DEFAULT_RESOLUTION)
        with self.assertRaisesRegex(UnknownPresetError, "unknown preset_id"):
            GeneratorFactory.generate_request(request)


class GenerationRequestTests(unittest.TestCase):
    def test_request_is_immutable_and_defensively_copies_overrides(self):
        overrides = {"cell_size": 12.0, "thickness": 0.25}
        request = GenerationRequest("sponge", overrides, 19)
        overrides["cell_size"] = 99.0

        self.assertEqual(request.parameter_overrides["cell_size"], 12.0)
        with self.assertRaises(TypeError):
            request.parameter_overrides["cell_size"] = 20.0
        with self.assertRaises(FrozenInstanceError):
            request.resolution = 21

    def test_optional_family_id_is_immutable_and_validated(self):
        request = GenerationRequest("rock", {}, 17, "river_stone")
        self.assertEqual(request.family_id, "river_stone")
        with self.assertRaises(FrozenInstanceError):
            request.family_id = "smooth"
        for value in (None, 1, "River Stone", "river-stone"):
            with self.subTest(value=value):
                with self.assertRaises((TypeError, ValueError)):
                    GenerationRequest("rock", {}, 17, value)

    def test_resolution_validation(self):
        for value in (MIN_RESOLUTION, DEFAULT_RESOLUTION, MAX_RESOLUTION):
            self.assertEqual(GenerationRequest("sponge", {}, value).resolution, value)
        for value in (MIN_RESOLUTION - 1, MAX_RESOLUTION + 1):
            with self.assertRaisesRegex(ValueError, "between"):
                GenerationRequest("sponge", {}, value)
        for value in (True, 17.0, "17"):
            with self.assertRaisesRegex(TypeError, "integer"):
                GenerationRequest("sponge", {}, value)

    def test_non_finite_parameter_overrides_are_rejected(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaisesRegex(TypeError, "finite"):
                GenerationRequest("sponge", {"cell_size": value}, 17)


class GyroidGeneratorTests(unittest.TestCase):
    def test_sponge_field_contains_rounded_exterior_connected_pores(self):
        field = _SpongeField(10.0, 0.2, 0)
        self.assertEqual(len(field._pores), 12)
        self.assertLess(field.sample(0.0, 0.0, 0.0), 0.0)
        for center, radius in field._pores:
            self.assertGreater(field.sample(*center), 0.0)
            face_axis = max(range(3), key=lambda axis: abs(center[axis]))
            self.assertGreater(
                abs(center[face_axis]) + radius,
                field._half_extent,
            )

    def test_sponge_runs_end_to_end(self):
        preset = PresetFactory.get("sponge")
        result = GeneratorFactory.generate(preset)

        self.assertIsInstance(result, GeneratorResult)
        self.assertIsInstance(result.mesh, TriangleMesh)
        self.assertGreater(len(result.mesh.vertices), 0)
        self.assertGreater(len(result.mesh.faces), 0)
        self.assertEqual(result.statistics, result.mesh.statistics())
        self.assertGreater(result.statistics.vertex_count, 0)
        self.assertGreater(result.statistics.face_count, 0)
        self.assertTrue(result.statistics.is_manifold)
        self.assertTrue(result.statistics.is_watertight)
        self.assertEqual(result.statistics.boundary_edge_count, 0)
        self.assertEqual(result.statistics.connected_component_count, 1)
        self.assertEqual(result.statistics.degenerate_face_count, 0)
        self.assertEqual(result.warnings, ())
        self.assertEqual(result.generator_id, "gyroid")
        self.assertEqual(result.preset_id, "sponge")
        self.assertGreater(result.elapsed_time, 0.0)

    def test_parameter_overrides_are_validated(self):
        with self.assertRaisesRegex(InvalidGeneratorParameters, "cell_size"):
            GeneratorFactory.generate(
                PresetFactory.get("sponge"), {"cell_size": 0.0}
            )
        with self.assertRaisesRegex(InvalidGeneratorParameters, "unknown"):
            GeneratorFactory.generate(
                PresetFactory.get("sponge"), {"unknown": 1.0}
            )
        with self.assertRaisesRegex(InvalidGeneratorParameters, "at most"):
            GeneratorFactory.generate(
                PresetFactory.get("sponge"), {"thickness": 1.5}
            )

    def test_request_applies_valid_parameter_overrides(self):
        thin = GeneratorFactory.generate_request(
            GenerationRequest(
                "sponge", {"cell_size": 12.0, "thickness": 0.1}, 17
            )
        )
        thick = GeneratorFactory.generate_request(
            GenerationRequest(
                "sponge", {"cell_size": 12.0, "thickness": 0.4}, 17
            )
        )
        self.assertGreater(thin.statistics.face_count, 0)
        self.assertGreater(thick.statistics.face_count, 0)
        self.assertNotEqual(thin.statistics.face_count, thick.statistics.face_count)

    def test_classic_family_matches_default_and_has_stable_digest(self):
        default = GeneratorFactory.generate_request(
            GenerationRequest("sponge", {}, DEFAULT_RESOLUTION)
        )
        family = GeneratorFactory.generate_request(
            GenerationRequest("sponge", {}, DEFAULT_RESOLUTION, "classic_sponge")
        )
        self.assertEqual(default.mesh.vertices, family.mesh.vertices)
        self.assertEqual(default.mesh.faces, family.mesh.faces)
        digest = hashlib.sha256(
            repr((family.mesh.vertices, family.mesh.faces)).encode("ascii")
        ).hexdigest()
        self.assertEqual(
            digest,
            "92fbd5d78f6797049fbafada00819d4cafa247e106be159a90d890cd6b502786",
        )
        self.assertEqual(family.statistics.vertex_count, 2984)
        self.assertEqual(family.statistics.face_count, 5964)

    def test_seed_is_deterministic_and_changes_pore_layout(self):
        first = GeneratorFactory.generate_request(
            GenerationRequest("sponge", {"seed": 42}, DEFAULT_RESOLUTION)
        )
        repeated = GeneratorFactory.generate_request(
            GenerationRequest("sponge", {"seed": 42}, DEFAULT_RESOLUTION)
        )
        changed = GeneratorFactory.generate_request(
            GenerationRequest("sponge", {"seed": 43}, DEFAULT_RESOLUTION)
        )
        self.assertEqual(first.mesh.vertices, repeated.mesh.vertices)
        self.assertEqual(first.mesh.faces, repeated.mesh.faces)
        self.assertNotEqual(first.mesh.vertices, changed.mesh.vertices)
        for result in (first, changed):
            self.assertTrue(result.statistics.is_watertight)
            self.assertTrue(result.statistics.is_manifold)
            self.assertEqual(result.statistics.connected_component_count, 1)
            self.assertEqual(result.statistics.degenerate_face_count, 0)
            self.assertTrue(all(
                math.isfinite(value)
                for vertex in result.mesh.vertices for value in vertex
            ))

    def test_unknown_sponge_family_and_invalid_seed_are_rejected(self):
        with self.assertRaises(InvalidGeneratorParameters):
            GeneratorFactory.generate_request(
                GenerationRequest("sponge", {}, DEFAULT_RESOLUTION, "missing")
            )
        with self.assertRaises(InvalidGeneratorParameters):
            GeneratorFactory.generate_request(
                GenerationRequest("sponge", {"seed": 1.5}, DEFAULT_RESOLUTION)
            )

    def test_legacy_factory_api_keeps_default_resolution(self):
        legacy = GeneratorFactory.generate(PresetFactory.get("sponge"))
        requested = GeneratorFactory.generate_request(
            GenerationRequest("sponge", {}, DEFAULT_RESOLUTION)
        )
        self.assertEqual(
            legacy.statistics.vertex_count, requested.statistics.vertex_count
        )
        self.assertEqual(legacy.statistics.face_count, requested.statistics.face_count)

    def test_request_rejects_invalid_cell_size_and_thickness(self):
        for cell_size in (0.0, -1.0, 0.5, 101.0):
            request = GenerationRequest(
                "sponge", {"cell_size": cell_size, "thickness": 0.2}, 17
            )
            with self.assertRaisesRegex(InvalidGeneratorParameters, "cell_size"):
                GeneratorFactory.generate_request(request)
        for thickness in (-0.1, 1.1):
            request = GenerationRequest(
                "sponge", {"cell_size": 10.0, "thickness": thickness}, 17
            )
            with self.assertRaisesRegex(InvalidGeneratorParameters, "thickness"):
                GeneratorFactory.generate_request(request)

    def test_resolution_changes_mesh_density(self):
        low = GeneratorFactory.generate_request(
            GenerationRequest("sponge", {}, MIN_RESOLUTION)
        )
        high = GeneratorFactory.generate_request(
            GenerationRequest("sponge", {}, 25)
        )
        self.assertGreater(high.statistics.vertex_count, low.statistics.vertex_count)
        self.assertGreater(high.statistics.face_count, low.statistics.face_count)

    def test_empty_extraction_has_meaningful_error(self):
        preset = NaturePreset(
            preset_id="empty_gyroid",
            display_name="Empty Gyroid",
            category="test",
            description="Gyroid configured outside its value range.",
            generator_id="gyroid",
            default_parameters={"cell_size": 10.0, "thickness": 2.0},
            available=True,
        )
        with self.assertRaisesRegex(MeshExtractionError, "no triangles"):
            GeneratorFactory.generate(preset)

    def test_result_is_immutable(self):
        result = GeneratorFactory.generate(PresetFactory.get("sponge"))
        with self.assertRaises(FrozenInstanceError):
            result.elapsed_time = 0.0


class CoralGeneratorTests(unittest.TestCase):
    def test_branch_graph_has_multiple_upward_connected_segments(self):
        for seed in (0, 42):
            field = _CoralField(14.0, 0.35, seed)
            self.assertGreaterEqual(len(field._segments), 6)
            self.assertTrue(all(
                end[2] > start[2] for start, end in field._segments
            ))
            endpoints = [
                endpoint for segment in field._segments for endpoint in segment
            ]
            self.assertLess(len(set(endpoints)), len(endpoints))

    def test_coral_runs_end_to_end_as_a_watertight_mesh(self):
        result = GeneratorFactory.generate_request(
            GenerationRequest("coral", {}, DEFAULT_RESOLUTION)
        )

        self.assertIsInstance(result, GeneratorResult)
        self.assertIsInstance(result.mesh, TriangleMesh)
        self.assertEqual(result.generator_id, "coral")
        self.assertEqual(result.preset_id, "coral")
        self.assertGreater(result.statistics.vertex_count, 0)
        self.assertGreater(result.statistics.face_count, 0)
        self.assertTrue(result.statistics.is_manifold)
        self.assertTrue(result.statistics.is_watertight)
        self.assertEqual(result.statistics.boundary_edge_count, 0)
        self.assertEqual(result.statistics.connected_component_count, 1)
        self.assertGreater(result.elapsed_time, 0.0)

    def test_classic_family_matches_backward_compatible_default(self):
        default = GeneratorFactory.generate_request(
            GenerationRequest("coral", {}, DEFAULT_RESOLUTION)
        )
        family = GeneratorFactory.generate_request(
            GenerationRequest("coral", {}, DEFAULT_RESOLUTION, "classic_coral")
        )
        self.assertEqual(default.mesh.vertices, family.mesh.vertices)
        self.assertEqual(default.mesh.faces, family.mesh.faces)

    def test_classic_coral_digest_is_stable(self):
        result = GeneratorFactory.generate_request(
            GenerationRequest("coral", {}, DEFAULT_RESOLUTION, "classic_coral")
        )
        digest = hashlib.sha256(
            repr((result.mesh.vertices, result.mesh.faces)).encode("ascii")
        ).hexdigest()
        self.assertEqual(
            digest,
            "f4c780ffb295c44a96d13311baae4c6987319c67f2dda515451c8ae0845834e4",
        )

    def test_seed_is_deterministic_and_changes_branch_geometry(self):
        first = GeneratorFactory.generate_request(
            GenerationRequest("coral", {"seed": 42}, DEFAULT_RESOLUTION)
        )
        repeated = GeneratorFactory.generate_request(
            GenerationRequest("coral", {"seed": 42}, DEFAULT_RESOLUTION)
        )
        changed = GeneratorFactory.generate_request(
            GenerationRequest("coral", {"seed": 43}, DEFAULT_RESOLUTION)
        )
        self.assertEqual(first.mesh.vertices, repeated.mesh.vertices)
        self.assertEqual(first.mesh.faces, repeated.mesh.faces)
        self.assertNotEqual(first.mesh.vertices, changed.mesh.vertices)
        for result in (first, changed):
            self.assertTrue(result.statistics.is_watertight)
            self.assertTrue(result.statistics.is_manifold)
            self.assertEqual(result.statistics.connected_component_count, 1)

    def test_unknown_coral_family_is_rejected(self):
        with self.assertRaises(InvalidGeneratorParameters):
            GeneratorFactory.generate_request(
                GenerationRequest("coral", {}, DEFAULT_RESOLUTION, "missing")
            )

    def test_legacy_factory_entry_point_supports_coral(self):
        result = GeneratorFactory.generate(PresetFactory.get("coral"))
        self.assertEqual(result.generator_id, "coral")
        self.assertTrue(result.statistics.is_watertight)

    def test_coral_is_visually_distinct_from_sponge_topology(self):
        coral = GeneratorFactory.generate_request(
            GenerationRequest("coral", {}, DEFAULT_RESOLUTION)
        )
        sponge = GeneratorFactory.generate_request(
            GenerationRequest("sponge", {}, DEFAULT_RESOLUTION)
        )

        self.assertTrue(coral.statistics.is_watertight)
        self.assertTrue(sponge.statistics.is_watertight)
        self.assertNotEqual(coral.statistics.face_count, sponge.statistics.face_count)

    def test_coral_is_quantitatively_distinct_from_rock_and_bark(self):
        coral = GeneratorFactory.generate_request(
            GenerationRequest("coral", {}, DEFAULT_RESOLUTION, "classic_coral")
        )
        rock = GeneratorFactory.generate_request(
            GenerationRequest("rock", {}, DEFAULT_RESOLUTION)
        )
        bark = GeneratorFactory.generate_request(
            GenerationRequest("bark", {}, 33)
        )

        def aspect(result):
            bounds = result.statistics.bounds
            spans = tuple(
                bounds[1][axis] - bounds[0][axis] for axis in range(3)
            )
            return spans[2] / max(spans[0], spans[1])

        self.assertGreater(aspect(coral), aspect(rock))
        self.assertLess(aspect(coral), aspect(bark))
        self.assertNotEqual(
            coral.statistics.face_count, rock.statistics.face_count
        )
        self.assertNotEqual(
            coral.statistics.face_count, bark.statistics.face_count
        )

    def test_coral_shared_parameters_affect_scale_and_mesh(self):
        small = GeneratorFactory.generate_request(
            GenerationRequest("coral", {"cell_size": 8.0, "thickness": 0.2}, 17)
        )
        large = GeneratorFactory.generate_request(
            GenerationRequest("coral", {"cell_size": 16.0, "thickness": 0.2}, 17)
        )
        thick = GeneratorFactory.generate_request(
            GenerationRequest("coral", {"cell_size": 8.0, "thickness": 0.8}, 17)
        )

        self.assertLess(small.statistics.bounds[1][0], large.statistics.bounds[1][0])
        self.assertNotEqual(small.statistics.face_count, thick.statistics.face_count)
        self.assertTrue(thick.statistics.is_watertight)

    def test_coral_rejects_invalid_parameters(self):
        for overrides in (
            {"cell_size": 0.0},
            {"thickness": -0.1},
            {"thickness": 1.1},
            {"seed": 1.5},
            {"unknown": 1.0},
        ):
            with self.assertRaises(InvalidGeneratorParameters):
                GeneratorFactory.generate_request(
                    GenerationRequest("coral", overrides, DEFAULT_RESOLUTION)
                )


class RockGeneratorTests(unittest.TestCase):
    def _generate(self, overrides=None, resolution=17):
        return GeneratorFactory.generate_request(
            GenerationRequest("rock", {} if overrides is None else overrides, resolution)
        )

    def test_deterministic_and_seed_changes_geometry(self):
        first = self._generate({"seed": 123})
        repeated = self._generate({"seed": 123})
        different = self._generate({"seed": 124})
        self.assertEqual(first.mesh.vertices, repeated.mesh.vertices)
        self.assertEqual(first.mesh.faces, repeated.mesh.faces)
        self.assertNotEqual(first.mesh.vertices, different.mesh.vertices)

    def test_parameters_change_shape_scale_and_density(self):
        smooth = self._generate({"roughness": 0.0})
        rough = self._generate({"roughness": 0.7})
        small = self._generate({"size": 20.0})
        large = self._generate({"size": 80.0})
        dense = self._generate(resolution=25)
        self.assertNotEqual(smooth.mesh.vertices, rough.mesh.vertices)
        self.assertLess(small.statistics.bounds[1][0], large.statistics.bounds[1][0])
        self.assertGreater(dense.statistics.face_count, smooth.statistics.face_count)

    def test_output_is_single_watertight_finite_non_degenerate_component(self):
        result = self._generate({"seed": 987, "roughness": 0.7}, 21)
        stats = result.statistics
        self.assertTrue(stats.is_manifold)
        self.assertTrue(stats.is_watertight)
        self.assertEqual(stats.connected_component_count, 1)
        self.assertEqual(stats.degenerate_face_count, 0)
        self.assertTrue(all(math.isfinite(value) for vertex in result.mesh.vertices for value in vertex))
        extent = 40.0 * 0.72
        self.assertTrue(all(abs(value) < extent for vertex in result.mesh.vertices for value in vertex))

    def test_v2_styles_are_grounded_and_rugged_has_stronger_planar_regions(self):
        smooth = self._generate({"roughness": 0.10, "seed": 1})
        weathered = self._generate({"roughness": 0.35, "seed": 1})
        rugged = self._generate(
            {"size": 45.0, "roughness": 0.62, "seed": 23}, 25
        )

        planar_face_counts = []
        grounded_face_counts = []
        for result in (smooth, weathered, rugged):
            stats = result.statistics
            self.assertTrue(stats.is_manifold)
            self.assertTrue(stats.is_watertight)
            self.assertEqual(stats.connected_component_count, 1)
            self.assertEqual(stats.nonmanifold_edge_count, 0)
            self.assertEqual(stats.nonmanifold_vertex_count, 0)
            self.assertEqual(stats.inconsistent_winding_edge_count, 0)
            normals = [
                tuple(round(value, 5) for value in result.mesh.face_normal(index))
                for index in range(len(result.mesh.faces))
            ]
            counts = Counter(normals)
            planar_face_counts.append(max(counts.values()))
            grounded_face_counts.append(counts[(0.0, -0.0, -1.0)])

        self.assertGreater(min(grounded_face_counts), 0)
        self.assertGreater(planar_face_counts[2], planar_face_counts[0] * 3)
        self.assertGreater(grounded_face_counts[2], grounded_face_counts[0] * 3)

    def test_roughness_changes_large_scale_silhouette_and_faceting(self):
        low = self._generate({"roughness": 0.10, "seed": 1}, 25)
        high = self._generate({"roughness": 0.70, "seed": 1}, 25)

        low_spans = tuple(
            low.statistics.bounds[1][axis] - low.statistics.bounds[0][axis]
            for axis in range(3)
        )
        high_spans = tuple(
            high.statistics.bounds[1][axis] - high.statistics.bounds[0][axis]
            for axis in range(3)
        )
        self.assertGreater(
            max(abs(a - b) for a, b in zip(low_spans, high_spans)), 4.0
        )

        def largest_planar_region(result):
            normals = (
                tuple(round(value, 5) for value in result.mesh.face_normal(index))
                for index in range(len(result.mesh.faces))
            )
            return max(Counter(normals).values())

        self.assertGreater(
            largest_planar_region(high), largest_planar_region(low) * 5
        )

    def test_invalid_parameters_are_rejected(self):
        for overrides in (
            {"size": 0.0}, {"roughness": -0.1}, {"roughness": 0.71},
            {"seed": 1.5}, {"seed": -1}, {"unknown": 1},
        ):
            with self.assertRaises(InvalidGeneratorParameters):
                self._generate(overrides)

    def test_empty_extraction_is_reported(self):
        with patch("generators.rock_generator.extract_isosurface", return_value=TriangleMesh((), ())):
            with self.assertRaisesRegex(MeshExtractionError, "no triangles"):
                self._generate()

    def test_v2_default_mesh_digest(self):
        result = self._generate()
        digest = hashlib.sha256(
            repr((result.mesh.vertices, result.mesh.faces)).encode("ascii")
        ).hexdigest()
        self.assertEqual(
            digest,
            "30a709c32fb7dd16b87f0388f21c6e24e12b6ad990b2872dd31f9549956e7c1d",
        )


class BarkGeneratorTests(unittest.TestCase):
    def _generate(self, overrides=None, resolution=33):
        return GeneratorFactory.generate_request(
            GenerationRequest("bark", {} if overrides is None else overrides, resolution)
        )

    def test_deterministic_same_seed_and_different_seed_variation(self):
        first = self._generate({"seed": 42})
        repeated = self._generate({"seed": 42})
        different = self._generate({"seed": 43})
        self.assertEqual(first.mesh.vertices, repeated.mesh.vertices)
        self.assertEqual(first.mesh.faces, repeated.mesh.faces)
        self.assertNotEqual(first.mesh.vertices, different.mesh.vertices)

    def test_classic_family_matches_backward_compatible_default(self):
        default = self._generate()
        family = GeneratorFactory.generate_request(
            GenerationRequest("bark", {}, 33, "classic_bark")
        )
        self.assertEqual(default.mesh.vertices, family.mesh.vertices)
        self.assertEqual(default.mesh.faces, family.mesh.faces)

    def test_classic_family_digest_is_stable(self):
        result = GeneratorFactory.generate_request(
            GenerationRequest("bark", {}, 33, "classic_bark")
        )
        digest = hashlib.sha256(
            repr((result.mesh.vertices, result.mesh.faces)).encode("ascii")
        ).hexdigest()
        self.assertEqual(
            digest,
            "7cd5810b943bcfb4f88537d547ca9dfcce82380048d8bd41c20c309fd69dd6b7",
        )

    def test_unknown_bark_family_is_rejected(self):
        with self.assertRaises(InvalidGeneratorParameters):
            GeneratorFactory.generate_request(
                GenerationRequest("bark", {}, 33, "missing")
            )

    def test_dimensions_depth_grooves_twist_and_resolution_affect_geometry(self):
        narrow = self._generate({"diameter": 50.0})
        wide = self._generate({"diameter": 120.0})
        short = self._generate({"height": 60.0})
        tall = self._generate({"height": 200.0})
        shallow = self._generate({"bark_depth": 1.0})
        deep = self._generate({"bark_depth": 10.0})
        broad = self._generate({"groove_scale": 36.0})
        twisted = self._generate({"twist": 0.75})
        dense = self._generate(resolution=41)
        self.assertLess(narrow.statistics.bounds[1][0], wide.statistics.bounds[1][0])
        self.assertLess(short.statistics.bounds[1][2], tall.statistics.bounds[1][2])
        self.assertNotEqual(shallow.mesh.vertices, deep.mesh.vertices)
        self.assertNotEqual(broad.mesh.vertices, shallow.mesh.vertices)
        self.assertNotEqual(twisted.mesh.vertices, shallow.mesh.vertices)
        self.assertGreater(dense.statistics.face_count, shallow.statistics.face_count)

    def test_closed_manufacturable_single_component_and_caps(self):
        result = self._generate({"bark_depth": 10.0, "twist": 1.0, "seed": 987}, 29)
        stats = result.statistics
        self.assertTrue(stats.is_manifold)
        self.assertTrue(stats.is_watertight)
        self.assertEqual(stats.connected_component_count, 1)
        self.assertEqual(stats.degenerate_face_count, 0)
        self.assertTrue(all(
            math.isfinite(value)
            for vertex in result.mesh.vertices for value in vertex
        ))
        for cap_z in (-60.0, 60.0):
            self.assertTrue(any(
                all(abs(result.mesh.vertices[index][2] - cap_z) < 1e-9 for index in face)
                for face in result.mesh.faces
            ))

    def test_surface_stays_inside_sampling_bounds(self):
        diameter, height, depth = 30.0, 240.0, 7.5
        result = self._generate({
            "diameter": diameter, "height": height, "bark_depth": depth,
            "groove_scale": 6.0, "twist": -1.0, "seed": 2147483647,
        }, 29)
        radial_extent = diameter * 0.56 + depth * 1.2
        vertical_extent = height / 2.0 + max(height * 0.05, depth * 1.5)
        self.assertTrue(all(
            abs(x) < radial_extent and abs(y) < radial_extent and abs(z) < vertical_extent
            for x, y, z in result.mesh.vertices
        ))

    def test_bark_is_quantitatively_distinct_from_rock(self):
        bark = self._generate()
        rock = GeneratorFactory.generate_request(GenerationRequest("rock", {}, 17))
        bark_bounds = bark.statistics.bounds
        rock_bounds = rock.statistics.bounds
        bark_aspect = (
            (bark_bounds[1][2] - bark_bounds[0][2]) /
            (bark_bounds[1][0] - bark_bounds[0][0])
        )
        rock_aspect = (
            (rock_bounds[1][2] - rock_bounds[0][2]) /
            (rock_bounds[1][0] - rock_bounds[0][0])
        )
        self.assertGreater(bark_aspect, rock_aspect * 2.0)
        self.assertNotEqual(bark.statistics.face_count, rock.statistics.face_count)

    def test_invalid_parameters_and_depth_ratio_are_rejected(self):
        for overrides in (
            {"diameter": 0.0}, {"height": 0.0}, {"bark_depth": 0.0},
            {"groove_scale": 0.0}, {"twist": 1.1}, {"seed": 1.5},
            {"diameter": 30.0, "bark_depth": 15.0}, {"unknown": 1},
        ):
            with self.assertRaises(InvalidGeneratorParameters):
                self._generate(overrides)
        with self.assertRaises(InvalidGeneratorParameters):
            self._generate(resolution=25)

    def test_legacy_factory_uses_bark_metadata_resolution_default(self):
        legacy = GeneratorFactory.generate(PresetFactory.get("bark"))
        explicit = self._generate(resolution=33)
        self.assertEqual(legacy.mesh.vertices, explicit.mesh.vertices)
        self.assertEqual(legacy.mesh.faces, explicit.mesh.faces)

    def test_empty_extraction_is_reported(self):
        with patch(
            "generators.bark_generator.extract_isosurface",
            return_value=TriangleMesh((), ()),
        ):
            with self.assertRaisesRegex(MeshExtractionError, "no triangles"):
                self._generate()


class RootSkeletonTests(unittest.TestCase):
    _DEFAULTS = (100.0, 8.0, 5, 0.45, 0.65, 0.65, 0.70, 11)

    def test_skeleton_is_deterministic_seeded_and_bounded(self):
        first = build_root_skeleton(*self._DEFAULTS)
        repeated = build_root_skeleton(*self._DEFAULTS)
        changed = build_root_skeleton(*self._DEFAULTS[:-1], 12)
        self.assertEqual(first, repeated)
        self.assertNotEqual(first, changed)
        self.assertEqual(sum(item.depth == 0 for item in first), 4)
        self.assertLessEqual(len(first), 28)
        self.assertTrue(all(item.start != item.end for item in first))
        self.assertTrue(all(
            item.start_radius > 0.0 and item.end_radius > 0.0 for item in first
        ))

    def test_branch_count_branching_taper_gravity_and_spread_affect_skeleton(self):
        few = build_root_skeleton(100, 8, 1, 0, 0.65, 0.65, 0.7, 11)
        many = build_root_skeleton(100, 8, 8, 1, 0.65, 0.65, 0.7, 11)
        low_taper = build_root_skeleton(100, 8, 5, .45, .65, .2, .7, 11)
        high_taper = build_root_skeleton(100, 8, 5, .45, .65, .85, .7, 11)
        low_gravity = build_root_skeleton(100, 8, 5, .45, .65, .65, 0, 11)
        high_gravity = build_root_skeleton(100, 8, 5, .45, .65, .65, 1, 11)
        narrow = build_root_skeleton(100, 8, 5, .45, .1, .65, .7, 11)
        wide = build_root_skeleton(100, 8, 5, .45, 1, .65, .7, 11)
        self.assertGreater(len(many), len(few))
        self.assertLess(
            min(item.end_radius for item in high_taper),
            min(item.end_radius for item in low_taper),
        )
        self.assertLess(
            sum(item.end[2] for item in high_gravity if item.depth > 0),
            sum(item.end[2] for item in low_gravity if item.depth > 0),
        )
        self.assertGreater(
            max(math.hypot(item.end[0], item.end[1]) for item in wide),
            max(math.hypot(item.end[0], item.end[1]) for item in narrow),
        )


class RootGeneratorTests(unittest.TestCase):
    def _generate(self, overrides=None, resolution=37):
        return GeneratorFactory.generate_request(GenerationRequest(
            "root", {} if overrides is None else overrides, resolution
        ))

    def test_deterministic_mesh_seed_variation_and_digest(self):
        first = self._generate()
        repeated = self._generate()
        changed = self._generate({"seed": 12})
        self.assertEqual(first.mesh.vertices, repeated.mesh.vertices)
        self.assertEqual(first.mesh.faces, repeated.mesh.faces)
        self.assertNotEqual(first.mesh.vertices, changed.mesh.vertices)
        digest = hashlib.sha256(
            repr((first.mesh.vertices, first.mesh.faces)).encode("ascii")
        ).hexdigest()
        self.assertEqual(
            digest,
            "889e8603de8b33404d6d1939cfb53dfd3bd9d1fa0abf7f21e2b7efe7de1e8b59",
        )

    def test_classic_family_matches_legacy_request_and_preserves_asset(self):
        legacy = self._generate()
        family = GeneratorFactory.generate_request(GenerationRequest(
            "root", {}, 37, "classic_root"
        ))
        self.assertEqual(legacy.mesh.vertices, family.mesh.vertices)
        self.assertEqual(legacy.mesh.faces, family.mesh.faces)
        self.assertIs(family.asset.mesh, family.mesh)
        self.assertEqual(family.asset.metadata.family_id, "classic_root")
        self.assertEqual(family.asset.material.material_id, "natural_root")
        self.assertEqual(family.asset.mapping.mode.value, "object_space")
        self.assertEqual(family.asset.textures.resources, ())

    def test_unknown_root_family_is_rejected(self):
        with self.assertRaisesRegex(
            InvalidGeneratorParameters, "unknown root family"
        ):
            GeneratorFactory.generate_request(GenerationRequest(
                "root", {}, 37, "missing_root"
            ))

    def test_parameters_and_resolution_affect_geometry(self):
        short = self._generate({"length": 60.0})
        long = self._generate({"length": 160.0, "root_radius": 16.0})
        thin = self._generate({"root_radius": 8.0})
        thick = self._generate({"root_radius": 16.0})
        few = self._generate({"branch_count": 1, "branching": 0.0})
        many = self._generate({"branch_count": 8, "branching": 1.0})
        tapered = self._generate({"taper": 0.85})
        gravity = self._generate({"gravity": 1.0})
        dense = self._generate(resolution=41)
        self.assertLess(abs(short.statistics.bounds[0][2]), abs(long.statistics.bounds[0][2]))
        self.assertLess(thin.statistics.bounds[1][0], thick.statistics.bounds[1][0])
        self.assertNotEqual(few.mesh.vertices, many.mesh.vertices)
        self.assertNotEqual(tapered.mesh.vertices, thin.mesh.vertices)
        self.assertNotEqual(gravity.mesh.vertices, thin.mesh.vertices)
        self.assertGreater(dense.statistics.face_count, thin.statistics.face_count)

    def test_output_is_closed_finite_single_component_without_boundary_contact(self):
        result = self._generate({
            "length": 180.0, "root_radius": 14.4,
            "branch_count": 8, "branching": 1.0, "spread": 1.0,
            "gravity": 0.0, "seed": 2147483647,
        }, 37)
        stats = result.statistics
        self.assertTrue(stats.is_manifold)
        self.assertTrue(stats.is_watertight)
        self.assertEqual(stats.connected_component_count, 1)
        self.assertEqual(stats.degenerate_face_count, 0)
        self.assertTrue(all(
            math.isfinite(value) for vertex in result.mesh.vertices for value in vertex
        ))
        skeleton = build_root_skeleton(
            180, 14.4, 8, 1, 1, .65, 0, 2147483647
        )
        points = tuple(point for item in skeleton for point in (item.start, item.end)) + ((0, 0, 0),)
        margin = max(14.4 * 1.8, 180 * .08)
        minimum = tuple(min(point[a] for point in points) - margin for a in range(3))
        maximum = tuple(max(point[a] for point in points) + margin for a in range(3))
        self.assertTrue(all(
            minimum[a] < vertex[a] < maximum[a]
            for vertex in result.mesh.vertices for a in range(3)
        ))

    def test_invalid_and_empty_generation_fail_clearly(self):
        for overrides in (
            {"length": 0.0}, {"root_radius": 0.0}, {"branch_count": 9},
            {"branching": 1.1}, {"spread": 0.0}, {"taper": 0.9},
            {"gravity": -0.1}, {"seed": 1.5},
            {"length": 40.0, "root_radius": 20.0},
            {"length": 180.0, "root_radius": 4.0}, {"unknown": 1},
        ):
            with self.assertRaises(InvalidGeneratorParameters):
                self._generate(overrides)
        with self.assertRaises(InvalidGeneratorParameters):
            self._generate(resolution=25)
        with patch(
            "generators.root_generator.extract_isosurface",
            return_value=TriangleMesh((), ()),
        ):
            with self.assertRaisesRegex(MeshExtractionError, "no triangles"):
                self._generate()

class GeneratorRuntimeDependencyTests(unittest.TestCase):
    def test_runtime_has_no_fusion_numpy_or_dynamic_discovery_imports(self):
        generator_root = Path(__file__).parents[1] / "generators"
        runtime_modules = (
            "generator.py",
            "generator_factory.py",
            "gyroid_generator.py",
            "coral_generator.py",
            "bark_generator.py",
            "value_noise.py",
            "root_generator.py",
            "sponge_generator.py",
            "result.py",
            "request.py",
        )
        forbidden = (
            "import adsk",
            "from adsk",
            "import numpy",
            "from numpy",
            "importlib",
            "pkgutil",
            "glob(",
            "os.listdir",
        )
        for name in runtime_modules:
            source = (generator_root / name).read_text(encoding="utf-8")
            for marker in forbidden:
                self.assertNotIn(marker, source, "{} contains {}".format(name, marker))


if __name__ == "__main__":
    unittest.main()
