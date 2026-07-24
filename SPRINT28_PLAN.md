# Sprint 28 Plan — Procedural Lab Foundation

## Status

Implementation complete; awaiting review and real Autodesk Fusion acceptance.

## Goal

Establish a second, independent product surface that applies registered
procedural operators to one existing Fusion solid or mesh.

## Scope

- register a standalone **Procedural Lab** Fusion command
- validate and adapt one `BRepBody` or `MeshBody` into the existing
  `TriangleMesh`
- add immutable input, request, result, operator, registry, and pipeline
  contracts
- register only the deterministic **Pass Through** operator
- provide command-owned Preview and permanent Apply/OK insertion
- preserve the source and all Nature Library behavior

## Out of scope

- Gyroid, Voronoi, noise, reaction-diffusion, remeshing, voxelization, or SDF
  operations
- modifier-stack UI, BRep output, material/UV transfer, texture baking, or
  export
- changes to presets, Families, generators, or existing geometry

## Acceptance criteria

- adapted input and Pass Through output have identical canonical mesh digests
- winding, bounds, connected components, manifold state, and watertight state
  are preserved
- Preview replacement and cleanup affect only the current Procedural Lab
  command
- the procedural core imports no Autodesk modules
- existing Nature Library tests and geometry digests remain unchanged
