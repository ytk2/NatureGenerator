"""Deterministic dependency-free rounded rock generation."""

import math
from typing import Any, Mapping

from core.marching_tetrahedra import extract_isosurface
from core.mesh import TriangleMesh
from core.voxel_grid import VoxelGrid
from presets import PresetFactory

from .generator import InvalidGeneratorParameters, MeshExtractionError, MeshGenerator
from .request import GenerationRequest


class _ValueNoise:
    """Seeded lattice value noise with smoothstep trilinear interpolation."""

    def __init__(self, seed: int) -> None:
        self.seed = seed

    def _lattice(self, x: int, y: int, z: int) -> float:
        # Fixed-width integer mixing is stable and does not use randomized hash().
        value = (self.seed ^ (x * 0x8DA6B343) ^ (y * 0xD8163841) ^
                 (z * 0xCB1AB31F)) & 0xFFFFFFFF
        value ^= value >> 16
        value = (value * 0x7FEB352D) & 0xFFFFFFFF
        value ^= value >> 15
        value = (value * 0x846CA68B) & 0xFFFFFFFF
        value ^= value >> 16
        return (value / 2147483647.5) - 1.0

    def sample(self, x: float, y: float, z: float) -> float:
        ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
        fx, fy, fz = x - ix, y - iy, z - iz

        def fade(value: float) -> float:
            return value * value * (3.0 - 2.0 * value)

        def blend(a: float, b: float, amount: float) -> float:
            return a + (b - a) * amount

        ux, uy, uz = fade(fx), fade(fy), fade(fz)
        planes = []
        for dz in (0, 1):
            rows = []
            for dy in (0, 1):
                rows.append(blend(
                    self._lattice(ix, iy + dy, iz + dz),
                    self._lattice(ix + 1, iy + dy, iz + dz), ux,
                ))
            planes.append(blend(rows[0], rows[1], uy))
        return blend(planes[0], planes[1], uz)


class _RockField:
    """Ellipsoid radial field deformed by directional terms and value noise."""

    def __init__(self, size: float, roughness: float, seed: int) -> None:
        self.size = size
        self.roughness = roughness
        self.seed = seed
        self.noise = _ValueNoise(seed)
        # Seeded but bounded axis proportions create broad asymmetry.
        self.radii = (
            size * (0.47 + 0.025 * self.noise._lattice(1, 0, 0)),
            size * (0.40 + 0.025 * self.noise._lattice(0, 1, 0)),
            size * (0.34 + 0.020 * self.noise._lattice(0, 0, 1)),
        )

    def __call__(self, x: float, y: float, z: float) -> float:
        nx, ny, nz = x / self.radii[0], y / self.radii[1], z / self.radii[2]
        radius = math.sqrt(nx * nx + ny * ny + nz * nz)
        if radius == 0.0:
            return -1.0
        dx, dy, dz = nx / radius, ny / radius, nz / radius
        broad = 0.055 * (dx * dy - 0.65 * dz * dz + 0.45 * dx * dz)
        frequency = 1.35
        amplitude = 1.0
        total = 0.0
        weight = 0.0
        for _ in range(3):
            total += amplitude * self.noise.sample(
                dx * frequency + 13.7,
                dy * frequency - 8.3,
                dz * frequency + 4.9,
            )
            weight += amplitude
            frequency *= 2.07
            amplitude *= 0.5
        variation = broad + self.roughness * 0.24 * (total / weight)
        return radius - (1.0 + variation)


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
