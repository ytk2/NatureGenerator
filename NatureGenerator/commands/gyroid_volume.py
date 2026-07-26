"""Application command boundary for independent Gyroid Volume generation."""

from typing import Callable, Tuple

from volume import GyroidVolumeRequest, GyroidVolumeResult, generate_gyroid_volume


MeshInserter = Callable[[object, str], object]


def execute_gyroid_volume(
    request: GyroidVolumeRequest,
    insert_mesh: MeshInserter,
    name: str,
) -> Tuple[GyroidVolumeResult, object]:
    if not isinstance(request, GyroidVolumeRequest):
        raise TypeError("request must be a GyroidVolumeRequest")
    if not callable(insert_mesh):
        raise TypeError("insert_mesh must be callable")
    result = generate_gyroid_volume(request)
    body = insert_mesh(result.mesh, name)
    if body is None:
        raise RuntimeError("the Fusion Adapter did not return a MeshBody")
    return result, body
