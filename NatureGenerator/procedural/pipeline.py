"""Ordered Procedural Lab operator pipeline."""

from dataclasses import replace
from typing import Optional, Tuple

from .models import ProceduralRequest, ProceduralResult
from .registry import DEFAULT_OPERATOR_REGISTRY, ProceduralOperatorRegistry


class ProceduralPipelineError(RuntimeError):
    pass


class OperatorPipeline:
    """Execute an immutable ordered operator representation.

    Sprint 28 accepts one operator. The tuple representation deliberately
    reserves ordering for a later modifier-stack UI.
    """

    def __init__(
        self,
        operator_ids: Tuple[str, ...],
        registry: Optional[ProceduralOperatorRegistry] = None,
    ) -> None:
        if not isinstance(operator_ids, tuple):
            raise TypeError("operator_ids must be a tuple")
        if len(operator_ids) != 1:
            raise ValueError("Sprint 28 pipelines require exactly one operator")
        self._operator_ids = operator_ids
        self._registry = registry or DEFAULT_OPERATOR_REGISTRY

    @property
    def operator_ids(self) -> Tuple[str, ...]:
        return self._operator_ids

    def execute(self, request: ProceduralRequest) -> ProceduralResult:
        if request.operator_id != self._operator_ids[0]:
            raise ProceduralPipelineError(
                "request operator does not match the pipeline"
            )
        try:
            operator = self._registry.get(self._operator_ids[0])
            operator.validate(request)
            return operator.execute(replace(request))
        except (KeyError, TypeError, ValueError):
            raise
        except Exception as error:
            raise ProceduralPipelineError(
                "procedural operator execution failed: {}".format(error)
            ) from error
