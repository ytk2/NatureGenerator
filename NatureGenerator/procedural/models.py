"""Immutable data exchanged by Procedural Lab operators."""

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import math
import re
from types import MappingProxyType
from typing import Any, Mapping, Optional, Tuple

from core.mesh import MeshStatistics, Point3, TriangleMesh


Bounds = Tuple[Point3, Point3]
_EMPTY = MappingProxyType({})


class SourceType(Enum):
    SOLID_BODY = "solid_body"
    MESH_BODY = "mesh_body"


class ExecutionContext(Enum):
    PREVIEW = "preview"
    FINAL = "final"


def _identifier(value: str, name: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[a-z][a-z0-9_]*", value) is None:
        raise ValueError("{} must be a lowercase stable identifier".format(name))
    return value


def _metadata(values: Optional[Mapping[str, Any]], name: str) -> Mapping[str, Any]:
    if values is None:
        return _EMPTY
    if not isinstance(values, Mapping):
        raise TypeError("{} must be a mapping".format(name))
    copied = {}
    for key, value in values.items():
        if not isinstance(key, str) or not key:
            raise ValueError("{} keys must be non-empty strings".format(name))
        if not isinstance(value, (bool, int, float, str)):
            raise TypeError("{} values must be scalar".format(name))
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("{} values must be finite".format(name))
        copied[key] = value
    return MappingProxyType(copied)


def canonical_mesh_digest(mesh: TriangleMesh) -> str:
    """Return the project's deterministic indexed-mesh digest."""

    if not isinstance(mesh, TriangleMesh):
        raise TypeError("mesh must be a TriangleMesh")
    return hashlib.sha256(
        repr((mesh.vertices, mesh.faces)).encode("ascii")
    ).hexdigest()


@dataclass(frozen=True)
class ProceduralInputGeometry:
    source_type: SourceType
    mesh: TriangleMesh
    source_name: str
    source_identifier: str
    bounds: Optional[Bounds] = None
    units: str = "mm"
    provenance: Mapping[str, Any] = field(default_factory=lambda: _EMPTY)

    def __post_init__(self) -> None:
        if not isinstance(self.source_type, SourceType):
            raise TypeError("source_type must be a SourceType")
        if not isinstance(self.mesh, TriangleMesh):
            raise TypeError("mesh must be a TriangleMesh")
        if not self.mesh.vertices or not self.mesh.faces:
            raise ValueError("input geometry mesh must be non-empty")
        if not isinstance(self.source_name, str) or not self.source_name.strip():
            raise ValueError("source_name must be non-empty")
        if not isinstance(self.source_identifier, str) or not self.source_identifier:
            raise ValueError("source_identifier must be non-empty")
        if self.units != "mm":
            raise ValueError("Procedural Lab core geometry units must be millimeters")
        actual_bounds = self.mesh.statistics().bounds
        if self.bounds is not None and self.bounds != actual_bounds:
            raise ValueError("bounds must match the input mesh")
        object.__setattr__(self, "bounds", actual_bounds)
        object.__setattr__(self, "provenance", _metadata(
            self.provenance, "provenance"
        ))

    @property
    def digest(self) -> str:
        return canonical_mesh_digest(self.mesh)


@dataclass(frozen=True)
class ProceduralRequest:
    input_geometry: ProceduralInputGeometry
    operator_id: str
    operator_parameters: Mapping[str, Any] = field(default_factory=lambda: _EMPTY)
    execution_context: ExecutionContext = ExecutionContext.FINAL

    def __post_init__(self) -> None:
        if not isinstance(self.input_geometry, ProceduralInputGeometry):
            raise TypeError("input_geometry must be ProceduralInputGeometry")
        _identifier(self.operator_id, "operator_id")
        if not isinstance(self.execution_context, ExecutionContext):
            raise TypeError("execution_context must be an ExecutionContext")
        object.__setattr__(self, "operator_parameters", _metadata(
            self.operator_parameters, "operator_parameters"
        ))


@dataclass(frozen=True)
class ProceduralResult:
    mesh: TriangleMesh
    statistics: MeshStatistics
    operator_id: str
    source_provenance: Mapping[str, Any]
    execution_metadata: Mapping[str, Any]
    units: str
    input_digest: str
    output_digest: str

    def __post_init__(self) -> None:
        if not isinstance(self.mesh, TriangleMesh):
            raise TypeError("mesh must be a TriangleMesh")
        if not isinstance(self.statistics, MeshStatistics):
            raise TypeError("statistics must be MeshStatistics")
        _identifier(self.operator_id, "operator_id")
        if self.statistics != self.mesh.statistics():
            raise ValueError("statistics must describe the result mesh")
        if self.units != "mm":
            raise ValueError("result units must be millimeters")
        for value, name in (
            (self.input_digest, "input_digest"),
            (self.output_digest, "output_digest"),
        ):
            if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise ValueError("{} must be a SHA-256 digest".format(name))
        if self.output_digest != canonical_mesh_digest(self.mesh):
            raise ValueError("output_digest must match the result mesh")
        object.__setattr__(self, "source_provenance", _metadata(
            self.source_provenance, "source_provenance"
        ))
        object.__setattr__(self, "execution_metadata", _metadata(
            self.execution_metadata, "execution_metadata"
        ))
