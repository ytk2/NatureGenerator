# Architecture

The current stable product baseline is the immutable `v0.7.0` release tag.
This file is current main-branch documentation describing that architecture;
later documentation edits do not alter the tagged commit. See the
[baseline checklist](docs/V0.5.0_BASELINE.md) and
[release history](docs/RELEASES.md) for validated capabilities and limitations.

## Design goals

NatureGenerator separates procedural geometry from Autodesk Fusion 360 so that
geometry algorithms can be tested with the Python standard library alone. The
core should produce plain Python data that can later be consumed by Fusion 360,
an STL writer, or another adapter.

## Layer boundaries

### Nature presets (`presets/`)

Defines the stable user-facing vocabulary of natural forms. Each immutable
`NaturePreset` contains display metadata, default parameters, availability, and
a stable `generator_id`. Presets reference generators only through that string;
they must not import generator implementations, sample scalar fields, or extract
meshes.

`PresetFactory` is the command/UI entry point. It uses explicit built-in
registration rather than filesystem discovery, keeping startup deterministic in
Fusion's Python environment. Sponge maps to the available `gyroid` generator
ID. Coral, Rock, and Sprint 10 Bark are available through the `coral`, `rock`,
and `bark` generator IDs; Bone remains visibly unavailable. Executable presets
describe all Fusion inputs through ordered parameter metadata.

### Generator runtime (`generators/`)

The Generator Runtime is the resolver and execution layer between presets and
procedural algorithms. `GeneratorFactory` maps a request's preset ID through an
explicit registration table to a `MeshGenerator`, then checks that the
implementation ID matches the preset's stable `generator_id`.
`GenerationRequest` carries a preset ID, immutable parameter overrides, and
samples-per-axis resolution without Fusion types. A `MeshGenerator` implements
`generate(request) -> TriangleMesh`. The factory validates that mesh and returns
an immutable `GeneratorResult` containing the mesh, statistics, warnings, IDs,
and elapsed time.

`SpongeGenerator` delegates to the unchanged `GyroidGenerator` pipeline, while
`CoralGenerator` produces a closed branching implicit solid, `RockGenerator`
produces a closed deformed ellipsoid with deterministic value noise, and
`BarkGenerator` produces a closed capped trunk field with directional periodic
detail using the same narrow deterministic value-noise primitive. The legacy
generator-ID factory and public result-returning entry points remain compatible.
The runtime uses explicit registration rather than filesystem discovery and
does not introduce `GeneratorDescriptor`.

### Scalar fields and generators (`generators/`)

A scalar field is the mathematical implicit representation of a form. It maps a
three-dimensional point to a scalar value that can be sampled and polygonized.
`GyroidField` returns `abs(g) - thickness` for a periodic gyroid sheet. Rock and
Bark supply bounded callable fields directly; Bark closes its finite cylinder
with the maximum of its radial side field and planar cap field.

Generator implementations may depend on the scalar-field contract and geometry
core, but must remain independent of Fusion 360. They do not contain user-facing
preset metadata.

### Core geometry (`core/`)

Owns scalar-field contracts, voxel sampling, marching-tetrahedra isosurface
extraction, indexed `TriangleMesh` data, optimization, validation, statistics,
and mesh exporters. This layer must not import `adsk` or depend on Fusion 360
runtime state.

The mesh stage includes deterministic construction and vertex welding,
conservative cleanup, face and vertex normals, topology validation and
statistics, plus STL, OBJ, and PLY serialization. Optimization does not alter the
surface through smoothing or decimation.

### Application commands (`commands/`)

Commands coordinate user intent without knowing algorithm classes or Autodesk
objects. `generate_nature.py` accepts a `GenerationRequest`, asks the Generator
Runtime to execute it, and passes the resulting mesh to an injected adapter
callable. This keeps orchestration thin and testable outside Fusion.

### Fusion adapter (`fusion/`)

The Fusion Adapter converts a core `TriangleMesh` into a Fusion `MeshBody` and
owns Fusion-specific validation and lifecycle behavior. `MeshBodyBuilder`
flattens indexed mesh data for Fusion and inserts it into the active design's
root component. The adapter converts the core's millimeter-based coordinates to
Fusion Design API database units (centimeters). `fusion.runtime` registers the
interactive **Generate Nature** command, builds its inputs from `PresetFactory`,
retains handlers for the required command lifetime, and removes its UI resources
when the add-in stops.

Functional Autodesk integration is confined to `fusion/`. The add-in entry
point delegates lifecycle calls to this layer and imports `adsk` only for fatal
startup and shutdown reporting. Because Fusion executes the entry-point file
directly, it also adds the directory containing `NatureGenerator.py` to
`sys.path` once before importing sibling packages. This bootstrap is confined to
the entry point. Presets, generators, commands, core, and Fusion modules do not
modify the import path.

## Runtime pipeline

```text
User / Fusion Command
    -> Generation Request
    -> Nature Preset
    -> Generator Runtime
    -> Scalar Field
    -> Voxel Grid
    -> Marching Tetrahedra
    -> Triangle Mesh
        -> STL Export
        -> Fusion Adapter
            -> Fusion MeshBody
```

1. A user or Fusion command creates an immutable request identifying a preset,
   parameter overrides, and sampling resolution.
2. The Generator Runtime resolves the preset ID to a registered mesh generator
   and verifies its stable `generator_id` against the preset metadata.
3. The implementation supplies a scalar field, such as `GyroidField`.
4. The core samples the field into a regular voxel grid.
5. Marching tetrahedra extracts a Fusion-independent indexed triangle mesh.
6. The mesh can be validated, optimized, exported to STL, or passed to the
   Fusion Adapter for insertion as a Fusion `MeshBody`.

The sampling, extraction, and mesh stages should use explicit tolerances and
deterministic iteration. Manufacturability checks—such as minimum feature size,
watertightness, and build-volume limits—will be introduced as separate passes so
they do not become implicit side effects of surface extraction.

## Dependency direction

```text
Fusion UI lifecycle
    -> Fusion Adapter runtime
    -> Generate Nature command
    -> GenerationRequest
    -> PresetFactory
    -> NaturePreset

Generator Runtime
    -> Generator implementation
    -> ScalarField
    -> core

Fusion Adapter
    -> core
```

Dependencies point toward the Fusion-independent geometry core. `core/` never
imports from presets, generators, commands, or Fusion integration. Presets
reference generator implementations only through stable `generator_id` strings.
The Generator Runtime owns ID resolution, and the Fusion Adapter depends on core
mesh types rather than the reverse. Autodesk dependencies stop at the
`fusion/` boundary.

These boundaries keep mathematical geometry testable in ordinary Python and
prevent Autodesk runtime concerns from leaking into presets or algorithms.
