"""Deterministic closure of scalar iso-surfaces at rectangular grid bounds."""

from collections import Counter, defaultdict
import math
from typing import Dict, Iterable, List, Sequence, Tuple

from core.mesh import Face, Point3, TriangleMesh
from core.voxel_grid import VoxelGrid


Plane = Tuple[str, int, float]
Edge = Tuple[int, int]


class BoundaryClosureError(ValueError):
    """Raised when an extracted boundary cannot be closed safely."""


def boundary_tolerance(grid: VoxelGrid) -> float:
    """Derive the boundary tolerance from the smallest voxel spacing."""

    return max(min(grid.spacing) * 1e-7, 1e-12)


def _boundary_edges(mesh: TriangleMesh) -> Tuple[Edge, ...]:
    counts = Counter(
        tuple(sorted((start, end)))
        for face in mesh.faces
        for start, end in (
            (face[0], face[1]),
            (face[1], face[2]),
            (face[2], face[0]),
        )
    )
    return tuple(edge for edge, count in sorted(counts.items()) if count == 1)


def _planes(minimum: Point3, maximum: Point3) -> Tuple[Plane, ...]:
    return (
        ("x_min", 0, minimum[0]),
        ("x_max", 0, maximum[0]),
        ("y_min", 1, minimum[1]),
        ("y_max", 1, maximum[1]),
        ("z_min", 2, minimum[2]),
        ("z_max", 2, maximum[2]),
    )


def _on_plane(point: Point3, plane: Plane, tolerance: float) -> bool:
    return abs(point[plane[1]] - plane[2]) <= tolerance


def _on_rectangle_edge(
    point: Point3,
    plane: Plane,
    minimum: Point3,
    maximum: Point3,
    tolerance: float,
) -> bool:
    other_axes = tuple(axis for axis in range(3) if axis != plane[1])
    return any(
        abs(point[axis] - bound) <= tolerance
        for axis in other_axes
        for bound in (minimum[axis], maximum[axis])
    )


def classify_boundary_edges(
    mesh: TriangleMesh,
    minimum: Point3,
    maximum: Point3,
    tolerance: float,
) -> Dict[str, Tuple[Edge, ...]]:
    """Classify every mesh boundary edge on exactly one rectangular plane."""

    classified: Dict[str, List[Edge]] = {
        plane[0]: [] for plane in _planes(minimum, maximum)
    }
    for edge in _boundary_edges(mesh):
        hits = [
            plane for plane in _planes(minimum, maximum)
            if _on_plane(mesh.vertices[edge[0]], plane, tolerance)
            and _on_plane(mesh.vertices[edge[1]], plane, tolerance)
        ]
        if len(hits) != 1:
            raise BoundaryClosureError(
                "boundary edge {} is not confined to exactly one rectangular "
                "domain plane".format(edge)
            )
        classified[hits[0][0]].append(edge)
    return {
        name: tuple(sorted(edges))
        for name, edges in classified.items()
    }


def boundary_paths(
    mesh: TriangleMesh,
    edges: Iterable[Edge],
    plane: Plane,
    minimum: Point3,
    maximum: Point3,
    tolerance: float,
) -> Tuple[Tuple[int, ...], ...]:
    """Return stable loops or valid box-edge-to-box-edge contour chains."""

    adjacency: Dict[int, List[int]] = defaultdict(list)
    remaining = set()
    for start, end in edges:
        edge = tuple(sorted((start, end)))
        remaining.add(edge)
        adjacency[start].append(end)
        adjacency[end].append(start)
    for neighbors in adjacency.values():
        neighbors.sort()
    invalid = [vertex for vertex, neighbors in adjacency.items()
               if len(neighbors) not in (1, 2)]
    if invalid:
        raise BoundaryClosureError(
            "boundary contour branches at vertex {}; reduce resolution or "
            "adjust the iso value".format(min(invalid))
        )
    endpoints = sorted(
        vertex for vertex, neighbors in adjacency.items()
        if len(neighbors) == 1
    )
    for vertex in endpoints:
        if not _on_rectangle_edge(
            mesh.vertices[vertex],
            plane,
            minimum,
            maximum,
            tolerance,
        ):
            raise BoundaryClosureError(
                "boundary contour has an open endpoint away from a domain "
                "edge at vertex {}".format(vertex)
            )

    paths = []
    starts = endpoints + sorted(adjacency)
    for candidate in starts:
        available = [
            neighbor for neighbor in adjacency.get(candidate, ())
            if tuple(sorted((candidate, neighbor))) in remaining
        ]
        if not available:
            continue
        path = [candidate]
        previous = None
        current = candidate
        while True:
            options = [
                neighbor for neighbor in adjacency[current]
                if neighbor != previous
                and tuple(sorted((current, neighbor))) in remaining
            ]
            if not options:
                break
            following = min(options)
            remaining.remove(tuple(sorted((current, following))))
            path.append(following)
            previous, current = current, following
            if current == path[0]:
                break
        paths.append(tuple(path))
    if remaining:
        raise BoundaryClosureError(
            "boundary contours could not be grouped deterministically"
        )
    ordered_paths = tuple(sorted(paths))
    projection_axes = tuple(
        axis for axis in range(3) if axis != plane[1]
    )

    def point2(vertex):
        point = mesh.vertices[vertex]
        return (point[projection_axes[0]], point[projection_axes[1]])

    def cross2(a, b, c):
        return (
            (b[0] - a[0]) * (c[1] - a[1])
            - (b[1] - a[1]) * (c[0] - a[0])
        )

    segments = []
    for path_index, path in enumerate(ordered_paths):
        for index in range(len(path) - 1):
            segments.append((
                path_index, index, path[index], path[index + 1]
            ))
    for first_index, first in enumerate(segments):
        for second in segments[first_index + 1:]:
            if set(first[2:]).intersection(second[2:]):
                continue
            a, b = point2(first[2]), point2(first[3])
            c, d = point2(second[2]), point2(second[3])
            ab_c = cross2(a, b, c)
            ab_d = cross2(a, b, d)
            cd_a = cross2(c, d, a)
            cd_b = cross2(c, d, b)
            if (
                ab_c * ab_d < -(tolerance ** 4)
                and cd_a * cd_b < -(tolerance ** 4)
            ):
                raise BoundaryClosureError(
                    "boundary contours self-intersect on plane {}".format(
                        plane[0]
                    )
                )
    return ordered_paths


def _validate_boundary_topology(
    mesh: TriangleMesh,
    classified: Dict[str, Tuple[Edge, ...]],
    minimum: Point3,
    maximum: Point3,
    tolerance: float,
) -> None:
    planes = {plane[0]: plane for plane in _planes(minimum, maximum)}
    for name, edges in classified.items():
        boundary_paths(
            mesh, edges, planes[name], minimum, maximum, tolerance
        )


def _clip_triangle(
    points: Sequence[Tuple[Point3, float]],
    iso_value: float,
) -> Tuple[Point3, ...]:
    """Clip one planar sample triangle to values strictly below the iso value."""

    output: List[Tuple[Point3, float]] = []
    previous_point, previous_value = points[-1]
    previous_inside = previous_value < iso_value
    for current_point, current_value in points:
        current_inside = current_value < iso_value
        if current_inside != previous_inside:
            denominator = current_value - previous_value
            fraction = (
                0.5 if denominator == 0.0
                else (iso_value - previous_value) / denominator
            )
            fraction = min(1.0, max(0.0, fraction))
            intersection = tuple(
                previous_point[axis]
                + fraction * (current_point[axis] - previous_point[axis])
                for axis in range(3)
            )
            output.append((intersection, iso_value))
        if current_inside:
            output.append((current_point, current_value))
        previous_point, previous_value = current_point, current_value
        previous_inside = current_inside
    return tuple(item[0] for item in output)


def _face_sample_triangles(grid: VoxelGrid):
    """Yield boundary sample triangles in deterministic outward winding."""

    nx, ny, nz = grid.shape

    def sample(i, j, k):
        index = grid.index(i, j, k)
        return (grid.point_at(i, j, k), grid.values[index])

    for k in range(nz - 1):
        for j in range(ny - 1):
            xmin = (
                sample(0, j, k), sample(0, j + 1, k + 1),
                sample(0, j + 1, k),
            )
            yield xmin
            yield (
                sample(0, j, k), sample(0, j, k + 1),
                sample(0, j + 1, k + 1),
            )
            yield (
                sample(nx - 1, j, k), sample(nx - 1, j + 1, k),
                sample(nx - 1, j + 1, k + 1),
            )
            yield (
                sample(nx - 1, j, k),
                sample(nx - 1, j + 1, k + 1),
                sample(nx - 1, j, k + 1),
            )
    for k in range(nz - 1):
        for i in range(nx - 1):
            yield (
                sample(i, 0, k), sample(i + 1, 0, k),
                sample(i + 1, 0, k + 1),
            )
            yield (
                sample(i, 0, k), sample(i + 1, 0, k + 1),
                sample(i, 0, k + 1),
            )
            yield (
                sample(i, ny - 1, k),
                sample(i + 1, ny - 1, k + 1),
                sample(i + 1, ny - 1, k),
            )
            yield (
                sample(i, ny - 1, k), sample(i, ny - 1, k + 1),
                sample(i + 1, ny - 1, k + 1),
            )
    for j in range(ny - 1):
        for i in range(nx - 1):
            yield (
                sample(i, j, 0), sample(i + 1, j + 1, 0),
                sample(i + 1, j, 0),
            )
            yield (
                sample(i, j, 0), sample(i, j + 1, 0),
                sample(i + 1, j + 1, 0),
            )
            yield (
                sample(i, j, nz - 1), sample(i + 1, j, nz - 1),
                sample(i + 1, j + 1, nz - 1),
            )
            yield (
                sample(i, j, nz - 1),
                sample(i + 1, j + 1, nz - 1),
                sample(i, j + 1, nz - 1),
            )


def close_rectangular_boundary(
    mesh: TriangleMesh,
    grid: VoxelGrid,
    iso_value: float,
) -> TriangleMesh:
    """Close the lower-valued region on all six rectangular domain faces."""

    if not isinstance(mesh, TriangleMesh):
        raise TypeError("mesh must be a TriangleMesh")
    if not isinstance(grid, VoxelGrid):
        raise TypeError("grid must be a VoxelGrid")
    minimum = grid.origin
    maximum = tuple(
        grid.origin[axis] + grid.spacing[axis] * (grid.shape[axis] - 1)
        for axis in range(3)
    )
    tolerance = boundary_tolerance(grid)
    classified = classify_boundary_edges(
        mesh, minimum, maximum, tolerance
    )
    _validate_boundary_topology(
        mesh, classified, minimum, maximum, tolerance
    )

    vertices = list(mesh.vertices)
    faces: List[Face] = list(mesh.faces)
    cache: Dict[Tuple[int, int, int], List[int]] = defaultdict(list)

    def key(point):
        return tuple(int(round(value / tolerance)) for value in point)

    for index, point in enumerate(vertices):
        cache[key(point)].append(index)

    def vertex_index(point):
        point_key = key(point)
        for index in cache.get(point_key, ()):
            if all(
                abs(vertices[index][axis] - point[axis]) <= tolerance
                for axis in range(3)
            ):
                return index
        index = len(vertices)
        vertices.append(tuple(float(value) for value in point))
        cache[point_key].append(index)
        return index

    area_epsilon_squared = tolerance ** 4
    for triangle in _face_sample_triangles(grid):
        polygon = _clip_triangle(triangle, iso_value)
        if len(polygon) < 3:
            continue
        indices = tuple(vertex_index(point) for point in polygon)
        for offset in range(1, len(indices) - 1):
            face = (indices[0], indices[offset], indices[offset + 1])
            if len(set(face)) < 3:
                continue
            a, b, c = (vertices[index] for index in face)
            ab = tuple(b[axis] - a[axis] for axis in range(3))
            ac = tuple(c[axis] - a[axis] for axis in range(3))
            cross = (
                ab[1] * ac[2] - ab[2] * ac[1],
                ab[2] * ac[0] - ab[0] * ac[2],
                ab[0] * ac[1] - ab[1] * ac[0],
            )
            if sum(value * value for value in cross) > area_epsilon_squared:
                faces.append(face)

    result = TriangleMesh(tuple(vertices), tuple(faces))
    statistics = result.statistics()
    if (
        statistics.boundary_edge_count
        or statistics.nonmanifold_edge_count
        or statistics.inconsistent_winding_edge_count
        or statistics.degenerate_face_count
        or not statistics.is_watertight
        or not statistics.is_manifold
    ):
        raise BoundaryClosureError(
            "rectangular boundary closure did not produce a clean watertight "
            "manifold: boundary={}, nonmanifold={}, winding={}, "
            "degenerate={}, nonmanifold_vertices={}, duplicate_faces={}".format(
                statistics.boundary_edge_count,
                statistics.nonmanifold_edge_count,
                statistics.inconsistent_winding_edge_count,
                statistics.degenerate_face_count,
                statistics.nonmanifold_vertex_count,
                statistics.duplicate_face_count,
            )
        )
    return result


def _clip_band_polygon(records, value_index):
    output = []
    previous_point, previous_values = records[-1]
    previous_inside = previous_values[value_index] < 0.0
    for current_point, current_values in records:
        current_inside = current_values[value_index] < 0.0
        if current_inside != previous_inside:
            previous_value = previous_values[value_index]
            current_value = current_values[value_index]
            fraction = -previous_value / (current_value - previous_value)
            point = tuple(
                previous_point[axis]
                + fraction * (current_point[axis] - previous_point[axis])
                for axis in range(3)
            )
            values = tuple(
                previous_values[index]
                + fraction
                * (current_values[index] - previous_values[index])
                for index in range(2)
            )
            output.append((point, values))
        if current_inside:
            output.append((current_point, current_values))
        previous_point, previous_values = current_point, current_values
        previous_inside = current_inside
    return output


def close_rectangular_band_boundary(
    mesh: TriangleMesh,
    upper_grid: VoxelGrid,
    lower_grid: VoxelGrid,
) -> TriangleMesh:
    """Close the intersection of two wall-side fields on the domain faces."""

    if not isinstance(mesh, TriangleMesh):
        raise TypeError("mesh must be a TriangleMesh")
    if not isinstance(upper_grid, VoxelGrid) or not isinstance(
        lower_grid, VoxelGrid
    ):
        raise TypeError("band grids must be VoxelGrid values")
    if (
        upper_grid.origin != lower_grid.origin
        or upper_grid.spacing != lower_grid.spacing
        or upper_grid.shape != lower_grid.shape
    ):
        raise ValueError("band grids must share bounds, spacing, and shape")
    minimum = upper_grid.origin
    maximum = tuple(
        upper_grid.origin[axis]
        + upper_grid.spacing[axis] * (upper_grid.shape[axis] - 1)
        for axis in range(3)
    )
    tolerance = boundary_tolerance(upper_grid)
    classified = classify_boundary_edges(
        mesh, minimum, maximum, tolerance
    )
    _validate_boundary_topology(
        mesh, classified, minimum, maximum, tolerance
    )

    vertices = list(mesh.vertices)
    faces: List[Face] = list(mesh.faces)
    cache: Dict[Tuple[int, int, int], List[int]] = defaultdict(list)

    def key(point):
        return tuple(int(round(value / tolerance)) for value in point)

    for index, point in enumerate(vertices):
        cache[key(point)].append(index)

    def vertex_index(point):
        point_key = key(point)
        for index in cache.get(point_key, ()):
            if all(
                abs(vertices[index][axis] - point[axis]) <= tolerance
                for axis in range(3)
            ):
                return index
        index = len(vertices)
        vertices.append(tuple(float(value) for value in point))
        cache[point_key].append(index)
        return index

    area_epsilon_squared = tolerance ** 4
    upper_triangles = _face_sample_triangles(upper_grid)
    lower_triangles = _face_sample_triangles(lower_grid)
    for upper_triangle, lower_triangle in zip(
        upper_triangles, lower_triangles
    ):
        records = [
            (
                upper_item[0],
                (upper_item[1], lower_item[1]),
            )
            for upper_item, lower_item in zip(
                upper_triangle, lower_triangle
            )
        ]
        polygon = _clip_band_polygon(records, 0)
        if len(polygon) < 3:
            continue
        polygon = _clip_band_polygon(polygon, 1)
        if len(polygon) < 3:
            continue
        indices = tuple(
            vertex_index(record[0]) for record in polygon
        )
        for offset in range(1, len(indices) - 1):
            face = (indices[0], indices[offset], indices[offset + 1])
            if len(set(face)) < 3:
                continue
            a, b, c = (vertices[index] for index in face)
            ab = tuple(b[axis] - a[axis] for axis in range(3))
            ac = tuple(c[axis] - a[axis] for axis in range(3))
            cross = (
                ab[1] * ac[2] - ab[2] * ac[1],
                ab[2] * ac[0] - ab[0] * ac[2],
                ab[0] * ac[1] - ab[1] * ac[0],
            )
            if sum(value * value for value in cross) > area_epsilon_squared:
                faces.append(face)

    result = TriangleMesh(tuple(vertices), tuple(faces))
    statistics = result.statistics()
    if not statistics.is_watertight or not statistics.is_manifold:
        raise BoundaryClosureError(
            "rectangular wall-band closure did not produce a clean watertight "
            "manifold: boundary={}, nonmanifold={}, winding={}, degenerate={}, "
            "nonmanifold_vertices={}, duplicate_faces={}".format(
                statistics.boundary_edge_count,
                statistics.nonmanifold_edge_count,
                statistics.inconsistent_winding_edge_count,
                statistics.degenerate_face_count,
                statistics.nonmanifold_vertex_count,
                statistics.duplicate_face_count,
            )
        )
    return result
