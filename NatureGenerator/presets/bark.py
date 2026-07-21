"""Bark preset definition."""

from .preset import NaturePreset, ParameterMetadata


BARK_PRESET = NaturePreset(
    preset_id="bark",
    display_name="Bark",
    category="botanical",
    description="Layered ridges and fissures inspired by tree bark.",
    generator_id="noise",
    default_parameters={"feature_size": 12.0, "roughness": 0.65},
    parameter_metadata={
        "feature_size": ParameterMetadata(
            "Feature Size",
            "float",
            12.0,
            minimum=1.0,
            maximum=60.0,
            unit="mm",
            description="Nominal spacing of bark ridges.",
        ),
        "roughness": ParameterMetadata(
            "Roughness",
            "float",
            0.65,
            minimum=0.0,
            maximum=1.0,
            description="Reserved strength of multi-scale surface variation.",
        ),
    },
    available=False,
    unavailable_reason="The noise generator is not implemented yet.",
)
