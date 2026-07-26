"""Deterministic Preview and Apply resolution selection."""

from dataclasses import dataclass
import math
from typing import Tuple

from .volume_request import (
    GyroidVolumeRequest,
    PreviewQuality,
    VolumeExecutionContext,
)


PREVIEW_QUALITY_SCALES = {
    PreviewQuality.DRAFT: 0.50,
    PreviewQuality.STANDARD: 0.75,
    PreviewQuality.FINAL: 1.00,
}
MINIMUM_EFFECTIVE_RESOLUTION = 8


@dataclass(frozen=True)
class VolumeResolutionSelection:
    final_resolution: Tuple[int, int, int]
    effective_resolution: Tuple[int, int, int]
    scale: float


def _scale_axis(value: int, scale: float) -> int:
    return max(
        MINIMUM_EFFECTIVE_RESOLUTION,
        int(math.floor(value * scale + 0.5)),
    )


def select_volume_resolution(
    request: GyroidVolumeRequest,
) -> VolumeResolutionSelection:
    """Resolve generation resolution without mutating final UI values."""

    if not isinstance(request, GyroidVolumeRequest):
        raise TypeError("request must be a GyroidVolumeRequest")
    final_resolution = request.resolution
    scale = (
        PREVIEW_QUALITY_SCALES[request.preview_quality]
        if request.execution_context is VolumeExecutionContext.PREVIEW
        else 1.0
    )
    effective = tuple(_scale_axis(value, scale) for value in final_resolution)
    return VolumeResolutionSelection(final_resolution, effective, scale)
