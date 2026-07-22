"""Immutable Fusion-independent generator variant definitions."""

from dataclasses import dataclass
import math
import re
from types import MappingProxyType
from typing import Any, Mapping


def _text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("{} must be a non-empty string".format(name))
    return value.strip()


def _stable_id(value: str, name: str) -> str:
    value = _text(value, name)
    if re.fullmatch(r"[a-z][a-z0-9_]*", value) is None:
        raise ValueError("{} must be a lowercase stable identifier".format(name))
    return value


def _value(value: Any, name: str) -> Any:
    if isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise TypeError("{} must be a finite bool, int, float, or string".format(name))


@dataclass(frozen=True)
class VariantDefinition:
    """One named configuration of an existing nature preset."""

    variant_id: str
    preset_id: str
    display_name: str
    description: str
    parameter_values: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "variant_id", _stable_id(self.variant_id, "variant_id")
        )
        object.__setattr__(self, "preset_id", _stable_id(self.preset_id, "preset_id"))
        object.__setattr__(
            self, "display_name", _text(self.display_name, "display_name")
        )
        object.__setattr__(self, "description", _text(self.description, "description"))
        if not isinstance(self.parameter_values, Mapping):
            raise TypeError("parameter_values must be a mapping")
        copied = {
            _stable_id(key, "parameter id"): _value(value, key)
            for key, value in self.parameter_values.items()
        }
        if not copied:
            raise ValueError("parameter_values must not be empty")
        object.__setattr__(self, "parameter_values", MappingProxyType(copied))
