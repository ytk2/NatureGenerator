"""Conservative, dependency-free cleanup for triangle meshes."""

import math
from typing import Set

from .mesh import Face, TriangleMesh, _cross, _length, _subtract
from .mesh_builder import MeshBuilder


def optimize_mesh(
    mesh: TriangleMesh,
    weld_tolerance: float = 0.0,
    area_epsilon: float = 1e-12,
) -> TriangleMesh:
    """Weld vertices and remove degenerate, duplicate, and unused data.

    Face order and winding are preserved for retained triangles. This function
    intentionally performs no decimation or smoothing.
    """

    area_epsilon = float(area_epsilon)
    if not math.isfinite(area_epsilon) or area_epsilon < 0.0:
        raise ValueError("area_epsilon must be finite and non-negative")
    builder = MeshBuilder(weld_tolerance)
    remap = [builder.add_vertex(vertex) for vertex in mesh.vertices]
    seen: Set[Face] = set()
    for face in mesh.faces:
        mapped = tuple(remap[index] for index in face)
        if len(set(mapped)) != 3:
            continue
        canonical = tuple(sorted(mapped))
        if canonical in seen:
            continue
        a, b, c = (builder.vertex(index) for index in mapped)
        if 0.5 * _length(_cross(_subtract(b, a), _subtract(c, a))) <= area_epsilon:
            continue
        seen.add(canonical)
        builder.add_face(*mapped)
    return builder.build(compact=True)
