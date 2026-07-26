# Sprint 34 Plan — TPMS Gyroid Volume Foundation

## Status

Implementation complete; awaiting review and manual Autodesk Fusion acceptance.

## Goal

Add the first true scalar-field-generated TPMS mesh as a third independent
Fusion command, without changing Gyroid Surface, Procedural Lab, or Generate
Nature.

## Scope

- add immutable Gyroid Volume request, parameter metadata, result, and safety
  contracts
- sample the analytical Gyroid field on an inclusive regular voxel grid
- extract a deterministic indexed mesh with marching tetrahedra
- clip the mathematically correct surface open at centered rectangular bounds
- report measured mesh topology rather than claiming watertight output
- add independent Preview, Apply, Cancel, destroy, and add-in-stop ownership
- reject oversized requests before voxel allocation

## Out of scope

- capping or thickening the clipped surface
- watertight TPMS solids, shells, infill, or booleans
- material assignment or source-body interaction
- external numerical libraries, threads, asynchronous work, or event loops
- changes to the Gyroid Surface operator or Operator Stack

## Definition of done

- deterministic field, sampling, extraction, and indexed-mesh digest
- all eleven parameters are metadata-driven and validated
- Preview and Apply use distinct centralized sample limits
- representative output is finite, oriented, nondegenerate, manifold, and
  accurately reported open at the bounds
- independent Fusion lifecycle and all existing product-surface regressions pass
- full warnings-as-errors validation and dependency scans pass
