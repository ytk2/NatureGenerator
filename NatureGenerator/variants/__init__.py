"""Curated parameter variants for NatureGenerator presets."""

from .builtins import BUILT_IN_VARIANTS
from .definition import VariantDefinition
from .registry import VariantRegistry


class VariantFactory:
    """Stable access to the explicit built-in variant catalog."""

    _registry = None

    @classmethod
    def create_registry(cls) -> VariantRegistry:
        registry = VariantRegistry()
        for variant in BUILT_IN_VARIANTS:
            registry.register(variant)
        return registry

    @classmethod
    def _get_registry(cls) -> VariantRegistry:
        if cls._registry is None:
            cls._registry = cls.create_registry()
        return cls._registry

    @classmethod
    def get(cls, variant_id: str) -> VariantDefinition:
        return cls._get_registry().get(variant_id)

    @classmethod
    def list_all(cls):
        return cls._get_registry().list_all()

    @classmethod
    def list_for_preset(cls, preset_id: str):
        return cls._get_registry().list_for_preset(preset_id)


__all__ = ["VariantDefinition", "VariantFactory", "VariantRegistry"]
