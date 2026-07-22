# Roadmap

## Current Stable Baseline

**v0.9.0 — Root Generator and Public Project Foundation**

The immutable `v0.9.0` Git tag is the released source baseline. This roadmap is
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
v0.9.0 unless a maintenance branch explicitly targets an earlier release.

See the [v0.5.0 baseline checklist](docs/V0.5.0_BASELINE.md) and
[release history](docs/RELEASES.md) for verified capabilities and limitations.

## Committed Next Sprint

**Sprint 12 — Interactive Preview Foundation**

In development on `feature/interactive-preview` and explicitly unreleased:

- add explicit, reversible preview MeshBodies
- replace previews safely and regenerate final output after preview rollback
- clean owned preview geometry on Destroy and add-in stop
- retain synchronous, generator-independent execution without unsafe threads
- real Fusion acceptance passed for preview display, replacement, OK, and Cancel

See [SPRINT12_DESIGN.md](docs/SPRINT12_DESIGN.md) for state, ownership,
architecture decisions, and Fusion acceptance checks.

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
