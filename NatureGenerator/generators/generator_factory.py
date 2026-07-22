"""Explicit generator registration and preset execution."""

import re
from time import perf_counter
from typing import Any, Callable, Dict, Mapping, Optional

from core.mesh_validator import MeshValidator
from presets import PresetFactory
from presets.preset import NaturePreset

from .coral_generator import CoralGenerator
from .bark_generator import BarkGenerator
from .generator import (
    Generator,
    MeshExtractionError,
    MeshGenerator,
    UnavailablePresetError,
    UnknownGeneratorError,
    UnknownPresetError,
)
from .gyroid_generator import GyroidGenerator
from .request import DEFAULT_RESOLUTION, GenerationRequest
from .result import GeneratorResult
from .sponge_generator import SpongeGenerator
from .rock_generator import RockGenerator


GeneratorConstructor = Callable[[], Generator]
MeshGeneratorConstructor = Callable[[], MeshGenerator]


class GeneratorFactory:
    """Resolve stable generator IDs without dynamic discovery."""

    _constructors: Dict[str, GeneratorConstructor] = {}
    _preset_constructors: Dict[str, MeshGeneratorConstructor] = {}
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
            cls.register_preset("sponge", SpongeGenerator)
            cls.register_preset("coral", CoralGenerator)
            cls.register_preset("rock", RockGenerator)
            cls.register_preset("bark", BarkGenerator)
            cls._builtins_registered = True

    @classmethod
    def register_preset(
        cls, preset_id: str, constructor: MeshGeneratorConstructor
    ) -> None:
        """Register one request-oriented generator by stable preset ID."""

        if not isinstance(preset_id, str) or re.fullmatch(
            r"[a-z][a-z0-9_]*", preset_id
        ) is None:
            raise ValueError("preset_id must be a lowercase stable identifier")
        if not callable(constructor):
            raise TypeError("constructor must be callable")
        if preset_id in cls._preset_constructors:
            raise ValueError("duplicate preset id: {}".format(preset_id))
        cls._preset_constructors[preset_id] = constructor

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
        try:
            registered = PresetFactory.get(preset.preset_id)
        except KeyError:
            registered = None
        if registered == preset:
            supplied = {} if parameters is None else dict(parameters)
            resolution = supplied.pop(
                "resolution",
                preset.default_parameters.get("resolution", DEFAULT_RESOLUTION),
            )
            return cls.generate_request(
                GenerationRequest(
                    preset.preset_id,
                    supplied,
                    resolution,
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
        started = perf_counter()
        generator = cls.create_for_preset(request.preset_id)
        mesh = generator.generate(request)
        validation = MeshValidator(
            require_watertight=generator.require_watertight
        ).validate(mesh)
        if not validation.valid:
            errors = tuple(
                issue.message
                for issue in validation.issues
                if issue.severity == "error"
            )
            raise MeshExtractionError(
                "{} mesh validation failed: {}".format(
                    generator.generator_id, "; ".join(errors)
                )
            )
        warnings = tuple(
            "{}: {} ({})".format(issue.code, issue.message, issue.count)
            for issue in validation.issues
            if issue.severity == "warning"
        )
        return GeneratorResult(
            mesh=mesh,
            statistics=validation.statistics,
            warnings=warnings,
            generator_id=generator.generator_id,
            preset_id=preset.preset_id,
            elapsed_time=perf_counter() - started,
        )

    @classmethod
    def create_for_preset(cls, preset_id: str) -> MeshGenerator:
        """Resolve a generator from a stable user-facing preset ID."""

        try:
            preset = PresetFactory.get(preset_id)
        except KeyError as error:
            raise UnknownPresetError(
                "unknown preset_id: {!r}".format(preset_id)
            ) from error
        if not preset.available:
            raise UnavailablePresetError(
                "preset {!r} is unavailable: {}".format(
                    preset.preset_id, preset.unavailable_reason
                )
            )
        cls._register_builtins()
        try:
            constructor = cls._preset_constructors[preset_id]
        except (KeyError, TypeError) as error:
            raise UnknownGeneratorError(
                "no generator registered for preset_id: {!r}".format(preset_id)
            ) from error
        generator = constructor()
        if not isinstance(generator, MeshGenerator):
            raise TypeError("registered constructor did not return a MeshGenerator")
        if generator.preset_id != preset_id:
            raise ValueError("registered preset_id does not match implementation")
        if generator.generator_id != preset.generator_id:
            raise ValueError("preset generator_id does not match implementation")
        return generator
