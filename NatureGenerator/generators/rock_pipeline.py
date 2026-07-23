"""Immutable internal stages for deterministic Rock scalar-field generation."""

from dataclasses import dataclass
import math
from typing import Tuple

from .value_noise import DeterministicValueNoise


Vector3 = Tuple[float, float, float]
Matrix3 = Tuple[Vector3, Vector3, Vector3]


@dataclass(frozen=True)
class MacroShapeParameters:
    """Family-owned coefficients used to construct a macro definition."""

    axis_base: Vector3
    axis_response: Vector3
    axis_seed_amplitude: Vector3
    axis_seed_base: float
    axis_seed_response: float
    broad_coefficients: Tuple[float, float, float, float]
    broad_amplitude_base: float
    broad_amplitude_response: float
    large_noise_frequency: float
    large_noise_offset: Vector3
    large_noise_amplitude_base: float
    large_noise_amplitude_response: float
    ground_offset_base: float
    ground_offset_response: float


@dataclass(frozen=True)
class FacetLayoutParameters:
    """Family-owned coefficients used to construct a facet layout."""

    plane_count: int
    scales: Tuple[str, ...]
    normal_z_base: float
    normal_z_range: float
    offset_base: float
    offset_response_base: float
    offset_response_noise: float
    weight: float


@dataclass(frozen=True)
class SurfaceDetailParameters:
    """Family-owned coefficients used to construct surface detail."""

    fbm_octaves: int
    fbm_frequency: float
    fbm_lacunarity: float
    fbm_gain: float
    fbm_offset: Vector3
    fbm_octave_offset: Vector3
    fbm_amplitude_base: float
    fbm_amplitude_response: float
    ridge_frequency: float
    ridge_offset: Vector3
    ridge_center: float
    ridge_amplitude_response: float
    ridge_response_power: float


DEFAULT_MACRO_PARAMETERS = MacroShapeParameters(
    axis_base=(0.47, 0.42, 0.36),
    axis_response=(0.025, -0.035, -0.040),
    axis_seed_amplitude=(0.025, 0.025, 0.020),
    axis_seed_base=0.35,
    axis_seed_response=0.65,
    broad_coefficients=(0.060, 0.040, -0.045, 0.025),
    broad_amplitude_base=0.35,
    broad_amplitude_response=0.95,
    large_noise_frequency=0.68,
    large_noise_offset=(2.7, -5.4, 8.1),
    large_noise_amplitude_base=0.018,
    large_noise_amplitude_response=0.145,
    ground_offset_base=0.95,
    ground_offset_response=-0.17,
)

DEFAULT_FACET_PARAMETERS = FacetLayoutParameters(
    plane_count=5,
    scales=("large", "medium", "small", "medium", "large"),
    normal_z_base=0.15,
    normal_z_range=0.70,
    offset_base=1.015,
    offset_response_base=0.245,
    offset_response_noise=0.030,
    weight=1.0,
)

DEFAULT_SURFACE_PARAMETERS = SurfaceDetailParameters(
    fbm_octaves=5,
    fbm_frequency=0.78,
    fbm_lacunarity=2.08,
    fbm_gain=0.52,
    fbm_offset=(11.3, -7.9, 5.1),
    fbm_octave_offset=(3.17, 1.91, -2.43),
    fbm_amplitude_base=0.012,
    fbm_amplitude_response=0.105,
    ridge_frequency=3.15,
    ridge_offset=(-4.7, 9.2, -2.6),
    ridge_center=0.38,
    ridge_amplitude_response=0.090,
    ridge_response_power=1.35,
)


@dataclass(frozen=True)
class RockGenerationContext:
    """Normalized inputs shared by all Rock pipeline stages."""

    size: float
    roughness: float
    seed: int
    roughness_response: float

    @classmethod
    def create(
        cls, size: float, roughness: float, seed: int
    ) -> "RockGenerationContext":
        normalized = max(0.0, min(1.0, roughness / 0.70))
        response = normalized * normalized * (3.0 - 2.0 * normalized)
        return cls(size, roughness, seed, response)


@dataclass(frozen=True)
class MacroShapeDefinition:
    """Large-scale proportions, orientation, mass, silhouette, and grounding."""

    radii: Vector3
    orientation: Matrix3
    center_offset: Vector3
    broad_coefficients: Tuple[float, float, float, float]
    broad_amplitude: float
    large_noise_frequency: float
    large_noise_offset: Vector3
    large_noise_amplitude: float
    ground_offset: float

    def normalized_point(self, x: float, y: float, z: float) -> Vector3:
        """Transform a world point into the accepted ellipsoid frame."""

        translated = (
            x - self.center_offset[0],
            y - self.center_offset[1],
            z - self.center_offset[2],
        )
        oriented = tuple(
            sum(axis[index] * translated[index] for index in range(3))
            for axis in self.orientation
        )
        return (
            oriented[0] / self.radii[0],
            oriented[1] / self.radii[1],
            oriented[2] / self.radii[2],
        )

    def deformation(
        self,
        normalized: Vector3,
        direction: Vector3,
        noise: DeterministicValueNoise,
    ) -> float:
        """Evaluate only broad directional and low-frequency deformation."""

        broad, large = self.deformation_terms(normalized, direction, noise)
        return broad + large

    def deformation_terms(
        self,
        normalized: Vector3,
        direction: Vector3,
        noise: DeterministicValueNoise,
    ) -> Tuple[float, float]:
        """Return broad and low-frequency terms without changing sum order."""

        nx, ny, nz = normalized
        dx, dy, dz = direction
        xy, xz, zz, anisotropy = self.broad_coefficients
        broad = (
            xy * dx * dy
            + xz * dx * dz
            + zz * dz * dz
            + anisotropy * (dx * dx - dy * dy)
        )
        large = noise.sample(
            nx * self.large_noise_frequency + self.large_noise_offset[0],
            ny * self.large_noise_frequency + self.large_noise_offset[1],
            nz * self.large_noise_frequency + self.large_noise_offset[2],
        )
        return broad * self.broad_amplitude, large * self.large_noise_amplitude

    def apply_ground(self, field: float, normalized_z: float) -> float:
        """Intersect the composed field with the lower bearing half-space."""

        return max(field, -normalized_z - self.ground_offset)


@dataclass(frozen=True)
class FacetPlane:
    """One deterministic clipping plane and its future family metadata."""

    normal: Vector3
    offset: float
    scale: str
    weight: float


@dataclass(frozen=True)
class FacetLayoutDefinition:
    """Deterministic large/medium/small planar-region layout."""

    planes: Tuple[FacetPlane, ...]

    def apply(self, field: float, normalized: Vector3) -> float:
        """Intersect *field* with all configured facet half-spaces."""

        nx, ny, nz = normalized
        for facet in self.planes:
            plane = (
                nx * facet.normal[0]
                + ny * facet.normal[1]
                + nz * facet.normal[2]
                - facet.offset
            )
            field = max(field, plane * facet.weight)
        return field


@dataclass(frozen=True)
class SurfaceDetailDefinition:
    """Medium/fine FBM, ridges, and local weathering configuration."""

    fbm_octaves: int
    fbm_frequency: float
    fbm_lacunarity: float
    fbm_gain: float
    fbm_offset: Vector3
    fbm_octave_offset: Vector3
    fbm_amplitude: float
    ridge_frequency: float
    ridge_offset: Vector3
    ridge_center: float
    ridge_amplitude: float

    def fbm(
        self, normalized: Vector3, noise: DeterministicValueNoise
    ) -> float:
        """Evaluate normalized deterministic multi-octave value-noise FBM."""

        x, y, z = normalized
        amplitude = 1.0
        frequency = self.fbm_frequency
        total = 0.0
        weight = 0.0
        for octave in range(self.fbm_octaves):
            total += amplitude * noise.sample(
                x * frequency + self.fbm_offset[0]
                + octave * self.fbm_octave_offset[0],
                y * frequency + self.fbm_offset[1]
                + octave * self.fbm_octave_offset[1],
                z * frequency + self.fbm_offset[2]
                + octave * self.fbm_octave_offset[2],
            )
            weight += amplitude
            frequency *= self.fbm_lacunarity
            amplitude *= self.fbm_gain
        return total / weight

    def ridged(
        self, normalized: Vector3, noise: DeterministicValueNoise
    ) -> float:
        """Evaluate centered ridge noise for local creases and shoulders."""

        x, y, z = normalized
        ridge = 1.0 - abs(noise.sample(
            x * self.ridge_frequency + self.ridge_offset[0],
            y * self.ridge_frequency + self.ridge_offset[1],
            z * self.ridge_frequency + self.ridge_offset[2],
        ))
        return ridge * ridge - self.ridge_center

    def deformation(
        self, normalized: Vector3, noise: DeterministicValueNoise
    ) -> float:
        """Evaluate only medium- and fine-scale surface deformation."""

        fbm, ridge = self.deformation_terms(normalized, noise)
        return fbm + ridge

    def deformation_terms(
        self, normalized: Vector3, noise: DeterministicValueNoise
    ) -> Tuple[float, float]:
        """Return FBM and ridge terms for explicit pipeline composition."""

        return (
            self.fbm_amplitude * self.fbm(normalized, noise),
            self.ridge_amplitude * self.ridged(normalized, noise),
        )


def build_macro_shape(
    context: RockGenerationContext,
    noise: DeterministicValueNoise,
    parameters: MacroShapeParameters = DEFAULT_MACRO_PARAMETERS,
) -> MacroShapeDefinition:
    """Build a deterministic family-configured large-scale definition."""

    response = context.roughness_response
    axis_variation = (
        parameters.axis_seed_base + parameters.axis_seed_response * response
    )
    lattice = (
        noise._lattice(1, 0, 0),
        noise._lattice(0, 1, 0),
        noise._lattice(0, 0, 1),
    )
    radii = (
        context.size * (
            parameters.axis_base[index]
            + parameters.axis_response[index] * response
            + parameters.axis_seed_amplitude[index] * axis_variation
            * lattice[index]
        )
        for index in range(3)
    )
    return MacroShapeDefinition(
        radii=tuple(radii),
        orientation=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        center_offset=(0.0, 0.0, 0.0),
        broad_coefficients=parameters.broad_coefficients,
        broad_amplitude=(
            parameters.broad_amplitude_base
            + parameters.broad_amplitude_response * response
        ),
        large_noise_frequency=parameters.large_noise_frequency,
        large_noise_offset=parameters.large_noise_offset,
        large_noise_amplitude=(
            parameters.large_noise_amplitude_base
            + parameters.large_noise_amplitude_response * response
        ),
        ground_offset=(
            parameters.ground_offset_base
            + parameters.ground_offset_response * response
        ),
    )


def build_facet_layout(
    context: RockGenerationContext,
    noise: DeterministicValueNoise,
    parameters: FacetLayoutParameters = DEFAULT_FACET_PARAMETERS,
) -> FacetLayoutDefinition:
    """Build a deterministic family-configured clipping-plane layout."""

    planes = []
    for index in range(parameters.plane_count):
        x = noise._lattice(17 + index * 5, 3, -7)
        y = noise._lattice(-11, 23 + index * 7, 5)
        z = parameters.normal_z_base + parameters.normal_z_range * abs(
            noise._lattice(7, -13, 31 + index * 3)
        )
        length = math.sqrt(x * x + y * y + z * z)
        normal = (x / length, y / length, z / length)
        offset = parameters.offset_base - context.roughness_response * (
            parameters.offset_response_base
            + parameters.offset_response_noise * noise._lattice(index, 41, -19)
        )
        planes.append(FacetPlane(
            normal,
            offset,
            parameters.scales[index],
            parameters.weight,
        ))
    return FacetLayoutDefinition(tuple(planes))


def build_surface_detail(
    context: RockGenerationContext,
    parameters: SurfaceDetailParameters = DEFAULT_SURFACE_PARAMETERS,
) -> SurfaceDetailDefinition:
    """Build family-configured detail settings from normalized Roughness."""

    response = context.roughness_response
    return SurfaceDetailDefinition(
        fbm_octaves=parameters.fbm_octaves,
        fbm_frequency=parameters.fbm_frequency,
        fbm_lacunarity=parameters.fbm_lacunarity,
        fbm_gain=parameters.fbm_gain,
        fbm_offset=parameters.fbm_offset,
        fbm_octave_offset=parameters.fbm_octave_offset,
        fbm_amplitude=(
            parameters.fbm_amplitude_base
            + parameters.fbm_amplitude_response * response
        ),
        ridge_frequency=parameters.ridge_frequency,
        ridge_offset=parameters.ridge_offset,
        ridge_center=parameters.ridge_center,
        ridge_amplitude=parameters.ridge_amplitude_response * math.pow(
            response, parameters.ridge_response_power
        ),
    )
