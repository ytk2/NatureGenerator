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

**Sprint 21 — Sponge Preset MVP**

- promote Sponge from a no-Family placeholder to `SpongeFamilyRegistry`
- register Classic Sponge through the generic Preset Catalog
- replace the boundary-clipped sheet with a closed porous solid
- add deterministic Seed-dependent rounded pore placement
- expose Sponge Family selection through the existing Fusion dialog
- preserve Rock, Bark, and Coral regression digests

See [SPRINT21_DESIGN.md](docs/SPRINT21_DESIGN.md).

**Sprint 22 — Generated Asset and Export Architecture**

- add a renderer-neutral `GeneratedAsset` around the existing mesh
- separate material, mapping, baked resource, and provenance intent
- preserve generator geometry and legacy mesh consumers
- establish future asset-export adapter contracts without implementing formats

See [SPRINT22_DESIGN.md](docs/SPRINT22_DESIGN.md).

**Sprint 23 — Complete Family Registry Migration**

- add Classic Root and `RootFamilyRegistry`
- route the final implemented preset through the generic Family architecture
- expose Root Family selection through the existing Fusion dropdown
- preserve Root geometry, deterministic Seed, Preview, and legacy requests
- leave Bone implementation for its dedicated generator sprint

See [SPRINT23_DESIGN.md](docs/SPRINT23_DESIGN.md).

**Sprint 24 — Bone Preset MVP**

- add Classic Bone and `BoneFamilyRegistry`
- add a curved variable-radius long-bone implicit generator
- provide enlarged asymmetric ends, shallow deterministic detail, and grounding
- integrate Bone with Family, Preview, OK, and GeneratedAsset workflows
- require closed, manifold, watertight, single-component printable output

See [SPRINT24_DESIGN.md](docs/SPRINT24_DESIGN.md).

**Sprint 25 — Rock Family Expansion**

- expose the accepted canonical geometry as Classic Rock
- add Layered Rock, Weathered Rock, and River Rock as immutable definitions
- add optional zero-default horizontal strata to the existing surface stage
- preserve all seven earlier Rock Family IDs and exact digests
- retain generic Family, Preview, OK, GeneratedAsset, and request workflows
- require deterministic watertight single-component output

See [SPRINT25_DESIGN.md](docs/SPRINT25_DESIGN.md).

**Sprint 26 — Crystal Preset MVP**

- add Classic Crystal and `CrystalFamilyRegistry`
- add an elongated irregular polygonal prism with tapered termination
- make Seed and all six shape/density controls geometrically meaningful
- integrate Crystal with generic Family, Preview, OK, and GeneratedAsset paths
- require deterministic watertight manifold single-component output
- preserve all existing preset geometry digests and architecture boundaries

See [SPRINT26_DESIGN.md](docs/SPRINT26_DESIGN.md).

**Sprint 27 — Natural Material Framework**

- introduce immutable shared `NaturalMaterial` catalog records
- centralize reusable Asset Browser category and keyword metadata
- prepare optional renderer-neutral thumbnail resource references
- standardize Form and Generation parameter groups for all built-ins
- preserve all existing geometry, IDs, defaults, requests, and asset behavior

See [SPRINT27_DESIGN.md](docs/SPRINT27_DESIGN.md).

**Sprint 28 — Procedural Lab Foundation**

- add an independent Procedural Lab command for selected Fusion geometry
- adapt one solid or mesh into the existing immutable TriangleMesh
- add operator contracts, an immutable registry, and ordered pipeline boundary
- prove Preview and Apply end to end with deterministic Pass Through
- isolate source geometry and Nature Library preview ownership

See [SPRINT28_DESIGN.md](docs/SPRINT28_DESIGN.md).

**Sprint 29 — Noise Displacement Operator**

- add deterministic object-space fractal value noise
- displace vertices along safe area-weighted normals
- expose registry-driven operator parameter controls
- preserve connectivity, winding, components, and Pass Through behavior
- retain MeshBody-only Preview and Apply routing

See [SPRINT29_DESIGN.md](docs/SPRINT29_DESIGN.md).

**Sprint 30 — Subdivision Operator**

- add the first topology-changing Procedural Lab operator
- split every triangle into four using shared deterministic edge midpoints
- expose registry-driven Subdivision Level values 1–3
- preserve winding, components, manifold adjacency, units, and source geometry
- prepare denser inputs for later Noise, Relax, Smooth, Voronoi, and Erosion

See [SPRINT30_DESIGN.md](docs/SPRINT30_DESIGN.md).

**Sprint 31 — Voronoi Surface Operator**

- add the first cell-based Procedural Lab deformation
- generate deterministic jittered object-space lattice sites on demand
- derive smooth boundary masks from nearest and second-nearest distances
- expose registry-driven Cell Size, Depth, Edge Width, Falloff, Jitter, and Seed
- preserve connectivity and prepare future cracks, cells, and porous surfaces

See [SPRINT31_DESIGN.md](docs/SPRINT31_DESIGN.md).

## Candidate Future Work

- Procedural Lab operator stack and real geometry operators

- Dedicated Utilities > Nature Generator panel
- Command icon and resource assets
- Improved bounded or capped mesh output
- Progress and cancellation support
- Additional generators and presets:
  - richer Coral models, including possible Gray-Scott growth
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
