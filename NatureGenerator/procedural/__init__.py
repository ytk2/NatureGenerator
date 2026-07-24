"""Fusion-independent Procedural Lab contracts and execution runtime."""

from .models import (
    ExecutionContext,
    OperatorInvocation,
    ProceduralInputGeometry,
    ProceduralRequest,
    ProceduralResult,
    ProceduralStackRequest,
    SourceType,
    canonical_mesh_digest,
)
from .noise import fractal_value_noise, value_noise, vertex_normals
from .gyroid import gyroid_field, gyroid_response
from .operators import (
    GyroidSurfaceOperator,
    NoiseDisplacementOperator,
    ParameterDefinition,
    PassThroughOperator,
    ProceduralOperator,
    SubdivisionOperator,
    VoronoiSurfaceOperator,
)
from .subdivision import subdivide, subdivide_once
from .subdivision_policy import (
    SUBDIVISION_APPLY_MAX_FACES,
    SUBDIVISION_PREVIEW_MAX_FACES,
    SubdivisionFaceLimitError,
    enforce_subdivision_face_limit,
    estimate_subdivision_faces,
    subdivision_face_limit,
    validate_subdivision_size,
)
from .voronoi import boundary_mask, lattice_site, nearest_site_distances
from .pipeline import OperatorPipeline, ProceduralPipelineError
from .registry import (
    DEFAULT_OPERATOR_REGISTRY,
    ProceduralOperatorRegistry,
    UnknownOperatorError,
)

__all__ = [
    "DEFAULT_OPERATOR_REGISTRY",
    "ExecutionContext",
    "GyroidSurfaceOperator",
    "OperatorPipeline",
    "OperatorInvocation",
    "NoiseDisplacementOperator",
    "ParameterDefinition",
    "PassThroughOperator",
    "ProceduralInputGeometry",
    "ProceduralOperator",
    "ProceduralOperatorRegistry",
    "ProceduralPipelineError",
    "ProceduralRequest",
    "ProceduralResult",
    "ProceduralStackRequest",
    "SourceType",
    "SubdivisionOperator",
    "SubdivisionFaceLimitError",
    "SUBDIVISION_APPLY_MAX_FACES",
    "SUBDIVISION_PREVIEW_MAX_FACES",
    "UnknownOperatorError",
    "VoronoiSurfaceOperator",
    "boundary_mask",
    "canonical_mesh_digest",
    "fractal_value_noise",
    "gyroid_field",
    "gyroid_response",
    "lattice_site",
    "nearest_site_distances",
    "subdivide",
    "subdivide_once",
    "enforce_subdivision_face_limit",
    "estimate_subdivision_faces",
    "subdivision_face_limit",
    "validate_subdivision_size",
    "value_noise",
    "vertex_normals",
]
