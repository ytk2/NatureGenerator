# Roadmap

## Current Stable Baseline

**v0.5.0 — Interactive Generation Command**

The immutable `v0.5.0` Git tag is the released source baseline. This roadmap is
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
v0.5.0 unless a maintenance branch explicitly targets an earlier release.

See the [v0.5.0 baseline checklist](docs/V0.5.0_BASELINE.md) and
[release history](docs/RELEASES.md) for verified capabilities and limitations.

## Committed Next Sprint

No next Sprint has been selected. Selecting one of the candidates below requires
an explicit scope and architecture review.

## Candidate Future Work

- Dedicated Utilities > Nature Generator panel
- Command icon and resource assets
- Improved bounded or capped mesh output
- Live or deferred preview
- Progress and cancellation support
- Additional generators and presets:
  - Coral / Gray-Scott
  - Rock / Voronoi and Noise
  - Bark / Noise
  - Bone / Cellular or Voronoi
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

This roadmap is directional. Each phase should remain small enough to review and
should add tests before expanding the public API.
