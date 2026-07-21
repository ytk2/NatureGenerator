"""Correctness-first marching tetrahedra isosurface extraction.

The extractor operates only on :class:`VoxelGrid` samples and emits an indexed
:class:`TriangleMesh`. Each voxel uses the same six-tetrahedra decomposition
around its 0-to-6 body diagonal, which gives adjacent voxels compatible face
diagonals. Intersections are cached by global sample-edge identity.
"""

import math
from typing import Dict, List, Sequence, Tuple

from .mesh import Face, Point3, TriangleMesh
from .scalar_field import ScalarField
from .voxel_grid import VoxelGrid


EdgeKey = Tuple[int, int]

# Corner ordering matches VoxelGrid.cell_corner_indices().
_TETRAHEDRA = (
    (0, 1, 2, 6),
    (0, 2, 3, 6),
    (0, 3, 7, 6),
    (0, 7, 4, 6),
    (0, 4, 5, 6),
    (0, 5, 1, 6),
)

_TETRAHEDRON_EDGES = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))


def _subtract(a: Point3, b: Point3) -> Point3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a: Point3, b: Point3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Point3, b: Point3) -> Point3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _mean(points: Sequence[Point3]) -> Point3:
    count = float(len(points))
    return (
        sum(point[0] for point in points) / count,
        sum(point[1] for point in points) / count,
        sum(point[2] for point in points) / count,
    )


def _ordered_polygon(
    vertex_ids: Sequence[int], vertices: Sequence[Point3], direction: Point3
) -> List[int]:
    """Order a planar polygon and orient it toward increasing scalar values."""

    center = _mean([vertices[index] for index in vertex_ids])
    direction_length = math.sqrt(_dot(direction, direction))
    if direction_length == 0.0:
        raise ValueError("cannot orient an isosurface with identical class centroids")
    normal = tuple(value / direction_length for value in direction)

    reference = (1.0, 0.0, 0.0) if abs(normal[0]) < 0.9 else (0.0, 1.0, 0.0)
    u = _cross(normal, reference)
    u_length = math.sqrt(_dot(u, u))
    u = tuple(value / u_length for value in u)
    v = _cross(normal, u)

    ordered = sorted(
        vertex_ids,
        key=lambda index: math.atan2(
            _dot(_subtract(vertices[index], center), v),
            _dot(_subtract(vertices[index], center), u),
        ),
    )
    if len(ordered) >= 3:
        a, b, c = (vertices[index] for index in ordered[:3])
        polygon_normal = _cross(_subtract(b, a), _subtract(c, a))
        if _dot(polygon_normal, direction) < 0.0:
            ordered.reverse()
    return ordered


def extract_isosurface(grid: VoxelGrid, iso_value: float = 0.0) -> TriangleMesh:
    """Extract an isosurface from *grid* using marching tetrahedra.

    Values strictly below ``iso_value`` are inside. Triangle normals point from
    lower values toward higher values. Degenerate triangles caused by an
    isosurface exactly touching a sample are omitted.
    """

    iso_value = float(iso_value)
    if not math.isfinite(iso_value):
        raise ValueError("iso_value must be finite")

    vertices: List[Point3] = []
    faces: List[Face] = []
    edge_vertices: Dict[EdgeKey, int] = {}
    sample_vertices: Dict[int, int] = {}

    def intersection(sample_a: int, sample_b: int) -> int:
        key = (sample_a, sample_b) if sample_a < sample_b else (sample_b, sample_a)
        cached = edge_vertices.get(key)
        if cached is not None:
            return cached

        value_a = grid.values[sample_a]
        value_b = grid.values[sample_b]
        denominator = value_b - value_a
        if denominator == 0.0:
            fraction = 0.5
        else:
            fraction = (iso_value - value_a) / denominator
        fraction = min(1.0, max(0.0, fraction))

        endpoint = None
        tolerance = 1e-12
        if fraction <= tolerance:
            endpoint = sample_a
        elif fraction >= 1.0 - tolerance:
            endpoint = sample_b
        if endpoint is not None and endpoint in sample_vertices:
            vertex_index = sample_vertices[endpoint]
            edge_vertices[key] = vertex_index
            return vertex_index

        nx, ny, _ = grid.shape

        def sample_point(index: int) -> Point3:
            i = index % nx
            remainder = index // nx
            j = remainder % ny
            k = remainder // ny
            return grid.point_at(i, j, k)

        point_a = sample_point(sample_a)
        point_b = sample_point(sample_b)
        point = (
            point_a[0] + fraction * (point_b[0] - point_a[0]),
            point_a[1] + fraction * (point_b[1] - point_a[1]),
            point_a[2] + fraction * (point_b[2] - point_a[2]),
        )
        vertex_index = len(vertices)
        vertices.append(point)
        edge_vertices[key] = vertex_index
        if endpoint is not None:
            sample_vertices[endpoint] = vertex_index
        return vertex_index

    for _, _, _, corners in grid.iter_cells():
        corner_points = []
        nx, ny, _ = grid.shape
        for sample_index in corners:
            i = sample_index % nx
            remainder = sample_index // nx
            j = remainder % ny
            k = remainder // ny
            corner_points.append(grid.point_at(i, j, k))

        for tetrahedron in _TETRAHEDRA:
            samples = tuple(corners[index] for index in tetrahedron)
            points = tuple(corner_points[index] for index in tetrahedron)
            inside = tuple(grid.values[index] < iso_value for index in samples)
            inside_count = sum(inside)
            if inside_count == 0 or inside_count == 4:
                continue

            polygon = []
            for local_a, local_b in _TETRAHEDRON_EDGES:
                if inside[local_a] != inside[local_b]:
                    polygon.append(intersection(samples[local_a], samples[local_b]))
            polygon = list(dict.fromkeys(polygon))
            if len(polygon) < 3:
                continue

            inside_center = _mean(
                [points[index] for index in range(4) if inside[index]]
            )
            outside_center = _mean(
                [points[index] for index in range(4) if not inside[index]]
            )
            direction = _subtract(outside_center, inside_center)
            ordered = _ordered_polygon(polygon, vertices, direction)

            for index in range(1, len(ordered) - 1):
                face = (ordered[0], ordered[index], ordered[index + 1])
                a, b, c = (vertices[vertex] for vertex in face)
                if _dot(_cross(_subtract(b, a), _subtract(c, a)), direction) > 1e-24:
                    faces.append(face)

    return TriangleMesh(tuple(vertices), tuple(faces))


def extract_field(
    field: ScalarField,
    minimum: Sequence[float],
    maximum: Sequence[float],
    shape: Sequence[int],
    iso_value: float = 0.0,
) -> TriangleMesh:
    """Sample any scalar field and extract its isosurface."""

    return extract_isosurface(VoxelGrid.sample(field, minimum, maximum, shape), iso_value)
