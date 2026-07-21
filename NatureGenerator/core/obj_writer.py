"""Wavefront OBJ export for indexed triangle meshes."""

from pathlib import Path
from typing import TextIO, Union

from .mesh import TriangleMesh


PathLike = Union[str, Path]


def _number(value: float) -> str:
    return "0" if value == 0.0 else format(value, ".17g")


def write_obj(
    mesh: TriangleMesh,
    destination: PathLike,
    name: str = "NatureGenerator",
    include_normals: bool = True,
) -> None:
    """Write *mesh* to a Wavefront OBJ file."""

    with Path(destination).open("w", encoding="utf-8", newline="\n") as stream:
        write_obj_stream(mesh, stream, name, include_normals)


def write_obj_stream(
    mesh: TriangleMesh,
    stream: TextIO,
    name: str = "NatureGenerator",
    include_normals: bool = True,
) -> None:
    """Write Wavefront OBJ text to an open stream."""

    object_name = "_".join(str(name).split()) or "NatureGenerator"
    stream.write("# NatureGenerator OBJ\n")
    stream.write("o {}\n".format(object_name))
    for vertex in mesh.vertices:
        stream.write("v {} {} {}\n".format(*map(_number, vertex)))

    if include_normals:
        for normal in mesh.vertex_normals():
            stream.write("vn {} {} {}\n".format(*map(_number, normal)))
        for face in mesh.faces:
            entries = ("{0}//{0}".format(index + 1) for index in face)
            stream.write("f {}\n".format(" ".join(entries)))
    else:
        for face in mesh.faces:
            stream.write("f {}\n".format(" ".join(str(index + 1) for index in face)))
