# Release History

This history is maintained on the current development branch. Release tags are
immutable recovery points; later documentation updates describe those releases
without becoming part of their tagged commits.

## v0.5.0 — Interactive Generation Command

**Status:** Current stable baseline

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
