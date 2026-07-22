"""Immutable, Fusion-independent input for one generation operation."""

from dataclasses import dataclass
import math
import re
from types import MappingProxyType
from typing import Any, Mapping


DEFAULT_RESOLUTION = 17
MIN_RESOLUTION = 9
MAX_RESOLUTION = 41


def validate_resolution(value: int) -> int:
    """Return a safe samples-per-axis value or raise ``ValueError``."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("resolution must be an integer")
    if value < MIN_RESOLUTION or value > MAX_RESOLUTION:
        raise ValueError(
            "resolution must be between {} and {} samples per axis".format(
                MIN_RESOLUTION, MAX_RESOLUTION
            )
        )
    return value


def _parameter_value(value: Any, parameter_id: str) -> Any:
    if isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise TypeError(
        "parameter {!r} must be a finite bool, int, float, or string".format(
            parameter_id
        )
    )


@dataclass(frozen=True)
class GenerationRequest:
    """Preset selection, immutable overrides, and sampling resolution."""

    preset_id: str
    parameter_overrides: Mapping[str, Any]
    resolution: int = DEFAULT_RESOLUTION

    def __post_init__(self) -> None:
        if not isinstance(self.preset_id, str) or re.fullmatch(
            r"[a-z][a-z0-9_]*", self.preset_id
        ) is None:
            raise ValueError("preset_id must be a lowercase stable identifier")
        if not isinstance(self.parameter_overrides, Mapping):
            raise TypeError("parameter_overrides must be a mapping")
        overrides = {}
        for parameter_id, value in self.parameter_overrides.items():
            if not isinstance(parameter_id, str) or not parameter_id:
                raise ValueError("parameter override IDs must be non-empty strings")
            overrides[parameter_id] = _parameter_value(value, parameter_id)

        object.__setattr__(self, "parameter_overrides", MappingProxyType(overrides))
        object.__setattr__(self, "resolution", validate_resolution(self.resolution))
