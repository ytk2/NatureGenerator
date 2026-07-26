"""Analytical deterministic Gyroid field for volumetric generation."""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class GyroidVolumeField:
    period: float
    phase_x: float = 0.0
    phase_y: float = 0.0
    phase_z: float = 0.0

    def __post_init__(self) -> None:
        values = (
            self.period, self.phase_x, self.phase_y, self.phase_z
        )
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for value in values
        ):
            raise ValueError("Gyroid field parameters must be finite numbers")
        if self.period <= 0.0:
            raise ValueError("period must be greater than zero")

    def sample(self, x: float, y: float, z: float) -> float:
        scale = (2.0 * math.pi) / float(self.period)
        gx = scale * x + float(self.phase_x)
        gy = scale * y + float(self.phase_y)
        gz = scale * z + float(self.phase_z)
        return (
            math.sin(gx) * math.cos(gy)
            + math.sin(gy) * math.cos(gz)
            + math.sin(gz) * math.cos(gx)
        )

    def __call__(self, x: float, y: float, z: float) -> float:
        return self.sample(x, y, z)
