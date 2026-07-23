# Sprint 19 Plan — Bark Preset MVP

## Status

Implementation complete; awaiting review and real Autodesk Fusion acceptance.

## Goal

Promote Bark from a no-Family Sprint 18 placeholder to the first non-Rock
preset registered through the generic Preset Registry architecture.

## Existing foundation

The deterministic capped Bark generator, seven Bark parameters, metadata-driven
Fusion inputs, Preview/OK execution, and topology validation were delivered
before Sprint 19. This Sprint reuses that accepted implementation rather than
creating a competing Bark algorithm.

## Scope

- add immutable `BarkFamilyDefinition` metadata
- add `BarkFamilyRegistry`
- register Bark through `PresetDefinition` in `PresetCatalog`
- expose one initial **Classic Bark** Family
- preserve Diameter, Height, Bark Depth, Groove Scale, Twist, Seed, and
  Resolution
- route Bark Family Preview and OK through the existing request and generator
  pipeline
- retain backward-compatible Bark requests without a Family ID
- add exact Bark digest, topology, Registry, Preview, OK, and Rock regression
  coverage

## Out of scope

- geometry-core or Marching Tetrahedra changes
- GeneratorFactory API changes
- new Bark algorithms or parameters
- species-specific bark
- cracks, plates, peeling, knots, branches, roots, or full trees
- materials, smoothing, decimation, or live Preview

## Acceptance criteria

- Bark is no longer a no-Family PresetCatalog placeholder.
- Bark displays Classic Bark in the existing Family control.
- Preview and OK carry `classic_bark` through `GenerationRequest`.
- Classic Bark exactly matches the accepted default Bark mesh.
- Bark remains deterministic, finite, watertight, manifold, nondegenerate,
  capped, and single-component.
- all seven Rock Family digests remain unchanged.
- the complete validation suite passes.
- changes remain uncommitted on `feature/bark-preset-mvp`.
