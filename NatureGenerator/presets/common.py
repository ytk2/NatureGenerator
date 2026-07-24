"""Reusable parameter presentation conventions for natural presets."""

from typing import Tuple

from .preset import ParameterGroupDefinition


FORM_GROUP_ID = "form"
GENERATION_GROUP_ID = "generation"


def natural_parameter_groups(
    form_parameter_ids: Tuple[str, ...],
    generation_parameter_ids: Tuple[str, ...] = ("seed", "resolution"),
) -> Tuple[ParameterGroupDefinition, ...]:
    """Return the standard Form and Generation parameter groups."""

    return (
        ParameterGroupDefinition(
            FORM_GROUP_ID,
            "Form",
            form_parameter_ids,
            "Parameters that control the natural object's shape.",
        ),
        ParameterGroupDefinition(
            GENERATION_GROUP_ID,
            "Generation",
            generation_parameter_ids,
            "Parameters that control deterministic variation and mesh density.",
        ),
    )
