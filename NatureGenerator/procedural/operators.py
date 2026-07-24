"""Procedural operator contract and built-in implementations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import math
import re
from typing import Any, Tuple

from core.mesh import TriangleMesh

from .models import ProceduralRequest, ProceduralResult, canonical_mesh_digest
from .noise import fractal_value_noise, vertex_normals
from .subdivision import subdivide
from .voronoi import boundary_mask, nearest_site_distances


@dataclass(frozen=True)
class ParameterDefinition:
    parameter_id: str
    display_name: str
    value_type: str
    default_value: Any
    minimum: Any = None
    maximum: Any = None
    unit: str = ""
    minimum_inclusive: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.parameter_id, str) or re.fullmatch(
            r"[a-z][a-z0-9_]*", self.parameter_id
        ) is None:
            raise ValueError("parameter_id must be a lowercase stable identifier")
        if not isinstance(self.display_name, str) or not self.display_name:
            raise ValueError("display_name must be non-empty")
        if self.value_type not in ("float", "integer", "length"):
            raise ValueError("unsupported parameter value_type")
        self.validate(self.default_value)

    def validate(self, value: Any) -> Any:
        if self.value_type == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError("{} must be an integer".format(self.display_name))
            normalized = value
        else:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError("{} must be numeric".format(self.display_name))
            normalized = float(value)
            if not math.isfinite(normalized):
                raise ValueError("{} must be finite".format(self.display_name))
        if self.minimum is not None:
            below = normalized < self.minimum
            equal_disallowed = (
                normalized == self.minimum and not self.minimum_inclusive
            )
            if below or equal_disallowed:
                relation = "greater than" if not self.minimum_inclusive else "at least"
                raise ValueError("{} must be {} {}".format(
                    self.display_name, relation, self.minimum
                ))
        if self.maximum is not None and normalized > self.maximum:
            raise ValueError("{} must be at most {}".format(
                self.display_name, self.maximum
            ))
        return normalized


class ProceduralOperator(ABC):
    operator_id: str
    display_name: str
    parameter_definitions: Tuple[ParameterDefinition, ...] = ()

    def validate(self, request: ProceduralRequest) -> None:
        if not isinstance(request, ProceduralRequest):
            raise TypeError("request must be a ProceduralRequest")
        if request.operator_id != self.operator_id:
            raise ValueError("request operator does not match this operator")
        known = {item.parameter_id for item in self.parameter_definitions}
        unknown = set(request.operator_parameters).difference(known)
        if unknown:
            raise ValueError("unknown operator parameters: {}".format(
                ", ".join(sorted(unknown))
            ))
        for definition in self.parameter_definitions:
            definition.validate(request.operator_parameters.get(
                definition.parameter_id, definition.default_value
            ))

    def parameters(self, request: ProceduralRequest) -> dict:
        """Return a fully populated, validated plain parameter mapping."""

        self.validate(request)
        return {
            definition.parameter_id: definition.validate(
                request.operator_parameters.get(
                    definition.parameter_id, definition.default_value
                )
            )
            for definition in self.parameter_definitions
        }

    @abstractmethod
    def execute(self, request: ProceduralRequest) -> ProceduralResult:
        raise NotImplementedError


class PassThroughOperator(ProceduralOperator):
    operator_id = "pass_through"
    display_name = "Pass Through"

    def execute(self, request: ProceduralRequest) -> ProceduralResult:
        self.validate(request)
        source = request.input_geometry
        output = TriangleMesh(
            vertices=tuple(source.mesh.vertices),
            faces=tuple(source.mesh.faces),
        )
        digest = canonical_mesh_digest(output)
        provenance = dict(source.provenance)
        provenance.update({
            "source_identifier": source.source_identifier,
            "source_name": source.source_name,
            "source_type": source.source_type.value,
        })
        return ProceduralResult(
            mesh=output,
            statistics=output.statistics(),
            operator_id=self.operator_id,
            source_provenance=provenance,
            execution_metadata={
                "execution_context": request.execution_context.value,
                "operator_display_name": self.display_name,
            },
            units=source.units,
            input_digest=source.digest,
            output_digest=digest,
        )


class NoiseDisplacementOperator(ProceduralOperator):
    """Displace vertices along area-weighted normals using object-space fBm."""

    operator_id = "noise_displacement"
    display_name = "Noise Displacement"
    parameter_definitions = (
        ParameterDefinition(
            "amplitude", "Amplitude", "length", 2.0, 0.0, 50.0, "mm"
        ),
        ParameterDefinition(
            "scale", "Scale", "length", 20.0, 0.1, 1000.0, "mm",
            minimum_inclusive=True,
        ),
        ParameterDefinition("octaves", "Octaves", "integer", 3, 1, 6),
        ParameterDefinition("persistence", "Persistence", "float", 0.5, 0.0, 1.0),
        ParameterDefinition(
            "lacunarity", "Lacunarity", "float", 2.0, 1.0, 4.0,
            minimum_inclusive=False,
        ),
        ParameterDefinition(
            "seed", "Seed", "integer", 0, -2147483647, 2147483647
        ),
    )

    def execute(self, request: ProceduralRequest) -> ProceduralResult:
        parameters = self.parameters(request)
        source = request.input_geometry
        normals = vertex_normals(source.mesh)
        amplitude = parameters["amplitude"]
        output_vertices = []
        for position, normal in zip(source.mesh.vertices, normals):
            noise = fractal_value_noise(
                position,
                scale=parameters["scale"],
                octaves=parameters["octaves"],
                persistence=parameters["persistence"],
                lacunarity=parameters["lacunarity"],
                seed=parameters["seed"],
            )
            displacement = amplitude * noise
            output_vertices.append(tuple(
                position[axis] + normal[axis] * displacement
                for axis in range(3)
            ))
        output = TriangleMesh(tuple(output_vertices), tuple(source.mesh.faces))
        provenance = dict(source.provenance)
        provenance.update({
            "source_identifier": source.source_identifier,
            "source_name": source.source_name,
            "source_type": source.source_type.value,
        })
        return ProceduralResult(
            mesh=output,
            statistics=output.statistics(),
            operator_id=self.operator_id,
            source_provenance=provenance,
            execution_metadata={
                "amplitude_mm": amplitude,
                "execution_context": request.execution_context.value,
                "lacunarity": parameters["lacunarity"],
                "octaves": parameters["octaves"],
                "operator_display_name": self.display_name,
                "persistence": parameters["persistence"],
                "scale_mm": parameters["scale"],
                "seed": parameters["seed"],
            },
            units=source.units,
            input_digest=source.digest,
            output_digest=canonical_mesh_digest(output),
        )


class SubdivisionOperator(ProceduralOperator):
    """Increase triangle density without moving the piecewise-linear surface."""

    operator_id = "subdivision"
    display_name = "Subdivision"
    parameter_definitions = (
        ParameterDefinition(
            "level", "Subdivision Level", "integer", 1, 1, 3
        ),
    )

    def execute(self, request: ProceduralRequest) -> ProceduralResult:
        parameters = self.parameters(request)
        source = request.input_geometry
        level = parameters["level"]
        output = subdivide(source.mesh, level)
        provenance = dict(source.provenance)
        provenance.update({
            "source_identifier": source.source_identifier,
            "source_name": source.source_name,
            "source_type": source.source_type.value,
        })
        return ProceduralResult(
            mesh=output,
            statistics=output.statistics(),
            operator_id=self.operator_id,
            source_provenance=provenance,
            execution_metadata={
                "execution_context": request.execution_context.value,
                "level": level,
                "operator_display_name": self.display_name,
            },
            units=source.units,
            input_digest=source.digest,
            output_digest=canonical_mesh_digest(output),
        )


class VoronoiSurfaceOperator(ProceduralOperator):
    """Displace vertices near deterministic object-space Voronoi boundaries."""

    operator_id = "voronoi_surface"
    display_name = "Voronoi Surface"
    parameter_definitions = (
        ParameterDefinition(
            "cell_size", "Cell Size", "length", 20.0, 1.0, 500.0, "mm"
        ),
        ParameterDefinition(
            "depth", "Depth", "length", 2.0, -20.0, 20.0, "mm"
        ),
        ParameterDefinition(
            "edge_width", "Edge Width", "length", 3.0, 0.1, 50.0, "mm"
        ),
        ParameterDefinition("falloff", "Falloff", "float", 2.0, 0.25, 8.0),
        ParameterDefinition("jitter", "Jitter", "float", 0.75, 0.0, 1.0),
        ParameterDefinition(
            "seed", "Seed", "integer", 0, -2147483647, 2147483647
        ),
    )

    def execute(self, request: ProceduralRequest) -> ProceduralResult:
        parameters = self.parameters(request)
        source = request.input_geometry
        normals = vertex_normals(source.mesh)
        depth = parameters["depth"]
        output_vertices = []
        for position, normal in zip(source.mesh.vertices, normals):
            nearest, second = nearest_site_distances(
                position,
                parameters["cell_size"],
                parameters["jitter"],
                parameters["seed"],
            )
            mask = boundary_mask(
                second - nearest,
                parameters["edge_width"],
                parameters["falloff"],
            )
            displacement = depth * mask
            output_vertices.append(tuple(
                position[axis] + normal[axis] * displacement
                for axis in range(3)
            ))
        output = TriangleMesh(tuple(output_vertices), tuple(source.mesh.faces))
        provenance = dict(source.provenance)
        provenance.update({
            "source_identifier": source.source_identifier,
            "source_name": source.source_name,
            "source_type": source.source_type.value,
        })
        return ProceduralResult(
            mesh=output,
            statistics=output.statistics(),
            operator_id=self.operator_id,
            source_provenance=provenance,
            execution_metadata={
                "cell_size_mm": parameters["cell_size"],
                "depth_mm": depth,
                "edge_width_mm": parameters["edge_width"],
                "execution_context": request.execution_context.value,
                "falloff": parameters["falloff"],
                "jitter": parameters["jitter"],
                "operator_display_name": self.display_name,
                "seed": parameters["seed"],
            },
            units=source.units,
            input_digest=source.digest,
            output_digest=canonical_mesh_digest(output),
        )
