"""Central checked-size policy for volume sampling."""

from dataclasses import dataclass

from .volume_request import VolumeExecutionContext


VOLUME_PREVIEW_MAX_SAMPLES = 750_000
VOLUME_APPLY_MAX_SAMPLES = 2_000_000
SCALAR_BYTES_PER_SAMPLE = 8


class VolumeSafetyLimitError(ValueError):
    pass


@dataclass(frozen=True)
class VolumeSizeEstimate:
    sample_count: int
    cell_count: int
    scalar_bytes: int


def estimate_volume_size(
    resolution_x: int, resolution_y: int, resolution_z: int
) -> VolumeSizeEstimate:
    values = (resolution_x, resolution_y, resolution_z)
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 2
        for value in values
    ):
        raise ValueError("volume resolutions must be integers of at least two")
    samples = resolution_x * resolution_y * resolution_z
    cells = (
        (resolution_x - 1)
        * (resolution_y - 1)
        * (resolution_z - 1)
    )
    return VolumeSizeEstimate(
        sample_count=samples,
        cell_count=cells,
        scalar_bytes=samples * SCALAR_BYTES_PER_SAMPLE,
    )


def volume_sample_limit(context: VolumeExecutionContext) -> int:
    if not isinstance(context, VolumeExecutionContext):
        raise TypeError("context must be a VolumeExecutionContext")
    if context is VolumeExecutionContext.PREVIEW:
        return VOLUME_PREVIEW_MAX_SAMPLES
    return VOLUME_APPLY_MAX_SAMPLES


def enforce_volume_sample_limit(
    sample_count: int,
    resolution: tuple,
    context: VolumeExecutionContext,
) -> int:
    if (
        isinstance(sample_count, bool)
        or not isinstance(sample_count, int)
        or sample_count < 0
    ):
        raise ValueError("sample_count must be a non-negative integer")
    if len(resolution) != 3:
        raise ValueError("resolution must contain three values")
    limit = volume_sample_limit(context)
    if sample_count > limit:
        operation = (
            "Preview"
            if context is VolumeExecutionContext.PREVIEW
            else "Apply"
        )
        raise VolumeSafetyLimitError(
            "Requested resolution {} × {} × {} requires {:,} scalar samples, "
            "exceeding the {} limit of {:,}. Reduce one or more resolution "
            "values.".format(
                resolution[0],
                resolution[1],
                resolution[2],
                sample_count,
                operation,
                limit,
            )
        )
    return sample_count


def validate_volume_size(
    resolution_x: int,
    resolution_y: int,
    resolution_z: int,
    context: VolumeExecutionContext,
) -> VolumeSizeEstimate:
    estimate = estimate_volume_size(
        resolution_x, resolution_y, resolution_z
    )
    enforce_volume_sample_limit(
        estimate.sample_count,
        (resolution_x, resolution_y, resolution_z),
        context,
    )
    return estimate
