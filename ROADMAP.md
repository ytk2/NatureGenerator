# Roadmap

## Current Stable Baseline

**v0.11.0 — Generator Variants**

The immutable `v0.11.0` Git tag is the released source baseline. This roadmap is
current main-branch documentation describing that baseline and future
candidates; it is not part of the historical tagged commit unless viewed from
that tag.

Completed:

- Geometry Core
- Nature Preset Framework
- Generator Runtime
- Fusion Adapter
- Generate Nature command
- Interactive Sponge parameters
- Real Fusion acceptance test

All future feature branches should be created from the latest `main` unless a
maintenance branch explicitly targets an earlier release.

See the [v0.5.0 baseline checklist](docs/V0.5.0_BASELINE.md) and
[release history](docs/RELEASES.md) for verified capabilities and limitations.

## Completed Development Milestones

**Sprint 14 — Rock Generator v2**

- natural multi-scale boulder silhouettes
- Roughness controls broad form, facets, ridges, and surface breakup
- Smooth, Weathered, and Rugged remain distinct
- adaptive Preview resolution preserves major features
- deterministic, watertight output retained

See [SPRINT14_DESIGN.md](docs/SPRINT14_DESIGN.md).

**Sprint 15 — Rock Family Architecture**

- separate Macro Shape, Facet Layout, and Surface Detail definitions
- make each internal stage immutable and independently testable
- preserve Sprint 14 geometry, parameters, Variants, and Preview behavior
- add an immutable, read-only internal Rock Family registry
- prove parameter-only family generation with River Stone
- keep River Stone intentionally absent from the Fusion UI

See [SPRINT15_DESIGN.md](docs/SPRINT15_DESIGN.md) for stage ownership,
family composition, compatibility, regression digests, and validation.

**Sprint 16 — Fusion Rock Family Selection**

- Registry-driven Rock Family dropdown
- Smooth, Weathered, Rugged, and River Stone selection
- unchanged Preview/Final lifecycle and backward-compatible requests
- manual Autodesk Fusion validation passed

See [SPRINT16_DESIGN.md](docs/SPRINT16_DESIGN.md).

## Completed Development Milestone

**Sprint 17 — Rock Diversity**

Completed on `feature/rock-diversity`:

- add Granite, Basalt, and Broken Rock through stage parameter tuning
- preserve the existing four Rock family digests
- create silhouette-level mass, axis, and facet differences
- retain Registry-driven UI and Preview/Final behavior
- maintain deterministic manufacturable topology
- real Autodesk Fusion acceptance passed

See [SPRINT17_DESIGN.md](docs/SPRINT17_DESIGN.md).

**Sprint 18 — Preset Registry Architecture**

- add immutable preset-to-Family registry definitions
- compose all built-in presets in one application catalog
- make Fusion Family presentation registry-driven rather than Rock-specific
- keep non-Rock presets as explicit no-Family placeholders
- preserve all generator, geometry, Preview, Final, and public preset behavior

See [SPRINT18_DESIGN.md](docs/SPRINT18_DESIGN.md).

**Sprint 19 — Bark Preset MVP**

- promote Bark from a no-Family placeholder to `BarkFamilyRegistry`
- add the initial Classic Bark Family through immutable parameter metadata
- preserve the accepted capped cylindrical Bark geometry
- keep all seven Bark inputs, Preview, OK, and GeneratorFactory behavior
- retain deterministic watertight single-component output

See [SPRINT19_DESIGN.md](docs/SPRINT19_DESIGN.md).

**Sprint 20 — Coral Preset MVP**

- promote Coral from a no-Family placeholder to `CoralFamilyRegistry`
- add Classic Coral as the initial branching Family
- preserve the accepted Seed 0 Coral geometry
- add deterministic Seed-dependent connected branch variation
- keep Preview, OK, topology, and GeneratorFactory behavior

See [SPRINT20_DESIGN.md](docs/SPRINT20_DESIGN.md).

## Candidate Future Work

- Dedicated Utilities > Nature Generator panel
- Command icon and resource assets
- Improved bounded or capped mesh output
- Progress and cancellation support
- Additional generators and presets:
  - richer Coral models, including possible Gray-Scott growth
  - Bone / Cellular or Voronoi
- Bark v2: longitudinal crack and plate-based surface model
- Safely debounced automatic preview when a host-supported timer is proven
- Release packaging or installer
- Gallery and demonstration assets backed by real Fusion captures
- Root v2 exploration: more natural branching angles, hierarchical thickness,
  finer terminal roots, ground interaction, and space-colonization growth
- Smoothing and mesh optimization

## Delivered Foundation

- Project and add-in structure
- Scalar-field and voxel-grid representations
- Marching-tetrahedra isosurface extraction
- Indexed meshes, validation, statistics, and exporters
- Gyroid field and Sponge runtime
- User-facing Nature Preset framework
- Interactive Fusion command and MeshBody insertion
- Deterministic watertight Rock generator and preset-driven Fusion inputs
- Deterministic closed Bark trunk generator with directional grooves
- Public documentation foundation for use, evidence, vision, and releases

This roadmap is directional. Each phase should remain small enough to review and
should add tests before expanding the public API.
