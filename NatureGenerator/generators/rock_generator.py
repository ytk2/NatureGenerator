"""Deterministic dependency-free multi-scale boulder generation."""

import math
from typing import Any

from core.marching_tetrahedra import extract_isosurface
from core.mesh import TriangleMesh
from core.voxel_grid import VoxelGrid
from presets import PresetFactory

from .generator import InvalidGeneratorParameters, MeshExtractionError, MeshGenerator
from .request import GenerationRequest
from .value_noise import DeterministicValueNoise


class _RockField:
    """Faceted ellipsoid field with FBM, ridges, and a grounded lower face."""

    def __init__(self, size: float, roughness: float, seed: int) -> None:
        self.size = size
        self.roughness = roughness
        self.seed = seed
        self.noise = DeterministicValueNoise(seed)
        normalized = max(0.0, min(1.0, roughness / 0.70))
        self.response = normalized * normalized * (3.0 - 2.0 * normalized)
        # Seeded axis proportions establish a broad non-spherical silhouette.
        axis_variation = 0.35 + 0.65 * self.response
        self.radii = (
            size * (
                0.47 + 0.025 * self.response
                + 0.025 * axis_variation * self.noise._lattice(1, 0, 0)
            ),
            size * (
                0.42 - 0.035 * self.response
                + 0.025 * axis_variation * self.noise._lattice(0, 1, 0)
            ),
            size * (
                0.36 - 0.040 * self.response
                + 0.020 * axis_variation * self.noise._lattice(0, 0, 1)
            ),
        )
        self.facets = tuple(self._facet(index) for index in range(5))

    def _facet(self, index: int):
        """Return one stable upper/side clipping plane in normalized space."""

        x = self.noise._lattice(17 + index * 5, 3, -7)
        y = self.noise._lattice(-11, 23 + index * 7, 5)
        z = 0.15 + 0.70 * abs(self.noise._lattice(7, -13, 31 + index * 3))
        length = math.sqrt(x * x + y * y + z * z)
        normal = (x / length, y / length, z / length)
        # Smooth rocks receive only tiny cap facets; Rugged exposes broad planes.
        offset = 1.015 - self.response * (
            0.245 + 0.030 * self.noise._lattice(index, 41, -19)
        )
        return normal, offset

    def _fbm(self, x: float, y: float, z: float, octaves: int) -> float:
        """Return normalized deterministic multi-octave value-noise FBM."""

        amplitude = 1.0
        frequency = 0.78
        total = 0.0
        weight = 0.0
        for octave in range(octaves):
            total += amplitude * self.noise.sample(
                x * frequency + 11.3 + octave * 3.17,
                y * frequency - 7.9 + octave * 1.91,
                z * frequency + 5.1 - octave * 2.43,
            )
            weight += amplitude
            frequency *= 2.08
            amplitude *= 0.52
        return total / weight

    def _ridged(self, x: float, y: float, z: float) -> float:
        """Return centered ridge noise for sharper creases and shoulders."""

        ridge = 1.0 - abs(self.noise.sample(
            x * 3.15 - 4.7,
            y * 3.15 + 9.2,
            z * 3.15 - 2.6,
        ))
        return ridge * ridge - 0.38

    def __call__(self, x: float, y: float, z: float) -> float:
        nx, ny, nz = x / self.radii[0], y / self.radii[1], z / self.radii[2]
        radius = math.sqrt(nx * nx + ny * ny + nz * nz)
        if radius == 0.0:
            return -1.0
        dx, dy, dz = nx / radius, ny / radius, nz / radius

        # Low-order terms break the sphere-like outline before noise is applied.
        broad = (
            0.060 * dx * dy
            + 0.040 * dx * dz
            - 0.045 * dz * dz
            + 0.025 * (dx * dx - dy * dy)
        )
        large = self.noise.sample(
            nx * 0.68 + 2.7,
            ny * 0.68 - 5.4,
            nz * 0.68 + 8.1,
        )
        fbm = self._fbm(nx, ny, nz, 5)
        ridge = self._ridged(nx, ny, nz)
        variation = (
            broad * (0.35 + 0.95 * self.response)
            + (0.018 + 0.145 * self.response) * large
            + (0.012 + 0.105 * self.response) * fbm
            + 0.090 * math.pow(self.response, 1.35) * ridge
        )
        field = radius - (1.0 + variation)

        # Intersect with stable half-spaces. The max operation creates genuine
        # planar regions while preserving a single continuous implicit solid.
        for normal, offset in self.facets:
            plane = nx * normal[0] + ny * normal[1] + nz * normal[2] - offset
            field = max(field, plane)

        # A small lower clipping face gives the boulder a plausible bearing
        # surface. Rougher stones receive a slightly broader grounded region.
        ground_offset = 0.95 - 0.17 * self.response
        return max(field, -nz - ground_offset)


class RockGenerator(MeshGenerator):
    """Generate one closed asymmetrical stone through the shared mesh pipeline."""

    _PARAMETER_IDS = frozenset(("size", "roughness", "seed"))

    @property
    def preset_id(self) -> str:
        return "rock"

    @property
    def generator_id(self) -> str:
        return "rock"

    @property
    def require_watertight(self) -> bool:
        return True

    def generate(self, request: GenerationRequest) -> TriangleMesh:
        if not isinstance(request, GenerationRequest):
            raise TypeError("request must be a GenerationRequest")
        if request.preset_id != self.preset_id:
            raise InvalidGeneratorParameters("request preset_id does not match 'rock'")
        preset = PresetFactory.get(self.preset_id)
        configured = dict(preset.default_parameters)
        configured.pop("resolution", None)
        configured.update(request.parameter_overrides)
        unknown = set(configured) - self._PARAMETER_IDS
        missing = self._PARAMETER_IDS - set(configured)
        if unknown or missing:
            detail = "unknown {}".format(sorted(unknown)) if unknown else "missing {}".format(sorted(missing))
            raise InvalidGeneratorParameters("invalid rock parameters: {}".format(detail))
        try:
            size = self._number(configured["size"], "size")
            roughness = self._number(configured["roughness"], "roughness")
            seed = configured["seed"]
            if isinstance(seed, bool) or not isinstance(seed, int):
                raise TypeError("seed must be an integer")
            for key, value in configured.items():
                metadata = preset.parameter_metadata[key]
                if metadata.minimum is not None and value < metadata.minimum:
                    raise ValueError("{} must be at least {}".format(key, metadata.minimum))
                if metadata.maximum is not None and value > metadata.maximum:
                    raise ValueError("{} must be at most {}".format(key, metadata.maximum))
            field = _RockField(size, roughness, seed)
        except (TypeError, ValueError, ArithmeticError, OverflowError) as error:
            raise InvalidGeneratorParameters("invalid rock parameters: {}".format(error)) from error
        try:
            extent = size * 0.72
            shape = (request.resolution,) * 3
            grid = VoxelGrid.sample(field, (-extent,) * 3, (extent,) * 3, shape)
            mesh = extract_isosurface(grid)
        except (TypeError, ValueError, ArithmeticError, OverflowError) as error:
            raise MeshExtractionError(
                "rock mesh extraction failed: {}".format(error)
            ) from error
        if not mesh.faces:
            raise MeshExtractionError("rock mesh extraction produced no triangles")
        return mesh

    @staticmethod
    def _number(value: Any, name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("{} must be numeric".format(name))
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("{} must be finite".format(name))
        return result
