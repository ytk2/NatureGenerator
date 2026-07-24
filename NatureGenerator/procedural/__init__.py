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
from .operators import (
    NoiseDisplacementOperator,
    ParameterDefinition,
    PassThroughOperator,
    ProceduralOperator,
    SubdivisionOperator,
    VoronoiSurfaceOperator,
)
from .subdivision import subdivide, subdivide_once
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
    "UnknownOperatorError",
    "VoronoiSurfaceOperator",
    "boundary_mask",
    "canonical_mesh_digest",
    "fractal_value_noise",
    "lattice_site",
    "nearest_site_distances",
    "subdivide",
    "subdivide_once",
    "value_noise",
    "vertex_normals",
]
