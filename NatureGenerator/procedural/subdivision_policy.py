"""Central face-count safety policy for deterministic subdivision."""

from .models import ExecutionContext


SUBDIVISION_PREVIEW_MAX_FACES = 500_000
SUBDIVISION_APPLY_MAX_FACES = 1_000_000


class SubdivisionFaceLimitError(ValueError):
    """Raised before allocation when subdivision would exceed its face limit."""


def estimate_subdivision_faces(input_face_count: int, level: int) -> int:
    """Return the exact midpoint-subdivision face count using integers."""

    if (
        isinstance(input_face_count, bool)
        or not isinstance(input_face_count, int)
        or input_face_count < 0
    ):
        raise ValueError("input_face_count must be a non-negative integer")
    if isinstance(level, bool) or not isinstance(level, int) or level < 1:
        raise ValueError("level must be a positive integer")
    return input_face_count * (4 ** level)


def subdivision_face_limit(
    execution_context: ExecutionContext,
) -> int:
    """Return the centralized Preview or Apply subdivision face limit."""

    if not isinstance(execution_context, ExecutionContext):
        raise TypeError("execution_context must be an ExecutionContext")
    if execution_context is ExecutionContext.PREVIEW:
        return SUBDIVISION_PREVIEW_MAX_FACES
    return SUBDIVISION_APPLY_MAX_FACES


def enforce_subdivision_face_limit(
    predicted_faces: int,
    level: int,
    execution_context: ExecutionContext,
) -> int:
    """Accept a prediction at the limit or raise an actionable error above it."""

    if (
        isinstance(predicted_faces, bool)
        or not isinstance(predicted_faces, int)
        or predicted_faces < 0
    ):
        raise ValueError("predicted_faces must be a non-negative integer")
    limit = subdivision_face_limit(execution_context)
    if predicted_faces > limit:
        operation = (
            "Preview"
            if execution_context is ExecutionContext.PREVIEW
            else "Apply"
        )
        raise SubdivisionFaceLimitError(
            "Subdivision Level {} would create approximately {:,} faces, "
            "exceeding the {} limit of {:,}. Reduce the level or use a "
            "lower-density input mesh.".format(
                level, predicted_faces, operation, limit
            )
        )
    return predicted_faces


def validate_subdivision_size(
    input_face_count: int,
    level: int,
    execution_context: ExecutionContext,
) -> int:
    """Estimate and validate one operation before subdivision starts."""

    return enforce_subdivision_face_limit(
        estimate_subdivision_faces(input_face_count, level),
        level,
        execution_context,
    )
