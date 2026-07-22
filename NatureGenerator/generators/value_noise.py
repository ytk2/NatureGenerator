"""Small deterministic value-noise primitive shared by procedural generators."""

import math


class DeterministicValueNoise:
    """Seeded lattice values with smoothstep trilinear interpolation.

    This is dependency-free value noise. It is intentionally narrow and does
    not implement Perlin, Simplex, or a general procedural-noise framework.
    """

    def __init__(self, seed: int) -> None:
        self.seed = seed

    def _lattice(self, x: int, y: int, z: int) -> float:
        """Return a stable value in [-1, 1] for one integer lattice point."""

        value = (self.seed ^ (x * 0x8DA6B343) ^ (y * 0xD8163841) ^
                 (z * 0xCB1AB31F)) & 0xFFFFFFFF
        value ^= value >> 16
        value = (value * 0x7FEB352D) & 0xFFFFFFFF
        value ^= value >> 15
        value = (value * 0x846CA68B) & 0xFFFFFFFF
        value ^= value >> 16
        return (value / 2147483647.5) - 1.0

    def sample(self, x: float, y: float, z: float) -> float:
        """Return smoothstep-interpolated trilinear lattice value noise."""

        ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
        fx, fy, fz = x - ix, y - iy, z - iz

        def fade(value: float) -> float:
            return value * value * (3.0 - 2.0 * value)

        def blend(a: float, b: float, amount: float) -> float:
            return a + (b - a) * amount

        ux, uy, uz = fade(fx), fade(fy), fade(fz)
        planes = []
        for dz in (0, 1):
            rows = []
            for dy in (0, 1):
                rows.append(blend(
                    self._lattice(ix, iy + dy, iz + dz),
                    self._lattice(ix + 1, iy + dy, iz + dz), ux,
                ))
            planes.append(blend(rows[0], rows[1], uy))
        return blend(planes[0], planes[1], uz)
