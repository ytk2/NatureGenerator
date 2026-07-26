"""Finite-thickness Gyroid band represented as a scalar field."""

from dataclasses import dataclass
import math
from typing import Sequence, Tuple

from core.mesh import TriangleMesh
from core.voxel_grid import VoxelGrid
from .gyroid_field import GyroidVolumeField


@dataclass(frozen=True)
class ThickenedGyroidField:
    """Approximate a physical wall around a Gyroid iso-surface.

    The zero set is ``abs(g - iso) - half_thickness * |gradient(g)| = 0``.
    The analytical gradient is measured in inverse millimetres, so the second
    term is dimensionless and represents a first-order physical offset.
    """

    field: GyroidVolumeField
    iso_value: float
    wall_thickness: float

    def __post_init__(self) -> None:
        if not isinstance(self.field, GyroidVolumeField):
            raise TypeError("field must be a GyroidVolumeField")
        values = (self.iso_value, self.wall_thickness)
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for value in values
        ):
            raise ValueError("thickened field values must be finite numbers")
        if self.wall_thickness <= 0.0:
            raise ValueError("wall_thickness must be greater than zero")

    def gradient_magnitude(self, x: float, y: float, z: float) -> float:
        gradient = self.field.gradient(x, y, z)
        magnitude = math.sqrt(sum(value * value for value in gradient))
        regularization = (
            (2.0 * math.pi) / float(self.field.period)
        ) * 1e-9
        return math.sqrt(
            magnitude * magnitude + regularization * regularization
        )

    def sample(self, x: float, y: float, z: float) -> float:
        return max(self.side_values(x, y, z))

    def side_values(
        self, x: float, y: float, z: float
    ) -> Tuple[float, float]:
        """Return upper and lower fields whose intersection is the wall."""

        half_band = (
            0.5
            * float(self.wall_thickness)
            * self.gradient_magnitude(x, y, z)
        )
        offset = self.field.sample(x, y, z) - float(self.iso_value)
        return (offset - half_band, -offset - half_band)

    def __call__(self, x: float, y: float, z: float) -> float:
        return self.sample(x, y, z)


def sample_thickened_band_grids(
    field: ThickenedGyroidField,
    minimum: Sequence[float],
    maximum: Sequence[float],
    shape: Sequence[int],
) -> Tuple[VoxelGrid, VoxelGrid]:
    """Sample both wall boundaries in one deterministic coordinate pass."""

    if not isinstance(field, ThickenedGyroidField):
        raise TypeError("field must be a ThickenedGyroidField")
    if len(minimum) != 3 or len(maximum) != 3 or len(shape) != 3:
        raise ValueError("bounds and shape must contain three values")
    lower = tuple(float(value) for value in minimum)
    upper = tuple(float(value) for value in maximum)
    if not all(
        math.isfinite(value) for value in lower + upper
    ) or any(
        high <= low for low, high in zip(lower, upper)
    ):
        raise ValueError("maximum must be finite and greater than minimum")
    if any(
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 2
        for value in shape
    ):
        raise ValueError("shape values must be integers of at least two")
    grid_shape = tuple(shape)
    spacing = tuple(
        (upper[axis] - lower[axis]) / (grid_shape[axis] - 1)
        for axis in range(3)
    )
    upper_values = []
    lower_values = []
    for k in range(grid_shape[2]):
        z = lower[2] + spacing[2] * k
        for j in range(grid_shape[1]):
            y = lower[1] + spacing[1] * j
            for i in range(grid_shape[0]):
                x = lower[0] + spacing[0] * i
                upper_value, lower_value = field.side_values(x, y, z)
                upper_values.append(upper_value)
                lower_values.append(lower_value)
    return (
        VoxelGrid(lower, spacing, grid_shape, tuple(upper_values)),
        VoxelGrid(lower, spacing, grid_shape, tuple(lower_values)),
    )


def combine_wall_surfaces(
    upper_mesh: TriangleMesh, lower_mesh: TriangleMesh
) -> TriangleMesh:
    """Combine two immutable indexed wall sides without changing either side."""

    if not isinstance(upper_mesh, TriangleMesh) or not isinstance(
        lower_mesh, TriangleMesh
    ):
        raise TypeError("wall sides must be TriangleMesh values")
    offset = len(upper_mesh.vertices)
    return TriangleMesh(
        upper_mesh.vertices + lower_mesh.vertices,
        upper_mesh.faces
        + tuple(
            tuple(index + offset for index in face)
            for face in lower_mesh.faces
        ),
    )
