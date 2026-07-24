"""Sponge preset backed by the closed porous Sponge field."""

from .preset import NaturePreset, ParameterMetadata
from .common import natural_parameter_groups


SPONGE_PRESET = NaturePreset(
    preset_id="sponge",
    display_name="Sponge",
    category="aquatic",
    description="Closed rounded solid with seed-dependent surface pores.",
    generator_id="gyroid",
    default_parameters={
        "cell_size": 10.0,
        "thickness": 0.2,
        "seed": 0,
        "resolution": 17,
    },
    parameter_metadata={
        "cell_size": ParameterMetadata(
            "Cell Size",
            "length",
            10.0,
            minimum=1.0,
            maximum=100.0,
            unit="mm",
            description="Overall world-space scale of the sponge body.",
        ),
        "thickness": ParameterMetadata(
            "Thickness",
            "float",
            0.2,
            minimum=0.0,
            maximum=1.0,
            unit="",
            description="Relative size of rounded surface pores.",
        ),
        "seed": ParameterMetadata(
            "Seed", "integer", 0, minimum=0, maximum=2147483647,
            description="Deterministic pore-layout seed.",
        ),
        "resolution": ParameterMetadata(
            "Resolution", "integer", 17, minimum=9, maximum=41,
            description="Voxel samples per axis.",
        ),
    },
    parameter_groups=natural_parameter_groups(("cell_size", "thickness")),
    available=True,
)
