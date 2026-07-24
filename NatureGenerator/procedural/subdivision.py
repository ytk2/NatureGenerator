"""Deterministic topology-preserving midpoint subdivision."""

from typing import Dict, List, Tuple

from core.mesh import Edge, Face, Point3, TriangleMesh


def _midpoint(a: Point3, b: Point3) -> Point3:
    return (
        (a[0] + b[0]) * 0.5,
        (a[1] + b[1]) * 0.5,
        (a[2] + b[2]) * 0.5,
    )


def subdivide_once(mesh: TriangleMesh) -> TriangleMesh:
    """Split every triangle into four using one shared midpoint per edge."""

    if not isinstance(mesh, TriangleMesh):
        raise TypeError("mesh must be a TriangleMesh")
    vertices: List[Point3] = list(mesh.vertices)
    faces: List[Face] = []
    edge_midpoints: Dict[Edge, int] = {}

    def midpoint_index(start: int, end: int) -> int:
        edge = (start, end) if start < end else (end, start)
        existing = edge_midpoints.get(edge)
        if existing is not None:
            return existing
        index = len(vertices)
        vertices.append(_midpoint(mesh.vertices[edge[0]], mesh.vertices[edge[1]]))
        edge_midpoints[edge] = index
        return index

    for a, b, c in mesh.faces:
        ab = midpoint_index(a, b)
        bc = midpoint_index(b, c)
        ca = midpoint_index(c, a)
        faces.extend((
            (a, ab, ca),
            (ab, b, bc),
            (ca, bc, c),
            (ab, bc, ca),
        ))
    return TriangleMesh(tuple(vertices), tuple(faces))


def subdivide(mesh: TriangleMesh, level: int) -> TriangleMesh:
    """Apply iterative midpoint subdivision for a positive level."""

    if isinstance(level, bool) or not isinstance(level, int):
        raise TypeError("subdivision level must be an integer")
    if level < 1:
        raise ValueError("subdivision level must be positive")
    result = mesh
    for _ in range(level):
        result = subdivide_once(result)
    return result
