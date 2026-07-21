"""Rock preset definition."""

from .preset import NaturePreset, ParameterMetadata


ROCK_PRESET = NaturePreset(
    preset_id="rock",
    display_name="Rock",
    category="geological",
    description="Irregular fractured mass inspired by weathered rock.",
    generator_id="voronoi",
    default_parameters={"feature_size": 20.0, "irregularity": 0.7},
    parameter_metadata={
        "feature_size": ParameterMetadata(
            "Feature Size",
            "float",
            20.0,
            minimum=2.0,
            maximum=100.0,
            unit="mm",
            description="Nominal spacing of future fractured regions.",
        ),
        "irregularity": ParameterMetadata(
            "Irregularity",
            "float",
            0.7,
            minimum=0.0,
            maximum=1.0,
            description="Reserved variation in region size and shape.",
        ),
    },
    available=False,
    unavailable_reason="The voronoi generator is not implemented yet.",
)
