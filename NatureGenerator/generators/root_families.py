"""Immutable Root Family metadata for the Preset Registry architecture."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Tuple


@dataclass(frozen=True)
class RootFamilyDefinition:
    """One Root presentation backed by the existing Root generator."""

    family_id: str
    display_name: str
    parameter_values: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "parameter_values", MappingProxyType(dict(self.parameter_values))
        )


CLASSIC_ROOT_FAMILY = RootFamilyDefinition(
    "classic_root",
    "Classic Root",
    {
        "length": 100.0,
        "root_radius": 8.0,
        "branch_count": 5,
        "branching": 0.45,
        "spread": 0.65,
        "taper": 0.65,
        "gravity": 0.70,
        "seed": 11,
        "resolution": 37,
    },
)


class RootFamilyRegistry:
    """Resolve Root Family metadata without generator or UI branching."""

    preset_id = "root"
    _definitions = MappingProxyType({
        CLASSIC_ROOT_FAMILY.family_id: CLASSIC_ROOT_FAMILY,
    })

    @classmethod
    def get(cls, family_id: str) -> RootFamilyDefinition:
        try:
            return cls._definitions[family_id]
        except (KeyError, TypeError) as error:
            raise KeyError("unknown root family: {!r}".format(family_id)) from error

    @classmethod
    def list_all(cls) -> Tuple[RootFamilyDefinition, ...]:
        return (CLASSIC_ROOT_FAMILY,)
