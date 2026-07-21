"""Incremental construction of indexed triangle meshes with vertex welding."""

import math
from typing import Dict, List, Sequence, Tuple

from .mesh import Face, Point3, TriangleMesh, _vertex


Bucket = Tuple[int, int, int]


class MeshBuilder:
    """Build a mesh while reusing exact or tolerance-close vertices.

    Welding is deterministic: the first matching vertex is retained. A zero
    tolerance performs exact tuple matching; a positive tolerance searches the
    containing spatial bucket and its 26 neighbors.
    """

    def __init__(self, weld_tolerance: float = 0.0) -> None:
        weld_tolerance = float(weld_tolerance)
        if not math.isfinite(weld_tolerance) or weld_tolerance < 0.0:
            raise ValueError("weld_tolerance must be finite and non-negative")
        self.weld_tolerance = weld_tolerance
        self._vertices: List[Point3] = []
        self._faces: List[Face] = []
        self._exact: Dict[Point3, int] = {}
        self._buckets: Dict[Bucket, List[int]] = {}

    @property
    def vertex_count(self) -> int:
        return len(self._vertices)

    @property
    def face_count(self) -> int:
        return len(self._faces)

    def _bucket(self, point: Point3) -> Bucket:
        tolerance = self.weld_tolerance
        return tuple(math.floor(value / tolerance) for value in point)  # type: ignore[return-value]

    def add_vertex(self, point: Sequence[float]) -> int:
        """Add or reuse a vertex and return its index."""

        candidate = _vertex(point)
        if self.weld_tolerance == 0.0:
            existing = self._exact.get(candidate)
            if existing is not None:
                return existing
            index = len(self._vertices)
            self._vertices.append(candidate)
            self._exact[candidate] = index
            return index

        bucket = self._bucket(candidate)
        tolerance_squared = self.weld_tolerance * self.weld_tolerance
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    neighbor = (bucket[0] + dx, bucket[1] + dy, bucket[2] + dz)
                    for index in self._buckets.get(neighbor, ()):
                        point = self._vertices[index]
                        distance_squared = sum(
                            (candidate[axis] - point[axis]) ** 2 for axis in range(3)
                        )
                        if distance_squared <= tolerance_squared:
                            return index
        index = len(self._vertices)
        self._vertices.append(candidate)
        self._buckets.setdefault(bucket, []).append(index)
        return index

    def add_face(self, a: int, b: int, c: int) -> int:
        """Add an indexed face and return its position in the face list."""

        face = (a, b, c)
        if any(isinstance(index, bool) or not isinstance(index, int) for index in face):
            raise TypeError("face indices must be integers")
        if len(set(face)) != 3:
            raise ValueError("a face must reference three distinct vertices")
        if any(index < 0 or index >= len(self._vertices) for index in face):
            raise ValueError("face index is outside the builder vertex array")
        self._faces.append(face)
        return len(self._faces) - 1

    def vertex(self, index: int) -> Point3:
        """Return a previously added vertex."""

        return self._vertices[index]

    def add_triangle(
        self, a: Sequence[float], b: Sequence[float], c: Sequence[float]
    ) -> int:
        """Weld three points, add their face, and return the face index."""

        return self.add_face(self.add_vertex(a), self.add_vertex(b), self.add_vertex(c))

    def extend(self, mesh: TriangleMesh) -> None:
        """Append another mesh, welding its vertices into this builder."""

        remap = [self.add_vertex(vertex) for vertex in mesh.vertices]
        for face in mesh.faces:
            mapped = tuple(remap[index] for index in face)
            if len(set(mapped)) == 3:
                self.add_face(*mapped)

    def build(self, compact: bool = True) -> TriangleMesh:
        """Return an immutable mesh, optionally removing unused vertices."""

        if not compact:
            return TriangleMesh(tuple(self._vertices), tuple(self._faces))
        used = sorted({index for face in self._faces for index in face})
        remap = {old: new for new, old in enumerate(used)}
        vertices = tuple(self._vertices[index] for index in used)
        faces = tuple(tuple(remap[index] for index in face) for face in self._faces)
        return TriangleMesh(vertices, faces)  # type: ignore[arg-type]
