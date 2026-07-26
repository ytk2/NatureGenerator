"""Validated immutable request and metadata for Gyroid Volume generation."""

from dataclasses import dataclass
from enum import Enum
import math
import re
from typing import Any, Tuple


class VolumeExecutionContext(Enum):
    PREVIEW = "preview"
    APPLY = "apply"


@dataclass(frozen=True)
class VolumeParameterDefinition:
    parameter_id: str
    display_name: str
    value_type: str
    default_value: Any
    minimum: Any
    maximum: Any
    unit: str = ""

    def __post_init__(self) -> None:
        if re.fullmatch(r"[a-z][a-z0-9_]*", self.parameter_id) is None:
            raise ValueError("parameter_id must be a stable identifier")
        if not self.display_name:
            raise ValueError("display_name must be non-empty")
        if self.value_type not in ("float", "integer", "length"):
            raise ValueError("unsupported volume parameter type")
        self.validate(self.default_value)

    def validate(self, value: Any) -> Any:
        if self.value_type == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError("{} must be an integer".format(
                    self.display_name
                ))
            normalized = value
        else:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError("{} must be numeric".format(self.display_name))
            normalized = float(value)
            if not math.isfinite(normalized):
                raise ValueError("{} must be finite".format(self.display_name))
        if normalized < self.minimum or normalized > self.maximum:
            raise ValueError(
                "{} must be between {} and {}".format(
                    self.display_name, self.minimum, self.maximum
                )
            )
        return normalized


VOLUME_PARAMETER_DEFINITIONS: Tuple[VolumeParameterDefinition, ...] = (
    VolumeParameterDefinition("width", "Width", "length", 60.0, 1.0, 500.0, "mm"),
    VolumeParameterDefinition("depth", "Depth", "length", 60.0, 1.0, 500.0, "mm"),
    VolumeParameterDefinition("height", "Height", "length", 60.0, 1.0, 500.0, "mm"),
    VolumeParameterDefinition("period", "Period", "length", 20.0, 1.0, 500.0, "mm"),
    VolumeParameterDefinition("iso_value", "Iso Value", "float", 0.0, -1.5, 1.5),
    VolumeParameterDefinition("resolution_x", "Resolution X", "integer", 40, 8, 160),
    VolumeParameterDefinition("resolution_y", "Resolution Y", "integer", 40, 8, 160),
    VolumeParameterDefinition("resolution_z", "Resolution Z", "integer", 40, 8, 160),
    VolumeParameterDefinition("phase_x", "Phase X", "float", 0.0, -6.283, 6.283, "rad"),
    VolumeParameterDefinition("phase_y", "Phase Y", "float", 0.0, -6.283, 6.283, "rad"),
    VolumeParameterDefinition("phase_z", "Phase Z", "float", 0.0, -6.283, 6.283, "rad"),
)


@dataclass(frozen=True)
class GyroidVolumeRequest:
    width: float = 60.0
    depth: float = 60.0
    height: float = 60.0
    period: float = 20.0
    iso_value: float = 0.0
    resolution_x: int = 40
    resolution_y: int = 40
    resolution_z: int = 40
    phase_x: float = 0.0
    phase_y: float = 0.0
    phase_z: float = 0.0
    execution_context: VolumeExecutionContext = VolumeExecutionContext.APPLY

    def __post_init__(self) -> None:
        values = {
            definition.parameter_id: definition.validate(
                getattr(self, definition.parameter_id)
            )
            for definition in VOLUME_PARAMETER_DEFINITIONS
        }
        if not isinstance(self.execution_context, VolumeExecutionContext):
            raise TypeError(
                "execution_context must be a VolumeExecutionContext"
            )
        for name, value in values.items():
            object.__setattr__(self, name, value)

    @property
    def resolution(self) -> Tuple[int, int, int]:
        return (self.resolution_x, self.resolution_y, self.resolution_z)

    @property
    def minimum(self) -> Tuple[float, float, float]:
        return (-self.width * 0.5, -self.depth * 0.5, -self.height * 0.5)

    @property
    def maximum(self) -> Tuple[float, float, float]:
        return (self.width * 0.5, self.depth * 0.5, self.height * 0.5)
