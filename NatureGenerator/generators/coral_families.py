"""Immutable Coral Family metadata for the Preset Registry architecture."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Tuple


@dataclass(frozen=True)
class CoralFamilyDefinition:
    """One Coral presentation backed by the existing Coral generator."""

    family_id: str
    display_name: str
    parameter_values: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "parameter_values", MappingProxyType(dict(self.parameter_values))
        )


CLASSIC_CORAL_FAMILY = CoralFamilyDefinition(
    "classic_coral",
    "Classic Coral",
    {
        "cell_size": 14.0,
        "thickness": 0.35,
        "seed": 0,
        "resolution": 17,
    },
)


class CoralFamilyRegistry:
    """Resolve Coral Family metadata without generator or UI branching."""

    preset_id = "coral"
    _definitions = MappingProxyType({
        CLASSIC_CORAL_FAMILY.family_id: CLASSIC_CORAL_FAMILY,
    })

    @classmethod
    def get(cls, family_id: str) -> CoralFamilyDefinition:
        try:
            return cls._definitions[family_id]
        except (KeyError, TypeError) as error:
            raise KeyError("unknown coral family: {!r}".format(family_id)) from error

    @classmethod
    def list_all(cls) -> Tuple[CoralFamilyDefinition, ...]:
        return (CLASSIC_CORAL_FAMILY,)
