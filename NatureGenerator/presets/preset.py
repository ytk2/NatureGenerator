"""Immutable definitions for natural-form presets and their parameters."""

from dataclasses import dataclass
import math
import re
from types import MappingProxyType
from typing import Any, Mapping, Optional


_PARAMETER_TYPES = {"bool", "float", "int", "integer", "length", "str"}


def _nonempty_text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("{} must be a non-empty string".format(name))
    return value.strip()


def _stable_id(value: str, name: str) -> str:
    value = _nonempty_text(value, name)
    if re.fullmatch(r"[a-z][a-z0-9_]*", value) is None:
        raise ValueError("{} must be a lowercase stable identifier".format(name))
    return value


def _parameter_value(value: Any, name: str) -> Any:
    if isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise TypeError("{} must be a finite bool, int, float, or string".format(name))


@dataclass(frozen=True)
class ParameterMetadata:
    """Presentation and validation metadata for one exposed parameter."""

    display_name: str
    value_type: str
    default_value: Any
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    unit: str = ""
    description: str = ""

    def __post_init__(self) -> None:
        display_name = _nonempty_text(self.display_name, "display_name")
        value_type = _nonempty_text(self.value_type, "value_type").lower()
        if value_type not in _PARAMETER_TYPES:
            raise ValueError("value_type must be one of {}".format(sorted(_PARAMETER_TYPES)))
        default_value = _parameter_value(self.default_value, "default_value")

        valid_default = {
            "bool": isinstance(default_value, bool),
            "float": isinstance(default_value, (int, float))
            and not isinstance(default_value, bool),
            "int": isinstance(default_value, int) and not isinstance(default_value, bool),
            "integer": isinstance(default_value, int)
            and not isinstance(default_value, bool),
            "length": isinstance(default_value, (int, float))
            and not isinstance(default_value, bool),
            "str": isinstance(default_value, str),
        }[value_type]
        if not valid_default:
            raise TypeError("default_value does not match value_type")

        minimum = self.minimum
        maximum = self.maximum
        for boundary, name in ((minimum, "minimum"), (maximum, "maximum")):
            if boundary is not None and (
                isinstance(boundary, bool)
                or not isinstance(boundary, (int, float))
                or not math.isfinite(float(boundary))
            ):
                raise TypeError("{} must be a finite number or None".format(name))
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValueError("minimum cannot exceed maximum")
        if value_type in ("float", "int", "integer", "length"):
            if minimum is not None and default_value < minimum:
                raise ValueError("default_value cannot be below minimum")
            if maximum is not None and default_value > maximum:
                raise ValueError("default_value cannot exceed maximum")
        elif minimum is not None or maximum is not None:
            raise ValueError("minimum and maximum apply only to numeric parameters")

        if not isinstance(self.unit, str) or not isinstance(self.description, str):
            raise TypeError("unit and description must be strings")
        object.__setattr__(self, "display_name", display_name)
        object.__setattr__(self, "value_type", value_type)
        object.__setattr__(self, "default_value", default_value)


@dataclass(frozen=True)
class NaturePreset:
    """Immutable user-facing definition of a natural form."""

    preset_id: str
    display_name: str
    category: str
    description: str
    generator_id: str
    default_parameters: Mapping[str, Any]
    parameter_metadata: Optional[Mapping[str, ParameterMetadata]] = None
    available: bool = False
    unavailable_reason: str = ""

    def __post_init__(self) -> None:
        for attribute in ("display_name", "category", "description"):
            object.__setattr__(
                self,
                attribute,
                _nonempty_text(getattr(self, attribute), attribute),
            )
        object.__setattr__(self, "preset_id", _stable_id(self.preset_id, "preset_id"))
        object.__setattr__(
            self, "generator_id", _stable_id(self.generator_id, "generator_id")
        )
        if not isinstance(self.default_parameters, Mapping):
            raise TypeError("default_parameters must be a mapping")
        defaults = {
            _nonempty_text(key, "parameter id"): _parameter_value(value, key)
            for key, value in self.default_parameters.items()
        }

        metadata_source = {} if self.parameter_metadata is None else self.parameter_metadata
        if not isinstance(metadata_source, Mapping):
            raise TypeError("parameter_metadata must be a mapping or None")
        metadata = {}
        for key, value in metadata_source.items():
            parameter_id = _nonempty_text(key, "parameter metadata id")
            if not isinstance(value, ParameterMetadata):
                raise TypeError("parameter metadata values must be ParameterMetadata")
            if parameter_id not in defaults:
                raise ValueError("parameter metadata requires a matching default value")
            if defaults[parameter_id] != value.default_value:
                raise ValueError("parameter metadata default must match preset defaults")
            metadata[parameter_id] = value

        if not isinstance(self.available, bool):
            raise TypeError("available must be a bool")
        if not isinstance(self.unavailable_reason, str):
            raise TypeError("unavailable_reason must be a string")
        if not self.available and not self.unavailable_reason.strip():
            raise ValueError("unavailable presets must explain why they are unavailable")
        if self.available and self.unavailable_reason:
            raise ValueError("available presets cannot have an unavailable reason")

        object.__setattr__(self, "default_parameters", MappingProxyType(defaults))
        object.__setattr__(self, "parameter_metadata", MappingProxyType(metadata))
        object.__setattr__(self, "unavailable_reason", self.unavailable_reason.strip())
