"""Immutable result returned by the generator runtime."""

from dataclasses import dataclass
import math
from typing import Sequence, Tuple

from core.mesh import MeshStatistics, TriangleMesh


@dataclass(frozen=True)
class GeneratorResult:
    """Mesh, diagnostics, identity, and timing for one generation run."""

    mesh: TriangleMesh
    statistics: MeshStatistics
    warnings: Tuple[str, ...]
    generator_id: str
    preset_id: str
    elapsed_time: float

    def __post_init__(self) -> None:
        if not isinstance(self.mesh, TriangleMesh):
            raise TypeError("mesh must be a TriangleMesh")
        if not isinstance(self.statistics, MeshStatistics):
            raise TypeError("statistics must be MeshStatistics")
        if not isinstance(self.warnings, Sequence) or isinstance(self.warnings, str):
            raise TypeError("warnings must be a sequence of strings")
        warnings = tuple(self.warnings)
        if any(not isinstance(warning, str) or not warning for warning in warnings):
            raise TypeError("warnings must contain non-empty strings")
        for value, name in (
            (self.generator_id, "generator_id"),
            (self.preset_id, "preset_id"),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError("{} must be a non-empty string".format(name))
        elapsed_time = float(self.elapsed_time)
        if not math.isfinite(elapsed_time) or elapsed_time < 0.0:
            raise ValueError("elapsed_time must be finite and non-negative")

        object.__setattr__(self, "warnings", warnings)
        object.__setattr__(self, "elapsed_time", elapsed_time)
