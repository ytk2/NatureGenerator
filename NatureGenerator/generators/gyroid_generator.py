"""Complete pure-Python runtime pipeline for gyroid presets."""

import math
from time import perf_counter
from typing import Any, Mapping, Optional, Tuple

from assets import GeneratedAssetFactory
from core.marching_tetrahedra import extract_isosurface
from core.mesh_validator import MeshValidator
from core.voxel_grid import VoxelGrid
from presets.preset import NaturePreset

from .generator import (
    Generator,
    InvalidGeneratorParameters,
    MeshExtractionError,
    UnavailablePresetError,
)
from .gyroid import GyroidField
from .result import GeneratorResult
from .request import DEFAULT_RESOLUTION, validate_resolution


class GyroidGenerator(Generator):
    """Generate a finite sampled gyroid sheet from preset parameters."""

    _PARAMETER_IDS = frozenset(("cell_size", "thickness"))

    @property
    def generator_id(self) -> str:
        return "gyroid"

    def generate(
        self,
        preset: NaturePreset,
        parameters: Optional[Mapping[str, Any]] = None,
        resolution: int = DEFAULT_RESOLUTION,
    ) -> GeneratorResult:
        """Run field construction, sampling, extraction, and validation."""

        started = perf_counter()
        try:
            resolution = validate_resolution(resolution)
        except (TypeError, ValueError) as error:
            raise InvalidGeneratorParameters(str(error)) from error
        if not isinstance(preset, NaturePreset):
            raise TypeError("preset must be a NaturePreset")
        if not preset.available:
            raise UnavailablePresetError(
                "preset {!r} is unavailable: {}".format(
                    preset.preset_id, preset.unavailable_reason
                )
            )
        if preset.generator_id != self.generator_id:
            raise InvalidGeneratorParameters(
                "preset generator_id {!r} does not match {!r}".format(
                    preset.generator_id, self.generator_id
                )
            )

        configured = dict(preset.default_parameters)
        configured.pop("resolution", None)
        if parameters is not None:
            if not isinstance(parameters, Mapping):
                raise InvalidGeneratorParameters("parameter overrides must be a mapping")
            configured.update(parameters)
        unknown = set(configured) - self._PARAMETER_IDS
        missing = self._PARAMETER_IDS - set(configured)
        if unknown:
            raise InvalidGeneratorParameters(
                "unknown gyroid parameters: {}".format(sorted(unknown))
            )
        if missing:
            raise InvalidGeneratorParameters(
                "missing gyroid parameters: {}".format(sorted(missing))
            )

        try:
            cell_size = self._finite_number(configured["cell_size"], "cell_size")
            thickness = self._finite_number(configured["thickness"], "thickness")
            self._validate_metadata_bounds(preset, configured)
            field = GyroidField(cell_size=cell_size, thickness=thickness)
        except (TypeError, ValueError, OverflowError) as error:
            raise InvalidGeneratorParameters(
                "invalid gyroid parameters: {}".format(error)
            ) from error

        half_extent = cell_size / 2.0
        minimum = (-half_extent, -half_extent, -half_extent)
        maximum = (half_extent, half_extent, half_extent)
        try:
            shape = (resolution, resolution, resolution)
            grid = VoxelGrid.sample(field, minimum, maximum, shape)
            mesh = extract_isosurface(grid)
        except (TypeError, ValueError, ArithmeticError) as error:
            raise MeshExtractionError(
                "gyroid mesh extraction failed: {}".format(error)
            ) from error

        if not mesh.faces:
            raise MeshExtractionError(
                "gyroid mesh extraction produced no triangles; adjust thickness"
            )
        validation = MeshValidator(require_watertight=False).validate(mesh)
        if not validation.valid:
            errors = tuple(
                issue.message
                for issue in validation.issues
                if issue.severity == "error"
            )
            raise MeshExtractionError(
                "gyroid mesh validation failed: {}".format("; ".join(errors))
            )
        warnings = tuple(
            "{}: {} ({})".format(issue.code, issue.message, issue.count)
            for issue in validation.issues
            if issue.severity == "warning"
        )
        elapsed = perf_counter() - started
        return GeneratorResult(
            mesh=mesh,
            statistics=validation.statistics,
            warnings=warnings,
            generator_id=self.generator_id,
            preset_id=preset.preset_id,
            elapsed_time=elapsed,
            asset=GeneratedAssetFactory.create(
                mesh=mesh,
                preset=preset,
                generator_id=self.generator_id,
                parameters=dict(configured, resolution=resolution),
            ),
        )

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
        preset: NaturePreset, parameters: Mapping[str, Any]
    ) -> None:
        for parameter_id, metadata in preset.parameter_metadata.items():
            if parameter_id not in parameters:
                continue
            value = parameters[parameter_id]
            if metadata.minimum is not None and value < metadata.minimum:
                raise ValueError(
                    "{} must be at least {}".format(
                        parameter_id, metadata.minimum
                    )
                )
            if metadata.maximum is not None and value > metadata.maximum:
                raise ValueError(
                    "{} must be at most {}".format(
                        parameter_id, metadata.maximum
                    )
                )
