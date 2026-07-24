"""Fusion-independent Procedural Lab application orchestration."""

from typing import Callable, Tuple

from procedural import OperatorPipeline, ProceduralRequest, ProceduralResult


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
