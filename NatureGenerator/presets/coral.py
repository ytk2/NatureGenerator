"""Coral preset definition."""

from .preset import NaturePreset, ParameterMetadata
from .common import natural_parameter_groups


CORAL_PRESET = NaturePreset(
    preset_id="coral",
    display_name="Coral",
    category="aquatic",
    description="Closed branching growth inspired by coral colonies.",
    generator_id="coral",
    default_parameters={
        "cell_size": 14.0,
        "thickness": 0.35,
        "seed": 0,
        "resolution": 17,
    },
    parameter_metadata={
        "cell_size": ParameterMetadata(
            "Cell Size",
            "length",
            14.0,
            minimum=1.0,
            maximum=100.0,
            unit="mm",
            description="Overall scale of the coral branching form.",
        ),
        "thickness": ParameterMetadata(
            "Thickness",
            "float",
            0.35,
            minimum=0.0,
            maximum=1.0,
            unit="",
            description="Relative radius of the connected coral branches.",
        ),
        "seed": ParameterMetadata(
            "Seed", "integer", 0, minimum=0, maximum=2147483647,
            description="Deterministic variation key.",
        ),
        "resolution": ParameterMetadata(
            "Resolution", "integer", 17, minimum=9, maximum=41,
            description="Voxel samples per axis.",
        ),
    },
    parameter_groups=natural_parameter_groups(("cell_size", "thickness")),
    available=True,
)
