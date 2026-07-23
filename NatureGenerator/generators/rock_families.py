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

GRANITE_ROCK_FAMILY = RockFamilyDefinition(
    "granite",
    "Granite",
    {"size": 50.0, "roughness": 0.45, "seed": 37, "resolution": 25},
    MacroShapeParameters(
        axis_base=(0.50, 0.43, 0.39),
        axis_response=(0.015, -0.020, -0.020),
        axis_seed_amplitude=(0.035, 0.030, 0.025),
        axis_seed_base=0.35,
        axis_seed_response=0.45,
        broad_coefficients=(0.070, 0.055, -0.035, 0.040),
        broad_amplitude_base=0.45,
        broad_amplitude_response=0.55,
        large_noise_frequency=0.62,
        large_noise_offset=(6.4, -3.1, 9.7),
        large_noise_amplitude_base=0.025,
        large_noise_amplitude_response=0.090,
        ground_offset_base=0.94,
        ground_offset_response=-0.11,
    ),
    FacetLayoutParameters(
        plane_count=4,
        scales=("medium", "medium", "small", "medium"),
        normal_z_base=0.20,
        normal_z_range=0.65,
        offset_base=1.030,
        offset_response_base=0.120,
        offset_response_noise=0.018,
        weight=1.0,
    ),
    SurfaceDetailParameters(
        fbm_octaves=4,
        fbm_frequency=0.62,
        fbm_lacunarity=2.12,
        fbm_gain=0.58,
        fbm_offset=(5.8, -12.4, 3.6),
        fbm_octave_offset=(2.73, -1.47, 3.31),
        fbm_amplitude_base=0.018,
        fbm_amplitude_response=0.075,
        ridge_frequency=2.45,
        ridge_offset=(-8.2, 4.6, 7.3),
        ridge_center=0.40,
        ridge_amplitude_response=0.040,
        ridge_response_power=1.25,
    ),
)

BASALT_ROCK_FAMILY = RockFamilyDefinition(
    "basalt",
    "Basalt",
    {"size": 50.0, "roughness": 0.25, "seed": 61, "resolution": 25},
    MacroShapeParameters(
        axis_base=(0.38, 0.36, 0.52),
        axis_response=(-0.005, -0.008, 0.006),
        axis_seed_amplitude=(0.012, 0.012, 0.010),
        axis_seed_base=0.20,
        axis_seed_response=0.20,
        broad_coefficients=(0.018, 0.012, -0.015, 0.025),
        broad_amplitude_base=0.20,
        broad_amplitude_response=0.25,
        large_noise_frequency=0.55,
        large_noise_offset=(-6.7, 2.9, 11.2),
        large_noise_amplitude_base=0.008,
        large_noise_amplitude_response=0.025,
        ground_offset_base=0.91,
        ground_offset_response=-0.05,
    ),
    FacetLayoutParameters(
        plane_count=6,
        scales=("large", "large", "medium", "medium", "large", "medium"),
        normal_z_base=0.05,
        normal_z_range=0.20,
        offset_base=0.985,
        offset_response_base=0.120,
        offset_response_noise=0.015,
        weight=1.0,
    ),
    SurfaceDetailParameters(
        fbm_octaves=4,
        fbm_frequency=0.88,
        fbm_lacunarity=2.0,
        fbm_gain=0.45,
        fbm_offset=(-3.4, 8.7, 12.1),
        fbm_octave_offset=(2.1, 3.4, -1.8),
        fbm_amplitude_base=0.004,
        fbm_amplitude_response=0.025,
        ridge_frequency=2.8,
        ridge_offset=(7.7, -5.5, 2.2),
        ridge_center=0.40,
        ridge_amplitude_response=0.012,
        ridge_response_power=1.30,
    ),
)

BROKEN_ROCK_FAMILY = RockFamilyDefinition(
    "broken_rock",
    "Broken Rock",
    {"size": 50.0, "roughness": 0.55, "seed": 97, "resolution": 25},
    MacroShapeParameters(
        axis_base=(0.52, 0.40, 0.36),
        axis_response=(0.025, -0.030, -0.025),
        axis_seed_amplitude=(0.045, 0.035, 0.030),
        axis_seed_base=0.45,
        axis_seed_response=0.50,
        broad_coefficients=(0.090, 0.075, -0.060, 0.055),
        broad_amplitude_base=0.60,
        broad_amplitude_response=0.65,
        large_noise_frequency=0.58,
        large_noise_offset=(13.2, -9.4, 4.1),
        large_noise_amplitude_base=0.020,
        large_noise_amplitude_response=0.065,
        ground_offset_base=0.92,
        ground_offset_response=-0.12,
    ),
    FacetLayoutParameters(
        plane_count=7,
        scales=("large", "large", "large", "medium", "large", "medium", "large"),
        normal_z_base=0.10,
        normal_z_range=0.75,
        offset_base=0.900,
        offset_response_base=0.230,
        offset_response_noise=0.025,
        weight=1.0,
    ),
    SurfaceDetailParameters(
        fbm_octaves=4,
        fbm_frequency=0.70,
        fbm_lacunarity=2.05,
        fbm_gain=0.48,
        fbm_offset=(-10.6, 6.8, 1.9),
        fbm_octave_offset=(3.5, -2.2, 1.6),
        fbm_amplitude_base=0.008,
        fbm_amplitude_response=0.040,
        ridge_frequency=2.35,
        ridge_offset=(4.4, 10.1, -6.3),
        ridge_center=0.36,
        ridge_amplitude_response=0.055,
        ridge_response_power=1.20,
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
        GRANITE_ROCK_FAMILY,
        BASALT_ROCK_FAMILY,
        BROKEN_ROCK_FAMILY,
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
