# Architecture

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
Fusion's Python environment. Sponge currently maps to the available `gyroid`
generator ID; Coral, Bone, Bark, and Rock remain visibly unavailable until their
reserved generator IDs have implementations.

### Generator runtime (`generators/`)

The Generator Runtime is the resolver and execution layer between presets and
procedural algorithms. `GeneratorFactory` maps a preset's `generator_id` through
an explicit registration table to a `Generator` implementation. A generator
applies parameters, samples its scalar field, runs the core geometry pipeline,
validates the mesh, and returns an immutable `GeneratorResult` containing the
mesh, statistics, warnings, IDs, and elapsed time.

`GyroidGenerator` is the only registered implementation. Sponge is executable;
the reserved IDs used by Coral, Bone, Bark, and Rock remain unavailable. The
runtime uses explicit registration rather than filesystem discovery and does not
introduce `GeneratorDescriptor`.

### Scalar fields and generators (`generators/`)

A scalar field is the mathematical implicit representation of a form. It maps a
three-dimensional point to a scalar value that can be sampled and polygonized.
`GyroidField` is the current implementation and returns `abs(g) - thickness` for
a periodic gyroid sheet.

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

Future commands will coordinate user intent without knowing algorithm classes.
They will obtain a `NaturePreset` through `PresetFactory`, then ask the Generator
Runtime to execute it and hand the resulting mesh to an exporter or adapter.

### Fusion adapter (`fusion/`, future work)

The Fusion Adapter will convert a core `TriangleMesh` into a Fusion `MeshBody`
and own Fusion-specific validation and lifecycle behavior. The adapter is not
implemented yet. Autodesk `adsk` imports must remain outside `presets/`,
`generators/`, and `core/`; they belong only in this adapter, future Fusion
commands, and the add-in entry point.

## Planned pipeline

```text
User / Future Fusion Command
    -> Nature Preset
    -> Generator Runtime
    -> Scalar Field
    -> Voxel Grid
    -> Marching Tetrahedra
    -> Triangle Mesh
        -> STL Export
        -> Future Fusion Adapter
```

1. A user or future Fusion command selects a natural form through a preset.
2. The Generator Runtime resolves the preset's `generator_id` and validated
   parameter values to an implementation.
3. The implementation supplies a scalar field, such as `GyroidField`.
4. The core samples the field into a regular voxel grid.
5. Marching tetrahedra extracts a Fusion-independent indexed triangle mesh.
6. The mesh can be validated, optimized, and exported to STL today; the future
   Fusion Adapter will convert it to a Fusion `MeshBody`.

The sampling, extraction, and mesh stages should use explicit tolerances and
deterministic iteration. Manufacturability checks—such as minimum feature size,
watertightness, and build-volume limits—will be introduced as separate passes so
they do not become implicit side effects of surface extraction.

## Dependency direction

```text
Future Fusion UI
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
The Generator Runtime owns ID resolution, and the future Fusion Adapter depends
on core mesh types rather than the reverse.

These boundaries keep mathematical geometry testable in ordinary Python and
prevent Autodesk runtime concerns from leaking into presets or algorithms.
