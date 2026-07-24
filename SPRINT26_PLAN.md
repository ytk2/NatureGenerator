# Sprint 26 Plan — Crystal Preset MVP

## Status

Implementation complete; awaiting review and real Autodesk Fusion acceptance.

## Goal

Introduce Crystal as the second major inorganic natural-object generator after
Rock, using the existing Family Registry, GeneratedAsset, Preview, and Fusion
insertion architecture.

## Scope

- add the available Crystal preset and focused parameter metadata
- add immutable `CrystalFamilyDefinition` and `CrystalFamilyRegistry`
- register **Classic Crystal** as `classic_crystal`
- add a deterministic faceted `CrystalGenerator`
- produce an elongated irregular prism with a tapered point termination
- register Crystal with `PresetCatalog` and `GeneratorFactory`
- add renderer-neutral crystal material intent
- validate topology, parameters, deterministic digest, Preview, OK, and assets

## Out of scope

- photorealism, refraction, transparency, inclusions, or mineral simulation
- crystal clusters, branching growth, or multiple Crystal Families
- export formats, texture baking, UV coordinates, smoothing, or decimation
- Geometry Core, GeneratedAsset model, exporter, or Preview lifecycle changes

## Acceptance criteria

- Classic Crystal is recognizable as an elongated faceted crystal
- Length, Width, Facet Count, Taper, Irregularity, Seed, and Resolution each
  have a meaningful geometric effect
- identical requests are deterministic and Seed changes the geometry
- output is finite, closed, manifold, watertight, consistently wound,
  nondegenerate, and single-component
- Crystal uses the generic Family dropdown, Preview, and OK workflows
- GeneratedAsset uses the existing mesh, object-space mapping, empty texture
  set, provenance metadata, and renderer-neutral material definition
- every pre-existing geometry digest remains unchanged
- all automated validation passes
