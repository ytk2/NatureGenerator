"""Sponge preset backed by the available gyroid scalar field."""

from .preset import NaturePreset, ParameterMetadata


SPONGE_PRESET = NaturePreset(
    preset_id="sponge",
    display_name="Sponge",
    category="aquatic",
    description="Continuous porous sheet structure inspired by natural sponges.",
    generator_id="gyroid",
    default_parameters={
        "cell_size": 10.0,
        "thickness": 0.2,
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
            description="World-space length of one gyroid period.",
        ),
        "thickness": ParameterMetadata(
            "Thickness",
            "float",
            0.2,
            minimum=0.0,
            maximum=1.0,
            unit="",
            description="Half-band around the mathematical gyroid surface.",
        ),
        "resolution": ParameterMetadata(
            "Resolution", "integer", 17, minimum=9, maximum=41,
            description="Voxel samples per axis.",
        ),
    },
    available=True,
)
