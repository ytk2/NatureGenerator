# Sprint 37 Plan — Gyroid Volume Preview Optimization

## Status

Implementation complete; manual Autodesk Fusion acceptance remains unchecked.

## Goal

Improve independent Gyroid Volume Preview responsiveness and diagnostics while
preserving Sprint 36 final-resolution geometry and Apply quality.

## Scope

- add metadata-driven Draft, Standard, and Final Preview Quality
- resolve deterministic effective Preview resolution without changing UI values
- estimate scalar, cell, cap, and known grid-memory costs before allocation
- apply centralized safety limits to the effective execution resolution
- measure core generation stages and Fusion insertion separately
- log a concise non-modal completion summary
- preserve all Surface/Thickened and Open/Cap geometry paths

## Out of scope

- asynchronous execution, cancellation, threads, or event-loop pumping
- adaptive octrees, GPU execution, remeshing, smoothing, or decimation
- changes to Gyroid mathematics, extraction, closure, or output naming
- Fusion MeshBody caching or cross-command cache ownership

## Definition of done

- Apply and Final Preview use the exact requested final resolution
- Final Preview preserves all four Sprint 36 40³ geometry digests
- Draft and Standard scale each axis predictably and never below eight
- generation cost and safety use the same effective resolution as sampling
- rejected requests allocate no scalar grid and leave no owned Preview
- immutable timings expose every required core stage
- focused and complete warnings-as-errors validation pass
- no generated meshes, benchmark artifacts, or caches are tracked
