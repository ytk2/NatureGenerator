"""Thin, Fusion-independent orchestration for the Generate Sponge command."""

from typing import Callable, Tuple

from core.mesh import TriangleMesh
from generators import GeneratorFactory, GeneratorResult
from presets import PresetFactory


MeshInserter = Callable[[TriangleMesh, str], object]


def generate_sponge(insert_mesh: MeshInserter) -> Tuple[GeneratorResult, object]:
    """Generate the Sponge preset and pass its mesh across an adapter boundary."""

    if not callable(insert_mesh):
        raise TypeError("insert_mesh must be callable")
    preset = PresetFactory.get("sponge")
    result = GeneratorFactory.generate(preset)
    body = insert_mesh(result.mesh, "NatureGenerator Sponge")
    if body is None:
        raise RuntimeError("the Fusion Adapter did not return a MeshBody")
    return result, body
