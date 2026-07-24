"""Format-neutral export contracts.

Sprint 22 intentionally provides no production exporter implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Tuple

from .definition import GeneratedAsset


class ExportFormat(Enum):
    """Planned generated-asset destinations."""

    OBJ = "obj"
    GLTF = "gltf"
    GLB = "glb"
    USD = "usd"
    USDZ = "usdz"
    STL = "stl"


@dataclass(frozen=True)
class ExportRequest:
    """One explicit request to serialize a generated asset."""

    asset: GeneratedAsset
    destination: Path
    format: ExportFormat

    def __post_init__(self) -> None:
        if not isinstance(self.asset, GeneratedAsset):
            raise TypeError("asset must be a GeneratedAsset")
        object.__setattr__(self, "destination", Path(self.destination))
        if not isinstance(self.format, ExportFormat):
            raise TypeError("format must be an ExportFormat")


@dataclass(frozen=True)
class ExportResult:
    """Files and non-fatal diagnostics produced by an exporter."""

    files: Tuple[Path, ...]
    warnings: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "files", tuple(Path(path) for path in self.files))
        object.__setattr__(self, "warnings", tuple(self.warnings))


class AssetExporter(ABC):
    """Adapter contract implemented by future file-format exporters."""

    @property
    @abstractmethod
    def format(self) -> ExportFormat:
        """Return the single format handled by this exporter."""

    @abstractmethod
    def export(self, request: ExportRequest) -> ExportResult:
        """Serialize *request* or raise a format-specific export error."""


class ExporterRegistry:
    """Explicit exporter registration without format-selection branching."""

    def __init__(self) -> None:
        self._exporters: Dict[ExportFormat, AssetExporter] = {}

    def register(self, exporter: AssetExporter) -> None:
        if not isinstance(exporter, AssetExporter):
            raise TypeError("exporter must be an AssetExporter")
        if exporter.format in self._exporters:
            raise ValueError(
                "duplicate exporter format: {}".format(exporter.format.value)
            )
        self._exporters[exporter.format] = exporter

    def get(self, format: ExportFormat) -> AssetExporter:
        if not isinstance(format, ExportFormat):
            raise TypeError("format must be an ExportFormat")
        try:
            return self._exporters[format]
        except KeyError as error:
            raise LookupError(
                "no exporter registered for format: {}".format(format.value)
            ) from error

    def export(self, request: ExportRequest) -> ExportResult:
        if not isinstance(request, ExportRequest):
            raise TypeError("request must be an ExportRequest")
        return self.get(request.format).export(request)
