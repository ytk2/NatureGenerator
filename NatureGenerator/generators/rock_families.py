"""Immutable internal Rock family parameter catalog."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Tuple

from .rock_pipeline import (
    DEFAULT_FACET_PARAMETERS,
    DEFAULT_MACRO_PARAMETERS,
    DEFAULT_SURFACE_PARAMETERS,
    FacetLayoutParameters,
    MacroShapeParameters,
    SurfaceDetailParameters,
)


@dataclass(frozen=True)
class RockFamilyDefinition:
    """One Rock family expressed as immutable UI values and stage parameters."""

    family_id: str
    display_name: str
    parameter_values: Mapping[str, Any]
    macro: MacroShapeParameters
    facets: FacetLayoutParameters
    surface: SurfaceDetailParameters

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "parameter_values", MappingProxyType(dict(self.parameter_values))
        )


DEFAULT_ROCK_FAMILY = RockFamilyDefinition(
    "default",
    "Default",
    {},
    DEFAULT_MACRO_PARAMETERS,
    DEFAULT_FACET_PARAMETERS,
    DEFAULT_SURFACE_PARAMETERS,
)

SMOOTH_ROCK_FAMILY = RockFamilyDefinition(
    "smooth",
    "Smooth",
    {"size": 40.0, "roughness": 0.10, "seed": 1, "resolution": 17},
    DEFAULT_MACRO_PARAMETERS,
    DEFAULT_FACET_PARAMETERS,
    DEFAULT_SURFACE_PARAMETERS,
)

WEATHERED_ROCK_FAMILY = RockFamilyDefinition(
    "weathered",
    "Weathered",
    {"size": 40.0, "roughness": 0.35, "seed": 1, "resolution": 17},
    DEFAULT_MACRO_PARAMETERS,
    DEFAULT_FACET_PARAMETERS,
    DEFAULT_SURFACE_PARAMETERS,
)

RUGGED_ROCK_FAMILY = RockFamilyDefinition(
    "rugged",
    "Rugged",
    {"size": 45.0, "roughness": 0.62, "seed": 23, "resolution": 25},
    DEFAULT_MACRO_PARAMETERS,
    DEFAULT_FACET_PARAMETERS,
    DEFAULT_SURFACE_PARAMETERS,
)

RIVER_STONE_FAMILY = RockFamilyDefinition(
    "river_stone",
    "River Stone",
    {"size": 40.0, "roughness": 0.35, "seed": 1, "resolution": 25},
    MacroShapeParameters(
        axis_base=(0.46, 0.44, 0.31),
        axis_response=(0.004, -0.004, -0.008),
        axis_seed_amplitude=(0.008, 0.008, 0.006),
        axis_seed_base=0.20,
        axis_seed_response=0.25,
        broad_coefficients=(0.020, 0.012, -0.012, 0.008),
        broad_amplitude_base=0.10,
        broad_amplitude_response=0.22,
        large_noise_frequency=0.58,
        large_noise_offset=(2.7, -5.4, 8.1),
        large_noise_amplitude_base=0.004,
        large_noise_amplitude_response=0.024,
        ground_offset_base=0.91,
        ground_offset_response=-0.045,
    ),
    FacetLayoutParameters(
        plane_count=2,
        scales=("small", "small"),
        normal_z_base=0.60,
        normal_z_range=0.18,
        offset_base=1.055,
        offset_response_base=0.020,
        offset_response_noise=0.004,
        weight=1.0,
    ),
    SurfaceDetailParameters(
        fbm_octaves=4,
        fbm_frequency=0.72,
        fbm_lacunarity=2.0,
        fbm_gain=0.46,
        fbm_offset=(11.3, -7.9, 5.1),
        fbm_octave_offset=(3.17, 1.91, -2.43),
        fbm_amplitude_base=0.003,
        fbm_amplitude_response=0.022,
        ridge_frequency=2.7,
        ridge_offset=(-4.7, 9.2, -2.6),
        ridge_center=0.38,
        ridge_amplitude_response=0.008,
        ridge_response_power=1.35,
    ),
)


class RockFamilyRegistry:
    """Resolve internal Rock family definitions without procedural branching."""

    preset_id = "rock"
    _selectable = (
        SMOOTH_ROCK_FAMILY,
        WEATHERED_ROCK_FAMILY,
        RUGGED_ROCK_FAMILY,
        RIVER_STONE_FAMILY,
    )
    _definitions: Mapping[str, RockFamilyDefinition] = MappingProxyType(
        {
            definition.family_id: definition
            for definition in (DEFAULT_ROCK_FAMILY,) + _selectable
        }
    )

    @classmethod
    def get(cls, family_id: str) -> RockFamilyDefinition:
        try:
            return cls._definitions[family_id]
        except (KeyError, TypeError) as error:
            raise KeyError("unknown rock family: {!r}".format(family_id)) from error

    @classmethod
    def list_all(cls) -> Tuple[RockFamilyDefinition, ...]:
        return cls._selectable
