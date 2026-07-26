"""Application command boundary for independent Gyroid Volume generation."""

import time
from typing import Callable, Optional, Tuple

from volume import GyroidVolumeRequest, GyroidVolumeResult, generate_gyroid_volume


MeshInserter = Callable[[object, str], object]
InsertionTimingSink = Callable[[float], None]


def execute_gyroid_volume(
    request: GyroidVolumeRequest,
    insert_mesh: MeshInserter,
    name: str,
    insertion_timing_sink: Optional[InsertionTimingSink] = None,
) -> Tuple[GyroidVolumeResult, object]:
    if not isinstance(request, GyroidVolumeRequest):
        raise TypeError("request must be a GyroidVolumeRequest")
    if not callable(insert_mesh):
        raise TypeError("insert_mesh must be callable")
    result = generate_gyroid_volume(request)
    insertion_started = time.perf_counter()
    body = insert_mesh(result.mesh, name)
    insertion_elapsed = time.perf_counter() - insertion_started
    if body is None:
        raise RuntimeError("the Fusion Adapter did not return a MeshBody")
    if insertion_timing_sink is not None:
        insertion_timing_sink(insertion_elapsed)
    return result, body
