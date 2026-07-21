"""ASCII and binary STL export for pure-Python triangle meshes."""

from dataclasses import dataclass
import math
from pathlib import Path
import re
import struct
from typing import BinaryIO, Optional, TextIO, Union

from .mesh import TriangleMesh


PathLike = Union[str, Path]


@dataclass(frozen=True)
class StlValidation:
    """Structural validation result for an STL file."""

    valid: bool
    encoding: str
    triangle_count: int
    message: str


def _solid_name(name: str) -> str:
    cleaned = re.sub(r"\s+", "_", str(name).strip())
    return cleaned or "NatureGenerator"


def _number(value: float) -> str:
    return "0" if value == 0.0 else format(value, ".17g")


def write_ascii(mesh: TriangleMesh, destination: PathLike, name: str = "NatureGenerator") -> None:
    """Write *mesh* as an ASCII STL file."""

    with Path(destination).open("w", encoding="ascii", newline="\n") as stream:
        write_ascii_stream(mesh, stream, name)


def write_ascii_stream(mesh: TriangleMesh, stream: TextIO, name: str = "NatureGenerator") -> None:
    """Write ASCII STL text to an open text stream."""

    solid = _solid_name(name)
    stream.write("solid {}\n".format(solid))
    for face_index, triangle in enumerate(mesh.triangles()):
        normal = mesh.face_normal(face_index)
        stream.write("  facet normal {} {} {}\n".format(*map(_number, normal)))
        stream.write("    outer loop\n")
        for vertex in triangle:
            stream.write("      vertex {} {} {}\n".format(*map(_number, vertex)))
        stream.write("    endloop\n")
        stream.write("  endfacet\n")
    stream.write("endsolid {}\n".format(solid))


def write_binary(mesh: TriangleMesh, destination: PathLike, header: str = "NatureGenerator") -> None:
    """Write *mesh* as a little-endian binary STL file."""

    with Path(destination).open("wb") as stream:
        write_binary_stream(mesh, stream, header)


def write_binary_stream(mesh: TriangleMesh, stream: BinaryIO, header: str = "NatureGenerator") -> None:
    """Write binary STL bytes to an open binary stream."""

    header_bytes = str(header).encode("ascii", errors="replace")[:80]
    stream.write(header_bytes.ljust(80, b"\0"))
    stream.write(struct.pack("<I", len(mesh.faces)))
    for face_index, triangle in enumerate(mesh.triangles()):
        normal = mesh.face_normal(face_index)
        values = normal + triangle[0] + triangle[1] + triangle[2]
        stream.write(struct.pack("<12fH", *values, 0))


def validate_stl(
    source: PathLike, expected_triangles: Optional[int] = None
) -> StlValidation:
    """Validate STL structure and optionally its triangle count.

    This checks binary record sizes and finite numeric data, or the required
    ASCII facet/vertex structure. It does not prove that the represented mesh is
    watertight; use :meth:`TriangleMesh.statistics` before export for that.
    """

    data = Path(source).read_bytes()
    if len(data) >= 84:
        binary_count = struct.unpack("<I", data[80:84])[0]
        expected_size = 84 + 50 * binary_count
        if expected_size == len(data):
            if expected_triangles is not None and binary_count != expected_triangles:
                return StlValidation(
                    False, "binary", binary_count, "unexpected triangle count"
                )
            for offset in range(84, len(data), 50):
                values = struct.unpack("<12fH", data[offset : offset + 50])
                if not all(math.isfinite(value) for value in values[:12]):
                    return StlValidation(
                        False, "binary", binary_count, "non-finite triangle data"
                    )
            return StlValidation(True, "binary", binary_count, "valid binary STL")

    try:
        text = data.decode("ascii")
    except UnicodeDecodeError:
        return StlValidation(False, "unknown", 0, "not a valid binary or ASCII STL")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or not lines[0].startswith("solid") or not lines[-1].startswith("endsolid"):
        return StlValidation(False, "ascii", 0, "missing solid delimiters")
    facet_count = sum(line.startswith("facet normal ") for line in lines)
    vertex_count = sum(line.startswith("vertex ") for line in lines)
    if (
        vertex_count != facet_count * 3
        or sum(line == "outer loop" for line in lines) != facet_count
        or sum(line == "endloop" for line in lines) != facet_count
        or sum(line == "endfacet" for line in lines) != facet_count
    ):
        return StlValidation(False, "ascii", facet_count, "incomplete facet structure")
    for line in lines:
        parts = line.split()
        numeric_parts = None
        if parts[:2] == ["facet", "normal"] and len(parts) == 5:
            numeric_parts = parts[2:]
        elif parts[:1] == ["vertex"] and len(parts) == 4:
            numeric_parts = parts[1:]
        if numeric_parts is not None:
            try:
                values = [float(value) for value in numeric_parts]
            except ValueError:
                return StlValidation(False, "ascii", facet_count, "invalid numeric data")
            if not all(math.isfinite(value) for value in values):
                return StlValidation(False, "ascii", facet_count, "non-finite triangle data")
    if expected_triangles is not None and facet_count != expected_triangles:
        return StlValidation(False, "ascii", facet_count, "unexpected triangle count")
    return StlValidation(True, "ascii", facet_count, "valid ASCII STL")
