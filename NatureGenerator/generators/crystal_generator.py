"""Deterministic faceted generator for a stylized prismatic crystal."""

import math
from typing import Any, Dict, List, Tuple

from core.mesh import TriangleMesh
from presets import PresetFactory

from .crystal_families import (
    CLASSIC_CRYSTAL_FAMILY,
    CrystalFamilyRegistry,
)
from .generator import InvalidGeneratorParameters, MeshGenerator
from .request import GenerationRequest
from .value_noise import DeterministicValueNoise


Point3 = Tuple[float, float, float]
Face = Tuple[int, int, int]


class CrystalGenerator(MeshGenerator):
    """Generate one closed elongated prism with a tapered termination."""

    _PARAMETER_IDS = frozenset((
        "length", "width", "facet_count", "taper", "irregularity", "seed",
    ))

    @property
    def preset_id(self) -> str:
        return "crystal"

    @property
    def generator_id(self) -> str:
        return "crystal"

    @property
    def require_watertight(self) -> bool:
        return True

    def generate(self, request: GenerationRequest) -> TriangleMesh:
        if not isinstance(request, GenerationRequest):
            raise TypeError("request must be a GenerationRequest")
        if request.preset_id != self.preset_id:
            raise InvalidGeneratorParameters(
                "request preset_id does not match 'crystal'"
            )
        preset = PresetFactory.get(self.preset_id)
        configured: Dict[str, Any] = dict(preset.default_parameters)
        try:
            family = (
                CrystalFamilyRegistry.get(request.family_id)
                if request.family_id else CLASSIC_CRYSTAL_FAMILY
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
                "invalid crystal parameters: {}".format(detail)
            )

        try:
            length = self._number(configured["length"], "length")
            width = self._number(configured["width"], "width")
            taper = self._number(configured["taper"], "taper")
            irregularity = self._number(
                configured["irregularity"], "irregularity"
            )
            facet_count = configured["facet_count"]
            seed = configured["seed"]
            if isinstance(facet_count, bool) or not isinstance(facet_count, int):
                raise TypeError("facet_count must be an integer")
            if isinstance(seed, bool) or not isinstance(seed, int):
                raise TypeError("seed must be an integer")
            for key, value in configured.items():
                metadata = preset.parameter_metadata[key]
                if metadata.minimum is not None and value < metadata.minimum:
                    raise ValueError(
                        "{} must be at least {}".format(key, metadata.minimum)
                    )
                if metadata.maximum is not None and value > metadata.maximum:
                    raise ValueError(
                        "{} must be at most {}".format(key, metadata.maximum)
                    )
            resolution_metadata = preset.parameter_metadata["resolution"]
            if request.resolution < resolution_metadata.minimum:
                raise ValueError(
                    "resolution must be at least {} for crystal".format(
                        int(resolution_metadata.minimum)
                    )
                )
            if request.resolution > resolution_metadata.maximum:
                raise ValueError(
                    "resolution must be at most {} for crystal".format(
                        int(resolution_metadata.maximum)
                    )
                )
        except (TypeError, ValueError, ArithmeticError, OverflowError) as error:
            raise InvalidGeneratorParameters(
                "invalid crystal parameters: {}".format(error)
            ) from error

        return self._build_mesh(
            length, width, facet_count, taper, irregularity, seed,
            request.resolution,
        )

    @staticmethod
    def _build_mesh(
        length: float,
        width: float,
        facet_count: int,
        taper: float,
        irregularity: float,
        seed: int,
        resolution: int,
    ) -> TriangleMesh:
        noise = DeterministicValueNoise(seed)
        base_radius = width * 0.5
        shoulder_z = length * (1.0 - taper)
        ring_count = max(3, (resolution - 9) // 4)
        angle_offset = noise._lattice(5, 11, 17) * math.pi / facet_count
        radii = tuple(
            base_radius * (
                1.0
                + irregularity * 0.32
                * noise._lattice(index + 23, index * 7 + 3, 41)
            )
            for index in range(facet_count)
        )

        vertices: List[Point3] = []
        for ring in range(ring_count):
            progress = ring / (ring_count - 1)
            z = shoulder_z * progress
            ring_variation = irregularity * 0.035 * noise.sample(
                progress * 1.7 + 2.3, 4.1, -6.7
            )
            twist = irregularity * 0.055 * math.sin(
                progress * math.pi
            ) * noise._lattice(59, 61, 67)
            center_x = (
                irregularity * width * 0.025
                * noise.sample(progress * 1.3 + 8.1, -3.5, 2.7)
            )
            center_y = (
                irregularity * width * 0.025
                * noise.sample(-4.9, progress * 1.3 + 6.2, 9.4)
            )
            for facet in range(facet_count):
                angle = (
                    angle_offset
                    + 2.0 * math.pi * facet / facet_count
                    + twist
                )
                radius = radii[facet] * (1.0 + ring_variation)
                vertices.append((
                    center_x + radius * math.cos(angle),
                    center_y + radius * math.sin(angle),
                    z,
                ))

        bottom_center = len(vertices)
        vertices.append((0.0, 0.0, 0.0))
        tip_shift = irregularity * width * 0.07
        tip = len(vertices)
        vertices.append((
            tip_shift * noise._lattice(71, 73, 79),
            tip_shift * noise._lattice(83, 89, 97),
            length,
        ))

        faces: List[Face] = []
        for facet in range(facet_count):
            next_facet = (facet + 1) % facet_count
            faces.append((bottom_center, next_facet, facet))
        for ring in range(ring_count - 1):
            lower = ring * facet_count
            upper = (ring + 1) * facet_count
            for facet in range(facet_count):
                next_facet = (facet + 1) % facet_count
                faces.append((
                    lower + facet,
                    lower + next_facet,
                    upper + next_facet,
                ))
                faces.append((
                    lower + facet,
                    upper + next_facet,
                    upper + facet,
                ))
        shoulder = (ring_count - 1) * facet_count
        for facet in range(facet_count):
            next_facet = (facet + 1) % facet_count
            faces.append((shoulder + facet, shoulder + next_facet, tip))
        return TriangleMesh(tuple(vertices), tuple(faces))

    @staticmethod
    def _number(value: Any, name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("{} must be numeric".format(name))
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("{} must be finite".format(name))
        return result
