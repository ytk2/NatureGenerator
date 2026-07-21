"""Regular, immutable samples of a three-dimensional scalar field."""

from dataclasses import dataclass
import math
from typing import Iterator, Sequence, Tuple

from .scalar_field import Point3, ScalarField, evaluate


GridShape = Tuple[int, int, int]
CellCorners = Tuple[int, int, int, int, int, int, int, int]


def _point3(values: Sequence[float], name: str) -> Point3:
    if len(values) != 3:
        raise ValueError("{} must contain exactly three values".format(name))
    point = (float(values[0]), float(values[1]), float(values[2]))
    if not all(math.isfinite(value) for value in point):
        raise ValueError("{} values must be finite".format(name))
    return point


def _shape3(values: Sequence[int]) -> GridShape:
    if len(values) != 3:
        raise ValueError("shape must contain exactly three values")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise TypeError("shape values must be integers")
    shape = (values[0], values[1], values[2])
    if any(value < 2 for value in shape):
        raise ValueError("each shape dimension must contain at least two samples")
    return shape


@dataclass(frozen=True)
class VoxelGrid:
    """Scalar samples on an axis-aligned regular grid.

    ``shape`` counts sample points, not cells. Values are stored with the x axis
    varying fastest, then y, then z. A shape of ``(nx, ny, nz)`` therefore
    contains ``(nx - 1) * (ny - 1) * (nz - 1)`` voxel cells.
    """

    origin: Point3
    spacing: Point3
    shape: GridShape
    values: Tuple[float, ...]

    def __post_init__(self) -> None:
        origin = _point3(self.origin, "origin")
        spacing = _point3(self.spacing, "spacing")
        shape = _shape3(self.shape)
        if any(value <= 0.0 for value in spacing):
            raise ValueError("spacing values must be greater than zero")

        values = tuple(float(value) for value in self.values)
        expected = shape[0] * shape[1] * shape[2]
        if len(values) != expected:
            raise ValueError(
                "values contains {} samples; expected {}".format(len(values), expected)
            )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("voxel samples must be finite")

        object.__setattr__(self, "origin", origin)
        object.__setattr__(self, "spacing", spacing)
        object.__setattr__(self, "shape", shape)
        object.__setattr__(self, "values", values)

    @classmethod
    def sample(
        cls,
        field: ScalarField,
        minimum: Sequence[float],
        maximum: Sequence[float],
        shape: Sequence[int],
    ) -> "VoxelGrid":
        """Sample *field* over inclusive axis-aligned bounds."""

        lower = _point3(minimum, "minimum")
        upper = _point3(maximum, "maximum")
        grid_shape = _shape3(shape)
        if any(high <= low for low, high in zip(lower, upper)):
            raise ValueError("maximum must be greater than minimum on every axis")

        spacing = tuple(
            (high - low) / (count - 1)
            for low, high, count in zip(lower, upper, grid_shape)
        )
        samples = []
        for k in range(grid_shape[2]):
            z = lower[2] + spacing[2] * k
            for j in range(grid_shape[1]):
                y = lower[1] + spacing[1] * j
                for i in range(grid_shape[0]):
                    x = lower[0] + spacing[0] * i
                    samples.append(evaluate(field, (x, y, z)))

        return cls(lower, spacing, grid_shape, tuple(samples))

    @property
    def cell_shape(self) -> GridShape:
        """Return the number of voxel cells on each axis."""

        return (self.shape[0] - 1, self.shape[1] - 1, self.shape[2] - 1)

    def index(self, i: int, j: int, k: int) -> int:
        """Return the flat sample index, validating all coordinates."""

        nx, ny, nz = self.shape
        if not (0 <= i < nx and 0 <= j < ny and 0 <= k < nz):
            raise IndexError("voxel sample index is out of range")
        return (k * ny + j) * nx + i

    def value_at(self, i: int, j: int, k: int) -> float:
        """Return the scalar sample at grid coordinates."""

        return self.values[self.index(i, j, k)]

    def point_at(self, i: int, j: int, k: int) -> Point3:
        """Return the world-space point at grid coordinates."""

        self.index(i, j, k)
        return (
            self.origin[0] + self.spacing[0] * i,
            self.origin[1] + self.spacing[1] * j,
            self.origin[2] + self.spacing[2] * k,
        )

    def cell_corner_indices(self, i: int, j: int, k: int) -> CellCorners:
        """Return a cell's eight flat sample indices.

        The lower z face is returned first in counter-clockwise order when seen
        from above, followed by the corresponding upper z face.
        """

        cx, cy, cz = self.cell_shape
        if not (0 <= i < cx and 0 <= j < cy and 0 <= k < cz):
            raise IndexError("voxel cell index is out of range")
        return (
            self.index(i, j, k),
            self.index(i + 1, j, k),
            self.index(i + 1, j + 1, k),
            self.index(i, j + 1, k),
            self.index(i, j, k + 1),
            self.index(i + 1, j, k + 1),
            self.index(i + 1, j + 1, k + 1),
            self.index(i, j + 1, k + 1),
        )

    def iter_cells(self) -> Iterator[Tuple[int, int, int, CellCorners]]:
        """Yield ``(i, j, k, corners)`` for every cell in stable order."""

        cx, cy, cz = self.cell_shape
        for k in range(cz):
            for j in range(cy):
                for i in range(cx):
                    yield i, j, k, self.cell_corner_indices(i, j, k)
