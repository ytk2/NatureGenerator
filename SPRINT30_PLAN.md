# Sprint 30 Plan — Subdivision Operator

## Status

Implementation complete; awaiting review and real Autodesk Fusion acceptance.

## Goal

Add Procedural Lab's first topology-changing operator so later surface
operators can work with denser triangle meshes.

## Scope

- register `subdivision` beside Pass Through and Noise Displacement
- expose registry-defined Subdivision Level values 1–3
- split every triangle into four using shared edge midpoints
- preserve the piecewise-linear surface, winding, components, manifold state,
  units, and source provenance
- reuse the existing Preview, Apply, registry, and operator pipeline

## Out of scope

- smoothing, relaxation, projection, curvature-aware refinement, or decimation
- Loop or Catmull-Clark subdivision
- adaptive subdivision or a modifier-stack UI
- changes to Nature Library, Fusion tessellation, or MeshBody insertion

## Acceptance criteria

- every level multiplies face count by four
- adjacent faces reuse exactly one midpoint for their shared edge
- levels 1–3 are deterministic and non-recursive
- closed manifold and disconnected/open topology remain consistent
- Pass Through, Noise Displacement, and Nature Library regressions remain green
- Preview replacement and Apply use the existing command lifecycle
