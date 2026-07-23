# Sprint 21 Plan — Sponge Preset MVP

## Status

Implementation complete; awaiting review and real Autodesk Fusion acceptance.

## Goal

Promote Sponge from a no-Family PresetCatalog placeholder to the fourth
Registry-driven Nature preset, with a closed deterministic porous mesh.

## Scope

- add immutable `SpongeFamilyDefinition` metadata
- add `SpongeFamilyRegistry`
- register **Classic Sponge** through `PresetDefinition`
- preserve Cell Size, Thickness, Seed, and Resolution controls
- replace the open finite Gyroid sheet with a closed porous Sponge field
- route Preview and OK through `GenerationRequest`
- retain backward-compatible Sponge requests without a Family ID
- verify exact Rock, Bark, and Coral digest compatibility

## Out of scope

- biological sponge growth or species reproduction
- changes to Geometry Core, Marching Tetrahedra, or mesh validation
- changes to GeneratorFactory public APIs
- changes to Preview generation or Fusion mesh insertion
- smoothing, decimation, materials, or texture generation

## Acceptance criteria

- Sponge is associated with `SpongeFamilyRegistry`.
- Fusion shows Classic Sponge in the Family dropdown.
- identical Seeds reproduce identical pores and different Seeds vary them.
- Classic Sponge is finite, watertight, manifold, nondegenerate, and
  single-component.
- existing Rock, Bark, and Coral digests remain unchanged.
- the complete validation suite passes.
- changes remain uncommitted on `feature/sponge-preset-mvp`.
