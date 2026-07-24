"""Renderer-neutral natural asset and export architecture."""

from .definition import (
    AssetMetadata,
    Color,
    GeneratedAsset,
    MappingDefinition,
    MappingMode,
    MaterialDefinition,
    TextureResource,
    TextureSemantic,
    TextureSet,
)
from .export import (
    AssetExporter,
    ExportFormat,
    ExportRequest,
    ExportResult,
    ExporterRegistry,
)
from .factory import GeneratedAssetFactory
from .natural_material import (
    AssetBrowserMetadata,
    NATURAL_MATERIALS,
    NaturalMaterial,
    NaturalMaterialRegistry,
    ThumbnailReference,
)

__all__ = [
    "AssetExporter",
    "AssetMetadata",
    "AssetBrowserMetadata",
    "Color",
    "ExportFormat",
    "ExportRequest",
    "ExportResult",
    "ExporterRegistry",
    "GeneratedAsset",
    "GeneratedAssetFactory",
    "MappingDefinition",
    "MappingMode",
    "MaterialDefinition",
    "NATURAL_MATERIALS",
    "NaturalMaterial",
    "NaturalMaterialRegistry",
    "ThumbnailReference",
    "TextureResource",
    "TextureSemantic",
    "TextureSet",
]
