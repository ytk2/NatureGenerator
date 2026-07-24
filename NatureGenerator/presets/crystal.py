"""Classic Crystal preset definition."""

from .preset import NaturePreset, ParameterMetadata


CRYSTAL_PRESET = NaturePreset(
    preset_id="crystal",
    display_name="Crystal",
    category="inorganic",
    description="Faceted elongated crystal with a tapered termination.",
    generator_id="crystal",
    default_parameters={
        "length": 80.0,
        "width": 28.0,
        "facet_count": 6,
        "taper": 0.30,
        "irregularity": 0.14,
        "seed": 13,
        "resolution": 33,
    },
    parameter_metadata={
        "length": ParameterMetadata(
            "Length", "length", 80.0, minimum=40.0, maximum=180.0,
            unit="mm", description="Overall base-to-tip crystal length.",
        ),
        "width": ParameterMetadata(
            "Width", "length", 28.0, minimum=12.0, maximum=70.0,
            unit="mm", description="Nominal prism diameter.",
        ),
        "facet_count": ParameterMetadata(
            "Facet Count", "integer", 6, minimum=5, maximum=10,
            description="Number of major prism faces.",
        ),
        "taper": ParameterMetadata(
            "Taper", "float", 0.30, minimum=0.15, maximum=0.50,
            description="Fraction of length occupied by the termination.",
        ),
        "irregularity": ParameterMetadata(
            "Irregularity", "float", 0.14, minimum=0.0, maximum=0.50,
            description="Seeded variation in facet width and axial alignment.",
        ),
        "seed": ParameterMetadata(
            "Seed", "integer", 13, minimum=0, maximum=2147483647,
            description="Deterministic shape variation key.",
        ),
        "resolution": ParameterMetadata(
            "Resolution", "integer", 33, minimum=21, maximum=41,
            description="Axial sampling density for subtle facet variation.",
            preview_resolutions=(21, 25),
        ),
    },
    available=True,
)
