"""Deterministic registry and factory for built-in nature presets."""

from typing import Dict, Tuple

from .preset import NaturePreset


def _sort_key(preset: NaturePreset) -> Tuple[str, str, str]:
    return (
        preset.category.casefold(),
        preset.display_name.casefold(),
        preset.preset_id,
    )


class PresetRegistry:
    """Mutable registration container that returns immutable presets."""

    def __init__(self) -> None:
        self._presets: Dict[str, NaturePreset] = {}

    def register(self, preset: NaturePreset) -> None:
        """Register *preset*, rejecting duplicate stable identifiers."""

        if not isinstance(preset, NaturePreset):
            raise TypeError("preset must be a NaturePreset")
        if preset.preset_id in self._presets:
            raise ValueError("duplicate preset id: {}".format(preset.preset_id))
        self._presets[preset.preset_id] = preset

    def get(self, preset_id: str) -> NaturePreset:
        """Return a preset by its stable identifier."""

        return self._presets[preset_id]

    def list_all(self) -> Tuple[NaturePreset, ...]:
        """Return every preset in deterministic category/name/id order."""

        return tuple(sorted(self._presets.values(), key=_sort_key))

    def list_by_category(self, category: str) -> Tuple[NaturePreset, ...]:
        """Return matching presets in deterministic order."""

        if not isinstance(category, str):
            raise TypeError("category must be a string")
        normalized = category.strip().casefold()
        return tuple(
            preset
            for preset in self.list_all()
            if preset.category.casefold() == normalized
        )


def _built_in_presets() -> Tuple[NaturePreset, ...]:
    """Import the explicit built-in set without filesystem discovery."""

    from .bark import BARK_PRESET
    from .bone import BONE_PRESET
    from .coral import CORAL_PRESET
    from .rock import ROCK_PRESET
    from .sponge import SPONGE_PRESET

    return (CORAL_PRESET, BONE_PRESET, BARK_PRESET, SPONGE_PRESET, ROCK_PRESET)


class PresetFactory:
    """Stable entry point for future command and UI code."""

    _registry = None

    @classmethod
    def create_registry(cls) -> PresetRegistry:
        """Return a fresh registry containing all explicit built-ins."""

        registry = PresetRegistry()
        for preset in _built_in_presets():
            registry.register(preset)
        return registry

    @classmethod
    def _get_registry(cls) -> PresetRegistry:
        if cls._registry is None:
            cls._registry = cls.create_registry()
        return cls._registry

    @classmethod
    def get(cls, preset_id: str) -> NaturePreset:
        """Return one built-in preset without importing its defining module."""

        return cls._get_registry().get(preset_id)

    @classmethod
    def list_all(cls) -> Tuple[NaturePreset, ...]:
        """Return all built-in presets in deterministic order."""

        return cls._get_registry().list_all()

    @classmethod
    def list_by_category(cls, category: str) -> Tuple[NaturePreset, ...]:
        """Return built-in presets for one category."""

        return cls._get_registry().list_by_category(category)
