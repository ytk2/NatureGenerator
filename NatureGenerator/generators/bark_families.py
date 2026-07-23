"""Immutable Bark Family metadata for the Preset Registry architecture."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Tuple


@dataclass(frozen=True)
class BarkFamilyDefinition:
    """One Bark presentation backed by the existing Bark generator."""

    family_id: str
    display_name: str
    parameter_values: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "parameter_values", MappingProxyType(dict(self.parameter_values))
        )


CLASSIC_BARK_FAMILY = BarkFamilyDefinition(
    "classic_bark",
    "Classic Bark",
    {
        "diameter": 80.0,
        "height": 120.0,
        "bark_depth": 4.0,
        "groove_scale": 18.0,
        "twist": 0.0,
        "seed": 10,
        "resolution": 33,
    },
)


class BarkFamilyRegistry:
    """Resolve Bark Family metadata without generator or UI branching."""

    preset_id = "bark"
    _definitions = MappingProxyType({
        CLASSIC_BARK_FAMILY.family_id: CLASSIC_BARK_FAMILY,
    })

    @classmethod
    def get(cls, family_id: str) -> BarkFamilyDefinition:
        try:
            return cls._definitions[family_id]
        except (KeyError, TypeError) as error:
            raise KeyError("unknown bark family: {!r}".format(family_id)) from error

    @classmethod
    def list_all(cls) -> Tuple[BarkFamilyDefinition, ...]:
        return (CLASSIC_BARK_FAMILY,)
