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
    resolution = getattr(estimate, "effective_resolution", request.resolution)
    spacing = tuple(
        dimension / (axis - 1)
        for dimension, axis in zip(
            (request.width, request.depth, request.height), resolution
        )
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
                resolution[0],
                resolution[1],
                resolution[2],
                minimum_reliable,
                (
                    estimate.scalar_samples_per_field
                    if hasattr(estimate, "scalar_samples_per_field")
                    else estimate.sample_count
                ),
            )
        )
    return request.wall_thickness


def validate_volume_request_size(request):
    """Validate allocation cost with thickened-request context when relevant."""

    from .cost_estimate import estimate_volume_cost

    cost = estimate_volume_cost(request)
    validate_volume_cost(request, cost)
    return VolumeSizeEstimate(
        cost.scalar_samples_per_field,
        cost.cell_count,
        cost.estimated_scalar_grid_bytes,
    )


def _resolution_text(resolution) -> str:
    return "{} × {} × {}".format(*resolution)


def validate_volume_cost(request, estimate):
    """Reject estimated effective work before allocating scalar grids."""

    operation = (
        "Preview"
        if request.execution_context is VolumeExecutionContext.PREVIEW
        else "Apply"
    )
    quality = (
        " ({})".format(request.preview_quality.value.title())
        if request.execution_context is VolumeExecutionContext.PREVIEW
        else ""
    )
    context = (
        "TPMS Type {}, Geometry Mode {}, Boundary Mode {}".format(
            request.tpms_type.value,
            request.geometry_mode.value,
            request.boundary_mode.value,
        )
        + (
            ", Wall Thickness {:.6g} mm".format(request.wall_thickness)
            if request.geometry_mode is GeometryMode.THICKENED
            else ""
        )
    )
    if estimate.total_scalar_samples > estimate.active_sample_limit:
        raise VolumeSafetyLimitError(
            "{}{} for {} requested final resolution {} and effective "
            "resolution {}. "
            "The request needs {:,} scalar samples (approximately {:.2f} MiB "
            "of scalar-grid payload), exceeding the active limit of {:,}. "
            "Reduce the final resolution or choose a lower Preview Quality."
            .format(
                operation,
                quality,
                context,
                _resolution_text(estimate.final_resolution),
                _resolution_text(estimate.effective_resolution),
                estimate.total_scalar_samples,
                estimate.estimated_known_bytes / (1024.0 * 1024.0),
                estimate.active_sample_limit,
            )
        )
    if (
        estimate.estimated_cap_triangles
        > estimate.active_cap_triangle_limit
    ):
        raise VolumeSafetyLimitError(
            "{}{} for {} requested final resolution {} and effective "
            "resolution {}. "
            "Boundary closure may require up to {:,} triangles, exceeding the "
            "active cap limit of {:,}. The request uses {:,} scalar samples "
            "(approximately {:.2f} MiB of known grid payload). Reduce the "
            "final resolution or choose a lower Preview Quality.".format(
                operation,
                quality,
                context,
                _resolution_text(estimate.final_resolution),
                _resolution_text(estimate.effective_resolution),
                estimate.estimated_cap_triangles,
                estimate.active_cap_triangle_limit,
                estimate.total_scalar_samples,
                estimate.estimated_known_bytes / (1024.0 * 1024.0),
            )
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
