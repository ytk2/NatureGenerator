"""Explicit generator registration and preset execution."""

import re
from typing import Any, Callable, Dict, Mapping, Optional

from presets.preset import NaturePreset
from presets import PresetFactory

from .generator import (
    Generator,
    UnavailablePresetError,
    UnknownGeneratorError,
    UnknownPresetError,
)
from .gyroid_generator import GyroidGenerator
from .result import GeneratorResult
from .request import DEFAULT_RESOLUTION, GenerationRequest


GeneratorConstructor = Callable[[], Generator]


class GeneratorFactory:
    """Resolve stable generator IDs without dynamic discovery."""

    _constructors: Dict[str, GeneratorConstructor] = {}
    _builtins_registered = False

    @classmethod
    def register(
        cls, generator_id: str, constructor: GeneratorConstructor
    ) -> None:
        """Register one generator constructor, rejecting duplicate IDs."""

        if not isinstance(generator_id, str) or re.fullmatch(
            r"[a-z][a-z0-9_]*", generator_id
        ) is None:
            raise ValueError("generator_id must be a lowercase stable identifier")
        if not callable(constructor):
            raise TypeError("constructor must be callable")
        if generator_id in cls._constructors:
            raise ValueError("duplicate generator id: {}".format(generator_id))
        cls._constructors[generator_id] = constructor

    @classmethod
    def _register_builtins(cls) -> None:
        if not cls._builtins_registered:
            cls.register("gyroid", GyroidGenerator)
            cls._builtins_registered = True

    @classmethod
    def create(cls, generator_id: str) -> Generator:
        """Return a new generator for *generator_id*."""

        cls._register_builtins()
        try:
            constructor = cls._constructors[generator_id]
        except (KeyError, TypeError) as error:
            raise UnknownGeneratorError(
                "unknown generator_id: {!r}".format(generator_id)
            ) from error
        generator = constructor()
        if not isinstance(generator, Generator):
            raise TypeError("registered constructor did not return a Generator")
        if generator.generator_id != generator_id:
            raise ValueError("registered generator_id does not match implementation")
        return generator

    @classmethod
    def generate(
        cls,
        preset: NaturePreset,
        parameters: Optional[Mapping[str, Any]] = None,
    ) -> GeneratorResult:
        """Resolve and execute the generator referenced by *preset*."""

        if not isinstance(preset, NaturePreset):
            raise TypeError("preset must be a NaturePreset")
        if not preset.available:
            raise UnavailablePresetError(
                "preset {!r} is unavailable: {}".format(
                    preset.preset_id, preset.unavailable_reason
                )
            )
        return cls.create(preset.generator_id).generate(
            preset, parameters, DEFAULT_RESOLUTION
        )

    @classmethod
    def generate_request(cls, request: GenerationRequest) -> GeneratorResult:
        """Resolve and execute a complete Fusion-independent request."""

        if not isinstance(request, GenerationRequest):
            raise TypeError("request must be a GenerationRequest")
        try:
            preset = PresetFactory.get(request.preset_id)
        except KeyError as error:
            raise UnknownPresetError(
                "unknown preset_id: {!r}".format(request.preset_id)
            ) from error
        if not preset.available:
            raise UnavailablePresetError(
                "preset {!r} is unavailable: {}".format(
                    preset.preset_id, preset.unavailable_reason
                )
            )
        return cls.create(preset.generator_id).generate(
            preset,
            request.parameter_overrides,
            request.resolution,
        )
