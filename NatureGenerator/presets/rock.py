"""Rock preset definition."""

from .preset import NaturePreset, ParameterMetadata


ROCK_PRESET = NaturePreset(
    preset_id="rock",
    display_name="Rock",
    category="geological",
    description="A rounded asymmetric stone with layered natural surface variation.",
    generator_id="rock",
    default_parameters={
        "size": 40.0,
        "roughness": 0.35,
        "seed": 1,
        "resolution": 17,
    },
    parameter_metadata={
        "size": ParameterMetadata(
            "Size", "length", 40.0, minimum=10.0, maximum=120.0,
            unit="mm",
            description="Nominal maximum diameter of the stone.",
        ),
        "roughness": ParameterMetadata(
            "Roughness", "float", 0.35, minimum=0.0, maximum=0.70,
            description="Amount of broad and fine surface variation.",
        ),
        "seed": ParameterMetadata(
            "Seed", "integer", 1, minimum=0, maximum=2147483647,
            description="Deterministic variation key.",
        ),
        "resolution": ParameterMetadata(
            "Resolution", "integer", 17, minimum=9, maximum=41,
            description="Voxel samples per axis.",
        ),
    },
    available=True,
)
