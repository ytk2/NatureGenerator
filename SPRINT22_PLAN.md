# Sprint 22 Plan — Generated Asset and Export Architecture

## Status

Implementation complete; awaiting review.

## Goal

Evolve the generation result from geometry-only output into a renderer-neutral
natural asset while preserving every generator's exact mesh.

## Scope

- add immutable generated-asset, material, mapping, texture, and provenance
  models
- retain the existing `TriangleMesh` as the only mesh representation
- compose a `GeneratedAsset` after existing mesh generation and validation
- preserve `GeneratorResult.mesh` and all current Fusion consumers
- establish explicit future export request, result, adapter, and registry
  contracts
- document dependency direction and exclusions

## Out of scope

- production OBJ/MTL, glTF/GLB, USD/USDZ, or new STL asset exporters
- UV generation or unwrapping
- triplanar or cylindrical projection algorithms
- procedural texture evaluation or texture baking
- renderer, game-engine, or Fusion appearance integration
- any generator, scalar field, mesh extraction, or topology changes

## Acceptance criteria

- every generated result contains a complete `GeneratedAsset`
- `result.asset.mesh is result.mesh`
- material and mapping definitions contain no host or format types
- object-space procedural mapping is explicit
- the texture set is valid and empty until a baker supplies resources
- generation identity, parameters, unit, and schema version are immutable
- exporter lookup is explicit and an unregistered format fails clearly
- existing automated geometry and Fusion-independent command tests pass
