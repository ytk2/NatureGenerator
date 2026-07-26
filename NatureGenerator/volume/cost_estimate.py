"""Immutable, pre-allocation TPMS Volume generation cost estimates."""

from dataclasses import dataclass
from typing import Optional, Tuple

from .resolution_policy import select_volume_resolution
from .volume_request import (
    BoundaryMode,
    GeometryMode,
    GyroidVolumeRequest,
    PreviewQuality,
    TPMSType,
    VolumeExecutionContext,
)


SCALAR_BYTES_PER_SAMPLE = 8
REGULAR_GRID_METADATA_BYTES = 72


@dataclass(frozen=True)
class VolumeCostEstimate:
    final_resolution: Tuple[int, int, int]
    effective_resolution: Tuple[int, int, int]
    scalar_samples_per_field: int
    total_scalar_samples: int
    cell_count: int
    stored_scalar_field_count: int
    estimated_scalar_grid_bytes: int
    estimated_grid_metadata_bytes: int
    estimated_cap_triangles: int
    geometry_mode: GeometryMode
    boundary_mode: BoundaryMode
    preview_quality: Optional[PreviewQuality]
    execution_context: VolumeExecutionContext
    active_sample_limit: int
    active_cap_triangle_limit: int
    tpms_type: TPMSType

    @property
    def estimated_known_bytes(self) -> int:
        return (
            self.estimated_scalar_grid_bytes
            + self.estimated_grid_metadata_bytes
        )


def estimate_volume_cost(request: GyroidVolumeRequest) -> VolumeCostEstimate:
    """Estimate numeric grid payload and topology work with integer arithmetic."""

    from .safety_policy import (
        VOLUME_APPLY_MAX_CAP_TRIANGLES,
        VOLUME_PREVIEW_MAX_CAP_TRIANGLES,
        estimate_band_cap_triangles,
        estimate_cap_triangles,
        volume_sample_limit,
    )

    selection = select_volume_resolution(request)
    rx, ry, rz = selection.effective_resolution
    samples = rx * ry * rz
    cells = (rx - 1) * (ry - 1) * (rz - 1)
    field_count = 2 if request.geometry_mode is GeometryMode.THICKENED else 1
    cap_estimate = 0
    if request.boundary_mode is BoundaryMode.CAP:
        estimator = (
            estimate_band_cap_triangles
            if field_count == 2
            else estimate_cap_triangles
        )
        cap_estimate = estimator(rx, ry, rz)
    preview = request.execution_context is VolumeExecutionContext.PREVIEW
    return VolumeCostEstimate(
        final_resolution=selection.final_resolution,
        effective_resolution=selection.effective_resolution,
        scalar_samples_per_field=samples,
        total_scalar_samples=samples * field_count,
        cell_count=cells,
        stored_scalar_field_count=field_count,
        estimated_scalar_grid_bytes=samples * field_count
        * SCALAR_BYTES_PER_SAMPLE,
        estimated_grid_metadata_bytes=field_count
        * REGULAR_GRID_METADATA_BYTES,
        estimated_cap_triangles=cap_estimate,
        geometry_mode=request.geometry_mode,
        boundary_mode=request.boundary_mode,
        preview_quality=request.preview_quality if preview else None,
        execution_context=request.execution_context,
        active_sample_limit=volume_sample_limit(request.execution_context),
        active_cap_triangle_limit=(
            VOLUME_PREVIEW_MAX_CAP_TRIANGLES
            if preview
            else VOLUME_APPLY_MAX_CAP_TRIANGLES
        ),
        tpms_type=request.tpms_type,
    )
