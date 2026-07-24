"""Fusion-independent Procedural Lab contracts and execution runtime."""

from .models import (
    ExecutionContext,
    ProceduralInputGeometry,
    ProceduralRequest,
    ProceduralResult,
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
)
from .subdivision import subdivide, subdivide_once
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
    "NoiseDisplacementOperator",
    "ParameterDefinition",
    "PassThroughOperator",
    "ProceduralInputGeometry",
    "ProceduralOperator",
    "ProceduralOperatorRegistry",
    "ProceduralPipelineError",
    "ProceduralRequest",
    "ProceduralResult",
    "SourceType",
    "SubdivisionOperator",
    "UnknownOperatorError",
    "canonical_mesh_digest",
    "fractal_value_noise",
    "subdivide",
    "subdivide_once",
    "value_noise",
    "vertex_normals",
]
