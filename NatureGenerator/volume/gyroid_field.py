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

    @property
    def type_id(self) -> str:
        return "gyroid"

    @property
    def normalization_factor(self) -> float:
        return 1.0

    def sample(self, x: float, y: float, z: float) -> float:
        gx, gy, gz = self.gyroid_coordinates(x, y, z)
        return self.normalized_sample(gx, gy, gz)

    def normalized_sample(self, gx: float, gy: float, gz: float) -> float:
        """Evaluate the released raw Gyroid formula in normalized coordinates."""

        return (
            math.sin(gx) * math.cos(gy)
            + math.sin(gy) * math.cos(gz)
            + math.sin(gz) * math.cos(gx)
        )

    def gyroid_coordinates(self, x: float, y: float, z: float):
        """Map world millimetres to dimensionless Gyroid coordinates."""

        scale = (2.0 * math.pi) / float(self.period)
        return (
            scale * x + float(self.phase_x),
            scale * y + float(self.phase_y),
            scale * z + float(self.phase_z),
        )

    def coordinates(self, x: float, y: float, z: float):
        return self.gyroid_coordinates(x, y, z)

    def gradient(self, x: float, y: float, z: float):
        """Return the analytical world-space gradient in inverse millimetres."""

        gx, gy, gz = self.gyroid_coordinates(x, y, z)
        scale = (2.0 * math.pi) / float(self.period)
        return (
            scale * (
                math.cos(gx) * math.cos(gy)
                - math.sin(gz) * math.sin(gx)
            ),
            scale * (
                -math.sin(gx) * math.sin(gy)
                + math.cos(gy) * math.cos(gz)
            ),
            scale * (
                -math.sin(gy) * math.sin(gz)
                + math.cos(gz) * math.cos(gx)
            ),
        )

    def __call__(self, x: float, y: float, z: float) -> float:
        return self.sample(x, y, z)
