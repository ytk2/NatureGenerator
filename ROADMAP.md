# Roadmap

## Current Stable Baseline

**v0.7.0 — Rock Generator**

The immutable `v0.7.0` Git tag is the released source baseline. This roadmap is
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

All future feature branches should be created from the latest `main` after
v0.7.0 unless a maintenance branch explicitly targets an earlier release.

See the [v0.5.0 baseline checklist](docs/V0.5.0_BASELINE.md) and
[release history](docs/RELEASES.md) for verified capabilities and limitations.

## Committed Next Sprint

**Sprint 10 — Bark Generator**

In development on `feature/bark-generator`:

- add a deterministic, watertight Bark trunk generator
- expose Bark-specific inputs through existing preset metadata
- share only the deterministic value-noise primitive with Rock
- preserve exact Rock output and Sponge/Coral routing

See [SPRINT10_DESIGN.md](docs/SPRINT10_DESIGN.md) for scope, exclusions,
architecture decisions, Definition of Done, and Fusion acceptance checks.

## Candidate Future Work

- Dedicated Utilities > Nature Generator panel
- Command icon and resource assets
- Improved bounded or capped mesh output
- Live or deferred preview
- Progress and cancellation support
- Additional generators and presets:
  - richer Coral models, including possible Gray-Scott growth
  - Bone / Cellular or Voronoi
- Bark v2: longitudinal crack and plate-based surface model
- Smoothing and mesh optimization
- Installer or release packaging

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

This roadmap is directional. Each phase should remain small enough to review and
should add tests before expanding the public API.
