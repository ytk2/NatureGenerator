"""Topology and geometry validation for triangle meshes."""

from dataclasses import dataclass
from typing import List, Tuple

from .mesh import MeshStatistics, TriangleMesh


@dataclass(frozen=True)
class ValidationIssue:
    """One actionable mesh validation finding."""

    severity: str
    code: str
    message: str
    count: int


@dataclass(frozen=True)
class MeshValidation:
    """Validation result and the statistics used to produce it."""

    valid: bool
    manifold: bool
    watertight: bool
    statistics: MeshStatistics
    issues: Tuple[ValidationIssue, ...]


class MeshValidator:
    """Validate topology, winding, degenerate geometry, and mesh hygiene."""

    def __init__(self, require_watertight: bool = False, area_epsilon: float = 1e-12) -> None:
        self.require_watertight = bool(require_watertight)
        self.area_epsilon = float(area_epsilon)

    def validate(self, mesh: TriangleMesh) -> MeshValidation:
        """Return a validation report without modifying *mesh*."""

        statistics = mesh.statistics(self.area_epsilon)
        issues: List[ValidationIssue] = []

        def add(severity: str, code: str, message: str, count: int) -> None:
            if count:
                issues.append(ValidationIssue(severity, code, message, count))

        add("error", "degenerate_faces", "zero-area or near-zero-area faces", statistics.degenerate_face_count)
        add("error", "duplicate_faces", "duplicate triangles", statistics.duplicate_face_count)
        add("error", "nonmanifold_edges", "edges incident to more than two faces", statistics.nonmanifold_edge_count)
        add("error", "nonmanifold_vertices", "vertices joining disconnected face fans", statistics.nonmanifold_vertex_count)
        add("error", "inconsistent_winding", "shared edges with matching face directions", statistics.inconsistent_winding_edge_count)
        boundary_severity = "error" if self.require_watertight else "warning"
        add(boundary_severity, "boundary_edges", "edges incident to only one face", statistics.boundary_edge_count)
        add("warning", "unused_vertices", "vertices not referenced by any face", statistics.unused_vertex_count)
        if statistics.face_count == 0:
            add("error", "empty_mesh", "mesh contains no faces", 1)

        return MeshValidation(
            valid=not any(issue.severity == "error" for issue in issues),
            manifold=statistics.is_manifold,
            watertight=statistics.is_watertight,
            statistics=statistics,
            issues=tuple(issues),
        )
