"""Immutable, Fusion-independent rectangular TPMS domain sizing."""

from dataclasses import dataclass
from enum import Enum
import math
from typing import Optional, Tuple


DOMAIN_DIMENSION_MIN_MM = 1.0
DOMAIN_DIMENSION_MAX_MM = 500.0
DOMAIN_CELL_COUNT_MIN = 1
DOMAIN_CELL_COUNT_MAX = 50

Dimensions3 = Tuple[float, float, float]
CellCounts3 = Tuple[int, int, int]


class DomainMode(Enum):
    DIMENSIONS = "dimensions"
    CELL_COUNT = "cell_count"


@dataclass(frozen=True)
class DomainDefinition:
    """Requested domain provenance and authoritative physical dimensions."""

    mode: DomainMode
    period: float
    resolved_dimensions: Dimensions3
    effective_cell_counts: Dimensions3
    requested_dimensions: Optional[Dimensions3] = None
    requested_cell_counts: Optional[CellCounts3] = None

    def __post_init__(self) -> None:
        if not isinstance(self.mode, DomainMode):
            raise TypeError("mode must be a DomainMode")
        if (
            len(self.resolved_dimensions) != 3
            or len(self.effective_cell_counts) != 3
        ):
            raise ValueError("domain dimensions and cell counts need three axes")
        if not math.isfinite(self.period) or self.period <= 0.0:
            raise ValueError("period must be finite and positive")
        if any(
            not math.isfinite(value) or value <= 0.0
            for value in self.resolved_dimensions
        ):
            raise ValueError("resolved dimensions must be finite and positive")
        if any(
            not math.isfinite(value) or value <= 0.0
            for value in self.effective_cell_counts
        ):
            raise ValueError(
                "effective cell counts must be finite and positive"
            )
        if self.mode is DomainMode.DIMENSIONS:
            if (
                self.requested_dimensions is None
                or len(self.requested_dimensions) != 3
                or self.requested_cell_counts is not None
            ):
                raise ValueError(
                    "Dimensions mode requires requested dimensions only"
                )
        elif (
            self.requested_cell_counts is None
            or len(self.requested_cell_counts) != 3
            or self.requested_dimensions is not None
        ):
            raise ValueError(
                "Cell Count mode requires requested cell counts only"
            )

    @property
    def width(self) -> float:
        return self.resolved_dimensions[0]

    @property
    def depth(self) -> float:
        return self.resolved_dimensions[1]

    @property
    def height(self) -> float:
        return self.resolved_dimensions[2]

    @property
    def minimum(self) -> Dimensions3:
        return tuple(-value * 0.5 for value in self.resolved_dimensions)

    @property
    def maximum(self) -> Dimensions3:
        return tuple(value * 0.5 for value in self.resolved_dimensions)

    def sample_spacing(self, resolution: CellCounts3) -> Dimensions3:
        _validate_resolution(resolution)
        return tuple(
            dimension / (samples - 1)
            for dimension, samples in zip(
                self.resolved_dimensions, resolution
            )
        )

    def intervals_per_cell(self, resolution: CellCounts3) -> Dimensions3:
        _validate_resolution(resolution)
        return tuple(
            (samples - 1) / cells
            for samples, cells in zip(
                resolution, self.effective_cell_counts
            )
        )


class DomainSizingError(ValueError):
    pass


def _validate_resolution(resolution: CellCounts3) -> None:
    if len(resolution) != 3 or any(
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 2
        for value in resolution
    ):
        raise ValueError(
            "resolution must contain three integers of at least two"
        )


def _validate_period(period: float) -> float:
    if isinstance(period, bool) or not isinstance(period, (int, float)):
        raise TypeError("Period must be numeric")
    value = float(period)
    if not math.isfinite(value):
        raise DomainSizingError("Period must be finite")
    if value < DOMAIN_DIMENSION_MIN_MM or value > DOMAIN_DIMENSION_MAX_MM:
        raise DomainSizingError(
            "Period must be between {} and {} mm".format(
                DOMAIN_DIMENSION_MIN_MM, DOMAIN_DIMENSION_MAX_MM
            )
        )
    return value


def _validate_dimension(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("{} must be numeric".format(name))
    normalized = float(value)
    if not math.isfinite(normalized):
        raise DomainSizingError("{} must be finite".format(name))
    if (
        normalized < DOMAIN_DIMENSION_MIN_MM
        or normalized > DOMAIN_DIMENSION_MAX_MM
    ):
        raise DomainSizingError(
            "{} must be between {} and {} mm".format(
                name, DOMAIN_DIMENSION_MIN_MM, DOMAIN_DIMENSION_MAX_MM
            )
        )
    return normalized


def _validate_cell_count(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("{} must be an integer".format(name))
    if value < DOMAIN_CELL_COUNT_MIN or value > DOMAIN_CELL_COUNT_MAX:
        raise DomainSizingError(
            "{} must be between {} and {}".format(
                name, DOMAIN_CELL_COUNT_MIN, DOMAIN_CELL_COUNT_MAX
            )
        )
    return value


def resolve_domain(
    mode: DomainMode,
    width: float,
    depth: float,
    height: float,
    cells_x: int,
    cells_y: int,
    cells_z: int,
    period: float,
) -> DomainDefinition:
    """Resolve requested sizing inputs before sampling or allocation."""

    if not isinstance(mode, DomainMode):
        raise TypeError("mode must be a DomainMode")
    period_value = _validate_period(period)
    if mode is DomainMode.DIMENSIONS:
        requested = (
            _validate_dimension("Width", width),
            _validate_dimension("Depth", depth),
            _validate_dimension("Height", height),
        )
        return DomainDefinition(
            mode=mode,
            period=period_value,
            requested_dimensions=requested,
            requested_cell_counts=None,
            resolved_dimensions=requested,
            effective_cell_counts=tuple(
                dimension / period_value for dimension in requested
            ),
        )

    counts = (
        _validate_cell_count("Cells X", cells_x),
        _validate_cell_count("Cells Y", cells_y),
        _validate_cell_count("Cells Z", cells_z),
    )
    labels = ("Width", "Depth", "Height")
    cell_labels = ("Cells X", "Cells Y", "Cells Z")
    resolved = []
    for label, cell_label, count in zip(labels, cell_labels, counts):
        dimension = count * period_value
        if not math.isfinite(dimension):
            raise DomainSizingError(
                "{} multiplication produced a non-finite dimension".format(
                    cell_label
                )
            )
        if dimension > DOMAIN_DIMENSION_MAX_MM:
            raise DomainSizingError(
                "Domain Mode Cell Count: {} = {} with Period = {:.6g} mm "
                "produces {} = {:.6g} mm, "
                "exceeding the {:.6g} mm domain limit. Reduce {} or Period."
                .format(
                    cell_label,
                    count,
                    period_value,
                    label,
                    dimension,
                    DOMAIN_DIMENSION_MAX_MM,
                    cell_label,
                )
            )
        if dimension < DOMAIN_DIMENSION_MIN_MM:
            raise DomainSizingError(
                "Domain Mode Cell Count: {} = {} with Period = {:.6g} mm "
                "produces {} = {:.6g} mm, "
                "below the {:.6g} mm domain limit. Increase {} or Period."
                .format(
                    cell_label,
                    count,
                    period_value,
                    label,
                    dimension,
                    DOMAIN_DIMENSION_MIN_MM,
                    cell_label,
                )
            )
        resolved.append(dimension)
    return DomainDefinition(
        mode=mode,
        period=period_value,
        requested_dimensions=None,
        requested_cell_counts=counts,
        resolved_dimensions=tuple(resolved),
        effective_cell_counts=tuple(float(value) for value in counts),
    )
