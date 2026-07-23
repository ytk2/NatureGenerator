"""Deterministic closed trunk segment with directional bark grooves."""

import math
from typing import Any

from core.marching_tetrahedra import extract_isosurface
from core.mesh import TriangleMesh
from core.voxel_grid import VoxelGrid
from presets import PresetFactory

from .bark_families import BarkFamilyRegistry, CLASSIC_BARK_FAMILY
from .generator import InvalidGeneratorParameters, MeshExtractionError, MeshGenerator
from .request import GenerationRequest
from .value_noise import DeterministicValueNoise


class _BarkField:
    """Finite capped-cylinder field with periodic anisotropic radial detail."""

    def __init__(
        self,
        diameter: float,
        height: float,
        bark_depth: float,
        groove_scale: float,
        twist: float,
        seed: int,
    ) -> None:
        self.diameter = diameter
        self.height = height
        self.bark_depth = bark_depth
        self.groove_scale = groove_scale
        self.twist = twist
        self.seed = seed
        self.radius = diameter / 2.0
        self.noise = DeterministicValueNoise(seed)
        self.ridge_count = min(
            6, max(3, int(round(diameter / groove_scale)))
        )
        self._phase_a = math.pi * self.noise._lattice(11, 2, 5)
        self._phase_b = math.pi * self.noise._lattice(3, 17, 7)
        self._phase_c = math.pi * self.noise._lattice(13, 19, 23)

    def __call__(self, x: float, y: float, z: float) -> float:
        radial = math.sqrt(x * x + y * y)
        theta = math.atan2(y, x)
        normalized_height = z / self.height
        helical_theta = theta - (
            2.0 * math.pi * self.twist * (normalized_height + 0.5)
        )

        broad = (
            0.65 * math.cos(2.0 * theta + self._phase_a)
            + 0.35 * math.cos(
                3.0 * theta - 0.45 * normalized_height + self._phase_b
            )
        )
        grooves = (
            0.72 * math.cos(self.ridge_count * helical_theta + self._phase_b)
            + 0.28 * math.cos(
                2.0 * self.ridge_count * helical_theta
                + 0.7 * normalized_height
                + self._phase_c
            )
        )
        angular_frequency = max(1.0, self.radius / self.groove_scale)
        anisotropic = self.noise.sample(
            angular_frequency * math.cos(theta) + 5.3,
            angular_frequency * math.sin(theta) - 7.1,
            0.85 * normalized_height + 2.7,
        )
        breakup = math.sin(
            (self.ridge_count + 3) * helical_theta
            + 2.4 * normalized_height
            + self._phase_a
        ) * math.sin(5.2 * normalized_height + self._phase_c)

        surface_radius = (
            self.radius
            + 0.04 * self.radius * broad
            + self.bark_depth * (
                0.52 * grooves + 0.25 * anisotropic + 0.12 * breakup
            )
        )
        side = radial - surface_radius
        cap = abs(z) - self.height / 2.0
        return max(side, cap)


class BarkGenerator(MeshGenerator):
    """Generate one capped, connected trunk segment through shared extraction."""

    _PARAMETER_IDS = frozenset((
        "diameter", "height", "bark_depth", "groove_scale", "twist", "seed",
    ))

    @property
    def preset_id(self) -> str:
        return "bark"

    @property
    def generator_id(self) -> str:
        return "bark"

    @property
    def require_watertight(self) -> bool:
        return True

    def generate(self, request: GenerationRequest) -> TriangleMesh:
        if not isinstance(request, GenerationRequest):
            raise TypeError("request must be a GenerationRequest")
        if request.preset_id != self.preset_id:
            raise InvalidGeneratorParameters("request preset_id does not match 'bark'")
        preset = PresetFactory.get(self.preset_id)
        configured = dict(preset.default_parameters)
        try:
            family = (
                BarkFamilyRegistry.get(request.family_id)
                if request.family_id else CLASSIC_BARK_FAMILY
            )
        except KeyError as error:
            raise InvalidGeneratorParameters(str(error)) from error
        configured.update(family.parameter_values)
        configured.pop("resolution", None)
        configured.update(request.parameter_overrides)
        unknown = set(configured) - self._PARAMETER_IDS
        missing = self._PARAMETER_IDS - set(configured)
        if unknown or missing:
            detail = (
                "unknown {}".format(sorted(unknown))
                if unknown else "missing {}".format(sorted(missing))
            )
            raise InvalidGeneratorParameters("invalid bark parameters: {}".format(detail))

        try:
            diameter = self._number(configured["diameter"], "diameter")
            height = self._number(configured["height"], "height")
            bark_depth = self._number(configured["bark_depth"], "bark_depth")
            groove_scale = self._number(configured["groove_scale"], "groove_scale")
            twist = self._number(configured["twist"], "twist")
            seed = configured["seed"]
            if isinstance(seed, bool) or not isinstance(seed, int):
                raise TypeError("seed must be an integer")
            for key, value in configured.items():
                metadata = preset.parameter_metadata[key]
                if metadata.minimum is not None and value < metadata.minimum:
                    raise ValueError("{} must be at least {}".format(key, metadata.minimum))
                if metadata.maximum is not None and value > metadata.maximum:
                    raise ValueError("{} must be at most {}".format(key, metadata.maximum))
            if bark_depth > diameter * 0.25:
                raise ValueError("bark_depth must not exceed 25% of diameter")
            resolution_metadata = preset.parameter_metadata["resolution"]
            if request.resolution < resolution_metadata.minimum:
                raise ValueError(
                    "resolution must be at least {} for bark".format(
                        int(resolution_metadata.minimum)
                    )
                )
            field = _BarkField(
                diameter, height, bark_depth, groove_scale, twist, seed
            )
        except (TypeError, ValueError, ArithmeticError, OverflowError) as error:
            raise InvalidGeneratorParameters(
                "invalid bark parameters: {}".format(error)
            ) from error

        radial_extent = diameter * 0.56 + bark_depth * 1.2
        vertical_extent = height / 2.0 + max(height * 0.05, bark_depth * 1.5)
        try:
            shape = (request.resolution,) * 3
            grid = VoxelGrid.sample(
                field,
                (-radial_extent, -radial_extent, -vertical_extent),
                (radial_extent, radial_extent, vertical_extent),
                shape,
            )
            mesh = extract_isosurface(grid)
        except (TypeError, ValueError, ArithmeticError, OverflowError) as error:
            raise MeshExtractionError(
                "bark mesh extraction failed: {}".format(error)
            ) from error
        if not mesh.faces:
            raise MeshExtractionError("bark mesh extraction produced no triangles")
        return mesh

    @staticmethod
    def _number(value: Any, name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("{} must be numeric".format(name))
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("{} must be finite".format(name))
        return result
