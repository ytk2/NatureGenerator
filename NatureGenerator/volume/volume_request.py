"""Validated immutable request and metadata for TPMS Volume generation."""

from dataclasses import dataclass, field
from enum import Enum
import math
import re
from typing import Any, Tuple

from .domain_sizing import (
    DOMAIN_CELL_COUNT_MAX,
    DOMAIN_CELL_COUNT_MIN,
    DOMAIN_DIMENSION_MAX_MM,
    DOMAIN_DIMENSION_MIN_MM,
    DomainDefinition,
    DomainMode,
    resolve_domain,
)


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


class TPMSType(Enum):
    GYROID = "gyroid"
    SCHWARZ_P = "schwarz_p"
    DIAMOND = "diamond"
    NEOVIUS = "neovius"


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
        "tpms_type",
        "TPMS Type",
        "enum",
        "gyroid",
        choices=(
            ("gyroid", "Gyroid"),
            ("schwarz_p", "Schwarz P"),
            ("diamond", "Diamond"),
            ("neovius", "Neovius"),
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
    VolumeParameterDefinition(
        "domain_mode",
        "Domain Mode",
        "enum",
        "dimensions",
        choices=(
            ("dimensions", "Dimensions"),
            ("cell_count", "Cell Count"),
        ),
    ),
    VolumeParameterDefinition(
        "width",
        "Width",
        "length",
        60.0,
        DOMAIN_DIMENSION_MIN_MM,
        DOMAIN_DIMENSION_MAX_MM,
        "mm",
        visible_when=("domain_mode", ("dimensions",)),
    ),
    VolumeParameterDefinition(
        "depth",
        "Depth",
        "length",
        60.0,
        DOMAIN_DIMENSION_MIN_MM,
        DOMAIN_DIMENSION_MAX_MM,
        "mm",
        visible_when=("domain_mode", ("dimensions",)),
    ),
    VolumeParameterDefinition(
        "height",
        "Height",
        "length",
        60.0,
        DOMAIN_DIMENSION_MIN_MM,
        DOMAIN_DIMENSION_MAX_MM,
        "mm",
        visible_when=("domain_mode", ("dimensions",)),
    ),
    VolumeParameterDefinition(
        "cells_x",
        "Cells X",
        "integer",
        1,
        DOMAIN_CELL_COUNT_MIN,
        DOMAIN_CELL_COUNT_MAX,
        visible_when=("domain_mode", ("cell_count",)),
    ),
    VolumeParameterDefinition(
        "cells_y",
        "Cells Y",
        "integer",
        1,
        DOMAIN_CELL_COUNT_MIN,
        DOMAIN_CELL_COUNT_MAX,
        visible_when=("domain_mode", ("cell_count",)),
    ),
    VolumeParameterDefinition(
        "cells_z",
        "Cells Z",
        "integer",
        1,
        DOMAIN_CELL_COUNT_MIN,
        DOMAIN_CELL_COUNT_MAX,
        visible_when=("domain_mode", ("cell_count",)),
    ),
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
    tpms_type: TPMSType = TPMSType.GYROID
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
    domain_mode: DomainMode = DomainMode.DIMENSIONS
    cells_x: int = 1
    cells_y: int = 1
    cells_z: int = 1
    _domain: DomainDefinition = field(init=False, repr=False)

    def __post_init__(self) -> None:
        values = {}
        for definition in VOLUME_PARAMETER_DEFINITIONS:
            raw = getattr(self, definition.parameter_id)
            enum_type = {
                "preview_quality": PreviewQuality,
                "tpms_type": TPMSType,
                "geometry_mode": GeometryMode,
                "domain_mode": DomainMode,
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
            elif definition.parameter_id in (
                "width",
                "depth",
                "height",
                "cells_x",
                "cells_y",
                "cells_z",
            ):
                values[definition.parameter_id] = raw
            else:
                values[definition.parameter_id] = definition.validate(raw)
        if not isinstance(self.execution_context, VolumeExecutionContext):
            raise TypeError(
                "execution_context must be a VolumeExecutionContext"
            )
        for name, value in values.items():
            enum_type = {
                "preview_quality": PreviewQuality,
                "tpms_type": TPMSType,
                "geometry_mode": GeometryMode,
                "domain_mode": DomainMode,
                "boundary_mode": BoundaryMode,
            }.get(name)
            object.__setattr__(
                self,
                name,
                enum_type(value) if enum_type is not None else value,
            )
        domain = resolve_domain(
            self.domain_mode,
            self.width,
            self.depth,
            self.height,
            self.cells_x,
            self.cells_y,
            self.cells_z,
            self.period,
        )
        object.__setattr__(self, "_domain", domain)
        if self.domain_mode is DomainMode.DIMENSIONS:
            for name, value in zip(
                ("width", "depth", "height"),
                domain.resolved_dimensions,
            ):
                object.__setattr__(self, name, value)
            for name in ("cells_x", "cells_y", "cells_z"):
                raw = getattr(self, name)
                if isinstance(raw, bool) or not isinstance(raw, int):
                    raise TypeError("{} must be an integer".format(
                        name.replace("_", " ").title()
                    ))
        else:
            for name, value in zip(
                ("cells_x", "cells_y", "cells_z"),
                domain.requested_cell_counts,
            ):
                object.__setattr__(self, name, value)
            for name in ("width", "depth", "height"):
                raw = getattr(self, name)
                if (
                    isinstance(raw, bool)
                    or not isinstance(raw, (int, float))
                    or not math.isfinite(float(raw))
                ):
                    raise ValueError("{} must be a finite number".format(
                        name.title()
                    ))
                object.__setattr__(self, name, float(raw))

    @property
    def resolution(self) -> Tuple[int, int, int]:
        return (self.resolution_x, self.resolution_y, self.resolution_z)

    @property
    def domain(self) -> DomainDefinition:
        return self._domain

    @property
    def resolved_dimensions(self) -> Tuple[float, float, float]:
        return self.domain.resolved_dimensions

    @property
    def effective_cell_counts(self) -> Tuple[float, float, float]:
        return self.domain.effective_cell_counts

    @property
    def minimum(self) -> Tuple[float, float, float]:
        return self.domain.minimum

    @property
    def maximum(self) -> Tuple[float, float, float]:
        return self.domain.maximum


# Backward-compatible default-Gyroid request name and generalized TPMS name
# intentionally share one immutable implementation.
TPMSVolumeRequest = GyroidVolumeRequest
