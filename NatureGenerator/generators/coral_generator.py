"""Closed branching coral generator built on the dependency-free geometry core."""

import math
from typing import Any, Mapping, Tuple

from core.marching_tetrahedra import extract_isosurface
from core.mesh import TriangleMesh
from core.voxel_grid import VoxelGrid
from presets import PresetFactory

from .generator import (
    MeshGenerator,
    InvalidGeneratorParameters,
    MeshExtractionError,
)
from .request import GenerationRequest


Point3 = Tuple[float, float, float]
Segment = Tuple[Point3, Point3]


class _CoralField:
    """Signed distance to a connected union of tapered-looking coral branches.

    The field is a union of capsules. Overlapping capsules form a single,
    closed implicit solid whose branches remain inside the sampling domain.
    """

    _SEGMENTS: Tuple[Segment, ...] = (
        ((0.0, 0.0, -0.30), (0.0, 0.0, 0.28)),
        ((0.0, 0.0, -0.08), (0.26, 0.03, 0.17)),
        ((0.0, 0.0, 0.03), (-0.23, 0.12, 0.29)),
        ((0.0, 0.0, 0.13), (0.04, -0.25, 0.34)),
        ((0.26, 0.03, 0.17), (0.31, 0.12, 0.31)),
        ((-0.23, 0.12, 0.29), (-0.30, 0.04, 0.38)),
    )

    def __init__(self, cell_size: float, thickness: float) -> None:
        self.cell_size = float(cell_size)
        self.thickness = float(thickness)
        self._radius = self.cell_size * (0.052 + 0.058 * self.thickness)
        self._segments = tuple(
            (
                tuple(coordinate * self.cell_size for coordinate in start),
                tuple(coordinate * self.cell_size for coordinate in end),
            )
            for start, end in self._SEGMENTS
        )

    def __call__(self, x: float, y: float, z: float) -> float:
        return self.sample(x, y, z)

    def sample(self, x: float, y: float, z: float) -> float:
        """Return the signed distance to the closest coral branch."""

        point = (float(x), float(y), float(z))
        return min(
            self._segment_distance(point, start, end)
            for start, end in self._segments
        ) - self._radius

    @staticmethod
    def _segment_distance(point: Point3, start: Point3, end: Point3) -> float:
        direction = tuple(end[i] - start[i] for i in range(3))
        offset = tuple(point[i] - start[i] for i in range(3))
        length_squared = sum(value * value for value in direction)
        fraction = sum(offset[i] * direction[i] for i in range(3)) / length_squared
        fraction = min(1.0, max(0.0, fraction))
        closest = tuple(start[i] + fraction * direction[i] for i in range(3))
        return math.sqrt(sum((point[i] - closest[i]) ** 2 for i in range(3)))


class CoralGenerator(MeshGenerator):
    """Generate a closed, branching coral solid from shared command parameters."""

    _PARAMETER_IDS = frozenset(("cell_size", "thickness"))

    @property
    def preset_id(self) -> str:
        return "coral"

    @property
    def generator_id(self) -> str:
        return "coral"

    @property
    def require_watertight(self) -> bool:
        return True

    def generate(self, request: GenerationRequest) -> TriangleMesh:
        """Sample the coral field and return a closed triangle mesh."""

        if not isinstance(request, GenerationRequest):
            raise TypeError("request must be a GenerationRequest")
        if request.preset_id != self.preset_id:
            raise InvalidGeneratorParameters(
                "request preset_id {!r} does not match {!r}".format(
                    request.preset_id, self.preset_id
                )
            )
        preset = PresetFactory.get(self.preset_id)

        configured = dict(preset.default_parameters)
        configured.pop("resolution", None)
        configured.update(request.parameter_overrides)
        unknown = set(configured) - self._PARAMETER_IDS
        missing = self._PARAMETER_IDS - set(configured)
        if unknown:
            raise InvalidGeneratorParameters(
                "unknown coral parameters: {}".format(sorted(unknown))
            )
        if missing:
            raise InvalidGeneratorParameters(
                "missing coral parameters: {}".format(sorted(missing))
            )

        try:
            cell_size = self._finite_number(configured["cell_size"], "cell_size")
            thickness = self._finite_number(configured["thickness"], "thickness")
            self._validate_metadata_bounds(preset, configured)
            field = _CoralField(cell_size, thickness)
        except (TypeError, ValueError, OverflowError) as error:
            raise InvalidGeneratorParameters(
                "invalid coral parameters: {}".format(error)
            ) from error

        half_extent = cell_size / 2.0
        bounds = (-half_extent, -half_extent, -half_extent)
        maximum = (half_extent, half_extent, half_extent)
        try:
            shape = (request.resolution, request.resolution, request.resolution)
            mesh = extract_isosurface(VoxelGrid.sample(field, bounds, maximum, shape))
        except (TypeError, ValueError, ArithmeticError) as error:
            raise MeshExtractionError(
                "coral mesh extraction failed: {}".format(error)
            ) from error

        if not mesh.faces:
            raise MeshExtractionError("coral mesh extraction produced no triangles")
        return mesh

    @staticmethod
    def _finite_number(value: Any, name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("{} must be numeric".format(name))
        converted = float(value)
        if not math.isfinite(converted):
            raise ValueError("{} must be finite".format(name))
        return converted

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
