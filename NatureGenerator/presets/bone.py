"""Bone preset definition."""

from .preset import NaturePreset, ParameterMetadata


BONE_PRESET = NaturePreset(
    preset_id="bone",
    display_name="Bone",
    category="biological",
    description="Trabecular structure inspired by cancellous bone.",
    generator_id="cellular",
    default_parameters={"cell_size": 6.0, "density": 0.55},
    parameter_metadata={
        "cell_size": ParameterMetadata(
            "Cell Size",
            "float",
            6.0,
            minimum=1.0,
            maximum=30.0,
            unit="mm",
            description="Nominal spacing of the future cellular structure.",
        ),
        "density": ParameterMetadata(
            "Density",
            "float",
            0.55,
            minimum=0.05,
            maximum=0.95,
            description="Reserved material fraction control.",
        ),
    },
    available=False,
    unavailable_reason="The cellular generator is not implemented yet.",
)
