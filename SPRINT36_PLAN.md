# Sprint 36 Plan — Gyroid Volume Wall Thickness

## Status

Implementation and manual Autodesk Fusion acceptance complete; ready for review.

## Goal

Add optional finite-thickness Gyroid Volume geometry derived from the analytical
scalar field while preserving Sprint 35 Surface output exactly.

## Scope

- add metadata-driven Surface and Thickened geometry modes
- expose Wall Thickness only while Thickened is selected
- derive the physical wall band from the analytical world-space gradient
- sample both wall boundaries in one coordinate traversal
- extract and combine the two deterministic indexed wall surfaces
- close the wall region on rectangular bounds through paired-field clipping
- retain Preview, Apply, Cancel, destroy, and add-in-stop ownership
- charge paired scalar storage and thickened cap complexity to central limits
- measure topology and reject invalid capped or nonmanifold output

## Out of scope

- vertex-normal mesh offsets
- adaptive sampling, remeshing, smoothing, or decimation
- BRep conversion, slicing, print simulation, or printability certification
- changes to Gyroid Surface, Procedural Lab, Generate Nature, or Nature Library
- external numerical dependencies, threads, asynchronous work, or event loops

## Definition of done

- Surface+Open and Surface+Cap retain the exact Sprint 35 default digests
- Thickened+Open produces two deterministic wall sides and remains open at bounds
- Thickened+Cap measures watertight, manifold, consistently wound geometry with
  no degenerate or duplicate faces and positive signed volume
- non-cubic dimensions and independent axis resolutions remain supported
- Wall Thickness, Period, Iso Value, dimensions, resolution, and phase changes
  have deterministic effects
- invalid, under-resolved, all-consuming, and oversized requests fail clearly
- focused and complete warnings-as-errors validation pass
