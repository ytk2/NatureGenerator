"""Root preset definition."""

from .preset import NaturePreset, ParameterMetadata


ROOT_PRESET = NaturePreset(
    preset_id="root",
    display_name="Root",
    category="botanical",
    description="Connected tapered primary and lateral root system.",
    generator_id="root",
    default_parameters={
        "length": 100.0,
        "root_radius": 8.0,
        "branch_count": 5,
        "branching": 0.45,
        "spread": 0.65,
        "taper": 0.65,
        "gravity": 0.70,
        "seed": 11,
        "resolution": 37,
    },
    parameter_metadata={
        "length": ParameterMetadata(
            "Length", "length", 100.0, minimum=40.0, maximum=180.0,
            unit="mm", description="Primary downward root extent.",
        ),
        "root_radius": ParameterMetadata(
            "Root Radius", "length", 8.0, minimum=4.0, maximum=20.0,
            unit="mm", description="Starting radius at the root crown.",
        ),
        "branch_count": ParameterMetadata(
            "Branch Count", "integer", 5, minimum=1, maximum=8,
            description="Number of first-stage lateral roots.",
        ),
        "branching": ParameterMetadata(
            "Branching", "float", 0.45, minimum=0.0, maximum=1.0,
            description="Secondary branching strength and probability.",
        ),
        "spread": ParameterMetadata(
            "Spread", "float", 0.65, minimum=0.1, maximum=1.0,
            description="Lateral direction strength.",
        ),
        "taper": ParameterMetadata(
            "Taper", "float", 0.65, minimum=0.2, maximum=0.85,
            description="Radius reduction toward terminal tips.",
        ),
        "gravity": ParameterMetadata(
            "Gravity", "float", 0.70, minimum=0.0, maximum=1.0,
            description="Downward growth bias.",
        ),
        "seed": ParameterMetadata(
            "Seed", "integer", 11, minimum=0, maximum=2147483647,
            description="Deterministic variation key.",
        ),
        "resolution": ParameterMetadata(
            "Resolution", "integer", 37, minimum=37, maximum=41,
            description="Voxel samples per axis.",
        ),
    },
    available=True,
)
