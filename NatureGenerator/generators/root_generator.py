"""Deterministic staged root skeleton and implicit thickening."""

from dataclasses import dataclass
import math
from typing import Any, Tuple

from core.marching_tetrahedra import extract_isosurface
from core.mesh import TriangleMesh
from core.voxel_grid import VoxelGrid
from presets import PresetFactory

from .generator import InvalidGeneratorParameters, MeshExtractionError, MeshGenerator
from .request import GenerationRequest
from .value_noise import DeterministicValueNoise


Point3 = Tuple[float, float, float]
MAX_ROOT_SEGMENTS = 28
MAX_ROOT_DEPTH = 2


@dataclass(frozen=True)
class RootSegment:
    """One immutable tapered skeleton segment."""

    start: Point3
    end: Point3
    start_radius: float
    end_radius: float
    depth: int

    def __post_init__(self) -> None:
        if self.start == self.end:
            raise ValueError("root segments must have non-zero length")
        if self.start_radius <= 0.0 or self.end_radius <= 0.0:
            raise ValueError("root segment radii must be positive")
        if self.depth < 0 or self.depth > MAX_ROOT_DEPTH:
            raise ValueError("root segment depth exceeds the safe limit")


def _add(a: Point3, b: Point3) -> Point3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _scale(vector: Point3, amount: float) -> Point3:
    return tuple(value * amount for value in vector)  # type: ignore[return-value]


def _normalize(vector: Point3) -> Point3:
    length = math.sqrt(sum(value * value for value in vector))
    if length == 0.0:
        raise ValueError("root direction must have non-zero length")
    return tuple(value / length for value in vector)  # type: ignore[return-value]


def _lerp(a: Point3, b: Point3, fraction: float) -> Point3:
    return tuple(
        a[index] + fraction * (b[index] - a[index]) for index in range(3)
    )  # type: ignore[return-value]


def build_root_skeleton(
    length: float,
    root_radius: float,
    branch_count: int,
    branching: float,
    spread: float,
    taper: float,
    gravity: float,
    seed: int,
) -> Tuple[RootSegment, ...]:
    """Return a bounded deterministic primary/lateral root skeleton."""

    noise = DeterministicValueNoise(seed)
    segments = []
    primary_points = [(0.0, 0.0, 0.0)]
    for index in range(4):
        fraction = (index + 1) / 4.0
        lateral_scale = length * 0.045 * spread * (1.0 - 0.45 * fraction)
        point = (
            lateral_scale * noise._lattice(index + 1, 31, 7),
            lateral_scale * noise._lattice(13, index + 1, 37),
            -length * fraction,
        )
        primary_points.append(point)
        start_fraction = index / 4.0
        start_radius = root_radius * (1.0 - 0.65 * taper * start_fraction)
        end_radius = root_radius * (1.0 - 0.65 * taper * fraction)
        segments.append(RootSegment(
            primary_points[-2], point, start_radius, end_radius, 0
        ))

    for index in range(branch_count):
        variation = noise._lattice(index + 41, 5, 17)
        attach_fraction = min(0.86, max(
            0.14,
            0.18 + 0.64 * ((index + 0.5) / branch_count) + 0.035 * variation,
        ))
        scaled = attach_fraction * 4.0
        segment_index = min(3, int(scaled))
        local_fraction = scaled - segment_index
        attach = _lerp(
            primary_points[segment_index],
            primary_points[segment_index + 1],
            local_fraction,
        )
        azimuth = (
            2.0 * math.pi * index / branch_count
            + math.pi * noise._lattice(19, index + 3, 43) / branch_count
        )
        downward = 0.20 + 0.90 * gravity
        direction = _normalize((
            spread * math.cos(azimuth), spread * math.sin(azimuth), -downward,
        ))
        lateral_length = length * (
            0.24 + 0.06 * (variation + 1.0) / 2.0
        ) * (0.72 + 0.28 * branching)
        bend = 0.22 * noise._lattice(53, index + 7, 11)
        middle = _add(attach, _scale(direction, lateral_length * 0.52))
        second_direction = _normalize((
            direction[0] + bend * -direction[1],
            direction[1] + bend * direction[0],
            direction[2] - 0.10 * gravity,
        ))
        end = _add(middle, _scale(second_direction, lateral_length * 0.48))
        start_radius = root_radius * (0.65 - 0.10 * attach_fraction)
        middle_radius = start_radius * (1.0 - 0.28 * taper)
        end_radius = start_radius * (1.0 - 0.48 * taper)
        segments.extend((
            RootSegment(attach, middle, start_radius, middle_radius, 1),
            RootSegment(middle, end, middle_radius, end_radius, 1),
        ))

        threshold = (noise._lattice(index + 71, 29, 3) + 1.0) / 2.0
        if threshold < branching:
            secondary_azimuth = azimuth + (
                0.65 + 0.45 * noise._lattice(31, index + 79, 23)
            )
            secondary_direction = _normalize((
                spread * math.cos(secondary_azimuth),
                spread * math.sin(secondary_azimuth),
                -(0.30 + 0.75 * gravity),
            ))
            secondary_length = lateral_length * (0.28 + 0.25 * branching)
            secondary_end = _add(
                middle, _scale(secondary_direction, secondary_length)
            )
            secondary_radius = middle_radius * (1.0 - 0.45 * taper)
            segments.append(RootSegment(
                middle, secondary_end, middle_radius * 0.90,
                secondary_radius * 0.90, 2,
            ))

    if len(segments) > MAX_ROOT_SEGMENTS:
        raise ValueError("root skeleton exceeds the safe segment limit")
    return tuple(segments)


class _RootField:
    """Hard union of tapered segment fields and a compact root crown."""

    def __init__(self, segments: Tuple[RootSegment, ...], crown_radius: float) -> None:
        self.segments = segments
        self.crown_radius = crown_radius

    def __call__(self, x: float, y: float, z: float) -> float:
        point = (x, y, z)
        crown = math.sqrt(x * x + y * y + z * z) - self.crown_radius
        return min(crown, *(self._segment_field(point, item) for item in self.segments))

    @staticmethod
    def _segment_field(point: Point3, segment: RootSegment) -> float:
        direction = tuple(
            segment.end[index] - segment.start[index] for index in range(3)
        )
        offset = tuple(
            point[index] - segment.start[index] for index in range(3)
        )
        length_squared = sum(value * value for value in direction)
        fraction = sum(
            offset[index] * direction[index] for index in range(3)
        ) / length_squared
        fraction = min(1.0, max(0.0, fraction))
        closest = tuple(
            segment.start[index] + fraction * direction[index]
            for index in range(3)
        )
        radius = segment.start_radius + fraction * (
            segment.end_radius - segment.start_radius
        )
        return math.sqrt(sum(
            (point[index] - closest[index]) ** 2 for index in range(3)
        )) - radius


class RootGenerator(MeshGenerator):
    """Generate a closed deterministic staged root system."""

    _PARAMETER_IDS = frozenset((
        "length", "root_radius", "branch_count", "branching", "spread",
        "taper", "gravity", "seed",
    ))

    @property
    def preset_id(self) -> str:
        return "root"

    @property
    def generator_id(self) -> str:
        return "root"

    @property
    def require_watertight(self) -> bool:
        return True

    def generate(self, request: GenerationRequest) -> TriangleMesh:
        if not isinstance(request, GenerationRequest):
            raise TypeError("request must be a GenerationRequest")
        if request.preset_id != self.preset_id:
            raise InvalidGeneratorParameters("request preset_id does not match 'root'")
        preset = PresetFactory.get(self.preset_id)
        configured = dict(preset.default_parameters)
        configured.pop("resolution", None)
        configured.update(request.parameter_overrides)
        unknown = set(configured) - self._PARAMETER_IDS
        missing = self._PARAMETER_IDS - set(configured)
        if unknown or missing:
            detail = (
                "unknown {}".format(sorted(unknown))
                if unknown else "missing {}".format(sorted(missing))
            )
            raise InvalidGeneratorParameters("invalid root parameters: {}".format(detail))

        try:
            values = self._validated_values(preset, configured, request.resolution)
            segments = build_root_skeleton(*values)
            if min(item.end_radius for item in segments) < 0.75:
                raise ValueError("root taper produces a tip radius below 0.75 mm")
            field = _RootField(segments, values[1] * 1.1)
        except (TypeError, ValueError, ArithmeticError, OverflowError) as error:
            raise InvalidGeneratorParameters(
                "invalid root parameters: {}".format(error)
            ) from error

        points = tuple(
            point for segment in segments for point in (segment.start, segment.end)
        ) + ((0.0, 0.0, 0.0),)
        margin = max(values[1] * 1.8, values[0] * 0.08)
        minimum = tuple(min(point[axis] for point in points) - margin for axis in range(3))
        maximum = tuple(max(point[axis] for point in points) + margin for axis in range(3))
        try:
            mesh = extract_isosurface(VoxelGrid.sample(
                field, minimum, maximum, (request.resolution,) * 3
            ))
        except (TypeError, ValueError, ArithmeticError, OverflowError) as error:
            raise MeshExtractionError(
                "root mesh extraction failed: {}".format(error)
            ) from error
        if not mesh.faces:
            raise MeshExtractionError("root mesh extraction produced no triangles")
        return mesh

    @staticmethod
    def _validated_values(preset, configured, resolution):
        numeric = {}
        for key in ("length", "root_radius", "branching", "spread", "taper", "gravity"):
            value = configured[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError("{} must be numeric".format(key))
            numeric[key] = float(value)
            if not math.isfinite(numeric[key]):
                raise ValueError("{} must be finite".format(key))
        branch_count = configured["branch_count"]
        seed = configured["seed"]
        for key, value in (("branch_count", branch_count), ("seed", seed)):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError("{} must be an integer".format(key))
        for key, value in configured.items():
            metadata = preset.parameter_metadata[key]
            if metadata.minimum is not None and value < metadata.minimum:
                raise ValueError("{} must be at least {}".format(key, metadata.minimum))
            if metadata.maximum is not None and value > metadata.maximum:
                raise ValueError("{} must be at most {}".format(key, metadata.maximum))
        if numeric["root_radius"] > numeric["length"] * 0.2:
            raise ValueError("root_radius must not exceed 20% of length")
        if numeric["root_radius"] < numeric["length"] * 0.08:
            raise ValueError(
                "root_radius must be at least 8% of length at supported resolution"
            )
        minimum_resolution = int(preset.parameter_metadata["resolution"].minimum)
        if resolution < minimum_resolution:
            raise ValueError(
                "resolution must be at least {} for root".format(minimum_resolution)
            )
        return (
            numeric["length"], numeric["root_radius"], branch_count,
            numeric["branching"], numeric["spread"], numeric["taper"],
            numeric["gravity"], seed,
        )
