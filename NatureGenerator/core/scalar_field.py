"""Contracts and validation helpers for three-dimensional scalar fields."""

import math
from typing import Protocol, Tuple


Point3 = Tuple[float, float, float]


class ScalarField(Protocol):
    """A field that maps an ``(x, y, z)`` position to a scalar value."""

    def sample(self, x: float, y: float, z: float) -> float:
        """Evaluate the field at a point."""
        ...

    def __call__(self, x: float, y: float, z: float) -> float:
        """Evaluate the field using callable syntax."""
        ...


def evaluate(field: ScalarField, point: Point3) -> float:
    """Evaluate *field* and return a finite floating-point value.

    ``ValueError`` is raised for NaN and infinite results because those values
    cannot be interpolated reliably during isosurface extraction.
    """

    value = float(field(*point))
    if not math.isfinite(value):
        raise ValueError("scalar field values must be finite")
    return value
