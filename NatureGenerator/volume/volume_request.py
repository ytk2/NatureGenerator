"""Validated immutable request and metadata for Gyroid Volume generation."""

from dataclasses import dataclass
from enum import Enum
import math
import re
from typing import Any, Tuple


class VolumeExecutionContext(Enum):
    PREVIEW = "preview"
    APPLY = "apply"


class BoundaryMode(Enum):
    OPEN = "open"
    CAP = "cap"


class GeometryMode(Enum):
    SURFACE = "surface"
    THICKENED = "thickened"


class PreviewQuality(Enum):
    DRAFT = "draft"
    STANDARD = "standard"
    FINAL = "final"


@dataclass(frozen=True)
class VolumeParameterDefinition:
    parameter_id: str
    display_name: str
    value_type: str
    default_value: Any
    minimum: Any = None
    maximum: Any = None
    unit: str = ""
    choices: Tuple[Tuple[str, str], ...] = ()
    visible_when: Tuple[str, Tuple[str, ...]] = ()

    def __post_init__(self) -> None:
        if re.fullmatch(r"[a-z][a-z0-9_]*", self.parameter_id) is None:
            raise ValueError("parameter_id must be a stable identifier")
        if not self.display_name:
            raise ValueError("display_name must be non-empty")
        if self.value_type not in ("enum", "float", "integer", "length"):
            raise ValueError("unsupported volume parameter type")
        if self.value_type == "enum" and not self.choices:
            raise ValueError("enum parameters require choices")
        if self.visible_when:
            if (
                len(self.visible_when) != 2
                or re.fullmatch(
                    r"[a-z][a-z0-9_]*", self.visible_when[0]
                ) is None
                or not self.visible_when[1]
            ):
                raise ValueError("visible_when must name a parameter and values")
        self.validate(self.default_value)

    def validate(self, value: Any) -> Any:
        if self.value_type == "enum":
            if not isinstance(value, str):
                raise TypeError("{} must be a string".format(
                    self.display_name
                ))
            allowed = {item[0] for item in self.choices}
            if value not in allowed:
                raise ValueError("{} must be one of {}".format(
                    self.display_name, ", ".join(sorted(allowed))
                ))
            return value
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
        if (
            self.minimum is not None and normalized < self.minimum
        ) or (
            self.maximum is not None and normalized > self.maximum
        ):
            raise ValueError(
                "{} must be between {} and {}".format(
                    self.display_name, self.minimum, self.maximum
                )
            )
        return normalized


VOLUME_PARAMETER_DEFINITIONS: Tuple[VolumeParameterDefinition, ...] = (
    VolumeParameterDefinition(
        "preview_quality",
        "Preview Quality",
        "enum",
        "standard",
        choices=(
            ("draft", "Draft"),
            ("standard", "Standard"),
            ("final", "Final"),
        ),
    ),
    VolumeParameterDefinition(
        "geometry_mode",
        "Geometry Mode",
        "enum",
        "surface",
        choices=(("surface", "Surface"), ("thickened", "Thickened")),
    ),
    VolumeParameterDefinition(
        "wall_thickness",
        "Wall Thickness",
        "length",
        1.0,
        0.1,
        20.0,
        "mm",
        visible_when=("geometry_mode", ("thickened",)),
    ),
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
    VolumeParameterDefinition(
        "boundary_mode",
        "Boundary Mode",
        "enum",
        "open",
        choices=(("open", "Open"), ("cap", "Cap")),
    ),
)


@dataclass(frozen=True)
class GyroidVolumeRequest:
    preview_quality: PreviewQuality = PreviewQuality.STANDARD
    geometry_mode: GeometryMode = GeometryMode.SURFACE
    wall_thickness: float = 1.0
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
    boundary_mode: BoundaryMode = BoundaryMode.OPEN
    execution_context: VolumeExecutionContext = VolumeExecutionContext.APPLY

    def __post_init__(self) -> None:
        values = {}
        for definition in VOLUME_PARAMETER_DEFINITIONS:
            raw = getattr(self, definition.parameter_id)
            enum_type = {
                "preview_quality": PreviewQuality,
                "geometry_mode": GeometryMode,
                "boundary_mode": BoundaryMode,
            }.get(definition.parameter_id)
            if enum_type is not None:
                if not isinstance(raw, enum_type):
                    raise TypeError(
                        "{} must be a {}".format(
                            definition.parameter_id, enum_type.__name__
                        )
                    )
                raw = raw.value
            if (
                definition.parameter_id == "wall_thickness"
                and self.geometry_mode is GeometryMode.SURFACE
            ):
                if (
                    isinstance(raw, bool)
                    or not isinstance(raw, (int, float))
                    or not math.isfinite(float(raw))
                ):
                    raise ValueError(
                        "Wall Thickness must be a finite number"
                    )
                values[definition.parameter_id] = float(raw)
            else:
                values[definition.parameter_id] = definition.validate(raw)
        if not isinstance(self.execution_context, VolumeExecutionContext):
            raise TypeError(
                "execution_context must be a VolumeExecutionContext"
            )
        for name, value in values.items():
            enum_type = {
                "preview_quality": PreviewQuality,
                "geometry_mode": GeometryMode,
                "boundary_mode": BoundaryMode,
            }.get(name)
            object.__setattr__(
                self,
                name,
                enum_type(value) if enum_type is not None else value,
            )

    @property
    def resolution(self) -> Tuple[int, int, int]:
        return (self.resolution_x, self.resolution_y, self.resolution_z)

    @property
    def minimum(self) -> Tuple[float, float, float]:
        return (-self.width * 0.5, -self.depth * 0.5, -self.height * 0.5)

    @property
    def maximum(self) -> Tuple[float, float, float]:
        return (self.width * 0.5, self.depth * 0.5, self.height * 0.5)
