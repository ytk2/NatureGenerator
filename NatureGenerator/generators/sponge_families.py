"""Immutable Sponge Family metadata for the Preset Registry architecture."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Tuple


@dataclass(frozen=True)
class SpongeFamilyDefinition:
    """One Sponge presentation backed by the Sponge generator."""

    family_id: str
    display_name: str
    parameter_values: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "parameter_values", MappingProxyType(dict(self.parameter_values))
        )


CLASSIC_SPONGE_FAMILY = SpongeFamilyDefinition(
    "classic_sponge",
    "Classic Sponge",
    {
        "cell_size": 10.0,
        "thickness": 0.2,
        "seed": 0,
        "resolution": 17,
    },
)


class SpongeFamilyRegistry:
    """Resolve Sponge Family metadata without generator or UI branching."""

    preset_id = "sponge"
    _definitions = MappingProxyType({
        CLASSIC_SPONGE_FAMILY.family_id: CLASSIC_SPONGE_FAMILY,
    })

    @classmethod
    def get(cls, family_id: str) -> SpongeFamilyDefinition:
        try:
            return cls._definitions[family_id]
        except (KeyError, TypeError) as error:
            raise KeyError("unknown sponge family: {!r}".format(family_id)) from error

    @classmethod
    def list_all(cls) -> Tuple[SpongeFamilyDefinition, ...]:
        return (CLASSIC_SPONGE_FAMILY,)
