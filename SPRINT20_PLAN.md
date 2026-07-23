# Sprint 20 Plan — Coral Preset MVP

## Status

Implementation complete; awaiting review and real Autodesk Fusion acceptance.

## Goal

Promote Coral from a no-Family Sprint 18 placeholder to the first branching
natural object registered through the generic Preset Registry architecture.

## Existing foundation

The closed connected Coral capsule-union generator, Cell Size and Thickness
controls, metadata-driven Fusion inputs, Preview/OK execution, and topology
validation existed before Sprint 20. This Sprint preserves the accepted Seed 0
geometry and adds Registry and deterministic Seed support.

## Scope

- add immutable `CoralFamilyDefinition` metadata
- add `CoralFamilyRegistry`
- register **Classic Coral** through `PresetDefinition`
- add a Seed parameter while preserving existing Coral parameters
- keep Seed 0 byte-for-byte compatible with the accepted Coral mesh
- add deterministic shared-node branch variation for nonzero Seeds
- route Preview and OK through `GenerationRequest`
- retain backward-compatible Coral requests without a Family ID
- verify exact Rock and Bark digest compatibility

## Out of scope

- geometry-core, Scalar Field framework, or Marching Tetrahedra changes
- GeneratorFactory public API changes
- disconnected colonies or separate fragments
- biological growth simulation
- species reproduction, materials, smoothing, or decimation

## Acceptance criteria

- Coral is no longer a no-Family PresetCatalog placeholder.
- Fusion shows Classic Coral in the existing Family dropdown.
- Cell Size, Thickness, Seed, and Resolution remain metadata-driven.
- Preview and OK carry `classic_coral`.
- Seed 0 preserves the accepted Coral digest.
- identical Seeds are deterministic and different Seeds alter branch geometry.
- all tested Coral meshes are finite, watertight, manifold, nondegenerate, and
  single-component.
- all seven Rock Family digests and Classic Bark digest remain unchanged.
- the complete validation suite passes.
- changes remain uncommitted on `feature/coral-preset-mvp`.
