# Sprint 35 Plan — Gyroid Volume Boundary Closure

## Status

Implementation complete; awaiting review and manual Autodesk Fusion acceptance.

## Goal

Add an optional, measured watertight boundary closure to Gyroid Volume while
preserving Sprint 34's Open output byte-for-byte and leaving every other command
and generator unchanged.

## Scope

- add metadata-driven Open and Cap boundary modes, with Open as the default
- keep scalar sampling and marching-tetrahedra extraction unchanged
- classify and validate extracted contours on all six rectangular faces
- deterministically triangulate the scalar-domain region on each box face
- share boundary vertices, reject malformed topology, and validate the result
- enforce separate Preview and Apply cap-complexity limits before closure
- preserve independent Preview, Apply, Cancel, destroy, and stop ownership

## Out of scope

- wall thickness, shells, offsets, infill, or BRep solid conversion
- arbitrary-mesh repair or general-purpose hole filling
- changes to Gyroid Surface, Procedural Lab, or Nature Library generators
- external numerical libraries, threads, asynchronous work, or event loops

## Definition of done

- the Open default retains the exact Sprint 34 focused and default digests
- Cap produces deterministic, finite, consistently wound indexed geometry
- representative Cap results measure zero boundary, nonmanifold, winding, and
  degenerate defects and report nonzero signed volume
- non-cubic dimensions and independent axis resolutions remain supported
- invalid, self-intersecting, or nonmanifold closures are rejected explicitly
- full warnings-as-errors validation and repository hygiene checks pass
