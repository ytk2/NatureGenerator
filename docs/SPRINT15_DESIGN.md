# Sprint 15 Design: Rock Family Architecture

## Objective

Sprint 15 separates Rock's accepted Sprint 14 implicit field into independently
constructible, immutable, and testable stages, then proves that architecture
with the first parameter-only internal family:

```text
RockFamilyRegistry
    -> RockFamilyDefinition
        -> MacroShapeParameters
        -> FacetLayoutParameters
        -> SurfaceDetailParameters
    -> RockGenerationContext
    -> three stage definitions
    -> composed Rock scalar field
    -> existing voxel and mesh pipeline
```

Phase 1 provides the pipeline foundation. Phase 2 adds River Stone by supplying
different stage parameters. No UI, preset, Variant, Preview, command, Fusion
API, GeneratorFactory, or other generator behavior changes in Sprint 15.

## Shared context

`RockGenerationContext` stores Size, Roughness, Seed, and the normalized
smoothstep Roughness response. Stage builders receive this context and the
same seeded deterministic value-noise source. The context and every generated
stage definition are frozen dataclasses.

## Stage ownership

### Macro Shape

`MacroShapeDefinition` owns ellipsoid radii, orientation, center offset,
broad directional deformation, large-scale noise, and the grounding
half-space. Its explicit orientation and offset fields are identity and zero
in Phase 1, leaving stable extension points for later diversity work.

### Facet Layout

`FacetLayoutDefinition` owns the deterministic clipping planes. Each immutable
`FacetPlane` records its unit normal, offset, scale classification, and weight.
The accepted five Sprint 14 planes remain unchanged; scale labels make future
layout experiments observable without introducing a rock-family branch.

### Surface Detail

`SurfaceDetailDefinition` owns medium/fine FBM and ridged-noise configuration.
It evaluates only local deformation and has no responsibility for global
proportions, grounding, or clipping.

## Composition and determinism

`RockGenerator` still validates the same `GenerationRequest`, samples the same
bounds at the same requested resolution, and uses the existing extraction and
validation pipeline. `_RockField` constructs the three definitions once and
composes their terms in the same arithmetic order as Sprint 14:

```text
ellipsoid distance
    + broad deformation
    + large-scale noise
    + FBM
    + ridged noise
    -> facet intersections
    -> grounding intersection
```

There is no Variant name or style identity in the generator. Smooth,
Weathered, Rugged, and Custom continue to reach Rock only as ordinary
parameter values. Identical parameters and Seed therefore construct identical
definitions and meshes.

The canonical default digest remains:

```text
30a709c32fb7dd16b87f0388f21c6e24e12b6ad990b2872dd31f9549956e7c1d
```

## Test strategy

Stage tests verify:

- immutability and deterministic construction
- Seed-dependent macro proportions and facet placement
- positive bounded radii and valid grounding
- orthonormal orientation and bounded center offset
- finite unit facet normals, bounded offsets, and mixed scale labels
- bounded FBM/ridge configuration and Roughness response

Integration tests retain Rock's digest, topology, determinism, Roughness,
resolution, and Variant coverage. The full suite protects all other
generators and the Preview/Final workflow.

## Local benchmark

Times are medians of three sequential direct generator runs on the development
machine and are not performance guarantees. The accepted Sprint 14 reference
and Phase 1 produce identical vertex/face counts and digests. The small timing
difference is ordinary run-to-run and interpreter overhead.

| Variant | Resolution | Sprint 14 reference vertices/faces | Phase 1 vertices/faces | Sprint 14 reference time | Phase 1 median |
| --- | ---: | ---: | ---: | ---: | ---: |
| Smooth | 17 | 1,138 / 2,272 | 1,138 / 2,272 | 0.265 s | 0.283 s |
| Weathered | 17 | 1,074 / 2,144 | 1,074 / 2,144 | 0.263 s | 0.283 s |
| Rugged | 25 | 2,402 / 4,800 | 2,402 / 4,800 | 0.825 s | 0.872 s |

Additional Phase 1 coverage:

| Configuration | Resolution | Vertices/faces | Median | Components | Watertight/manifold |
| --- | ---: | ---: | ---: | ---: | --- |
| Custom Roughness 0.10 | 25 | 2,574 / 5,144 | 0.886 s | 1 | yes / yes |
| Custom Roughness 0.70 | 25 | 2,160 / 4,316 | 0.878 s | 1 | yes / yes |
| Weathered | 25 | 2,384 / 4,764 | 0.857 s | 1 | yes / yes |
| Weathered | 41 | 6,730 / 13,456 | 3.750 s | 1 | yes / yes |

## Compatibility

- Public Rock parameters and the Roughness range remain unchanged.
- Built-in Variant definitions remain unchanged.
- Preview continues to use the existing adaptive metadata policy.
- Final generation continues through the normal execute path.
- `GeneratorFactory` and all public generator APIs remain unchanged.
- No third-party dependency is introduced.

## Rock families

`RockFamilyDefinition` contains exactly one immutable parameter object per
stage. `RockFamilyRegistry` is read-only and resolves the default family and
River Stone by stable internal ID. `RockGenerator.generate_family` delegates
to the same private generation method as `RockGenerator.generate`; family
identity never appears in scalar-field evaluation.

River Stone changes only these values:

- rounder horizontal and flatter vertical Macro proportions
- weaker seeded asymmetry and large-scale displacement
- two small, minimally intrusive facet planes instead of five mixed planes
- lower-gain FBM and much weaker ridged displacement
- stable grounding and the same normalized Roughness response

Its resolution-25 digest is:

```text
61264e6e929229247ac7b4d89f2916f5c5cb875dc985c5c258fa79334c18abd4
```

See [SPRINT15_PHASE2_DESIGN.md](SPRINT15_PHASE2_DESIGN.md) for the detailed
tuning and benchmark record.

## Extension points

Later reviewed phases can vary orientation, center offset, mass distribution,
facet count and grouping, or surface-detail profiles with parameter bundles.
Sprint 15 deliberately does not expose any family in the Fusion UI and does not
implement Granite, Basalt, Limestone, Broken Rock, or other future families.

## Remaining limitations

Rock remains an artistic procedural boulder rather than a geological
simulation. It does not simulate strata or fracture mechanics, detect arbitrary
self-intersection, or add smoothing and decimation. River Stone selection is
internal until Sprint 16.
