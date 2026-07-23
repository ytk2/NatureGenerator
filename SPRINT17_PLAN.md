# Sprint 17 Plan: Rock Diversity

## Status

Complete. Automated validation and real Autodesk Fusion acceptance passed.

## Objective

Add three silhouette-level Rock families through the existing immutable
Macro Shape, Facet Layout, and Surface Detail parameter contracts:

1. Granite
2. Basalt
3. Broken Rock

No family owns a generator, scalar field, mesh path, or Fusion branch.

## Implemented scope

- register all three families in `RockFamilyRegistry`
- preserve the required seven-family display order
- apply family defaults through the existing Registry-driven Fusion input
- retain Size, Roughness, Seed, and Resolution as the only Rock controls
- retain adaptive Preview resolution and fresh full-resolution Final generation
- preserve Smooth, Weathered, Rugged, and River Stone definitions and digests
- add deterministic, topology, grounding, silhouette, UI, and regression tests
- document tuning, measurements, benchmarks, limitations, and Fusion retest

## Family goals

### Granite

A broad, heavy, irregular boulder with unequal proportions, rounded major
masses, moderate planar breaks, and coarse multi-scale detail.

### Basalt

A tall, dense, directional block with strong planar sides and restrained local
surface displacement. This does not simulate column-joint topology.

### Broken Rock

An asymmetric wedge-like stone dominated by multiple large deterministic
fracture planes and pronounced angular transitions.

## Architecture constraints

- `RockFamilyRegistry` remains the single source of truth.
- Every family uses the same three-stage Rock field and existing mesh pipeline.
- Fusion contains no family-name or family-default hardcoding.
- GeneratorFactory, Geometry Core, Marching Tetrahedra, MeshBody insertion,
  Preview policy, and command lifecycle remain unchanged.
- No third-party dependency, thread, async work, timer, sleep, or automatic
  Preview is introduced.

## Acceptance gates

- exact existing four-family digest regression
- stable new-family digests
- deterministic Seed behavior and measurable Roughness response
- finite, nondegenerate, consistently wound meshes
- zero boundary, non-manifold edge, and non-manifold vertex counts
- one closed watertight component with a practical grounding region
- measurable silhouette and planar-region differentiation
- Preview resolution 21 and Final resolution 25 at defaults
- Preview below approximately one second on the local benchmark machine
- complete automated and real Autodesk Fusion validation

## Out of scope

- geological or material simulation
- column-joint, mineral, or fracture-mechanics modeling
- new public Rock controls
- saved or custom families
- smoothing, decimation, materials, or textures
- changes to non-Rock generators

## Real Fusion acceptance

- Granite, Basalt, and Broken Rock were visually distinct.
- all three new families behaved correctly.
- existing Rock families remained functional and unchanged.
- Sponge, Coral, Bark, and Root remained functional.
- no further Sprint 17 functional changes were required.

See [`docs/SPRINT17_DESIGN.md`](docs/SPRINT17_DESIGN.md).
