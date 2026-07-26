"""Central checked-size policy for volume sampling."""

from dataclasses import dataclass

from .volume_request import GeometryMode, VolumeExecutionContext


VOLUME_PREVIEW_MAX_SAMPLES = 750_000
VOLUME_APPLY_MAX_SAMPLES = 2_000_000
SCALAR_BYTES_PER_SAMPLE = 8
VOLUME_PREVIEW_MAX_CAP_TRIANGLES = 500_000
VOLUME_APPLY_MAX_CAP_TRIANGLES = 1_000_000


class VolumeSafetyLimitError(ValueError):
    pass


def validate_wall_thickness_resolution(request, estimate) -> float:
    """Reject thickened requests that the regular grid cannot represent."""

    if request.geometry_mode is GeometryMode.SURFACE:
        return request.wall_thickness
    spacing = (
        request.width / (request.resolution_x - 1),
        request.depth / (request.resolution_y - 1),
        request.height / (request.resolution_z - 1),
    )
    minimum_reliable = max(spacing) / 16.0
    if request.wall_thickness < minimum_reliable:
        raise VolumeSafetyLimitError(
            "Geometry Mode Thickened with Wall Thickness {:.6g} mm, Period "
            "{:.6g} mm, and resolution {} × {} × {} is too thin for the "
            "current voxel spacing. Use at least {:.6g} mm or increase the "
            "resolution. The request would sample {:,} values.".format(
                request.wall_thickness,
                request.period,
                request.resolution_x,
                request.resolution_y,
                request.resolution_z,
                minimum_reliable,
                estimate.sample_count,
            )
        )
    return request.wall_thickness


def validate_volume_request_size(request):
    """Validate allocation cost with thickened-request context when relevant."""

    try:
        estimate = validate_volume_size(
            request.resolution_x,
            request.resolution_y,
            request.resolution_z,
            request.execution_context,
        )
    except VolumeSafetyLimitError as error:
        if request.geometry_mode is GeometryMode.SURFACE:
            raise
        raise VolumeSafetyLimitError(
            "Geometry Mode Thickened with Wall Thickness {:.6g} mm, Period "
            "{:.6g} mm, and resolution {} × {} × {} exceeds the volume "
            "safety policy: {}".format(
                request.wall_thickness,
                request.period,
                request.resolution_x,
                request.resolution_y,
                request.resolution_z,
                error,
            )
        ) from error
    if request.geometry_mode is GeometryMode.THICKENED:
        effective_samples = estimate.sample_count * 2
        try:
            enforce_volume_sample_limit(
                effective_samples,
                request.resolution,
                request.execution_context,
            )
        except VolumeSafetyLimitError as error:
            raise VolumeSafetyLimitError(
                "Geometry Mode Thickened requires two scalar grids for Wall "
                "Thickness {:.6g} mm, Period {:.6g} mm, and resolution {} × {} "
                "× {}: {}".format(
                    request.wall_thickness,
                    request.period,
                    request.resolution_x,
                    request.resolution_y,
                    request.resolution_z,
                    error,
                )
            ) from error
        return VolumeSizeEstimate(
            estimate.sample_count,
            estimate.cell_count,
            estimate.scalar_bytes * 2,
        )
    return estimate


def estimate_cap_triangles(
    resolution_x: int, resolution_y: int, resolution_z: int
) -> int:
    """Return a conservative bound for clipped rectangular-face triangles."""

    return 4 * (
        (resolution_x - 1) * (resolution_y - 1)
        + (resolution_x - 1) * (resolution_z - 1)
        + (resolution_y - 1) * (resolution_z - 1)
    )


def estimate_band_cap_triangles(
    resolution_x: int, resolution_y: int, resolution_z: int
) -> int:
    """Return a conservative bound for a two-inequality wall-band cap."""

    return 6 * (
        (resolution_x - 1) * (resolution_y - 1)
        + (resolution_x - 1) * (resolution_z - 1)
        + (resolution_y - 1) * (resolution_z - 1)
    )


def _enforce_cap_complexity(predicted, context, label):
    limit = (
        VOLUME_PREVIEW_MAX_CAP_TRIANGLES
        if context is VolumeExecutionContext.PREVIEW
        else VOLUME_APPLY_MAX_CAP_TRIANGLES
    )
    if predicted > limit:
        operation = (
            "Preview"
            if context is VolumeExecutionContext.PREVIEW
            else "Apply"
        )
        raise VolumeSafetyLimitError(
            "{} may require up to {:,} triangles, exceeding the {} cap limit "
            "of {:,}. Reduce one or more resolution values.".format(
                label, predicted, operation, limit
            )
        )
    return predicted


def validate_cap_complexity(
    resolution_x: int,
    resolution_y: int,
    resolution_z: int,
    context: VolumeExecutionContext,
) -> int:
    predicted = estimate_cap_triangles(
        resolution_x, resolution_y, resolution_z
    )
    return _enforce_cap_complexity(
        predicted, context, "Boundary Cap"
    )


def validate_band_cap_complexity(
    resolution_x: int,
    resolution_y: int,
    resolution_z: int,
    context: VolumeExecutionContext,
) -> int:
    predicted = estimate_band_cap_triangles(
        resolution_x, resolution_y, resolution_z
    )
    return _enforce_cap_complexity(
        predicted, context, "Thickened Boundary Cap"
    )


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
