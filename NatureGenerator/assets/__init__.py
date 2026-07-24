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

__all__ = [
    "AssetExporter",
    "AssetMetadata",
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
    "TextureResource",
    "TextureSemantic",
    "TextureSet",
]
