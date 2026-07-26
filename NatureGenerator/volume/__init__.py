"""Fusion-independent volumetric Gyroid generation pipeline."""

import hashlib
import time

from .gyroid_field import GyroidVolumeField
from .boundary_closure import (
    BoundaryClosureError,
    boundary_paths,
    boundary_tolerance,
    classify_boundary_edges,
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
    validate_volume_size,
    validate_cap_complexity,
    volume_sample_limit,
)
from .scalar_field import Point3, ScalarField, evaluate
from .volume_request import (
    BoundaryMode,
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
    """Sample and extract one bounded, open-at-bounds Gyroid iso-surface."""

    if not isinstance(request, GyroidVolumeRequest):
        raise TypeError("request must be a GyroidVolumeRequest")
    estimate = validate_volume_size(
        request.resolution_x,
        request.resolution_y,
        request.resolution_z,
        request.execution_context,
    )
    started = time.perf_counter()
    field = GyroidVolumeField(
        request.period,
        request.phase_x,
        request.phase_y,
        request.phase_z,
    )
    grid = VoxelGrid.sample(
        field, request.minimum, request.maximum, request.resolution
    )
    mesh = extract_isosurface(grid, request.iso_value)
    boundary_behavior = "open_at_bounds"
    if request.boundary_mode is BoundaryMode.CAP:
        validate_cap_complexity(
            request.resolution_x,
            request.resolution_y,
            request.resolution_z,
            request.execution_context,
        )
        mesh = close_rectangular_boundary(mesh, grid, request.iso_value)
        boundary_behavior = "capped_at_bounds"
    elapsed = time.perf_counter() - started
    return GyroidVolumeResult(
        mesh=mesh,
        statistics=mesh.statistics(),
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
    "GyroidVolumeRequest",
    "GyroidVolumeResult",
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
    "enforce_volume_sample_limit",
    "evaluate",
    "extract_isosurface",
    "generate_gyroid_volume",
    "validate_volume_size",
    "validate_cap_complexity",
    "volume_sample_limit",
    "boundary_paths",
    "boundary_tolerance",
    "classify_boundary_edges",
    "close_rectangular_boundary",
]
