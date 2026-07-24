"""Deterministic object-space gyroid field and smooth band response."""

import math

from core.mesh import Point3


def gyroid_field(
    position: Point3,
    period: float,
    phase_x: float = 0.0,
    phase_y: float = 0.0,
    phase_z: float = 0.0,
) -> float:
    """Evaluate one full gyroid period per object-space ``period``."""

    scale = (2.0 * math.pi) / period
    x = position[0] * scale + phase_x
    y = position[1] * scale + phase_y
    z = position[2] * scale + phase_z
    return (
        math.sin(x) * math.cos(y)
        + math.sin(y) * math.cos(z)
        + math.sin(z) * math.cos(x)
    )


def gyroid_response(field: float, threshold: float, band_width: float) -> float:
    """Return a smooth compact response around a selected gyroid isovalue."""

    normalized = min(1.0, abs(field - threshold) / band_width)
    smoothstep = normalized * normalized * (3.0 - 2.0 * normalized)
    return 1.0 - smoothstep
