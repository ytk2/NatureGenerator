# Sprint 33 Plan — Gyroid Surface Operator

## Status

Implementation complete; awaiting review and manual Autodesk Fusion acceptance.

## Goal

Add the first TPMS-inspired Procedural Lab operator as a deterministic
topology-preserving surface deformation that works alone or in the three-slot
Operator Stack.

## Scope

- register Gyroid Surface through the existing operator registry
- evaluate the analytical gyroid field in object space
- concentrate normal displacement around a smooth configurable isovalue band
- expose Period, Amplitude, Threshold, Band Width, three phases, and Invert
- preserve vertex and face counts, connectivity, winding, components, units,
  provenance, and source immutability
- reuse robust normals, stack execution, Preview ownership, and Apply insertion
- validate open, closed, subdivided, and partly degenerate triangle meshes
- extend Midpoint Subdivision to Levels 1–5 for finer surface sampling
- reject predicted subdivision outputs above the centralized 500,000-face
  Preview limit or 1,000,000-face Apply limit before allocation

## Out of scope

- volumetric TPMS solids or infill
- voxelization, Marching Cubes, booleans, hollowing, or perforation
- topology changes or intermediate stack bodies
- operator-specific Fusion UI branches
- external numerical dependencies or background execution

## Definition of done

- all Gyroid parameters produce deterministic and meaningful changes
- zero Amplitude is exact identity and signed Amplitudes move oppositely
- mixed Subdivision, Noise, and Voronoi chains execute in either useful order
- Preview and Apply continue to insert only the final stack result
- full warnings-as-errors validation and a representative dense-mesh benchmark
  pass
- manual Fusion checklist is ready for execution
