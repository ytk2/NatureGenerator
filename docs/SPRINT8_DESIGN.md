# Sprint 8 — First Multi-Generator Architecture

## Goal

Add the first second executable natural form while preserving the public
Fusion-independent runtime API and the existing Sponge behavior.

A user should be able to select either Sponge or Coral in Generate Nature and
receive geometry from the corresponding runtime generator.

## Architecture

```text
Fusion Generate Nature command
    -> GenerationRequest(preset_id, overrides, resolution)
    -> GeneratorFactory
        -> PresetFactory
        -> explicit generator registration
            -> sponge -> SpongeGenerator -> existing GyroidGenerator
            -> coral          -> CoralGenerator
    -> GeneratorResult
        -> TriangleMesh
        -> validation and statistics
    -> Fusion Adapter
    -> MeshBody
```

The command submits a stable preset ID and shared parameter overrides. It does
not import, instantiate, or branch on concrete generator implementations.
`GeneratorFactory` resolves the preset and its stable `generator_id` through
explicit registration; it does not scan modules or use an `if`/`elif` dispatch
chain.

The public `GeneratorFactory.generate(preset, parameters)` and
`GeneratorFactory.generate_request(request)` entry points continue returning an
immutable `GeneratorResult`. Preset-selected generators implement
`generate(request) -> TriangleMesh`; the factory validates that mesh and builds
the public result. `SpongeGenerator` is a thin adapter around the unchanged
`GyroidGenerator` pipeline. This retains the v0.5.0 runtime contract while
allowing preset-ID-based selection.

## Coral Generator

`CoralGenerator` samples a signed-distance field formed from a connected union
of overlapping capsules. The result is a closed branching solid that is
visually and topologically distinct from the open, periodic Sponge gyroid.

- Cell Size scales the complete coral form in millimeters.
- Thickness controls relative branch radius.
- Resolution controls voxel samples per axis.
- All branches remain inside the sampled domain.
- Watertight validation is required before a result is returned.

The implementation reuses `VoxelGrid`, Marching Tetrahedra, `TriangleMesh`,
`MeshValidator`, mesh statistics, `GeneratorResult`, and the existing Fusion
MeshBody adapter. It introduces no parallel mesh implementation.

## Preset and Factory Changes

- Coral becomes available with `generator_id="coral"`.
- Sponge remains available with `generator_id="gyroid"`.
- Bone, Bark, and Rock remain unavailable and retain clear reasons.
- `GeneratorFactory.create_for_preset(preset_id)` provides explicit preset-ID
  resolution while the existing generator-ID factory method remains compatible.
- `SpongeGenerator` and `CoralGenerator` share the request-to-mesh contract;
  the existing `GyroidGenerator` remains the Sponge implementation.

## Fusion Behavior

The preset dropdown presents both **Sponge** and **Coral** without a Coming Soon
suffix. Selecting either form creates the same immutable `GenerationRequest`;
the runtime selects the implementation. Cell Size, Thickness, and Resolution
remain the shared command inputs.

No preview, live parameter update, or command-layout redesign is included.

## Dependency Boundaries

- `core/`, `generators/`, `presets/`, and `commands/` must not import `adsk`.
- Fusion APIs remain inside `fusion/` and the add-in lifecycle boundary.
- Presets contain metadata and stable IDs, not implementation imports.
- Generator registration is explicit and deterministic.
- No NumPy or third-party dependency is introduced.

## Out of Scope

- Gray-Scott reaction diffusion
- Voronoi, noise, or cellular generators
- Bone, Bark, or Rock execution
- Preview and live updates
- Progress and cancellation
- GPU or performance optimization
- New Fusion command placement or UI redesign

## Definition of Done

- [x] Coral is available in the built-in preset registry.
- [x] GeneratorFactory resolves Sponge and Coral by preset ID.
- [x] Sponge behavior and public runtime APIs remain compatible.
- [x] Coral creates a non-empty, manifold, watertight `TriangleMesh`.
- [x] Cell Size, Thickness, and Resolution affect Coral generation.
- [x] Fusion lists Sponge and Coral without duplicate controls.
- [x] Selecting Coral routes a Coral request through the command layer.
- [x] Full unit test suite passes.
- [x] Python compilation passes.
- [x] `git diff --check` passes.
- [x] Fusion dependency-boundary scan passes.
- [x] Real Fusion acceptance test is ready to run.

## Fusion Acceptance Checklist

- [x] Add-in loads without startup errors.
- [x] Generate Nature appears once.
- [x] Preset dropdown contains Sponge and Coral.
- [x] Neither Sponge nor Coral is marked Coming Soon.
- [x] Sponge still generates successfully.
- [x] Coral generates a visually distinct branching MeshBody.
- [x] Coral has no visible open crop boundary.
- [ ] Cell Size changes Coral scale.
- [ ] Thickness changes Coral branch radius.
- [ ] Resolution changes Coral mesh density.
- [x] Switching repeatedly between presets selects the correct generator.
- [ ] Cancel creates no geometry during the Sprint 8 acceptance session.
- [x] Stopping and restarting the add-in creates no duplicate controls.

Unchecked parameter and cancellation cases were not exhaustively exercised in
the Sprint 8 acceptance session and remain suitable regression checks.

## Real Fusion Acceptance

- tested successfully on macOS Autodesk Fusion
- Coral preset displayed correctly without Coming Soon.
- Coral created a Fusion `MeshBody` named `NatureGenerator Coral`.
- The observed run produced 820 vertices and 1,636 faces in approximately
  0.148 seconds.
- Coral was visually distinct from Sponge.
- Sponge and Coral routed to their respective generators.
- Sponge behavior remained unchanged.
- No duplicate command controls appeared.
- Startup diagnostics and package bootstrapping continued to work.

This acceptance result covers the observed configuration. It does not claim
that every Cell Size, Thickness, and Resolution combination was tested.
