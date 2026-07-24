"""Procedural operator contract and Sprint 28 Pass Through implementation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping, Tuple

from core.mesh import TriangleMesh

from .models import ProceduralRequest, ProceduralResult, canonical_mesh_digest


@dataclass(frozen=True)
class ParameterDefinition:
    parameter_id: str
    display_name: str
    value_type: str
    default_value: Any


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
