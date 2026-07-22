# Sprint 7 — Interactive Generation Command

## Goal

Replace the fixed **Generate Sponge** demonstration with one interactive
**Generate Nature** command. A user selects a natural-form preset, adjusts the
available Sponge parameters and sampling resolution, and creates a Fusion
`MeshBody` through the existing generation pipeline.

```text
Fusion Generate Nature Command
    -> GenerationRequest
    -> PresetFactory
    -> GeneratorFactory
    -> GyroidGenerator
    -> TriangleMesh
    -> Fusion Adapter
    -> MeshBody
```

## Architecture

`GenerationRequest` is the Fusion-independent data contract between UI intent
and the Generator Runtime. It identifies a preset, carries immutable parameter
overrides, and specifies samples per axis. `GeneratorFactory` resolves the
preset and generator; `GyroidGenerator` uses the request resolution when
sampling its `VoxelGrid`. The Fusion command constructs the request from dialog
values and gives the resulting `TriangleMesh` to the existing
`MeshBodyBuilder`.

The legacy `GeneratorFactory.generate(preset, parameters)` API remains available
and uses the former 17-sample resolution. New code should use
`GeneratorFactory.generate_request(request)`.

## Deliverables

- An immutable `GenerationRequest` with defensive parameter storage.
- Configurable resolution in the Generator Runtime.
- A Fusion **Generate Nature** command with preset, cell-size, thickness, and
  resolution inputs.
- Explicit unavailable-preset behavior with no geometry side effects.
- Reusable Fusion-independent generation orchestration.
- Updated automated tests and user/architecture documentation.

## Input Model

The command dialog contains:

- **Preset:** all built-in presets from `PresetFactory`; unavailable choices are
  labelled “Coming Soon.”
- **Cell Size:** physical length of one gyroid period in millimeters. Its default
  and bounds come from Sponge parameter metadata.
- **Thickness:** dimensionless isosurface offset around the gyroid surface. Its
  default and bounds come from Sponge parameter metadata.
- **Resolution:** integer samples per axis. The default is 17, matching the
  Sprint 5–6 runtime.

Selecting an unavailable preset is allowed for discoverability, but execution
reports its `unavailable_reason` and creates no geometry.

## Validation Rules

- `preset_id` must be a stable non-empty identifier known to `PresetFactory`.
- Parameter overrides must be a mapping of string IDs to immutable scalar
  values and are copied into a read-only mapping.
- `cell_size` must be finite, numeric, greater than zero, and within Sponge's
  metadata bounds of 1–100 mm.
- `thickness` must be finite, numeric, and within Sponge's metadata bounds of
  0–1.
- `resolution` must be an integer from 9 through 41 inclusive; booleans are not
  integers for this contract.

The 9–41 range is conservative for dependency-free Python inside Fusion.
Runtime cost and memory grow cubically: 41 samples per axis is about 14 times
the sample count of the 17-sample default. This range permits visibly different
mesh density without exposing accidentally extreme workloads.

Validation completes before voxel sampling and before the Fusion Adapter is
called. Any invalid or unavailable request displays a useful message and leaves
the active design unchanged.

## Fusion Event Lifecycle

1. Add-in `start` resolves or creates one stable command definition and toolbar
   control.
2. The `commandCreated` handler creates all four inputs from preset/runtime
   defaults and retains one execute handler for that command instance.
3. The execute handler reads the final input values, constructs a
   `GenerationRequest`, runs the Generator Runtime, and inserts the completed
   mesh.
4. Cancel does not fire the execute event and therefore creates no request or
   geometry.
5. Repeated command instances receive independent execute handlers. Add-in
   start reuses existing definitions and controls, while stop deletes them and
   clears retained handler references.

All `adsk` imports and Fusion input objects remain in `fusion/`. The entry point
retains only its existing fatal-diagnostic import and `__file__`-relative path
bootstrap. Core, presets, generators, and commands remain Fusion-independent.

## Required API Migration

- Replace `commands.generate_sponge.generate_sponge` with a general request
  executor; do not leave a misleading Sponge-only public command API.
- Rename the stable command definition and visible command to Generate Nature.
- Replace `GyroidGenerator._SHAPE` with validated request resolution.
- Preserve `GeneratorFactory.generate(preset, parameters)` as a compatibility
  wrapper using resolution 17.
- Keep scalar-field, voxel, extraction, validation, and adapter implementations
  unchanged and reused.

## Out of Scope

- Live preview
- Progress bar
- Voronoi
- Gray-Scott
- New natural-form generators
- GPU or parallel processing
- Smoothing or decimation
- Advanced UI styling
- Animation

## Known Follow-up

The command currently remains in Fusion's generic Utilities Add-Ins panel. A
future UI-integration Sprint should move NatureGenerator to a dedicated
Utilities panel or a more direct Utilities placement. That placement change is
not part of Sprint 7.

## Definition of Done

- [x] Generate Nature appears in Fusion.
- [x] The dialog shows preset, cell size, thickness, and resolution inputs.
- [x] Sponge defaults come from `PresetFactory` and current runtime defaults.
- [x] Valid overrides create a `MeshBody`.
- [x] Unavailable and invalid requests create no geometry and explain why.
- [x] Cancel creates no geometry.
- [x] Resolution changes mesh density.
- [x] Repeated command execution and add-in lifecycle do not duplicate UI.
- [x] Startup logging, traceback diagnostics, and loader bootstrap are preserved.
- [x] Geometry and runtime layers remain Fusion-independent.
- [x] Full tests, compilation, diff, dependency, documentation, and artifact
  checks pass.
- [x] Real Fusion 360 acceptance completed successfully on macOS, including
  resolution 41.
