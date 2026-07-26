"""Fusion-independent volumetric Gyroid generation pipeline."""

import hashlib
import time

from .gyroid_field import GyroidVolumeField
from .iso_surface import extract_isosurface
from .safety_policy import (
    SCALAR_BYTES_PER_SAMPLE,
    VOLUME_APPLY_MAX_SAMPLES,
    VOLUME_PREVIEW_MAX_SAMPLES,
    VolumeSafetyLimitError,
    VolumeSizeEstimate,
    enforce_volume_sample_limit,
    estimate_volume_size,
    validate_volume_size,
    volume_sample_limit,
)
from .scalar_field import Point3, ScalarField, evaluate
from .volume_request import (
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
    elapsed = time.perf_counter() - started
    return GyroidVolumeResult(
        mesh=mesh,
        statistics=mesh.statistics(),
        digest=canonical_volume_mesh_digest(mesh),
        sample_count=estimate.sample_count,
        cell_count=estimate.cell_count,
        scalar_bytes=estimate.scalar_bytes,
        elapsed_time=elapsed,
    )


__all__ = [
    "GyroidVolumeField",
    "GyroidVolumeRequest",
    "GyroidVolumeResult",
    "Point3",
    "SCALAR_BYTES_PER_SAMPLE",
    "ScalarField",
    "VOLUME_APPLY_MAX_SAMPLES",
    "VOLUME_PARAMETER_DEFINITIONS",
    "VOLUME_PREVIEW_MAX_SAMPLES",
    "VolumeExecutionContext",
    "VolumeParameterDefinition",
    "VolumeSafetyLimitError",
    "VolumeSizeEstimate",
    "VoxelGrid",
    "canonical_volume_mesh_digest",
    "estimate_volume_size",
    "enforce_volume_sample_limit",
    "evaluate",
    "extract_isosurface",
    "generate_gyroid_volume",
    "validate_volume_size",
    "volume_sample_limit",
]
