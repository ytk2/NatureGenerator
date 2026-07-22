"""Fusion-independent orchestration for the Generate Nature command."""

from typing import Callable, Tuple

from core.mesh import TriangleMesh
from generators import GenerationRequest, GeneratorFactory, GeneratorResult
from presets import PresetFactory


MeshInserter = Callable[[TriangleMesh, str], object]


def generate_nature(
    request: GenerationRequest,
    insert_mesh: MeshInserter,
) -> Tuple[GeneratorResult, object]:
    """Execute *request* and pass its completed mesh to an adapter."""

    if not isinstance(request, GenerationRequest):
        raise TypeError("request must be a GenerationRequest")
    if not callable(insert_mesh):
        raise TypeError("insert_mesh must be callable")
    preset = PresetFactory.get(request.preset_id)
    result = GeneratorFactory.generate_request(request)
    body = insert_mesh(result.mesh, "NatureGenerator {}".format(preset.display_name))
    if body is None:
        raise RuntimeError("the Fusion Adapter did not return a MeshBody")
    return result, body
