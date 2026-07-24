"""Ordered Procedural Lab operator pipeline."""

from dataclasses import replace
from typing import Optional, Tuple

from .models import (
    OperatorInvocation,
    ProceduralInputGeometry,
    ProceduralRequest,
    ProceduralResult,
    ProceduralStackRequest,
)
from .registry import DEFAULT_OPERATOR_REGISTRY, ProceduralOperatorRegistry


class ProceduralPipelineError(RuntimeError):
    pass


class OperatorPipeline:
    """Execute an immutable ordered operator representation.

    The same runtime supports legacy one-operator requests and ordered stacks.
    """

    def __init__(
        self,
        operator_ids: Tuple[str, ...],
        registry: Optional[ProceduralOperatorRegistry] = None,
    ) -> None:
        if not isinstance(operator_ids, tuple):
            raise TypeError("operator_ids must be a tuple")
        if not operator_ids or len(operator_ids) > 3:
            raise ValueError("pipelines require between one and three operators")
        if any(not isinstance(operator_id, str) for operator_id in operator_ids):
            raise TypeError("operator IDs must be strings")
        self._operator_ids = operator_ids
        self._registry = registry or DEFAULT_OPERATOR_REGISTRY

    @property
    def operator_ids(self) -> Tuple[str, ...]:
        return self._operator_ids

    def execute(self, request: ProceduralRequest) -> ProceduralResult:
        """Execute the legacy single-operator request API unchanged."""

        if len(self._operator_ids) != 1:
            raise ProceduralPipelineError(
                "multi-operator pipelines require execute_stack"
            )
        if request.operator_id != self._operator_ids[0]:
            raise ProceduralPipelineError(
                "request operator does not match the pipeline"
            )
        try:
            stack_request = ProceduralStackRequest(
                request.input_geometry,
                (OperatorInvocation(
                    request.operator_id, request.operator_parameters
                ),),
                request.execution_context,
            )
            return self.execute_stack(stack_request)
        except (KeyError, TypeError, ValueError):
            raise
        except Exception as error:
            raise ProceduralPipelineError(
                "procedural operator execution failed: {}".format(error)
            ) from error

    def execute_stack(
        self, request: ProceduralStackRequest
    ) -> ProceduralResult:
        """Execute invocations top-to-bottom, feeding each result forward."""

        if not isinstance(request, ProceduralStackRequest):
            raise TypeError("request must be a ProceduralStackRequest")
        invocation_ids = tuple(
            invocation.operator_id for invocation in request.invocations
        )
        if invocation_ids != self._operator_ids:
            raise ProceduralPipelineError(
                "stack operators do not match the pipeline"
            )

        current_geometry = request.input_geometry
        final_result = None
        for index, invocation in enumerate(request.invocations):
            try:
                operator = self._registry.get(invocation.operator_id)
                stage_request = ProceduralRequest(
                    current_geometry,
                    invocation.operator_id,
                    invocation.operator_parameters,
                    request.execution_context,
                )
                operator.validate(stage_request)
                final_result = operator.execute(stage_request)
            except (KeyError, TypeError, ValueError):
                raise
            except Exception as error:
                raise ProceduralPipelineError(
                    "procedural operator {} failed: {}".format(index + 1, error)
                ) from error

            if index + 1 < len(request.invocations):
                stage_provenance = dict(request.input_geometry.provenance)
                stage_provenance["operator_stack_completed"] = ">".join(
                    invocation_ids[:index + 1]
                )
                current_geometry = ProceduralInputGeometry(
                    source_type=request.input_geometry.source_type,
                    mesh=final_result.mesh,
                    source_name=request.input_geometry.source_name,
                    source_identifier=request.input_geometry.source_identifier,
                    units=request.input_geometry.units,
                    provenance=stage_provenance,
                )

        if final_result is None:
            raise ProceduralPipelineError("operator stack produced no result")
        metadata = dict(final_result.execution_metadata)
        metadata.update({
            "operator_count": len(invocation_ids),
            "operator_stack": ">".join(invocation_ids),
        })
        return replace(
            final_result,
            input_digest=request.input_geometry.digest,
            execution_metadata=metadata,
        )
