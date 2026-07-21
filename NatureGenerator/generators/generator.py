"""Generator runtime contract and domain-specific exceptions."""

from abc import ABC, abstractmethod
from typing import Any, Mapping, Optional

from presets.preset import NaturePreset

from .result import GeneratorResult


class GeneratorError(Exception):
    """Base class for generator runtime failures."""


class UnknownGeneratorError(GeneratorError, LookupError):
    """Raised when no generator is registered for a stable ID."""


class InvalidGeneratorParameters(GeneratorError, ValueError):
    """Raised when parameters cannot configure a generator."""


class MeshExtractionError(GeneratorError):
    """Raised when a configured field cannot produce a valid mesh."""


class UnavailablePresetError(GeneratorError):
    """Raised when execution is requested for an unavailable preset."""


class Generator(ABC):
    """Interface for executing a preset into a complete result."""

    @property
    @abstractmethod
    def generator_id(self) -> str:
        """Return the stable ID used by ``NaturePreset.generator_id``."""

    @abstractmethod
    def generate(
        self,
        preset: NaturePreset,
        parameters: Optional[Mapping[str, Any]] = None,
    ) -> GeneratorResult:
        """Execute *preset* with optional parameter overrides."""
