"""Immutable result metadata for volume generation."""

from dataclasses import dataclass, field
import math

from core.mesh import MeshStatistics, TriangleMesh
from .cost_estimate import VolumeCostEstimate
from .timings import VolumeGenerationTimings


@dataclass(frozen=True)
class GyroidVolumeResult:
    mesh: TriangleMesh
    statistics: MeshStatistics
    digest: str
    sample_count: int
    cell_count: int
    scalar_bytes: int
    elapsed_time: float = field(compare=False)
    boundary_behavior: str = "open_at_bounds"
    cost_estimate: VolumeCostEstimate = None
    timings: VolumeGenerationTimings = field(default=None, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.mesh, TriangleMesh):
            raise TypeError("mesh must be a TriangleMesh")
        if self.statistics != self.mesh.statistics():
            raise ValueError("statistics must describe mesh")
        if not self.mesh.vertices or not self.mesh.faces:
            raise ValueError("volume generation produced an empty iso-surface")
        if not math.isfinite(self.elapsed_time) or self.elapsed_time < 0.0:
            raise ValueError("elapsed_time must be finite and non-negative")
        if (
            self.cost_estimate is not None
            and not isinstance(self.cost_estimate, VolumeCostEstimate)
        ):
            raise TypeError("cost_estimate must be a VolumeCostEstimate")
        if (
            self.timings is not None
            and not isinstance(self.timings, VolumeGenerationTimings)
        ):
            raise TypeError("timings must be VolumeGenerationTimings")
