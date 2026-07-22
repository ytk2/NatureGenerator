"""Bark preset definition."""

from .preset import NaturePreset, ParameterMetadata


BARK_PRESET = NaturePreset(
    preset_id="bark",
    display_name="Bark",
    category="botanical",
    description="Closed trunk segment with directional ridges and fissures.",
    generator_id="bark",
    default_parameters={
        "diameter": 80.0,
        "height": 120.0,
        "bark_depth": 4.0,
        "groove_scale": 18.0,
        "twist": 0.0,
        "seed": 10,
        "resolution": 33,
    },
    parameter_metadata={
        "diameter": ParameterMetadata(
            "Diameter", "length", 80.0, minimum=30.0, maximum=160.0,
            unit="mm",
            description="Nominal trunk diameter.",
        ),
        "height": ParameterMetadata(
            "Height", "length", 120.0, minimum=40.0, maximum=240.0,
            unit="mm", description="Height of the closed trunk segment.",
        ),
        "bark_depth": ParameterMetadata(
            "Bark Depth", "length", 4.0, minimum=0.5, maximum=15.0,
            unit="mm", description="Nominal radial bark displacement.",
        ),
        "groove_scale": ParameterMetadata(
            "Groove Scale", "length", 18.0, minimum=6.0, maximum=40.0,
            unit="mm", description="Approximate spacing of broad bark grooves.",
        ),
        "twist": ParameterMetadata(
            "Twist", "float", 0.0, minimum=-1.0, maximum=1.0,
            description="Ridge turns over the full trunk height.",
        ),
        "seed": ParameterMetadata(
            "Seed", "integer", 10, minimum=0, maximum=2147483647,
            description="Deterministic variation key.",
        ),
        "resolution": ParameterMetadata(
            "Resolution", "integer", 33, minimum=29, maximum=41,
            description="Voxel samples per axis.",
        ),
    },
    available=True,
)
