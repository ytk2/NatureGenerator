"""Renderer-neutral generated asset definitions."""

from dataclasses import dataclass, field
from enum import Enum
import math
import re
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, Tuple

from core.mesh import Point3, TriangleMesh


Color = Tuple[float, float, float, float]
_EMPTY_MAPPING = MappingProxyType({})


def _stable_id(value: str, name: str) -> str:
    if not isinstance(value, str) or re.fullmatch(
        r"[a-z][a-z0-9_]*", value
    ) is None:
        raise ValueError("{} must be a lowercase stable identifier".format(name))
    return value


def _finite(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("{} must be numeric".format(name))
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("{} must be finite".format(name))
    return result


def _unit_interval(value: float, name: str) -> float:
    result = _finite(value, name)
    if result < 0.0 or result > 1.0:
        raise ValueError("{} must be between 0 and 1".format(name))
    return result


def _vector(values: Sequence[float], name: str) -> Point3:
    if isinstance(values, (str, bytes)) or len(values) != 3:
        raise ValueError("{} must contain exactly three values".format(name))
    return tuple(
        _finite(value, "{} component".format(name)) for value in values
    )  # type: ignore[return-value]


def _immutable_metadata(
    values: Optional[Mapping[str, Any]], name: str
) -> Mapping[str, Any]:
    if values is None:
        return _EMPTY_MAPPING
    if not isinstance(values, Mapping):
        raise TypeError("{} must be a mapping".format(name))
    copied = {}
    for key, value in values.items():
        if not isinstance(key, str) or not key:
            raise ValueError("{} keys must be non-empty strings".format(name))
        if not isinstance(value, (bool, int, float, str)):
            raise TypeError(
                "{} values must be bool, int, float, or string".format(name)
            )
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("{} float values must be finite".format(name))
        copied[key] = value
    return MappingProxyType(copied)


class MappingMode(Enum):
    """Coordinate derivation strategy for a material."""

    OBJECT_SPACE = "object_space"


class TextureSemantic(Enum):
    """Renderer-neutral role of one baked texture resource."""

    BASE_COLOR = "base_color"
    METALLIC = "metallic"
    ROUGHNESS = "roughness"
    NORMAL = "normal"
    AMBIENT_OCCLUSION = "ambient_occlusion"


@dataclass(frozen=True)
class MaterialDefinition:
    """Procedural PBR-like material intent, independent of a renderer."""

    material_id: str
    display_name: str
    base_color: Color
    metallic: float = 0.0
    roughness: float = 0.5
    normal_strength: float = 1.0
    ambient_occlusion_strength: float = 1.0
    procedural_parameters: Mapping[str, Any] = field(
        default_factory=lambda: _EMPTY_MAPPING
    )

    def __post_init__(self) -> None:
        _stable_id(self.material_id, "material_id")
        if not isinstance(self.display_name, str) or not self.display_name.strip():
            raise ValueError("display_name must be a non-empty string")
        if isinstance(self.base_color, (str, bytes)) or len(self.base_color) not in (3, 4):
            raise ValueError("base_color must contain three or four values")
        color = tuple(
            _unit_interval(value, "base_color component") for value in self.base_color
        )
        if len(color) == 3:
            color = color + (1.0,)
        object.__setattr__(self, "base_color", color)
        object.__setattr__(self, "metallic", _unit_interval(self.metallic, "metallic"))
        object.__setattr__(self, "roughness", _unit_interval(self.roughness, "roughness"))
        object.__setattr__(
            self, "normal_strength", _finite(self.normal_strength, "normal_strength")
        )
        if self.normal_strength < 0.0:
            raise ValueError("normal_strength must be non-negative")
        object.__setattr__(
            self,
            "ambient_occlusion_strength",
            _unit_interval(
                self.ambient_occlusion_strength, "ambient_occlusion_strength"
            ),
        )
        object.__setattr__(
            self,
            "procedural_parameters",
            _immutable_metadata(
                self.procedural_parameters, "procedural_parameters"
            ),
        )


@dataclass(frozen=True)
class MappingDefinition:
    """Material-coordinate intent without UV generation or renderer state."""

    mode: MappingMode = MappingMode.OBJECT_SPACE
    scale: Point3 = (1.0, 1.0, 1.0)
    rotation: Point3 = (0.0, 0.0, 0.0)
    offset: Point3 = (0.0, 0.0, 0.0)
    projection_metadata: Mapping[str, Any] = field(
        default_factory=lambda: _EMPTY_MAPPING
    )

    def __post_init__(self) -> None:
        if not isinstance(self.mode, MappingMode):
            raise TypeError("mode must be a MappingMode")
        scale = _vector(self.scale, "scale")
        if any(value <= 0.0 for value in scale):
            raise ValueError("scale components must be positive")
        object.__setattr__(self, "scale", scale)
        object.__setattr__(self, "rotation", _vector(self.rotation, "rotation"))
        object.__setattr__(self, "offset", _vector(self.offset, "offset"))
        object.__setattr__(
            self,
            "projection_metadata",
            _immutable_metadata(
                self.projection_metadata, "projection_metadata"
            ),
        )


@dataclass(frozen=True)
class TextureResource:
    """One optional baked image payload and its renderer-neutral role."""

    resource_id: str
    semantic: TextureSemantic
    media_type: str
    data: bytes
    width: int
    height: int
    metadata: Mapping[str, Any] = field(default_factory=lambda: _EMPTY_MAPPING)

    def __post_init__(self) -> None:
        _stable_id(self.resource_id, "resource_id")
        if not isinstance(self.semantic, TextureSemantic):
            raise TypeError("semantic must be a TextureSemantic")
        if not isinstance(self.media_type, str) or not self.media_type.startswith("image/"):
            raise ValueError("media_type must be an image media type")
        if not isinstance(self.data, bytes):
            raise TypeError("data must be bytes")
        for value, name in ((self.width, "width"), (self.height, "height")):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError("{} must be a positive integer".format(name))
        object.__setattr__(
            self, "metadata", _immutable_metadata(self.metadata, "metadata")
        )


@dataclass(frozen=True)
class TextureSet:
    """Immutable collection of baked resources; empty until baking exists."""

    resources: Tuple[TextureResource, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.resources, Sequence) or isinstance(
            self.resources, (str, bytes)
        ):
            raise TypeError("resources must be a sequence")
        resources = tuple(self.resources)
        if any(not isinstance(item, TextureResource) for item in resources):
            raise TypeError("resources must contain TextureResource values")
        resource_ids = [item.resource_id for item in resources]
        semantics = [item.semantic for item in resources]
        if len(resource_ids) != len(set(resource_ids)):
            raise ValueError("texture resource IDs must be unique")
        if len(semantics) != len(set(semantics)):
            raise ValueError("texture semantics must be unique")
        object.__setattr__(self, "resources", resources)

    def get(self, semantic: TextureSemantic) -> Optional[TextureResource]:
        """Return the resource for *semantic*, if one is present."""

        if not isinstance(semantic, TextureSemantic):
            raise TypeError("semantic must be a TextureSemantic")
        return next(
            (resource for resource in self.resources if resource.semantic is semantic),
            None,
        )


@dataclass(frozen=True)
class AssetMetadata:
    """Stable generation provenance carried with a generated asset."""

    asset_id: str
    display_name: str
    preset_id: str
    generator_id: str
    family_id: str = ""
    parameters: Mapping[str, Any] = field(default_factory=lambda: _EMPTY_MAPPING)
    coordinate_unit: str = "mm"
    schema_version: int = 1

    def __post_init__(self) -> None:
        _stable_id(self.asset_id, "asset_id")
        _stable_id(self.preset_id, "preset_id")
        _stable_id(self.generator_id, "generator_id")
        if self.family_id:
            _stable_id(self.family_id, "family_id")
        if not isinstance(self.display_name, str) or not self.display_name.strip():
            raise ValueError("display_name must be a non-empty string")
        if not isinstance(self.coordinate_unit, str) or not self.coordinate_unit:
            raise ValueError("coordinate_unit must be a non-empty string")
        if (
            isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version < 1
        ):
            raise ValueError("schema_version must be a positive integer")
        object.__setattr__(
            self, "parameters", _immutable_metadata(self.parameters, "parameters")
        )


@dataclass(frozen=True)
class GeneratedAsset:
    """Complete renderer-neutral output of one natural asset generation."""

    mesh: TriangleMesh
    material: MaterialDefinition
    mapping: MappingDefinition
    textures: TextureSet
    metadata: AssetMetadata

    def __post_init__(self) -> None:
        for value, expected, name in (
            (self.mesh, TriangleMesh, "mesh"),
            (self.material, MaterialDefinition, "material"),
            (self.mapping, MappingDefinition, "mapping"),
            (self.textures, TextureSet, "textures"),
            (self.metadata, AssetMetadata, "metadata"),
        ):
            if not isinstance(value, expected):
                raise TypeError("{} must be a {}".format(name, expected.__name__))
