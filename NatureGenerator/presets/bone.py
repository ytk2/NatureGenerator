"""Classic Bone preset definition."""

from .preset import NaturePreset, ParameterMetadata


BONE_PRESET = NaturePreset(
    preset_id="bone",
    display_name="Bone",
    category="biological",
    description="Stylized long bone with a curved shaft and enlarged ends.",
    generator_id="bone",
    default_parameters={
        "length": 100.0,
        "shaft_radius": 12.0,
        "end_scale": 1.6,
        "curvature": 0.28,
        "asymmetry": 0.22,
        "surface_detail": 0.12,
        "seed": 7,
        "resolution": 33,
    },
    parameter_metadata={
        "length": ParameterMetadata(
            "Length", "length", 100.0, minimum=60.0, maximum=180.0,
            unit="mm",
            description="Nominal end-to-end extent of the long bone.",
        ),
        "shaft_radius": ParameterMetadata(
            "Shaft Radius", "length", 12.0, minimum=8.0, maximum=22.0,
            unit="mm", description="Nominal radius of the central shaft.",
        ),
        "end_scale": ParameterMetadata(
            "End Scale", "float", 1.6, minimum=1.2, maximum=2.1,
            description="Relative enlargement of both rounded bone ends.",
        ),
        "curvature": ParameterMetadata(
            "Curvature", "float", 0.28, minimum=0.0, maximum=1.0,
            description="Amount of smooth shaft bowing.",
        ),
        "asymmetry": ParameterMetadata(
            "Asymmetry", "float", 0.22, minimum=0.0, maximum=1.0,
            description="Difference in end placement and proportions.",
        ),
        "surface_detail": ParameterMetadata(
            "Surface Detail", "float", 0.12, minimum=0.0, maximum=0.40,
            description="Amplitude of shallow deterministic organic variation.",
        ),
        "seed": ParameterMetadata(
            "Seed", "integer", 7, minimum=0, maximum=2147483647,
            description="Deterministic shape variation key.",
        ),
        "resolution": ParameterMetadata(
            "Resolution", "integer", 33, minimum=21, maximum=41,
            description="Voxel samples per axis.",
            preview_resolutions=(21, 25),
        ),
    },
    available=True,
)
