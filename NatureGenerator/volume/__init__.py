"""Fusion-independent volumetric Gyroid generation pipeline."""

import hashlib
import math
import time

from .cost_estimate import VolumeCostEstimate, estimate_volume_cost
from .domain_sizing import (
    DOMAIN_CELL_COUNT_MAX,
    DOMAIN_CELL_COUNT_MIN,
    DOMAIN_DIMENSION_MAX_MM,
    DOMAIN_DIMENSION_MIN_MM,
    DomainDefinition,
    DomainMode,
    DomainSizingError,
    resolve_domain,
)
from .gyroid_field import GyroidVolumeField
from .thickened_field import (
    ThickenedGyroidField,
    ThickenedTPMSField,
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
    validate_volume_cost,
    volume_sample_limit,
)
from .scalar_field import Point3, ScalarField, evaluate
from .volume_request import (
    BoundaryMode,
    GeometryMode,
    GyroidVolumeRequest,
    PreviewQuality,
    TPMSType,
    TPMSVolumeRequest,
    VOLUME_PARAMETER_DEFINITIONS,
    VolumeExecutionContext,
    VolumeParameterDefinition,
)
from .volume_result import GyroidVolumeResult, TPMSVolumeResult
from .tpms_field import (
    AnalyticalTPMSField,
    TPMSFieldFactory,
    TPMS_NORMALIZATION_FACTORS,
    TPMS_TYPE_ORDER,
)
from .resolution_policy import (
    PREVIEW_QUALITY_SCALES,
    VolumeResolutionSelection,
    select_volume_resolution,
)
from .timings import VolumeGenerationTimings
from .voxel_grid import VoxelGrid


def canonical_volume_mesh_digest(mesh) -> str:
    """Return the deterministic indexed-mesh digest without another subsystem."""

    return hashlib.sha256(
        repr((mesh.vertices, mesh.faces)).encode("ascii")
    ).hexdigest()


def generate_tpms_volume(request: TPMSVolumeRequest) -> TPMSVolumeResult:
    """Generate one deterministic Surface or Thickened TPMS volume mesh."""

    if not isinstance(request, GyroidVolumeRequest):
        raise TypeError("request must be a GyroidVolumeRequest")
    total_started = time.perf_counter()
    stage_started = time.perf_counter()
    estimate = estimate_volume_cost(request)
    validate_volume_cost(request, estimate)
    validate_wall_thickness_resolution(request, estimate)
    validation_and_estimation = time.perf_counter() - stage_started
    effective_resolution = estimate.effective_resolution

    stage_started = time.perf_counter()
    surface_field = TPMSFieldFactory.create(
        request.tpms_type,
        request.period,
        request.phase_x,
        request.phase_y,
        request.phase_z,
    )
    field = surface_field
    extraction_iso_value = request.iso_value
    band_grids = None
    if request.geometry_mode is GeometryMode.THICKENED:
        field = ThickenedTPMSField(
            surface_field, request.iso_value, request.wall_thickness
        )
        extraction_iso_value = 0.0
        band_grids = sample_thickened_band_grids(
            field, request.minimum, request.maximum, effective_resolution
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
                    effective_resolution[0],
                    effective_resolution[1],
                    effective_resolution[2],
                    estimate.scalar_samples_per_field,
                )
            )
        scalar_field_sampling = time.perf_counter() - stage_started
        stage_started = time.perf_counter()
        mesh = combine_wall_surfaces(
            extract_isosurface(upper_grid, 0.0),
            extract_isosurface(lower_grid, 0.0),
        )
        grid = upper_grid
    else:
        grid = VoxelGrid.sample(
            field, request.minimum, request.maximum, effective_resolution
        )
        scalar_field_sampling = time.perf_counter() - stage_started
        stage_started = time.perf_counter()
        mesh = extract_isosurface(grid, extraction_iso_value)
    iso_surface_extraction = time.perf_counter() - stage_started
    if not mesh.faces:
        raise VolumeSafetyLimitError(
            "Geometry Mode {} produced no triangles for Wall Thickness "
            "{:.6g} mm, Period {:.6g} mm, and resolution {} × {} × {}. "
            "Adjust Iso Value, Wall Thickness, Period, or resolution.".format(
                request.geometry_mode.value,
                request.wall_thickness,
                request.period,
                effective_resolution[0],
                effective_resolution[1],
                effective_resolution[2],
            )
        )
    boundary_behavior = "open_at_bounds"
    boundary_closure = 0.0
    if request.boundary_mode is BoundaryMode.CAP:
        stage_started = time.perf_counter()
        if band_grids is None:
            mesh = close_rectangular_boundary(
                mesh, grid, extraction_iso_value
            )
        else:
            mesh = close_rectangular_band_boundary(
                mesh, band_grids[0], band_grids[1]
            )
        boundary_closure = time.perf_counter() - stage_started
        boundary_behavior = "capped_at_bounds"
    stage_started = time.perf_counter()
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
                effective_resolution[0],
                effective_resolution[1],
                effective_resolution[2],
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
                effective_resolution[0],
                effective_resolution[1],
                effective_resolution[2],
            )
        )
    geometry_validation = time.perf_counter() - stage_started
    elapsed = time.perf_counter() - total_started
    timings = VolumeGenerationTimings(
        validation_and_estimation=validation_and_estimation,
        scalar_field_sampling=scalar_field_sampling,
        iso_surface_extraction=iso_surface_extraction,
        boundary_closure=boundary_closure,
        geometry_validation=geometry_validation,
        total_core=elapsed,
    )
    return GyroidVolumeResult(
        mesh=mesh,
        statistics=statistics,
        digest=canonical_volume_mesh_digest(mesh),
        sample_count=estimate.scalar_samples_per_field,
        cell_count=estimate.cell_count,
        scalar_bytes=estimate.estimated_scalar_grid_bytes,
        elapsed_time=elapsed,
        boundary_behavior=boundary_behavior,
        cost_estimate=estimate,
        timings=timings,
        domain=request.domain,
    )


def generate_gyroid_volume(request: GyroidVolumeRequest) -> GyroidVolumeResult:
    """Backward-compatible entry point using the shared TPMS pipeline."""

    return generate_tpms_volume(request)


__all__ = [
    "GyroidVolumeField",
    "BoundaryClosureError",
    "BoundaryMode",
    "GeometryMode",
    "DomainMode",
    "DomainDefinition",
    "DomainSizingError",
    "PreviewQuality",
    "TPMSType",
    "TPMSVolumeRequest",
    "TPMSVolumeResult",
    "GyroidVolumeRequest",
    "GyroidVolumeResult",
    "ThickenedGyroidField",
    "ThickenedTPMSField",
    "AnalyticalTPMSField",
    "TPMSFieldFactory",
    "TPMS_NORMALIZATION_FACTORS",
    "TPMS_TYPE_ORDER",
    "Point3",
    "SCALAR_BYTES_PER_SAMPLE",
    "ScalarField",
    "VOLUME_APPLY_MAX_SAMPLES",
    "VOLUME_APPLY_MAX_CAP_TRIANGLES",
    "VOLUME_PARAMETER_DEFINITIONS",
    "VOLUME_PREVIEW_MAX_SAMPLES",
    "VOLUME_PREVIEW_MAX_CAP_TRIANGLES",
    "DOMAIN_CELL_COUNT_MAX",
    "DOMAIN_CELL_COUNT_MIN",
    "DOMAIN_DIMENSION_MAX_MM",
    "DOMAIN_DIMENSION_MIN_MM",
    "VolumeExecutionContext",
    "VolumeParameterDefinition",
    "VolumeSafetyLimitError",
    "VolumeCostEstimate",
    "VolumeGenerationTimings",
    "VolumeResolutionSelection",
    "VolumeSizeEstimate",
    "VoxelGrid",
    "canonical_volume_mesh_digest",
    "estimate_volume_size",
    "estimate_volume_cost",
    "estimate_cap_triangles",
    "estimate_band_cap_triangles",
    "enforce_volume_sample_limit",
    "evaluate",
    "extract_isosurface",
    "generate_gyroid_volume",
    "generate_tpms_volume",
    "validate_volume_size",
    "validate_volume_request_size",
    "validate_cap_complexity",
    "validate_band_cap_complexity",
    "validate_wall_thickness_resolution",
    "validate_volume_cost",
    "volume_sample_limit",
    "boundary_paths",
    "boundary_tolerance",
    "classify_boundary_edges",
    "close_rectangular_band_boundary",
    "close_rectangular_boundary",
    "combine_wall_surfaces",
    "sample_thickened_band_grids",
    "PREVIEW_QUALITY_SCALES",
    "select_volume_resolution",
    "resolve_domain",
]
