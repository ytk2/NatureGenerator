"""Composition root for preset metadata and optional Family registries."""

from typing import Tuple

from generators.bark_families import BarkFamilyRegistry
from generators.rock_families import RockFamilyRegistry
from presets import PresetDefinition, PresetFactory, PresetRegistry


def _built_in_registry() -> PresetRegistry:
    """Compose built-in metadata without placing generator imports in presets."""

    registry = PresetRegistry()
    family_registries = {
        BarkFamilyRegistry.preset_id: BarkFamilyRegistry,
        RockFamilyRegistry.preset_id: RockFamilyRegistry,
    }
    for preset in PresetFactory.list_all():
        registry.register(preset, family_registries.get(preset.preset_id))
    return registry


class PresetCatalog:
    """Read-only application catalog consumed by Fusion presentation code."""

    _registry = None

    @classmethod
    def _get_registry(cls) -> PresetRegistry:
        if cls._registry is None:
            cls._registry = _built_in_registry()
        return cls._registry

    @classmethod
    def get(cls, preset_id: str) -> PresetDefinition:
        return cls._get_registry().get_definition(preset_id)

    @classmethod
    def list_all(cls) -> Tuple[PresetDefinition, ...]:
        return cls._get_registry().list_definitions()
