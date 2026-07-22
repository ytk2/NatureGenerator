"""Request-oriented Sponge adapter around the existing GyroidGenerator."""

from core.mesh import TriangleMesh
from presets import PresetFactory

from .generator import InvalidGeneratorParameters, MeshGenerator
from .gyroid_generator import GyroidGenerator
from .request import GenerationRequest


class SpongeGenerator(MeshGenerator):
    """Preserve the existing Gyroid pipeline behind the mesh-generator contract."""

    @property
    def preset_id(self) -> str:
        return "sponge"

    @property
    def generator_id(self) -> str:
        return "gyroid"

    @property
    def require_watertight(self) -> bool:
        return False

    def generate(self, request: GenerationRequest) -> TriangleMesh:
        """Delegate without changing GyroidGenerator geometry or validation."""

        if not isinstance(request, GenerationRequest):
            raise TypeError("request must be a GenerationRequest")
        if request.preset_id != self.preset_id:
            raise InvalidGeneratorParameters(
                "request preset_id {!r} does not match {!r}".format(
                    request.preset_id, self.preset_id
                )
            )
        preset = PresetFactory.get(self.preset_id)
        return GyroidGenerator().generate(
            preset, request.parameter_overrides, request.resolution
        ).mesh
