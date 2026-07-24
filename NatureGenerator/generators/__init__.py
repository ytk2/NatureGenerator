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
from .bone_generator import BoneGenerator
from .crystal_generator import CrystalGenerator
from .crystal_families import (
    CLASSIC_CRYSTAL_FAMILY,
    CrystalFamilyDefinition,
    CrystalFamilyRegistry,
)
from .bone_families import (
    BoneFamilyDefinition,
    BoneFamilyRegistry,
    CLASSIC_BONE_FAMILY,
)
from .sponge_generator import SpongeGenerator
from .rock_generator import RockGenerator
from .root_generator import RootGenerator, RootSegment, build_root_skeleton
from .root_families import (
    CLASSIC_ROOT_FAMILY,
    RootFamilyDefinition,
    RootFamilyRegistry,
)
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
    "BoneGenerator",
    "BoneFamilyDefinition",
    "BoneFamilyRegistry",
    "CLASSIC_BONE_FAMILY",
    "CrystalGenerator",
    "CrystalFamilyDefinition",
    "CrystalFamilyRegistry",
    "CLASSIC_CRYSTAL_FAMILY",
    "MeshGenerator",
    "SpongeGenerator",
    "RockGenerator",
    "RootGenerator",
    "RootFamilyDefinition",
    "RootFamilyRegistry",
    "CLASSIC_ROOT_FAMILY",
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
