# Roadmap

## Current Stable Baseline

**v0.8.0 — Bark Generator**

The immutable `v0.8.0` Git tag is the released source baseline. This roadmap is
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
v0.8.0 unless a maintenance branch explicitly targets an earlier release.

See the [v0.5.0 baseline checklist](docs/V0.5.0_BASELINE.md) and
[release history](docs/RELEASES.md) for verified capabilities and limitations.

## Committed Next Sprint

**Sprint 11 — Root Generator and Public Project Foundation**

In development on `feature/root-generator` and explicitly unreleased:

- add a deterministic, connected, watertight Root generator
- expose nine Root inputs through existing preset metadata
- preserve Sponge, Coral, Rock, and Bark behavior
- add public vision, getting-started, gallery, and release-process documents

See [SPRINT11_DESIGN.md](docs/SPRINT11_DESIGN.md) for scope, exclusions,
architecture decisions, Definition of Done, and Fusion acceptance checks.

## Candidate Future Work

- Dedicated Utilities > Nature Generator panel
- Command icon and resource assets
- Improved bounded or capped mesh output
- Progress and cancellation support
- Additional generators and presets:
  - richer Coral models, including possible Gray-Scott growth
  - Bone / Cellular or Voronoi
- Bark v2: longitudinal crack and plate-based surface model
- Preview workflow, including live or deferred preview
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
