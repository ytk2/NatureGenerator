"""Immutable Bone Family metadata for the Preset Registry architecture."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Tuple


@dataclass(frozen=True)
class BoneFamilyDefinition:
    """One Bone presentation backed by the Bone generator."""

    family_id: str
    display_name: str
    parameter_values: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "parameter_values", MappingProxyType(dict(self.parameter_values))
        )


CLASSIC_BONE_FAMILY = BoneFamilyDefinition(
    "classic_bone",
    "Classic Bone",
    {
        "length": 100.0,
        "shaft_radius": 12.0,
        "end_scale": 1.6,
        "curvature": 0.28,
        "asymmetry": 0.22,
        "surface_detail": 0.12,
        "seed": 7,
        "resolution": 33,
    },
)


class BoneFamilyRegistry:
    """Resolve Bone Family metadata without generator or UI branching."""

    preset_id = "bone"
    _definitions = MappingProxyType({
        CLASSIC_BONE_FAMILY.family_id: CLASSIC_BONE_FAMILY,
    })

    @classmethod
    def get(cls, family_id: str) -> BoneFamilyDefinition:
        try:
            return cls._definitions[family_id]
        except (KeyError, TypeError) as error:
            raise KeyError("unknown bone family: {!r}".format(family_id)) from error

    @classmethod
    def list_all(cls) -> Tuple[BoneFamilyDefinition, ...]:
        return (CLASSIC_BONE_FAMILY,)
