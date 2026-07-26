"""Deterministic analytical TPMS field registry and factory."""

from dataclasses import dataclass
import math
from typing import Dict, Tuple

from .gyroid_field import GyroidVolumeField
from .volume_request import TPMSType


TPMS_TYPE_ORDER: Tuple[TPMSType, ...] = (
    TPMSType.GYROID,
    TPMSType.SCHWARZ_P,
    TPMSType.DIAMOND,
    TPMSType.NEOVIUS,
)

# Gyroid remains raw for exact compatibility. Other fields are scaled to keep
# their ordinary numerical ranges useful with the shared Iso Value control.
TPMS_NORMALIZATION_FACTORS: Dict[TPMSType, float] = {
    TPMSType.GYROID: 1.0,
    TPMSType.SCHWARZ_P: 1.0 / 3.0,
    TPMSType.DIAMOND: 1.0 / 2.0,
    TPMSType.NEOVIUS: 1.0 / 13.0,
}


@dataclass(frozen=True)
class AnalyticalTPMSField:
    """World-space analytical field for one non-Gyroid TPMS family."""

    tpms_type: TPMSType
    period: float
    phase_x: float = 0.0
    phase_y: float = 0.0
    phase_z: float = 0.0

    def __post_init__(self) -> None:
        if self.tpms_type is TPMSType.GYROID:
            raise ValueError("Gyroid uses its compatibility field")
        values = (self.period, self.phase_x, self.phase_y, self.phase_z)
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for value in values
        ):
            raise ValueError("TPMS field parameters must be finite numbers")
        if self.period <= 0.0:
            raise ValueError("period must be greater than zero")

    @property
    def type_id(self) -> str:
        return self.tpms_type.value

    @property
    def normalization_factor(self) -> float:
        return TPMS_NORMALIZATION_FACTORS[self.tpms_type]

    def coordinates(self, x: float, y: float, z: float):
        scale = (2.0 * math.pi) / float(self.period)
        return (
            scale * x + float(self.phase_x),
            scale * y + float(self.phase_y),
            scale * z + float(self.phase_z),
        )

    def normalized_sample(self, x: float, y: float, z: float) -> float:
        sx, sy, sz = math.sin(x), math.sin(y), math.sin(z)
        cx, cy, cz = math.cos(x), math.cos(y), math.cos(z)
        if self.tpms_type is TPMSType.SCHWARZ_P:
            raw = cx + cy + cz
        elif self.tpms_type is TPMSType.DIAMOND:
            raw = (
                sx * sy * sz
                + sx * cy * cz
                + cx * sy * cz
                + cx * cy * sz
            )
        else:
            raw = 3.0 * (cx + cy + cz) + 4.0 * cx * cy * cz
        return self.normalization_factor * raw

    def sample(self, x: float, y: float, z: float) -> float:
        return self.normalized_sample(*self.coordinates(x, y, z))

    def normalized_gradient(self, x: float, y: float, z: float):
        sx, sy, sz = math.sin(x), math.sin(y), math.sin(z)
        cx, cy, cz = math.cos(x), math.cos(y), math.cos(z)
        if self.tpms_type is TPMSType.SCHWARZ_P:
            raw = (-sx, -sy, -sz)
        elif self.tpms_type is TPMSType.DIAMOND:
            raw = (
                cx * sy * sz + cx * cy * cz
                - sx * sy * cz - sx * cy * sz,
                sx * cy * sz - sx * sy * cz
                + cx * cy * cz - cx * sy * sz,
                sx * sy * cz - sx * cy * sz
                - cx * sy * sz + cx * cy * cz,
            )
        else:
            raw = (
                -3.0 * sx - 4.0 * sx * cy * cz,
                -3.0 * sy - 4.0 * cx * sy * cz,
                -3.0 * sz - 4.0 * cx * cy * sz,
            )
        factor = self.normalization_factor
        return tuple(factor * value for value in raw)

    def gradient(self, x: float, y: float, z: float):
        coordinates = self.coordinates(x, y, z)
        scale = (2.0 * math.pi) / float(self.period)
        return tuple(
            scale * value
            for value in self.normalized_gradient(*coordinates)
        )

    def __call__(self, x: float, y: float, z: float) -> float:
        return self.sample(x, y, z)


class TPMSFieldFactory:
    """Resolve the deterministic analytical field for a stable TPMS type."""

    @staticmethod
    def create(
        tpms_type: TPMSType,
        period: float,
        phase_x: float = 0.0,
        phase_y: float = 0.0,
        phase_z: float = 0.0,
    ):
        if not isinstance(tpms_type, TPMSType):
            raise TypeError("tpms_type must be a TPMSType")
        if tpms_type is TPMSType.GYROID:
            return GyroidVolumeField(
                period, phase_x, phase_y, phase_z
            )
        return AnalyticalTPMSField(
            tpms_type, period, phase_x, phase_y, phase_z
        )
