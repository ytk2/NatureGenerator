"""Deterministic dependency-free multi-scale boulder generation."""

import math
from typing import Any

from core.marching_tetrahedra import extract_isosurface
from core.mesh import TriangleMesh
from core.voxel_grid import VoxelGrid
from presets import PresetFactory

from .generator import InvalidGeneratorParameters, MeshExtractionError, MeshGenerator
from .rock_families import (
    DEFAULT_ROCK_FAMILY,
    RockFamilyDefinition,
    RockFamilyRegistry,
)
from .rock_pipeline import (
    RockGenerationContext,
    build_facet_layout,
    build_macro_shape,
    build_surface_detail,
)
from .request import GenerationRequest
from .value_noise import DeterministicValueNoise


class _RockField:
    """Faceted ellipsoid field with FBM, ridges, and a grounded lower face."""

    def __init__(
        self,
        size: float,
        roughness: float,
        seed: int,
        family: RockFamilyDefinition = DEFAULT_ROCK_FAMILY,
    ) -> None:
        self.context = RockGenerationContext.create(size, roughness, seed)
        self.noise = DeterministicValueNoise(seed)
        self.macro_shape = build_macro_shape(
            self.context, self.noise, family.macro
        )
        self.facet_layout = build_facet_layout(
            self.context, self.noise, family.facets
        )
        self.surface_detail = build_surface_detail(
            self.context, family.surface
        )

    def __call__(self, x: float, y: float, z: float) -> float:
        normalized = self.macro_shape.normalized_point(x, y, z)
        nx, ny, nz = normalized
        radius = math.sqrt(nx * nx + ny * ny + nz * nz)
        if radius == 0.0:
            return -1.0
        direction = (nx / radius, ny / radius, nz / radius)
        macro_terms = self.macro_shape.deformation_terms(
            normalized, direction, self.noise
        )
        detail_terms = self.surface_detail.deformation_terms(
            normalized, self.noise
        )
        variation = (
            macro_terms[0] + macro_terms[1] + detail_terms[0] + detail_terms[1]
        )
        field = radius - (1.0 + variation)
        field = self.facet_layout.apply(field, normalized)
        return self.macro_shape.apply_ground(field, nz)


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
        family = (
            RockFamilyRegistry.get(request.family_id)
            if request.family_id else DEFAULT_ROCK_FAMILY
        )
        return self._generate(request, family)

    def generate_family(
        self, request: GenerationRequest, family_id: str
    ) -> TriangleMesh:
        """Generate an internal family through the same three-stage pipeline."""

        return self._generate(request, RockFamilyRegistry.get(family_id))

    def _generate(
        self,
        request: GenerationRequest,
        family: RockFamilyDefinition,
    ) -> TriangleMesh:
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
            field = _RockField(size, roughness, seed, family)
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
