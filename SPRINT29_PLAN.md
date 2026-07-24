# Sprint 29 Plan — Noise Displacement Operator

## Status

Implementation complete; awaiting review and real Autodesk Fusion acceptance.

## Goal

Add the first geometry-transforming Procedural Lab operator by displacing
existing mesh vertices along deterministic area-weighted normals.

## Scope

- register `noise_displacement` beside Sprint 28 Pass Through
- add registry-driven Amplitude, Scale, Octaves, Persistence, Lacunarity, and
  Seed controls
- implement dependency-free object-space fractal value noise
- compute safe area-weighted vertex normals in linear time
- preserve vertex/face counts, indices, winding, and component topology
- route Preview and Apply through the existing operator pipeline

## Out of scope

- subdivision, remeshing, smoothing, erosion, voxelization, or SDF conversion
- BRep output, material/UV transfer, texture transfer, or export
- modifier-stack UI or background execution

## Acceptance criteria

- identical meshes and parameters produce identical output digests
- different seeds and shape parameters produce different geometry
- zero Amplitude exactly preserves the input digest
- imported-mesh unusable normals use deterministic finite fallbacks, while
  wholly degenerate meshes and invalid parameters fail clearly
- Pass Through and every Nature Library digest remain unchanged
- Fusion parameter controls are rendered from operator definitions
