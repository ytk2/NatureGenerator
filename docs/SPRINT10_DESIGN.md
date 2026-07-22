# Sprint 10 Design: Bark Generator

## Goal and scope

Sprint 10 adds an executable, deterministic Bark preset that produces one
closed trunk segment. It is a bark-covered finite cylinder intended for Fusion
MeshBody creation and additive manufacturing, not a biological growth model.
Species simulation, branches, knots, roots, hollow shells, flat panels, UV
unwrapping, arbitrary-body application, preview, progress, asynchronous work,
smoothing, materials, and GPU processing remain out of scope.

## Implementation plan

1. Replace the reserved Bark metadata with ordered `diameter`, `height`,
   `bark_depth`, `groove_scale`, `twist`, `seed`, and `resolution` inputs.
2. Extract Rock's exact deterministic lattice value-noise primitive into one
   small Fusion-independent generator utility and prove that Rock meshes do not
   change.
3. Implement `BarkGenerator` as a bounded capped-cylinder scalar field sampled
   by `VoxelGrid` and extracted by the shared Marching Tetrahedra pipeline.
4. Register `bark -> BarkGenerator`; the existing metadata-driven Fusion UI
   will expose it without preset-specific or concrete-generator branches.
5. Add preset, geometry, topology, determinism, regression, UI, boundary, and
   failure tests. Benchmark default and maximum resolution locally.

## Parameters

| Parameter | Default | Bounds | Meaning |
| --- | ---: | ---: | --- |
| Diameter | 80 mm | 30–160 mm | Nominal trunk diameter |
| Height | 120 mm | 40–240 mm | Closed segment height |
| Bark Depth | 4 mm | 0.5–15 mm | Maximum nominal radial variation |
| Groove Scale | 18 mm | 6–40 mm | Approximate circumferential ridge spacing |
| Twist | 0 turns | -1–1 turns | Ridge rotation over the full height |
| Seed | 10 | 0–2,147,483,647 | Deterministic variation key |
| Resolution | 33 | 29–41 | Samples per axis |

Metadata bounds are supplemented by a cross-parameter rule:
`bark_depth <= 0.25 * diameter`. This leaves a large positive core radius even
at maximum inward displacement. Values are finite and positive where their
physical meaning requires it.

## Exact scalar-field construction

Let `r = sqrt(x²+y²)`, `theta = atan2(y,x)`, `q = z/height`, and
`R = diameter/2`. The closed field is:

```text
side = r - surface_radius(theta, q)
cap  = abs(z) - height/2
field = max(side, cap)
```

Negative values are inside. The surface radius combines four bounded terms:

```text
surface_radius = R
    + 0.04 R * broad(theta, q, seed)
    + bark_depth * (
          0.52 * grooves(theta - 2 pi twist (q + 1/2))
        + 0.25 * anisotropic_value_noise(theta, q, seed)
        + 0.12 * secondary_breakup(theta, q, seed)
      )
```

`broad` is a small combination of two- and three-lobed angular waves whose
phase and slow height modulation come from the seed. `grooves` combines a main
angular cosine and a smaller harmonic. The integer ridge count is the nearest
practical broad count to `diameter / groove_scale`, clamped to 3–6; using an
integer keeps the seam periodic and the upper cap prevents unsupported angular
aliasing. `twist` rotates this phase by the documented number of turns between
caps.

The anisotropic term uses deterministic lattice value noise. Its coordinates
are `(f cos(theta), f sin(theta), low_frequency * q)`: wrapping theta onto a
circle makes it seamless, while the much lower height frequency stretches
features vertically. Secondary breakup uses smaller periodic angular waves
with slowly varying height phase. This is smoothstep-interpolated trilinear
value noise, not Perlin, Simplex, Voronoi, or biological simulation.

## Shared deterministic noise

Rock's existing 32-bit integer lattice mixer and smoothstep trilinear
interpolation are moved unchanged to `generators/value_noise.py`. Rock retains
the same seed, coordinates, octave frequencies, amplitudes, and floating-point
operation order. An exact vertex-and-face regression test compares the shared
implementation with a frozen legacy copy, so the refactor cannot silently
alter Rock output.

## Topology and sampling bounds

The `max(side, cap)` construction closes both ends and describes one star-shaped
solid around the Z axis. The displacement coefficients sum to less than one
`bark_depth`, and the cross-parameter rule preserves a substantial minimum
radius. No separate field islands are introduced.

XY sampling extent includes the analytically bounded maximum of base radius,
broad deformation, and bark displacement plus additional grid margin. Z bounds
extend beyond both caps. Consequently every outer grid face is outside the
solid at supported limits. Runtime validation requires a non-empty, manifold,
watertight mesh; tests additionally require finite vertices, no degenerates,
one connected component, closed caps, and no contact with sampling bounds.

## API and compatibility

No new request or Fusion API is required. Bark uses existing `length`, `float`,
and `integer` metadata. Resolution remains metadata-visible but is transported
by `GenerationRequest.resolution`. `GeneratorFactory` gains one explicit preset
registration. Commands and Fusion modules continue to depend only on metadata,
stable keys, and factory contracts and do not import `BarkGenerator`.

Sponge and Coral code is unchanged. Rock's only source change is the narrow
noise import, guarded by exact deterministic regression. The UI already creates
available preset inputs once per dialog and toggles visibility, so Bark values
are preserved without duplicate fields or event handlers.

## Limitations and acceptance

Samples-per-axis is intentionally retained as one scalar for compatibility.
Tall Bark forms therefore have coarser physical Z spacing than XY spacing.
Default 33 and maximum 41 are benchmarked. Bark narrows the shared resolution
range to 29–41 because lower grids can alias the supported directional grooves
into disconnected extracted components; higher values are not exposed because
the pure-Python voxel and extraction cost grows cubically. Real Fusion must
still confirm input presentation, parameter effects, MeshBody insertion, and
Sponge/Coral/Rock regressions after the automated suite passes.

## Real Fusion acceptance

Tested successfully on macOS Autodesk Fusion:

- NatureGenerator loaded and **Generate Nature** appeared once.
- Bark was executable without a Coming Soon label.
- Diameter, Height, Bark Depth, Groove Scale, Twist, Seed, and Resolution were
  displayed correctly from preset metadata.
- Bark MeshBody creation succeeded with the body name `NatureGenerator Bark`.
- Diameter and Height changed overall dimensions; Twist and other parameter
  changes produced different geometry.
- Bark Depth validation rejected an invalid combination with
  `bark_depth must not exceed 25% of diameter`.
- Sponge, Coral, and Rock remained available and no startup failure or duplicate
  command control was observed.

Observed Bark runs included:

| Vertices | Faces | Time |
| ---: | ---: | ---: |
| 14,422 | 28,840 | approximately 0.914 seconds |
| 17,018 | 34,032 | approximately 1.454 seconds |

These are observed real-Fusion configurations, not exhaustive benchmarks of
every supported parameter combination.

## Known visual limitation

Bark v1 produces a closed procedural trunk segment with directional grooves.
The present visual result is closer to an irregular or twisted trunk than to
realistic deeply fractured tree bark. Parameter adjustment changes depth,
spacing, twist, and deterministic variation, but cannot fully overcome this
algorithmic limitation. Realistic longitudinal cracks, peeling plates, knots,
and species-specific bark remain future work. Bark v1 does not claim biological
realism or species reproduction.
