# Sprint 15 Phase 2 Design: River Stone

## Objective

Phase 2 proves that the three-stage Rock pipeline can produce a distinct rock
family using immutable parameter tuning alone. River Stone targets a rounded,
slightly flattened, water-weathered form with subtle detail, negligible
faceting, and a stable grounding face.

River Stone is internal in Sprint 15. It is not added to preset metadata,
Variants, or the Fusion interface.

## Architecture

`RockFamilyDefinition` is a frozen parameter bundle containing exactly one
configuration for each Phase 1 stage:

```text
RockFamilyRegistry
    -> RockFamilyDefinition
        -> MacroShapeParameters
        -> FacetLayoutParameters
        -> SurfaceDetailParameters
    -> existing _RockField composition
    -> existing mesh pipeline
```

`RockGenerator.generate_family(request, family_id)` is the internal entry
point. It resolves the definition and delegates to the same validation,
sampling, extraction, and three-stage field path used by normal Rock
generation. There is no River Stone field, generator class, procedural branch,
or alternate meshing path.

## River Stone tuning

### Macro Shape

- closer horizontal axis proportions produce a rounder outline
- a shorter vertical radius produces the water-worn flattened mass
- reduced seeded axis amplitude limits asymmetry
- broad directional terms and low-frequency displacement are substantially
  weaker
- center offset remains zero
- the lower half-space provides a stable, restrained grounding face

### Facet Layout

- two small-scale planes replace the default five mixed-scale planes
- normals are biased toward a more uniform upper orientation
- roughness-driven offset excursion is much lower
- the planes remain outside almost all of the rounded surface, preventing
  visible large planar regions

### Surface Detail

- four lower-gain FBM octaves replace the default five-octave profile
- base and Roughness-driven FBM displacement are reduced
- ridged displacement is reduced by more than an order of magnitude
- the same normalized Roughness response still increases both FBM and ridge
  amplitudes

## Compatibility and regression protection

The default family constants reproduce the accepted Sprint 14 coefficients
and arithmetic order. Smooth, Weathered, Rugged, and Custom continue through
`RockGenerator.generate()` and never select a family by Variant identity.

Exact regression digests:

| Configuration | Resolution | Digest |
| --- | ---: | --- |
| Smooth | 17 | `29d6402a0148637fd00cbc1274d8f6be6c9f8901b2b856e2de75dc43f91bdc3e` |
| Weathered | 17 | `30a709c32fb7dd16b87f0388f21c6e24e12b6ad990b2872dd31f9549956e7c1d` |
| Rugged | 25 | `040bd703ef44549b418fdb5fd6804b9e36ce93e372cbbea00e5e63a8b8ffadde` |
| River Stone | 25 | `61264e6e929229247ac7b4d89f2916f5c5cb875dc985c5c258fa79334c18abd4` |

## Test coverage

- immutable family definitions and deterministic registry order
- unknown family rejection
- all three existing pipeline stages used by River Stone
- lower Macro deformation, facet count, FBM, and ridge settings
- preserved Roughness scaling
- identical mesh for identical input and Seed
- Seed-sensitive geometry
- exact River Stone digest
- finite, nondegenerate, watertight, manifold, single-component mesh
- flatter proportions and absence of large non-ground planar regions
- exact Smooth, Weathered, and Rugged digest regression

## Local benchmark

River Stone uses Size 40, Roughness 0.35, and Seed 1. Times are medians of
three sequential direct internal-family runs on the development machine.

| Path | Resolution | Vertices/faces | Median | Components | Watertight/manifold |
| --- | ---: | ---: | ---: | ---: | --- |
| Preview-density | 21 | 1,714 / 3,424 | 0.447 s | 1 | yes / yes |
| Final-density | 25 | 2,482 / 4,960 | 0.747 s | 1 | yes / yes |

The Preview-density result remains below one second and the Final-density
result is comparable to the Sprint 14 Rugged resolution-25 reference of
2,402 vertices, 4,800 faces, and 0.825 seconds. These are local development
measurements, not runtime guarantees.

## Scope

Phase 2 does not add UI controls, preset IDs, Variants, Fusion behavior,
Preview policy, GeneratorFactory registration, or new public request
parameters. Granite, Basalt, Limestone, Broken Rock, and other future families
are not implemented.

## Remaining limitations

River Stone is an artistic procedural family, not a geological or erosion
simulation. It does not model transport history, mineral composition, impact
marks, cracks, or species of stone. Visual Fusion acceptance and public family
selection remain future work.
