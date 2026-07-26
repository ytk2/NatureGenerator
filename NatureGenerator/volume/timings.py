"""Immutable diagnostic timings for Fusion-independent volume generation."""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class VolumeGenerationTimings:
    validation_and_estimation: float
    scalar_field_sampling: float
    iso_surface_extraction: float
    boundary_closure: float
    geometry_validation: float
    total_core: float

    def __post_init__(self) -> None:
        for value in (
            self.validation_and_estimation,
            self.scalar_field_sampling,
            self.iso_surface_extraction,
            self.boundary_closure,
            self.geometry_validation,
            self.total_core,
        ):
            if not math.isfinite(value) or value < 0.0:
                raise ValueError("timings must be finite and non-negative")
