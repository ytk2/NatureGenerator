"""Immutable registry for available procedural operators."""

from types import MappingProxyType
from typing import Dict, Iterable, Tuple

from .operators import (
    GyroidSurfaceOperator,
    NoiseDisplacementOperator,
    PassThroughOperator,
    ProceduralOperator,
    SubdivisionOperator,
    VoronoiSurfaceOperator,
)


class UnknownOperatorError(KeyError):
    pass


class ProceduralOperatorRegistry:
    def __init__(self, operators: Iterable[ProceduralOperator]) -> None:
        values: Dict[str, ProceduralOperator] = {}
        display_names = set()
        for operator in operators:
            if not isinstance(operator, ProceduralOperator):
                raise TypeError("operators must implement ProceduralOperator")
            if operator.operator_id in values:
                raise ValueError("duplicate operator id: {}".format(
                    operator.operator_id
                ))
            if operator.display_name in display_names:
                raise ValueError("duplicate operator display name: {}".format(
                    operator.display_name
                ))
            values[operator.operator_id] = operator
            display_names.add(operator.display_name)
        self._operators = MappingProxyType(values)

    def get(self, operator_id: str) -> ProceduralOperator:
        try:
            return self._operators[operator_id]
        except KeyError as error:
            raise UnknownOperatorError(
                "unknown procedural operator: {}".format(operator_id)
            ) from error

    def list_all(self) -> Tuple[ProceduralOperator, ...]:
        return tuple(self._operators.values())


DEFAULT_OPERATOR_REGISTRY = ProceduralOperatorRegistry((
    PassThroughOperator(),
    NoiseDisplacementOperator(),
    SubdivisionOperator(),
    VoronoiSurfaceOperator(),
    GyroidSurfaceOperator(),
))
