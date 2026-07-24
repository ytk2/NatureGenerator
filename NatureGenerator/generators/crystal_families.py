"""Immutable Crystal Family metadata for the Preset Registry architecture."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Tuple


@dataclass(frozen=True)
class CrystalFamilyDefinition:
    """One Crystal presentation backed by the Crystal generator."""

    family_id: str
    display_name: str
    parameter_values: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "parameter_values", MappingProxyType(dict(self.parameter_values))
        )


CLASSIC_CRYSTAL_FAMILY = CrystalFamilyDefinition(
    "classic_crystal",
    "Classic Crystal",
    {
        "length": 80.0,
        "width": 28.0,
        "facet_count": 6,
        "taper": 0.30,
        "irregularity": 0.14,
        "seed": 13,
        "resolution": 33,
    },
)


class CrystalFamilyRegistry:
    """Resolve Crystal Family metadata without generator or UI branching."""

    preset_id = "crystal"
    _definitions = MappingProxyType({
        CLASSIC_CRYSTAL_FAMILY.family_id: CLASSIC_CRYSTAL_FAMILY,
    })

    @classmethod
    def get(cls, family_id: str) -> CrystalFamilyDefinition:
        try:
            return cls._definitions[family_id]
        except (KeyError, TypeError) as error:
            raise KeyError(
                "unknown crystal family: {!r}".format(family_id)
            ) from error

    @classmethod
    def list_all(cls) -> Tuple[CrystalFamilyDefinition, ...]:
        return (CLASSIC_CRYSTAL_FAMILY,)
