"""Fusion-independent Procedural Lab application orchestration."""

from typing import Callable, Tuple

from procedural import (
    OperatorPipeline,
    ProceduralRequest,
    ProceduralResult,
    ProceduralStackRequest,
)


MeshInserter = Callable[[object, str], object]


def execute_procedural(
    request: ProceduralRequest,
    insert_mesh: MeshInserter,
    name: str,
) -> Tuple[ProceduralResult, object]:
    if not isinstance(request, ProceduralRequest):
        raise TypeError("request must be a ProceduralRequest")
    if not callable(insert_mesh):
        raise TypeError("insert_mesh must be callable")
    result = OperatorPipeline((request.operator_id,)).execute(request)
    body = insert_mesh(result.mesh, name)
    if body is None:
        raise RuntimeError("the Fusion Adapter did not return a MeshBody")
    return result, body


def execute_procedural_stack(
    request: ProceduralStackRequest,
    insert_mesh: MeshInserter,
    name: str,
) -> Tuple[ProceduralResult, object]:
    """Execute an ordered stack and pass its final mesh to Fusion."""

    if not isinstance(request, ProceduralStackRequest):
        raise TypeError("request must be a ProceduralStackRequest")
    if not callable(insert_mesh):
        raise TypeError("insert_mesh must be callable")
    operator_ids = tuple(
        invocation.operator_id for invocation in request.invocations
    )
    result = OperatorPipeline(operator_ids).execute_stack(request)
    body = insert_mesh(result.mesh, name)
    if body is None:
        raise RuntimeError("the Fusion Adapter did not return a MeshBody")
    return result, body
