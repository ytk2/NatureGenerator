"""Deterministic implicit generator for a stylized long bone."""

import math
from typing import Any, Tuple

from core.marching_tetrahedra import extract_isosurface
from core.mesh import TriangleMesh
from core.voxel_grid import VoxelGrid
from presets import PresetFactory

from .bone_families import BoneFamilyRegistry, CLASSIC_BONE_FAMILY
from .generator import InvalidGeneratorParameters, MeshExtractionError, MeshGenerator
from .request import GenerationRequest
from .value_noise import DeterministicValueNoise


Point3 = Tuple[float, float, float]


class _BoneField:
    """Smooth union of a curved tapered shaft and asymmetric end lobes."""

    def __init__(
        self,
        length: float,
        shaft_radius: float,
        end_scale: float,
        curvature: float,
        asymmetry: float,
        surface_detail: float,
        seed: int,
    ) -> None:
        self.length = length
        self.shaft_radius = shaft_radius
        self.end_scale = end_scale
        self.curvature = curvature
        self.asymmetry = asymmetry
        self.surface_detail = surface_detail
        self.seed = seed
        self._noise = DeterministicValueNoise(seed)
        self._seed_bias = self._noise._lattice(17, 31, 47)
        self._end_radius = shaft_radius * end_scale
        self._ground_z = -self._end_radius * 0.88

    @staticmethod
    def _smooth_min(a: float, b: float, blend: float) -> float:
        difference = abs(a - b)
        if difference >= blend:
            return min(a, b)
        amount = (blend - difference) / blend
        return min(a, b) - blend * amount * amount * 0.25

    @staticmethod
    def _ellipsoid(
        point: Point3, center: Point3, radii: Point3
    ) -> float:
        normalized = math.sqrt(sum(
            ((point[index] - center[index]) / radii[index]) ** 2
            for index in range(3)
        ))
        return (normalized - 1.0) * min(radii)

    def __call__(self, x: float, y: float, z: float) -> float:
        half_length = self.length * 0.5
        normalized_x = max(-1.0, min(1.0, x / (half_length * 0.90)))
        middle_weight = 1.0 - normalized_x * normalized_x
        center_y = (
            self.curvature * self.shaft_radius * 0.72 * middle_weight
            + self.asymmetry * self.shaft_radius * 0.12 * normalized_x
        )
        center_z = (
            self.curvature * self.shaft_radius * 0.18
            * math.sin(math.pi * normalized_x)
            + self.asymmetry * self.shaft_radius * 0.08 * middle_weight
        )
        shaft_radius = self.shaft_radius * (
            0.70 + 0.30 * abs(normalized_x) ** 1.65
        )
        axial = max(abs(x) - half_length * 0.78, 0.0)
        shaft = math.sqrt(
            axial * axial
            + (y - center_y) ** 2
            + ((z - center_z) / 0.92) ** 2
        ) - shaft_radius

        end_x = self.length * 0.40
        asymmetry_shift = self.asymmetry * self.shaft_radius * 0.30
        seed_shift = self._seed_bias * self.asymmetry * self.shaft_radius * 0.18
        left_center = (
            -end_x,
            asymmetry_shift + seed_shift,
            -self.curvature * self.shaft_radius * 0.10,
        )
        right_center = (
            end_x,
            -asymmetry_shift * 0.55,
            self.curvature * self.shaft_radius * 0.12 + seed_shift * 0.35,
        )
        left_scale = 1.0 + self.asymmetry * 0.08
        right_scale = 1.0 - self.asymmetry * 0.05
        end_radius = self._end_radius
        left = self._ellipsoid(
            (x, y, z),
            left_center,
            (
                end_radius * 0.82 * left_scale,
                end_radius * 0.98 * left_scale,
                end_radius * 0.86,
            ),
        )
        right = self._ellipsoid(
            (x, y, z),
            right_center,
            (
                end_radius * 0.88 * right_scale,
                end_radius * 0.90 * right_scale,
                end_radius * 0.94,
            ),
        )

        lobe_offset = end_radius * (0.30 + 0.10 * self.asymmetry)
        left_lobe = self._ellipsoid(
            (x, y, z),
            (
                left_center[0] - end_radius * 0.10,
                left_center[1] + lobe_offset,
                left_center[2] + end_radius * 0.08,
            ),
            (end_radius * 0.62, end_radius * 0.68, end_radius * 0.58),
        )
        right_lobe = self._ellipsoid(
            (x, y, z),
            (
                right_center[0] + end_radius * 0.08,
                right_center[1] - lobe_offset * 0.88,
                right_center[2] - end_radius * 0.05,
            ),
            (end_radius * 0.66, end_radius * 0.63, end_radius * 0.65),
        )

        blend = self.shaft_radius * 0.42
        field = shaft
        for primitive in (left, right, left_lobe, right_lobe):
            field = self._smooth_min(field, primitive, blend)

        if self.surface_detail > 0.0:
            frequency = 1.0 / (self.shaft_radius * 1.25)
            detail = self._noise.sample(
                x * frequency + 3.7,
                y * frequency - 5.1,
                z * frequency + 7.9,
            )
            field += detail * self.surface_detail * self.shaft_radius * 0.10

        # Intersect with a shallow half-space to provide a small stable base.
        return max(field, self._ground_z - z)

    def bounds(self) -> Tuple[Point3, Point3]:
        margin = max(self.shaft_radius * 0.55, 4.0)
        x_extent = self.length * 0.43 + self._end_radius * 0.95 + margin
        y_extent = self._end_radius * 1.45 + margin
        z_min = self._ground_z - margin
        z_max = self._end_radius * 1.12 + margin
        return (
            (-x_extent, -y_extent, z_min),
            (x_extent, y_extent, z_max),
        )


class BoneGenerator(MeshGenerator):
    """Generate one closed stylized long bone through shared extraction."""

    _PARAMETER_IDS = frozenset((
        "length", "shaft_radius", "end_scale", "curvature", "asymmetry",
        "surface_detail", "seed",
    ))

    @property
    def preset_id(self) -> str:
        return "bone"

    @property
    def generator_id(self) -> str:
        return "bone"

    @property
    def require_watertight(self) -> bool:
        return True

    def generate(self, request: GenerationRequest) -> TriangleMesh:
        if not isinstance(request, GenerationRequest):
            raise TypeError("request must be a GenerationRequest")
        if request.preset_id != self.preset_id:
            raise InvalidGeneratorParameters("request preset_id does not match 'bone'")
        preset = PresetFactory.get(self.preset_id)
        configured = dict(preset.default_parameters)
        try:
            family = (
                BoneFamilyRegistry.get(request.family_id)
                if request.family_id else CLASSIC_BONE_FAMILY
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
            raise InvalidGeneratorParameters("invalid bone parameters: {}".format(detail))

        try:
            values = {}
            for key in (
                "length", "shaft_radius", "end_scale", "curvature",
                "asymmetry", "surface_detail",
            ):
                values[key] = self._number(configured[key], key)
            seed = configured["seed"]
            if isinstance(seed, bool) or not isinstance(seed, int):
                raise TypeError("seed must be an integer")
            for key, value in configured.items():
                metadata = preset.parameter_metadata[key]
                if metadata.minimum is not None and value < metadata.minimum:
                    raise ValueError("{} must be at least {}".format(
                        key, metadata.minimum
                    ))
                if metadata.maximum is not None and value > metadata.maximum:
                    raise ValueError("{} must be at most {}".format(
                        key, metadata.maximum
                    ))
            resolution_metadata = preset.parameter_metadata["resolution"]
            if request.resolution < resolution_metadata.minimum:
                raise ValueError(
                    "resolution must be at least {} for bone".format(
                        int(resolution_metadata.minimum)
                    )
                )
            field = _BoneField(seed=seed, **values)
        except (TypeError, ValueError, ArithmeticError, OverflowError) as error:
            raise InvalidGeneratorParameters(
                "invalid bone parameters: {}".format(error)
            ) from error

        try:
            minimum, maximum = field.bounds()
            mesh = extract_isosurface(VoxelGrid.sample(
                field, minimum, maximum, (request.resolution,) * 3
            ))
        except (TypeError, ValueError, ArithmeticError, OverflowError) as error:
            raise MeshExtractionError(
                "bone mesh extraction failed: {}".format(error)
            ) from error
        if not mesh.faces:
            raise MeshExtractionError("bone mesh extraction produced no triangles")
        return mesh

    @staticmethod
    def _number(value: Any, name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("{} must be numeric".format(name))
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("{} must be finite".format(name))
        return result
