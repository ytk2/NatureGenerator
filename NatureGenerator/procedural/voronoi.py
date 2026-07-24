"""Deterministic bounded-memory object-space Voronoi evaluation."""

import math
from typing import Tuple

from core.mesh import Point3


Cell3 = Tuple[int, int, int]


def _unit_hash(seed: int, x: int, y: int, z: int, channel: int) -> float:
    """Return a stable scalar in [0, 1] for one lattice cell and channel."""

    value = (
        seed
        ^ (x * 0x8DA6B343)
        ^ (y * 0xD8163841)
        ^ (z * 0xCB1AB31F)
        ^ (channel * 0x9E3779B9)
    ) & 0xFFFFFFFF
    value ^= value >> 16
    value = (value * 0x7FEB352D) & 0xFFFFFFFF
    value ^= value >> 15
    value = (value * 0x846CA68B) & 0xFFFFFFFF
    value ^= value >> 16
    return value / 4294967295.0


def lattice_site(
    cell: Cell3,
    cell_size: float,
    jitter: float,
    seed: int,
) -> Point3:
    """Return the deterministic site inside one object-space lattice cell."""

    return tuple(
        (
            cell[axis]
            + 0.5
            + jitter * (
                _unit_hash(seed, cell[0], cell[1], cell[2], axis) - 0.5
            )
        ) * cell_size
        for axis in range(3)
    )  # type: ignore[return-value]


def nearest_site_distances(
    position: Point3,
    cell_size: float,
    jitter: float,
    seed: int,
    search_radius: int = 1,
) -> Tuple[float, float]:
    """Return nearest and second-nearest site distances from local cells."""

    if (
        isinstance(cell_size, bool)
        or not isinstance(cell_size, (int, float))
        or not math.isfinite(float(cell_size))
        or cell_size <= 0
    ):
        raise ValueError("cell_size must be finite and positive")
    if (
        isinstance(jitter, bool)
        or not isinstance(jitter, (int, float))
        or not math.isfinite(float(jitter))
        or jitter < 0
        or jitter > 1
    ):
        raise ValueError("jitter must be finite and between 0 and 1")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    if (
        isinstance(search_radius, bool)
        or not isinstance(search_radius, int)
        or search_radius < 1
    ):
        raise ValueError("search_radius must be a positive integer")

    size = float(cell_size)
    base = tuple(math.floor(value / size) for value in position)
    nearest_squared = math.inf
    second_squared = math.inf
    for z in range(base[2] - search_radius, base[2] + search_radius + 1):
        for y in range(base[1] - search_radius, base[1] + search_radius + 1):
            for x in range(base[0] - search_radius, base[0] + search_radius + 1):
                site = lattice_site((x, y, z), size, float(jitter), seed)
                distance_squared = (
                    (position[0] - site[0]) ** 2
                    + (position[1] - site[1]) ** 2
                    + (position[2] - site[2]) ** 2
                )
                if distance_squared < nearest_squared:
                    second_squared = nearest_squared
                    nearest_squared = distance_squared
                elif distance_squared < second_squared:
                    second_squared = distance_squared
    return math.sqrt(nearest_squared), math.sqrt(second_squared)


def boundary_mask(edge_measure: float, edge_width: float, falloff: float) -> float:
    """Map the nearest-distance difference to a smooth boundary strength."""

    normalized = max(0.0, 1.0 - edge_measure / edge_width)
    return normalized ** falloff
