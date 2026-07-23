"""Closed deterministic porous Sponge generation."""

import math
from typing import Any, Mapping, Tuple

from core.marching_tetrahedra import extract_isosurface
from core.mesh import TriangleMesh
from core.voxel_grid import VoxelGrid
from presets import PresetFactory

from .generator import InvalidGeneratorParameters, MeshExtractionError, MeshGenerator
from .request import GenerationRequest
from .sponge_families import CLASSIC_SPONGE_FAMILY, SpongeFamilyRegistry
from .value_noise import DeterministicValueNoise


Point3 = Tuple[float, float, float]


class _SpongeField:
    """Rounded solid with seed-dependent spherical pores open to its exterior."""

    _PORE_FACES = (
        (0, -1.0), (0, 1.0),
        (1, -1.0), (1, 1.0),
        (2, -1.0), (2, 1.0),
        (0, -1.0), (0, 1.0),
        (1, -1.0), (1, 1.0),
        (2, -1.0), (2, 1.0),
    )

    def __init__(self, cell_size: float, thickness: float, seed: int) -> None:
        self.cell_size = float(cell_size)
        self.thickness = float(thickness)
        self.seed = seed
        self._half_extent = self.cell_size * 0.43
        self._corner_radius = self.cell_size * 0.10
        noise = DeterministicValueNoise(seed)
        pores = []
        for index, (axis, sign) in enumerate(self._PORE_FACES):
            tangential = tuple(value for value in range(3) if value != axis)
            center = [0.0, 0.0, 0.0]
            center[axis] = sign * self._half_extent * 0.94
            center[tangential[0]] = self.cell_size * 0.23 * noise.sample(
                index * 1.73 + 0.2, axis * 2.1 + 0.4, sign * 1.9
            )
            center[tangential[1]] = self.cell_size * 0.23 * noise.sample(
                index * 2.17 + 1.1, axis * 1.7 + 0.8, sign * 2.3
            )
            radius_variation = noise.sample(
                index * 1.31 + 0.7, axis * 2.9 + 0.3, sign * 3.1
            )
            radius = self.cell_size * (
                0.095 + 0.11 * self.thickness + 0.012 * radius_variation
            )
            pores.append((tuple(center), radius))
        self._pores = tuple(pores)

    def __call__(self, x: float, y: float, z: float) -> float:
        return self.sample(x, y, z)

    def sample(self, x: float, y: float, z: float) -> float:
        point = (float(x), float(y), float(z))
        field = self._rounded_box_distance(point)
        for center, radius in self._pores:
            cavity = math.sqrt(
                sum((point[axis] - center[axis]) ** 2 for axis in range(3))
            ) - radius
            field = max(field, -cavity)
        return field

    def _rounded_box_distance(self, point: Point3) -> float:
        inner = self._half_extent - self._corner_radius
        offset = tuple(abs(value) - inner for value in point)
        outside = math.sqrt(sum(max(value, 0.0) ** 2 for value in offset))
        inside = min(max(offset), 0.0)
        return outside + inside - self._corner_radius


class SpongeGenerator(MeshGenerator):
    """Generate one closed porous sponge through the shared mesh pipeline."""

    _PARAMETER_IDS = frozenset(("cell_size", "thickness", "seed"))

    @property
    def preset_id(self) -> str:
        return "sponge"

    @property
    def generator_id(self) -> str:
        return "gyroid"

    @property
    def require_watertight(self) -> bool:
        return True

    def generate(self, request: GenerationRequest) -> TriangleMesh:
        if not isinstance(request, GenerationRequest):
            raise TypeError("request must be a GenerationRequest")
        if request.preset_id != self.preset_id:
            raise InvalidGeneratorParameters("request preset_id does not match 'sponge'")
        preset = PresetFactory.get(self.preset_id)
        configured = dict(preset.default_parameters)
        try:
            family = (
                SpongeFamilyRegistry.get(request.family_id)
                if request.family_id else CLASSIC_SPONGE_FAMILY
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
            raise InvalidGeneratorParameters(
                "invalid sponge parameters: {}".format(detail)
            )
        try:
            cell_size = self._number(configured["cell_size"], "cell_size")
            thickness = self._number(configured["thickness"], "thickness")
            seed = configured["seed"]
            if isinstance(seed, bool) or not isinstance(seed, int):
                raise TypeError("seed must be an integer")
            self._validate_metadata_bounds(preset, configured)
            field = _SpongeField(cell_size, thickness, seed)
        except (TypeError, ValueError, ArithmeticError, OverflowError) as error:
            raise InvalidGeneratorParameters(
                "invalid sponge parameters: {}".format(error)
            ) from error

        extent = cell_size * 0.58
        try:
            shape = (request.resolution,) * 3
            grid = VoxelGrid.sample(field, (-extent,) * 3, (extent,) * 3, shape)
            mesh = extract_isosurface(grid)
        except (TypeError, ValueError, ArithmeticError, OverflowError) as error:
            raise MeshExtractionError(
                "sponge mesh extraction failed: {}".format(error)
            ) from error
        if not mesh.faces:
            raise MeshExtractionError("sponge mesh extraction produced no triangles")
        return mesh

    @staticmethod
    def _number(value: Any, name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("{} must be numeric".format(name))
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("{} must be finite".format(name))
        return result

    @staticmethod
    def _validate_metadata_bounds(
        preset, parameters: Mapping[str, Any]
    ) -> None:
        for parameter_id, metadata in preset.parameter_metadata.items():
            if parameter_id not in parameters:
                continue
            value = parameters[parameter_id]
            if metadata.minimum is not None and value < metadata.minimum:
                raise ValueError(
                    "{} must be at least {}".format(parameter_id, metadata.minimum)
                )
            if metadata.maximum is not None and value > metadata.maximum:
                raise ValueError(
                    "{} must be at most {}".format(parameter_id, metadata.maximum)
                )
