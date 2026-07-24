# Sprint 25 Plan — Rock Family Expansion

## Status

Implementation complete; awaiting review and real Autodesk Fusion acceptance.

## Goal

Expand Rock with Classic Rock, Layered Rock, Weathered Rock, and River Rock
while preserving every existing Rock and non-Rock geometry digest.

## Scope

- expose the accepted default geometry as **Classic Rock**
- add immutable Layered Rock, Weathered Rock, and River Rock definitions
- register all four through `RockFamilyRegistry`
- add optional horizontal strata to the existing Surface Detail stage
- preserve Smooth, Weathered, Rugged, River Stone, Granite, Basalt, and Broken
  Rock as backward-compatible Family IDs
- use the generic Family dropdown, Preview, OK, request, and asset workflows
- validate deterministic generation and manufacturable topology

## Out of scope

- new presets or a new generator architecture
- preset-specific Fusion or command branches
- Geometry Core, Marching Tetrahedra, GeneratedAsset, or exporter changes
- erosion simulation, fluid simulation, smoothing, or decimation
- texture baking or UV mapping

## Acceptance criteria

- Classic Rock has the accepted canonical digest
- all seven previously selectable Rock Family digests remain unchanged
- Layered Rock has horizontally stratified, broken edges
- Weathered Rock has a soft silhouette with strong broad erosion
- River Rock is rounded, worn, low-frequency, and minimally faceted
- each new mesh is finite, closed, manifold, watertight, nondegenerate, and
  single-component with zero boundary edges
- identical requests repeat exactly and Seed changes the result
- Fusion Preview and OK remain generic and Family-driven
- all non-Rock regression digests and GeneratedAsset behavior remain unchanged
- all automated validation passes
