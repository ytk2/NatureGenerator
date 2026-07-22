# Sprint 14 Design: Rock Generator v2

## Scope

Sprint 14 changes the internal procedural field in `RockGenerator`, dedicated
tests, and Rock's metadata-driven Preview density hint. It adds no UI controls
or parameters and does not change Variants, commands, `GeneratorFactory`, the
Preview lifecycle, Fusion insertion, or another generator. Existing Smooth,
Weathered, and Rugged Variant definitions continue to supply the same Size,
Roughness, Seed, and Final Resolution values.

Geometry is still determined by the normalized request values. There is no
hidden Variant identity or style-specific branch in the generator.

## Problem with Rock v1

Rock v1 displaced an ellipsoid radius with three octaves of value noise sampled
mostly on the unit direction vector. It was deterministic and watertight, but
the uniform radial treatment often read as a noisy sphere. It lacked a bearing
surface, coherent ridge structures, and genuinely planar fracture regions.

## Rock v2 field

Rock v2 remains one continuous dependency-free implicit solid:

```text
seeded asymmetric ellipsoid
    + low-order broad silhouette terms
    + five-octave positional FBM
    + centered ridged noise
    intersect deterministic facet half-spaces
    intersect subtle lower support plane
    -> existing VoxelGrid
    -> existing Marching Tetrahedra
    -> existing mesh validation
```

### Multi-scale FBM

Five deterministic value-noise octaves use lacunarity 2.08 and gain 0.52. The
first octaves move the boulder silhouette, middle octaves create weathered
undulation, and later octaves add fine relief. Sampling normalized position
rather than only direction makes features spatially coherent across the form.

### Ridged detail

The ridge term squares `1 - abs(noise)` and recenters it before applying the
existing Roughness value. This produces sharper shoulders and creases without
introducing a discontinuous random surface. Smooth receives a small amount;
Weathered receives moderate detail; Rugged receives the strongest ridges.

### Roughness response refinement

The first Rock v2 pass left the seeded axis ratios and broad silhouette term
nearly independent of Roughness. Facet offsets changed only over a narrow
linear range. Consequently, real Fusion testing showed mostly local surface
changes between Roughness 0.1 and 0.7 while the silhouette and facet layout
remained too similar.

The refined mapping normalizes the unchanged public 0.0–0.7 range and applies a
smoothstep response. That response now controls all of the following:

- seeded axis proportions and large-scale asymmetry;
- low-order directional silhouette deformation;
- a dedicated low-frequency positional noise term;
- the complete five-octave FBM amplitude;
- ridged-noise strength;
- facet-plane offsets and exposed planar area;
- lower support-plane width.

At Roughness 0.1, the response is deliberately small and the clipping planes
barely intersect the rounded form. At 0.35, medium-scale deformation and
facets become clear. At 0.7, axis proportions, low-frequency displacement,
ridges, facets, and grounding all approach their full strength. Roughness is
therefore not a multiplier on high-frequency noise alone.

### Facets and grounding

Five seed-derived upper/side half-spaces clip small regions of the implicit
ellipsoid. Their offsets depend continuously on Roughness, so Smooth retains
small softened caps while Rugged exposes broader planar regions. A lower
half-space adds a subtle bearing face, widened for rougher rocks. Intersections
use the maximum of continuous field functions; the zero set remains the
boundary of one implicit solid before extraction.

The sampling cube remains `size * 0.72`. The enlarged base radii and maximum
displacement remain inside this conservative domain, and clipping planes only
remove material. The outer grid layer therefore stays outside the solid.

## Determinism and compatibility

All variation comes from `DeterministicValueNoise(seed)`, fixed arithmetic, and
ordered loops. No Python `hash()`, random state, third-party noise library,
thread, timer, or hidden Variant state is used. Identical requests produce
identical vertices and faces.

The public Rock request remains:

- Size: unchanged
- Roughness: unchanged
- Seed: unchanged
- Resolution: unchanged

Preview and Final continue through the same request, factory, extraction, and
MeshBody paths. The expected canonical digest changes because Sprint 14
deliberately changes Rock geometry.

## Adaptive Rock Preview resolution

Sprint 12 previously capped every Rock Preview at the preset default resolution
17. For a high-resolution Final this sampled the same deterministic field too
coarsely to preserve important facets and ridges.

Rock's existing Resolution metadata now contains the generic ordered Preview
candidates `(17, 21, 25)`. The Preview helper chooses the highest candidate
strictly below the requested Final resolution, while never exceeding the
request:

| Requested Final | Rock Preview |
| ---: | ---: |
| 17 | 17 |
| 25 | 21 |
| 41 | 25 |

Presets without candidates retain the previous default-cap policy, so other
generators are unchanged. Preview and Final retain identical Preset ID,
normalized parameters, Seed, Roughness, facet planes, ridge placement,
grounding, and implicit field. Only `GenerationRequest.resolution` differs.
Final remains a fresh normal execute-path generation and never reuses the
Preview MeshBody.

## Quality and topology validation

Dedicated tests cover:

- identical-request determinism and seed variation;
- finite vertices and conservative sampling bounds;
- non-empty, single-component, oriented manifold and watertight topology;
- zero degenerate faces, nonmanifold edges, nonmanifold vertices, and
  inconsistent-winding edges;
- a downward planar bearing region for Smooth, Weathered, and Rugged;
- materially stronger planar regions and grounding for Rugged than Smooth;
- a greater than 4 mm large-axis-span change between Roughness 0.1 and 0.7 at
  equal Size, Seed, and Resolution;
- deterministic, bounded adaptive Preview selection and unchanged parameters;
- parameter-dependent scale, roughness, and mesh density;
- the new exact default Rock digest.

An exhaustive triangle/triangle self-intersection proof is outside the current
dependency-free mesh validator. Closed oriented two-manifold topology, valid
vertex fans, consistent winding, nondegenerate triangles, and construction as
the boundary of one sampled implicit solid are the practical safeguards used in
Sprint 14.

## Local algorithm benchmark

The table reports the median of three sequential direct generator runs per
configuration, including mesh-statistics calculation, on the same local
machine. Times are development references rather than performance guarantees.
Variant definitions are unchanged.

| Variant | Resolution | Initial v2 vertices/faces | Initial v2 time | Refined v2 vertices/faces | Refined v2 time |
| --- | ---: | ---: | ---: | ---: | ---: |
| Smooth | 17 | 1,040 / 2,076 | 0.238 s | 1,138 / 2,272 | 0.265 s |
| Weathered | 17 | 990 / 1,976 | 0.236 s | 1,074 / 2,144 | 0.263 s |
| Rugged | 25 | 2,388 / 4,772 | 0.740 s | 2,402 / 4,800 | 0.825 s |

All built-in Final configurations remain below one second. Each result was
finite, single-component, oriented-manifold, and watertight. The refined
canonical default (Weathered) digest is
`30a709c32fb7dd16b87f0388f21c6e24e12b6ad990b2872dd31f9549956e7c1d`.

## Local Preview and Final benchmark

| Configuration | Preview res. | Preview vertices/faces | Preview time | Final res. | Final vertices/faces | Final time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Smooth | 17 | 1,138 / 2,272 | 0.265 s | 17 | 1,138 / 2,272 | 0.266 s |
| Weathered | 17 | 1,074 / 2,144 | 0.262 s | 17 | 1,074 / 2,144 | 0.263 s |
| Rugged | 21 | 1,630 / 3,256 | 0.493 s | 25 | 2,402 / 4,800 | 0.825 s |
| Roughness 0.70 high-density check | 25 | 2,160 / 4,316 | 0.816 s | 41 | 5,986 / 11,968 | 3.509 s |

All adaptive Preview measurements remain below one second on the benchmark
machine. Counts differ with density, but the field definition and feature
placement are identical.

## Limitations

- Rock v2 is an artistic procedural boulder, not geological simulation.
- It does not model strata, mineral composition, erosion history, or fracture
  mechanics.
- Planar regions are implicit clipping facets, not a volumetric crack network.
- Marching Tetrahedra and sampling resolution limit the finest visible detail.
- No smoothing, decimation, collision acceleration, or automatic live Preview
  is added.
- Comparison screenshots require a later real Fusion visual acceptance run.
