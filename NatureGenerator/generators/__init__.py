"""Procedural fields and runtime generators built on the geometry core."""

from .generator import (
    Generator,
    MeshGenerator,
    GeneratorError,
    InvalidGeneratorParameters,
    MeshExtractionError,
    UnavailablePresetError,
    UnknownGeneratorError,
    UnknownPresetError,
)
from .generator_factory import GeneratorFactory
from .coral_generator import CoralGenerator
from .bark_generator import BarkGenerator
from .sponge_generator import SpongeGenerator
from .rock_generator import RockGenerator
from .root_generator import RootGenerator, RootSegment, build_root_skeleton
from .gyroid import GyroidField
from .gyroid_generator import GyroidGenerator
from .result import GeneratorResult
from .request import (
    DEFAULT_RESOLUTION,
    MAX_RESOLUTION,
    MIN_RESOLUTION,
    GenerationRequest,
)

__all__ = [
    "Generator",
    "CoralGenerator",
    "BarkGenerator",
    "MeshGenerator",
    "SpongeGenerator",
    "RockGenerator",
    "RootGenerator",
    "RootSegment",
    "build_root_skeleton",
    "GeneratorError",
    "GeneratorFactory",
    "GeneratorResult",
    "GenerationRequest",
    "GyroidField",
    "GyroidGenerator",
    "InvalidGeneratorParameters",
    "DEFAULT_RESOLUTION",
    "MIN_RESOLUTION",
    "MAX_RESOLUTION",
    "MeshExtractionError",
    "UnavailablePresetError",
    "UnknownGeneratorError",
    "UnknownPresetError",
]
