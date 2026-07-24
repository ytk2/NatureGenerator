# Sprint 31 Plan — Voronoi Surface Operator

## Status

Implementation complete; awaiting review and real Autodesk Fusion acceptance.

## Goal

Add Procedural Lab's first cell-based deformation using deterministic
object-space Voronoi boundaries.

## Scope

- register `voronoi_surface` beside Pass Through, Noise Displacement, and
  Subdivision
- expose Cell Size, Depth, Edge Width, Falloff, Jitter, and Seed metadata
- evaluate nearest and second-nearest sites from a local virtual lattice
- displace existing vertices along robust area-weighted normals
- preserve connectivity, winding, components, boundary topology, and units
- reuse the existing Preview, Apply, registry, and operator pipeline

## Out of scope

- volumetric Voronoi, cell extraction, holes, cuts, booleans, or separate cells
- remeshing, subdivision, voxelization, SDF conversion, or Lloyd relaxation
- material, UV, texture, or per-face attribute transfer

## Acceptance criteria

- identical input and parameters produce identical output digests
- different Seeds and pattern parameters change geometry deterministically
- Depth zero exactly preserves the input digest
- local site search matches a wider reference on tested domains
- positive and negative Depth move in opposite normal directions
- all topology and prior-operator regressions remain green
