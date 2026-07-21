"""Immutable, Fusion-independent indexed triangle meshes."""

from dataclasses import dataclass
import math
from typing import Dict, Iterator, List, Optional, Sequence, Set, Tuple


Point3 = Tuple[float, float, float]
Vector3 = Point3
Face = Tuple[int, int, int]
Triangle = Tuple[Point3, Point3, Point3]
Edge = Tuple[int, int]


def _cross(a: Vector3, b: Vector3) -> Vector3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _subtract(a: Point3, b: Point3) -> Vector3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _length(vector: Vector3) -> float:
    return math.sqrt(sum(component * component for component in vector))


@dataclass(frozen=True)
class MeshStatistics:
    """Topology and geometry summary for an indexed triangle mesh."""

    vertex_count: int
    face_count: int
    edge_count: int
    boundary_edge_count: int
    nonmanifold_edge_count: int
    nonmanifold_vertex_count: int
    inconsistent_winding_edge_count: int
    degenerate_face_count: int
    duplicate_face_count: int
    unused_vertex_count: int
    connected_component_count: int
    surface_area: float
    signed_volume: float
    bounds: Optional[Tuple[Point3, Point3]]

    @property
    def is_manifold(self) -> bool:
        """Return whether the mesh is an oriented 2-manifold, possibly open."""

        return (
            self.nonmanifold_edge_count == 0
            and self.nonmanifold_vertex_count == 0
            and self.inconsistent_winding_edge_count == 0
            and self.degenerate_face_count == 0
            and self.duplicate_face_count == 0
        )

    @property
    def is_watertight(self) -> bool:
        """Return whether the non-empty mesh is a closed oriented manifold."""

        return self.face_count > 0 and self.boundary_edge_count == 0 and self.is_manifold


def _vertex(values: Sequence[float]) -> Point3:
    if len(values) != 3:
        raise ValueError("each vertex must contain exactly three coordinates")
    vertex = (float(values[0]), float(values[1]), float(values[2]))
    if not all(math.isfinite(value) for value in vertex):
        raise ValueError("vertex coordinates must be finite")
    return vertex


def _face(values: Sequence[int]) -> Face:
    if len(values) != 3:
        raise ValueError("each face must contain exactly three indices")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise TypeError("face indices must be integers")
    face = (values[0], values[1], values[2])
    if len(set(face)) != 3:
        raise ValueError("a face must reference three distinct vertices")
    return face


@dataclass(frozen=True)
class TriangleMesh:
    """A validated indexed triangle mesh using plain Python tuples."""

    vertices: Tuple[Point3, ...]
    faces: Tuple[Face, ...]

    def __post_init__(self) -> None:
        vertices = tuple(_vertex(vertex) for vertex in self.vertices)
        faces = tuple(_face(face) for face in self.faces)
        vertex_count = len(vertices)
        for face in faces:
            if any(index < 0 or index >= vertex_count for index in face):
                raise ValueError("face index is outside the vertex array")

        object.__setattr__(self, "vertices", vertices)
        object.__setattr__(self, "faces", faces)

    def triangle(self, face_index: int) -> Triangle:
        """Return the three vertices referenced by a face."""

        face = self.faces[face_index]
        return tuple(self.vertices[index] for index in face)  # type: ignore[return-value]

    def triangles(self) -> Iterator[Triangle]:
        """Iterate over expanded triangles in face order."""

        for index in range(len(self.faces)):
            yield self.triangle(index)

    def face_cross(self, face_index: int) -> Vector3:
        """Return the unnormalized, area-weighted face normal."""

        a, b, c = self.triangle(face_index)
        return _cross(_subtract(b, a), _subtract(c, a))

    def face_normal(self, face_index: int) -> Vector3:
        """Return a unit normal using the face's right-hand winding order."""

        normal = self.face_cross(face_index)
        length = _length(normal)
        if length == 0.0:
            raise ValueError("cannot compute a normal for a zero-area face")
        return tuple(component / length for component in normal)  # type: ignore[return-value]

    def face_normals(self) -> Tuple[Vector3, ...]:
        """Return unit normals for all faces in mesh order."""

        return tuple(self.face_normal(index) for index in range(len(self.faces)))

    def vertex_normals(self) -> Tuple[Vector3, ...]:
        """Return normalized area-weighted vertex normals.

        Isolated vertices and vertices whose incident normals cancel receive a
        zero vector. Degenerate faces make no contribution.
        """

        accumulated: List[List[float]] = [[0.0, 0.0, 0.0] for _ in self.vertices]
        for face_index, face in enumerate(self.faces):
            weighted = self.face_cross(face_index)
            for vertex_index in face:
                for axis in range(3):
                    accumulated[vertex_index][axis] += weighted[axis]

        normals = []
        for vector in accumulated:
            length = _length((vector[0], vector[1], vector[2]))
            if length == 0.0:
                normals.append((0.0, 0.0, 0.0))
            else:
                normals.append(tuple(component / length for component in vector))
        return tuple(normals)  # type: ignore[return-value]

    def statistics(self, area_epsilon: float = 1e-12) -> MeshStatistics:
        """Compute topology, area, signed volume, components, and bounds."""

        area_epsilon = float(area_epsilon)
        if not math.isfinite(area_epsilon) or area_epsilon < 0.0:
            raise ValueError("area_epsilon must be finite and non-negative")

        edge_directions: Dict[Edge, List[int]] = {}
        vertex_faces: Dict[int, List[int]] = {}
        used_vertices: Set[int] = set()
        canonical_faces: Set[Face] = set()
        duplicate_faces = 0
        degenerate_faces = 0
        area = 0.0
        signed_volume = 0.0

        for face_index, face in enumerate(self.faces):
            canonical = tuple(sorted(face))
            if canonical in canonical_faces:
                duplicate_faces += 1
            canonical_faces.add(canonical)
            used_vertices.update(face)
            for vertex_index in face:
                vertex_faces.setdefault(vertex_index, []).append(face_index)
            for start, end in (
                (face[0], face[1]),
                (face[1], face[2]),
                (face[2], face[0]),
            ):
                edge = (start, end) if start < end else (end, start)
                direction = 1 if (start, end) == edge else -1
                edge_directions.setdefault(edge, []).append(direction)

            cross = self.face_cross(face_index)
            doubled_area = _length(cross)
            if doubled_area <= area_epsilon * 2.0:
                degenerate_faces += 1
            area += 0.5 * doubled_area
            a, b, c = self.triangle(face_index)
            signed_volume += (
                a[0] * (b[1] * c[2] - b[2] * c[1])
                + a[1] * (b[2] * c[0] - b[0] * c[2])
                + a[2] * (b[0] * c[1] - b[1] * c[0])
            ) / 6.0

        remaining = set(range(len(self.faces)))
        component_count = 0
        while remaining:
            component_count += 1
            pending = [remaining.pop()]
            while pending:
                face_index = pending.pop()
                for vertex_index in self.faces[face_index]:
                    for neighbor in vertex_faces[vertex_index]:
                        if neighbor in remaining:
                            remaining.remove(neighbor)
                            pending.append(neighbor)

        nonmanifold_vertices = 0
        for vertex_index, incident_faces in vertex_faces.items():
            fan_remaining = set(incident_faces)
            fan_components = 0
            while fan_remaining:
                fan_components += 1
                fan_pending = [fan_remaining.pop()]
                while fan_pending:
                    face_index = fan_pending.pop()
                    face = self.faces[face_index]
                    neighbors = [index for index in face if index != vertex_index]
                    for neighbor_vertex in neighbors:
                        for candidate in vertex_faces[vertex_index]:
                            if (
                                candidate in fan_remaining
                                and neighbor_vertex in self.faces[candidate]
                            ):
                                fan_remaining.remove(candidate)
                                fan_pending.append(candidate)
                if fan_components > 1:
                    nonmanifold_vertices += 1
                    break

        bounds = None
        if self.vertices:
            bounds = (
                tuple(min(vertex[axis] for vertex in self.vertices) for axis in range(3)),
                tuple(max(vertex[axis] for vertex in self.vertices) for axis in range(3)),
            )
        return MeshStatistics(
            vertex_count=len(self.vertices),
            face_count=len(self.faces),
            edge_count=len(edge_directions),
            boundary_edge_count=sum(len(uses) == 1 for uses in edge_directions.values()),
            nonmanifold_edge_count=sum(len(uses) > 2 for uses in edge_directions.values()),
            nonmanifold_vertex_count=nonmanifold_vertices,
            inconsistent_winding_edge_count=sum(
                len(uses) == 2 and uses[0] == uses[1]
                for uses in edge_directions.values()
            ),
            degenerate_face_count=degenerate_faces,
            duplicate_face_count=duplicate_faces,
            unused_vertex_count=len(self.vertices) - len(used_vertices),
            connected_component_count=component_count,
            surface_area=area,
            signed_volume=signed_volume,
            bounds=bounds,  # type: ignore[arg-type]
        )
