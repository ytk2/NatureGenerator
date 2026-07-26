# Sprint 38 Plan — TPMS Family

## Status

Implementation and manual Autodesk Fusion acceptance are complete.

## Goal

Generalize the independent volume generator from Gyroid-only construction to a
registry-driven TPMS family while preserving every released Gyroid result and
Preview/Apply behavior.

## Scope

- add Gyroid, Schwarz P, Diamond/Schwarz D, and Neovius stable TPMS types
- add one analytical TPMS field factory and shared field contract
- retain the original Gyroid field implementation for exact compatibility
- generalize scalar-field wall thickening to every TPMS type
- support Surface/Thickened and Open/Cap for all types
- retain Sprint 37 Preview Quality, estimates, safety, and timings
- rename the user-facing command to TPMS Volume while preserving its command ID
- add type-aware Preview, permanent body names, and diagnostics
- retain backward-compatible Gyroid request and generation APIs

## Out of scope

- additional TPMS types, arbitrary-body clipping, runtime caching, export UI
- adaptive sampling, GPU execution, threads, asynchronous execution
- smoothing, remeshing, decimation, BRep conversion, or simulation
- changes to the Gyroid Surface deformation operator

## Definition of done

- all four fields and analytical gradients pass mathematical reference tests
- all sixteen type/mode/boundary combinations are deterministic
- representative Thickened+Cap fixtures measure watertight and manifold
- all four released 40³ Gyroid digests remain unchanged
- Final Preview and Apply remain identical
- metadata, lifecycle, names, diagnostics, estimates, and errors include type
- focused and complete warnings-as-errors validation pass
- changes remain uncommitted and unpushed for review
- exact Phase X `0.12566` boundary-sliver regression closes cleanly without
  changing released or canonical default digests
- exact Schwarz P zero-isovalue ambiguity is resolved during deterministic
  sample classification at 20³, 30³, and 40³ without changing canonical digests
