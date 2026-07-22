"""Coral preset definition."""

from .preset import NaturePreset, ParameterMetadata


CORAL_PRESET = NaturePreset(
    preset_id="coral",
    display_name="Coral",
    category="aquatic",
    description="Closed branching growth inspired by coral colonies.",
    generator_id="coral",
    default_parameters={"cell_size": 14.0, "thickness": 0.35},
    parameter_metadata={
        "cell_size": ParameterMetadata(
            "Cell Size",
            "float",
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
            unit="relative",
            description="Relative radius of the connected coral branches.",
        ),
    },
    available=True,
)
