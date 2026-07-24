"""Shared renderer-neutral material records for natural presets."""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping, Optional, Tuple

from .definition import MaterialDefinition


_EMPTY_METADATA = MappingProxyType({})


def _nonempty(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("{} must be a non-empty string".format(name))
    return value.strip()


@dataclass(frozen=True)
class ThumbnailReference:
    """Stable reference for a future packaged preset thumbnail."""

    resource_id: str
    alt_text: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "resource_id", _nonempty(self.resource_id, "resource_id"))
        object.__setattr__(self, "alt_text", _nonempty(self.alt_text, "alt_text"))


@dataclass(frozen=True)
class AssetBrowserMetadata:
    """Renderer-independent discovery metadata for a future Asset Browser."""

    category: str
    keywords: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "category", _nonempty(self.category, "category"))
        if not isinstance(self.keywords, tuple):
            raise TypeError("keywords must be a tuple")
        keywords = tuple(_nonempty(value, "keyword") for value in self.keywords)
        if len(keywords) != len(set(keywords)):
            raise ValueError("keywords must be unique")
        object.__setattr__(self, "keywords", keywords)


@dataclass(frozen=True)
class NaturalMaterial:
    """Material intent plus reusable presentation and discovery metadata."""

    preset_id: str
    definition: MaterialDefinition
    browser: AssetBrowserMetadata
    thumbnail: Optional[ThumbnailReference] = None
    metadata: Mapping[str, str] = field(default_factory=lambda: _EMPTY_METADATA)

    def __post_init__(self) -> None:
        object.__setattr__(self, "preset_id", _nonempty(self.preset_id, "preset_id"))
        if not isinstance(self.definition, MaterialDefinition):
            raise TypeError("definition must be a MaterialDefinition")
        if not isinstance(self.browser, AssetBrowserMetadata):
            raise TypeError("browser must be AssetBrowserMetadata")
        if self.thumbnail is not None and not isinstance(
            self.thumbnail, ThumbnailReference
        ):
            raise TypeError("thumbnail must be ThumbnailReference or None")
        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        copied = {}
        for key, value in self.metadata.items():
            copied[_nonempty(key, "metadata key")] = _nonempty(value, "metadata value")
        object.__setattr__(self, "metadata", MappingProxyType(copied))


class NaturalMaterialRegistry:
    """Immutable lookup of material records by stable preset identifier."""

    def __init__(self, materials: Tuple[NaturalMaterial, ...]) -> None:
        if not isinstance(materials, tuple):
            raise TypeError("materials must be a tuple")
        values = {}
        for material in materials:
            if not isinstance(material, NaturalMaterial):
                raise TypeError("materials must contain NaturalMaterial values")
            if material.preset_id in values:
                raise ValueError(
                    "duplicate natural material preset id: {}".format(
                        material.preset_id
                    )
                )
            values[material.preset_id] = material
        self._materials = MappingProxyType(values)

    def get(self, preset_id: str) -> NaturalMaterial:
        """Return the material record for *preset_id*."""

        return self._materials[preset_id]

    def list_all(self) -> Tuple[NaturalMaterial, ...]:
        """Return all material records in stable preset-ID order."""

        return tuple(self._materials[key] for key in sorted(self._materials))


NATURAL_MATERIALS = NaturalMaterialRegistry(
    (
        NaturalMaterial(
            "rock",
            MaterialDefinition(
                "natural_rock",
                "Natural Rock",
                (0.34, 0.32, 0.28, 1.0),
                roughness=0.86,
                procedural_parameters={"pattern": "mineral_variation"},
            ),
            AssetBrowserMetadata("geological", ("rock", "stone", "mineral")),
        ),
        NaturalMaterial(
            "bark",
            MaterialDefinition(
                "natural_bark",
                "Natural Bark",
                (0.24, 0.12, 0.055, 1.0),
                roughness=0.92,
                normal_strength=1.2,
                procedural_parameters={"pattern": "directional_ridges"},
            ),
            AssetBrowserMetadata("botanical", ("bark", "wood", "trunk")),
        ),
        NaturalMaterial(
            "coral",
            MaterialDefinition(
                "natural_coral",
                "Natural Coral",
                (0.78, 0.36, 0.28, 1.0),
                roughness=0.7,
                procedural_parameters={"pattern": "branch_gradient"},
            ),
            AssetBrowserMetadata("aquatic", ("coral", "branching", "reef")),
        ),
        NaturalMaterial(
            "sponge",
            MaterialDefinition(
                "natural_sponge",
                "Natural Sponge",
                (0.78, 0.58, 0.16, 1.0),
                roughness=0.88,
                procedural_parameters={"pattern": "porous_variation"},
            ),
            AssetBrowserMetadata("aquatic", ("sponge", "porous", "organic")),
        ),
        NaturalMaterial(
            "root",
            MaterialDefinition(
                "natural_root",
                "Natural Root",
                (0.29, 0.16, 0.075, 1.0),
                roughness=0.9,
                procedural_parameters={"pattern": "fibrous_variation"},
            ),
            AssetBrowserMetadata("botanical", ("root", "branching", "plant")),
        ),
        NaturalMaterial(
            "bone",
            MaterialDefinition(
                "natural_bone",
                "Natural Bone",
                (0.82, 0.79, 0.68, 1.0),
                roughness=0.72,
                procedural_parameters={"pattern": "porous_variation"},
            ),
            AssetBrowserMetadata("biological", ("bone", "organic", "skeletal")),
        ),
        NaturalMaterial(
            "crystal",
            MaterialDefinition(
                "natural_crystal",
                "Natural Crystal",
                (0.68, 0.82, 0.88, 1.0),
                roughness=0.28,
                procedural_parameters={"pattern": "crystalline_variation"},
            ),
            AssetBrowserMetadata("inorganic", ("crystal", "faceted", "mineral")),
        ),
    )
)
