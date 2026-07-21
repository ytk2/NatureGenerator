"""Coral preset definition."""

from .preset import NaturePreset, ParameterMetadata


CORAL_PRESET = NaturePreset(
    preset_id="coral",
    display_name="Coral",
    category="aquatic",
    description="Branching porous growth inspired by coral colonies.",
    generator_id="gray_scott",
    default_parameters={"feature_size": 8.0, "growth_bias": 0.5},
    parameter_metadata={
        "feature_size": ParameterMetadata(
            "Feature Size",
            "float",
            8.0,
            minimum=1.0,
            maximum=50.0,
            unit="mm",
            description="Nominal size of major coral features.",
        ),
        "growth_bias": ParameterMetadata(
            "Growth Bias",
            "float",
            0.5,
            minimum=0.0,
            maximum=1.0,
            description="Reserved control for directional colony growth.",
        ),
    },
    available=False,
    unavailable_reason="The gray_scott generator is not implemented yet.",
)
