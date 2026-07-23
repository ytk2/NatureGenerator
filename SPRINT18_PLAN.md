# Sprint 18 Plan — Preset Registry Architecture

## Status

Implementation complete; awaiting review.

## Goal

Generalize the Registry-driven Family presentation proven by Rock into a
preset-level catalog without changing generator algorithms, geometry, request
execution, Preview, or Final insertion.

## Scope

- add an immutable `PresetDefinition` that associates existing
  `NaturePreset` metadata with an optional Family registry
- compose all built-in presets in one application-level `PresetCatalog`
- register `RockFamilyRegistry` through that catalog
- represent Bark, Coral, Sponge, Root, and Bone as explicit no-Family
  placeholders
- make Fusion Family selection consume only the generic catalog contract
- preserve `PresetFactory`, `GeneratorFactory`, and `GenerationRequest` APIs
- preserve the current Fusion control labels, ordering, visibility, and
  behavior
- add architecture, boundary, UI, and digest regression coverage

## Out of scope

- new generators, presets, families, or controls
- Bark, Coral, Sponge, or Root Family definitions
- geometry, scalar-field, mesh, topology, or sampling changes
- Preview policy or command-lifecycle changes
- GeneratorFactory registration changes
- migration of Rock stage parameters out of the Rock generator layer

## Acceptance criteria

- Fusion has no direct `RockFamilyRegistry` dependency.
- Rock remains the only preset with a Family selector.
- All other presets retain their current Variant workflow.
- all seven Rock families retain their exact deterministic digests
- Preview and Final behavior remain unchanged
- the complete validation suite passes with warnings treated as errors
- changes remain uncommitted on `feature/preset-registry`

## Known risks

- The application catalog is a deliberate composition root that imports both
  preset metadata and the Rock Family registry. Moving this dependency into
  `presets/` would invert the existing preset-to-generator boundary.
- Family definitions still contain preset-specific parameter bundles. A future
  preset may require a different concrete Family definition while conforming
  to the same UI-facing registry shape.
- Placeholder presets intentionally expose no Family UI until reviewed Family
  registries exist.
