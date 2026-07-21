"""Dependency-free text visualization helpers for scalar fields."""

import math
from typing import Sequence, Tuple

from core.scalar_field import ScalarField


Range = Tuple[float, float]


def _range(values: Sequence[float], name: str) -> Range:
    if len(values) != 2:
        raise ValueError("{} must contain two values".format(name))
    result = (float(values[0]), float(values[1]))
    if not all(math.isfinite(value) for value in result) or result[1] <= result[0]:
        raise ValueError("{} must be a finite increasing range".format(name))
    return result


def render_ascii_slice(
    field: ScalarField,
    x_range: Sequence[float],
    y_range: Sequence[float],
    *,
    z: float = 0.0,
    width: int = 61,
    height: int = 31,
    iso_value: float = 0.0,
    band: float = 0.05,
) -> str:
    """Render a z-plane slice as dependency-free ASCII art.

    ``#`` marks samples within ``band`` of the isovalue, ``.`` marks lower
    values, and a space marks higher values. The first row is the maximum y
    coordinate so the result reads like a conventional Cartesian plot.
    """

    x_bounds = _range(x_range, "x_range")
    y_bounds = _range(y_range, "y_range")
    if isinstance(width, bool) or not isinstance(width, int) or width < 2:
        raise ValueError("width must be an integer of at least two")
    if isinstance(height, bool) or not isinstance(height, int) or height < 2:
        raise ValueError("height must be an integer of at least two")
    z = float(z)
    iso_value = float(iso_value)
    band = float(band)
    if not all(math.isfinite(value) for value in (z, iso_value, band)) or band < 0.0:
        raise ValueError("z and iso_value must be finite and band must be non-negative")

    rows = []
    for row in range(height):
        y = y_bounds[1] - (y_bounds[1] - y_bounds[0]) * row / (height - 1)
        characters = []
        for column in range(width):
            x = x_bounds[0] + (x_bounds[1] - x_bounds[0]) * column / (width - 1)
            value = float(field(x, y, z))
            if not math.isfinite(value):
                raise ValueError("scalar field values must be finite")
            if abs(value - iso_value) <= band:
                characters.append("#")
            elif value < iso_value:
                characters.append(".")
            else:
                characters.append(" ")
        rows.append("".join(characters))
    return "\n".join(rows)
