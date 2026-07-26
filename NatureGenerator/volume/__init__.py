"""Fusion-independent volumetric Gyroid generation pipeline."""

import hashlib
import math
import time

from .gyroid_field import GyroidVolumeField
from .thickened_field import (
    ThickenedGyroidField,
    combine_wall_surfaces,
    sample_thickened_band_grids,
)
from .boundary_closure import (
    BoundaryClosureError,
    boundary_paths,
    boundary_tolerance,
    classify_boundary_edges,
    close_rectangular_band_boundary,
    close_rectangular_boundary,
)
from .iso_surface import extract_isosurface
from .safety_policy import (
    SCALAR_BYTES_PER_SAMPLE,
    VOLUME_APPLY_MAX_SAMPLES,
    VOLUME_APPLY_MAX_CAP_TRIANGLES,
    VOLUME_PREVIEW_MAX_SAMPLES,
    VOLUME_PREVIEW_MAX_CAP_TRIANGLES,
    VolumeSafetyLimitError,
    VolumeSizeEstimate,
    enforce_volume_sample_limit,
    estimate_volume_size,
    estimate_cap_triangles,
    estimate_band_cap_triangles,
    validate_volume_size,
    validate_volume_request_size,
    validate_cap_complexity,
    validate_band_cap_complexity,
    validate_wall_thickness_resolution,
    volume_sample_limit,
)
from .scalar_field import Point3, ScalarField, evaluate
from .volume_request import (
    BoundaryMode,
    GeometryMode,
    GyroidVolumeRequest,
    VOLUME_PARAMETER_DEFINITIONS,
    VolumeExecutionContext,
    VolumeParameterDefinition,
)
from .volume_result import GyroidVolumeResult
from .voxel_grid import VoxelGrid


def canonical_volume_mesh_digest(mesh) -> str:
    """Return the deterministic indexed-mesh digest without another subsystem."""

    return hashlib.sha256(
        repr((mesh.vertices, mesh.faces)).encode("ascii")
    ).hexdigest()


def generate_gyroid_volume(request: GyroidVolumeRequest) -> GyroidVolumeResult:
    """Generate one deterministic Surface or Thickened Gyroid volume mesh."""

    if not isinstance(request, GyroidVolumeRequest):
        raise TypeError("request must be a GyroidVolumeRequest")
    estimate = validate_volume_request_size(request)
    validate_wall_thickness_resolution(request, estimate)
    started = time.perf_counter()
    surface_field = GyroidVolumeField(
        request.period,
        request.phase_x,
        request.phase_y,
        request.phase_z,
    )
    field = surface_field
    extraction_iso_value = request.iso_value
    band_grids = None
    if request.geometry_mode is GeometryMode.THICKENED:
        field = ThickenedGyroidField(
            surface_field, request.iso_value, request.wall_thickness
        )
        extraction_iso_value = 0.0
        band_grids = sample_thickened_band_grids(
            field, request.minimum, request.maximum, request.resolution
        )
        upper_grid, lower_grid = band_grids
        if max(
            max(upper_value, lower_value)
            for upper_value, lower_value in zip(
                upper_grid.values, lower_grid.values
            )
        ) < 0.0:
            raise VolumeSafetyLimitError(
                "Geometry Mode Thickened with Wall Thickness {:.6g} mm, "
                "Period {:.6g} mm, Iso Value {:.6g}, and resolution {} × {} × "
                "{} consumes the sampled scalar domain. Reduce Wall Thickness "
                "or adjust Period or Iso Value; {:,} spatial samples and two "
                "scalar grids were evaluated.".format(
                    request.wall_thickness,
                    request.period,
                    request.iso_value,
                    request.resolution_x,
                    request.resolution_y,
                    request.resolution_z,
                    estimate.sample_count,
                )
            )
        mesh = combine_wall_surfaces(
            extract_isosurface(upper_grid, 0.0),
            extract_isosurface(lower_grid, 0.0),
        )
        grid = upper_grid
    else:
        grid = VoxelGrid.sample(
            field, request.minimum, request.maximum, request.resolution
        )
        mesh = extract_isosurface(grid, extraction_iso_value)
    if not mesh.faces:
        raise VolumeSafetyLimitError(
            "Geometry Mode {} produced no triangles for Wall Thickness "
            "{:.6g} mm, Period {:.6g} mm, and resolution {} × {} × {}. "
            "Adjust Iso Value, Wall Thickness, Period, or resolution.".format(
                request.geometry_mode.value,
                request.wall_thickness,
                request.period,
                request.resolution_x,
                request.resolution_y,
                request.resolution_z,
            )
        )
    boundary_behavior = "open_at_bounds"
    if request.boundary_mode is BoundaryMode.CAP:
        cap_validator = (
            validate_band_cap_complexity
            if request.geometry_mode is GeometryMode.THICKENED
            else validate_cap_complexity
        )
        cap_validator(
            request.resolution_x,
            request.resolution_y,
            request.resolution_z,
            request.execution_context,
        )
        if band_grids is None:
            mesh = close_rectangular_boundary(
                mesh, grid, extraction_iso_value
            )
        else:
            mesh = close_rectangular_band_boundary(
                mesh, band_grids[0], band_grids[1]
            )
        boundary_behavior = "capped_at_bounds"
    statistics = mesh.statistics()
    if (
        request.geometry_mode is GeometryMode.THICKENED
        and not statistics.is_manifold
    ):
        raise VolumeSafetyLimitError(
            "Geometry Mode Thickened produced nonmanifold geometry for Wall "
            "Thickness {:.6g} mm, Period {:.6g} mm, and resolution {} × {} × "
            "{}. Increase resolution or adjust thickness, phase, or Iso "
            "Value.".format(
                request.wall_thickness,
                request.period,
                request.resolution_x,
                request.resolution_y,
                request.resolution_z,
            )
        )
    if (
        request.geometry_mode is GeometryMode.THICKENED
        and request.boundary_mode is BoundaryMode.CAP
        and (
            not statistics.is_watertight
            or not math.isfinite(statistics.signed_volume)
            or statistics.signed_volume <= 0.0
        )
    ):
        raise VolumeSafetyLimitError(
            "Geometry Mode Thickened with Boundary Mode Cap did not produce "
            "a finite positive enclosed volume for Wall Thickness {:.6g} mm, "
            "Period {:.6g} mm, and resolution {} × {} × {}. Increase "
            "resolution or adjust thickness, phase, or Iso Value.".format(
                request.wall_thickness,
                request.period,
                request.resolution_x,
                request.resolution_y,
                request.resolution_z,
            )
        )
    elapsed = time.perf_counter() - started
    return GyroidVolumeResult(
        mesh=mesh,
        statistics=statistics,
        digest=canonical_volume_mesh_digest(mesh),
        sample_count=estimate.sample_count,
        cell_count=estimate.cell_count,
        scalar_bytes=estimate.scalar_bytes,
        elapsed_time=elapsed,
        boundary_behavior=boundary_behavior,
    )


__all__ = [
    "GyroidVolumeField",
    "BoundaryClosureError",
    "BoundaryMode",
    "GeometryMode",
    "GyroidVolumeRequest",
    "GyroidVolumeResult",
    "ThickenedGyroidField",
    "Point3",
    "SCALAR_BYTES_PER_SAMPLE",
    "ScalarField",
    "VOLUME_APPLY_MAX_SAMPLES",
    "VOLUME_APPLY_MAX_CAP_TRIANGLES",
    "VOLUME_PARAMETER_DEFINITIONS",
    "VOLUME_PREVIEW_MAX_SAMPLES",
    "VOLUME_PREVIEW_MAX_CAP_TRIANGLES",
    "VolumeExecutionContext",
    "VolumeParameterDefinition",
    "VolumeSafetyLimitError",
    "VolumeSizeEstimate",
    "VoxelGrid",
    "canonical_volume_mesh_digest",
    "estimate_volume_size",
    "estimate_cap_triangles",
    "estimate_band_cap_triangles",
    "enforce_volume_sample_limit",
    "evaluate",
    "extract_isosurface",
    "generate_gyroid_volume",
    "validate_volume_size",
    "validate_volume_request_size",
    "validate_cap_complexity",
    "validate_band_cap_complexity",
    "validate_wall_thickness_resolution",
    "volume_sample_limit",
    "boundary_paths",
    "boundary_tolerance",
    "classify_boundary_edges",
    "close_rectangular_band_boundary",
    "close_rectangular_boundary",
    "combine_wall_surfaces",
    "sample_thickened_band_grids",
]
