"""Validated deterministic registry for generator variants."""

from typing import Any, Dict, Tuple

from presets import PresetFactory

from .definition import VariantDefinition


def _validate_value(parameter_id: str, value: Any, metadata) -> None:
    numeric = isinstance(value, (int, float)) and not isinstance(value, bool)
    valid = {
        "bool": isinstance(value, bool),
        "float": numeric,
        "int": isinstance(value, int) and not isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "length": numeric,
        "str": isinstance(value, str),
    }[metadata.value_type]
    if not valid:
        raise TypeError(
            "variant parameter {!r} does not match {}".format(
                parameter_id, metadata.value_type
            )
        )
    if metadata.minimum is not None and value < metadata.minimum:
        raise ValueError("variant parameter {!r} is below minimum".format(parameter_id))
    if metadata.maximum is not None and value > metadata.maximum:
        raise ValueError("variant parameter {!r} exceeds maximum".format(parameter_id))


class VariantRegistry:
    """Register immutable variants after validating their preset contract."""

    def __init__(self) -> None:
        self._variants: Dict[str, VariantDefinition] = {}
        self._by_preset: Dict[str, list] = {}

    def register(self, variant: VariantDefinition) -> None:
        if not isinstance(variant, VariantDefinition):
            raise TypeError("variant must be a VariantDefinition")
        if variant.variant_id in self._variants:
            raise ValueError("duplicate variant id: {}".format(variant.variant_id))
        try:
            preset = PresetFactory.get(variant.preset_id)
        except KeyError as error:
            raise ValueError("unknown preset id: {}".format(variant.preset_id)) from error
        if not preset.available:
            raise ValueError("variants require an available preset")
        current = self._by_preset.get(variant.preset_id, [])
        if any(item.display_name == variant.display_name for item in current):
            raise ValueError(
                "duplicate variant display name for {}: {}".format(
                    variant.preset_id, variant.display_name
                )
            )
        unknown = set(variant.parameter_values).difference(preset.parameter_metadata)
        if unknown:
            raise ValueError(
                "unknown parameters for {}: {}".format(
                    variant.preset_id, ", ".join(sorted(unknown))
                )
            )
        combined = dict(preset.default_parameters)
        for parameter_id, value in variant.parameter_values.items():
            _validate_value(parameter_id, value, preset.parameter_metadata[parameter_id])
            combined[parameter_id] = value
        for constraint in preset.parameter_constraints:
            constraint.validate(combined)
        self._variants[variant.variant_id] = variant
        self._by_preset.setdefault(variant.preset_id, []).append(variant)

    def get(self, variant_id: str) -> VariantDefinition:
        return self._variants[variant_id]

    def list_all(self) -> Tuple[VariantDefinition, ...]:
        return tuple(self._variants.values())

    def list_for_preset(self, preset_id: str) -> Tuple[VariantDefinition, ...]:
        return tuple(self._by_preset.get(preset_id, ()))
