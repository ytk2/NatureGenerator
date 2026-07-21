"""Pure-Python scalar field for a sheet-like gyroid surface."""

from dataclasses import dataclass
import math

from core.scalar_field import ScalarField


@dataclass(frozen=True)
class GyroidField(ScalarField):
    """A periodic gyroid sheet field in world-space units.

    ``cell_size`` is the length of one full gyroid period. ``thickness`` is the
    half-band around the mathematical zero surface: negative values returned by
    :meth:`sample` are inside that band, zero is its boundary, and positive
    values are outside. Mesh extraction is deliberately outside this class.
    """

    cell_size: float = 10.0
    thickness: float = 0.2

    def __post_init__(self) -> None:
        cell_size = float(self.cell_size)
        thickness = float(self.thickness)
        if not math.isfinite(cell_size) or cell_size <= 0.0:
            raise ValueError("cell_size must be a finite value greater than zero")
        if not math.isfinite(thickness) or thickness < 0.0:
            raise ValueError("thickness must be a finite value greater than or equal to zero")
        object.__setattr__(self, "cell_size", cell_size)
        object.__setattr__(self, "thickness", thickness)

    def raw_sample(self, x: float, y: float, z: float) -> float:
        """Return the dimensionless mathematical gyroid function value.

        World coordinates are scaled so one ``cell_size`` maps to ``2 * pi``:

        ``sin(x)cos(y) + sin(y)cos(z) + sin(z)cos(x)``.
        """

        scale = 2.0 * math.pi / self.cell_size
        sx, sy, sz = float(x) * scale, float(y) * scale, float(z) * scale
        if not all(math.isfinite(value) for value in (sx, sy, sz)):
            raise ValueError("sample coordinates must be finite")
        return (
            math.sin(sx) * math.cos(sy)
            + math.sin(sy) * math.cos(sz)
            + math.sin(sz) * math.cos(sx)
        )

    def sample(self, x: float, y: float, z: float) -> float:
        """Return signed distance-like sheet membership at a point.

        The value is ``abs(raw_sample) - thickness``. It is not a Euclidean
        distance; its magnitude is in gyroid field-value units.
        """

        return abs(self.raw_sample(x, y, z)) - self.thickness

    def __call__(self, x: float, y: float, z: float) -> float:
        """Delegate callable field evaluation to :meth:`sample`."""

        return self.sample(x, y, z)
