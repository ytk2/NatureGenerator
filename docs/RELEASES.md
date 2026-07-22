# Release History

This history is maintained on the current development branch. Release tags are
immutable recovery points; later documentation updates describe those releases
without becoming part of their tagged commits.

## Unreleased — Sprint 13 Generator Variants

Development on `feature/generator-variants` adds immutable curated parameter
configurations for Sponge, Coral, Rock, Bark, and Root, plus a generic Variant
dropdown and Custom editing state. Variants flow through the existing Preview
and OK request paths and do not alter generator algorithms. Names describe
parameter configurations rather than biological or species realism.

Real Fusion acceptance on macOS verified one filtered Variant dropdown, named
parameter application, explicit Preview and replacement, Custom transition
after editing, Rock/Bark/Root switching, OK, Cancel, and clean event lifecycle.
Visual checks covered Rock Smooth, Rock Rugged, Rock Custom, Bark Grooved, and
Root Dense; they do not represent visual inspection of every Variant. Sprint 13
remains unreleased pending merge and release tagging.

## v0.10.0 — Interactive Preview Foundation

Added an explicit Preview button,
temporary preview-body ownership, deterministic request reuse, safe replacement,
transactional preview insertion, final regeneration, and Destroy/stop cleanup.
Preview resolution is capped at each preset's existing default Resolution.
Automatic preview and background generation are intentionally not included.

Real Fusion acceptance on macOS verified the explicit Preview button, viewport
and Browser display, replacement after Cell Size changes, OK finalization,
Cancel cleanup, and absence of orphaned bodies or duplicate controls. The
observed Sponge preview at resolution 17 contained 5,684 vertices and 10,944
faces and completed in approximately 0.25–0.27 seconds.

## v0.9.0 — Root Generator and Public Project Foundation

Development on `feature/root-generator` adds a deterministic connected Root
system with Length, Root Radius, Branch Count, Branching, Spread, Taper,
Gravity, Seed, and Resolution controls. It also establishes public vision,
getting-started, gallery, and release-process documentation. Root completed real
Fusion acceptance and is part of v0.9.0.

Real Fusion acceptance on macOS verified all nine Root inputs, creation of
`NatureGenerator Root` MeshBodies, parameter-dependent geometry, and clean
command startup without duplicate controls. Observed runs produced 6,568
vertices and 13,136 faces in approximately 2.498 seconds, and 7,452 vertices and
14,900 faces in approximately 3.941 seconds. These runs do not represent an
exhaustive test of every parameter combination.

Root v1 is structurally successful but can resemble a simplified branching
pipe or stylized root rather than a botanically realistic root system. Natural
branching angles, hierarchical thickness, finer terminal roots, ground
interaction, and space-colonization growth remain future work. No botanical
simulation or species reproduction is claimed.

## v0.8.0 — Bark Generator

Real Fusion acceptance on macOS verified Bark preset inputs, MeshBody creation,
parameter effects, Bark Depth rejection, and command lifecycle behavior. Bark
v1 is a closed directional-groove trunk, but its visual character remains closer
to an irregular or twisted trunk than realistic fractured bark. Crack, plate,
peeling, knot, and species-specific models remain future work.

## v0.7.0 — Rock Generator

Added the deterministic watertight Rock generator, Size/Roughness/Seed controls,
and metadata-driven preset-specific Fusion inputs while preserving Sponge and
Coral behavior.

## v0.5.0 — Interactive Generation Command

**Status:** Historical stable release

### Capabilities

- NatureGenerator loads as a Fusion add-in.
- Provides the interactive **Generate Nature** command.
- Uses a Fusion-native parameter dialog.
- Generates the Sponge preset.
- Exposes Cell Size, Thickness, and Resolution controls.
- Produces a Fusion-independent `TriangleMesh`.
- Inserts the result as a Fusion `MeshBody`.
- Provides diagnostic logging and startup error reporting.

### Real Fusion validation

Validated with Autodesk Fusion on macOS:

- Generate Nature displayed successfully.
- The interactive command dialog displayed successfully.
- A Sponge `MeshBody` was generated successfully.
- Resolution 41 completed successfully.
- The observed result contained 44,396 vertices and 86,400 faces and completed
  in approximately 1.869 seconds.

![Generate Nature dialog and generated Sponge mesh](images/v0.5.0-generate-nature-dialog.png)

### Known limitations

- Sponge is the only executable preset.
- There is no live preview.
- There is no progress indicator.
- Generation is synchronous and pure Python.
- The command is currently located under Utilities > Add-Ins.
- Generated finite gyroid meshes have open crop boundaries.
- There is no smoothing or decimation.
- There is no installation package.

## v0.4.0 — First Fusion Integration

Added the first working Fusion boundary: the add-in loaded, exposed a minimal
Sponge command, executed the existing Generator Runtime, and inserted its
`TriangleMesh` as a Fusion `MeshBody`. This release also established startup
diagnostics and the add-in-loader package bootstrap.

## v0.3.0 — Generator Runtime

Added the Generator interface, explicit `GeneratorFactory`, immutable
`GeneratorResult`, and the complete Sponge preset-to-gyroid-to-mesh execution
pipeline while keeping the runtime Fusion-independent.

## v0.2.0 — Nature Preset Framework

Added immutable user-facing preset definitions, parameter metadata,
`PresetRegistry`, and `PresetFactory`. Sponge was connected to the stable
`gyroid` generator ID; Coral, Bone, Bark, and Rock remained explicitly
unavailable.

## v0.1.0 — Geometry Engine Foundation

Established the dependency-free geometry engine: scalar fields, voxel grids,
marching tetrahedra, indexed triangle meshes, validation and statistics, mesh
optimization, and STL/OBJ/PLY export foundations.
