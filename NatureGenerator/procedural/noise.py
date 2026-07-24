"""Dependency-free object-space noise and safe area-weighted mesh normals."""

import math
from typing import Tuple

from core.mesh import Point3, TriangleMesh


def vertex_normals(mesh: TriangleMesh) -> Tuple[Point3, ...]:
    """Return normalized sums of adjacent face cross products.

    A face cross product has magnitude twice its area, so summing these vectors
    produces deterministic area-weighted vertex normals in linear time.
    """

    if not isinstance(mesh, TriangleMesh):
        raise TypeError("mesh must be a TriangleMesh")
    accumulated = [[0.0, 0.0, 0.0] for _ in mesh.vertices]
    strongest = [None for _ in mesh.vertices]
    strongest_length = [0.0 for _ in mesh.vertices]
    global_normal = None
    global_length = 0.0
    for face_index, face in enumerate(mesh.faces):
        cross = mesh.face_cross(face_index)
        cross_length = math.sqrt(sum(value * value for value in cross))
        if cross_length <= 1e-15:
            continue
        if cross_length > global_length:
            global_length = cross_length
            global_normal = cross
        for vertex_index in face:
            for axis in range(3):
                accumulated[vertex_index][axis] += cross[axis]
            if cross_length > strongest_length[vertex_index]:
                strongest_length[vertex_index] = cross_length
                strongest[vertex_index] = cross
    if global_normal is None:
        raise ValueError("mesh has no usable non-degenerate triangle normal")

    centroid = tuple(
        sum(vertex[axis] for vertex in mesh.vertices) / len(mesh.vertices)
        for axis in range(3)
    )
    normals = []
    for index, values in enumerate(accumulated):
        length = math.sqrt(sum(value * value for value in values))
        candidate = values
        if length <= 1e-15 and strongest[index] is not None:
            candidate = strongest[index]
            length = strongest_length[index]
        if length <= 1e-15:
            radial = tuple(
                mesh.vertices[index][axis] - centroid[axis]
                for axis in range(3)
            )
            radial_length = math.sqrt(
                sum(value * value for value in radial)
            )
            if radial_length > 1e-15:
                candidate = radial
                length = radial_length
            else:
                candidate = global_normal
                length = global_length
        normals.append(tuple(value / length for value in candidate))
    return tuple(normals)  # type: ignore[return-value]


def _lattice(seed: int, x: int, y: int, z: int) -> float:
    value = (seed ^ (x * 0x8DA6B343) ^ (y * 0xD8163841) ^
             (z * 0xCB1AB31F)) & 0xFFFFFFFF
    value ^= value >> 16
    value = (value * 0x7FEB352D) & 0xFFFFFFFF
    value ^= value >> 15
    value = (value * 0x846CA68B) & 0xFFFFFFFF
    value ^= value >> 16
    return (value / 2147483647.5) - 1.0


def value_noise(position: Point3, frequency: float, seed: int) -> float:
    """Sample smooth trilinear value noise at an object-space position."""

    coordinates = tuple(value * frequency for value in position)
    cells = tuple(math.floor(value) for value in coordinates)
    fractions = tuple(
        coordinates[axis] - cells[axis] for axis in range(3)
    )
    fades = tuple(value * value * (3.0 - 2.0 * value) for value in fractions)

    def blend(a: float, b: float, amount: float) -> float:
        return a + (b - a) * amount

    planes = []
    for dz in (0, 1):
        rows = []
        for dy in (0, 1):
            rows.append(blend(
                _lattice(seed, cells[0], cells[1] + dy, cells[2] + dz),
                _lattice(seed, cells[0] + 1, cells[1] + dy, cells[2] + dz),
                fades[0],
            ))
        planes.append(blend(rows[0], rows[1], fades[1]))
    return blend(planes[0], planes[1], fades[2])


def fractal_value_noise(
    position: Point3,
    scale: float,
    octaves: int,
    persistence: float,
    lacunarity: float,
    seed: int,
) -> float:
    """Return normalized deterministic fractal value noise in approximately [-1, 1]."""

    frequency = 1.0 / scale
    weight = 1.0
    total = 0.0
    weight_total = 0.0
    for octave in range(octaves):
        total += weight * value_noise(
            position, frequency, seed + octave * 1013
        )
        weight_total += weight
        weight *= persistence
        frequency *= lacunarity
    return total / weight_total
