# Sprint 15 Plan: Rock Family Architecture

## Status

Complete.

Sprint 15 increased the architectural capacity for Rock diversity while
preserving deterministic, watertight, single-component, manufacturable
geometry. Work was delivered in two reviewed phases.

## Phase 1: pipeline foundation

The accepted Sprint 14 Rock scalar field was separated into three immutable,
Fusion-independent stages:

1. Macro Shape
2. Facet Layout
3. Surface Detail

Phase 1 preserved all public parameters, built-in Variants, deterministic
digests, Preview policy, and Final generation behavior. Dedicated stage tests
cover immutability, bounds, determinism, Seed response, and Roughness response.

## Phase 2: first internal family

River Stone was added as the first internal Rock family. It is defined only by
one immutable parameter set for each Phase 1 stage and uses the same field
composition, validation, sampling, extraction, and mesh pipeline as existing
Rock generation.

River Stone remains intentionally absent from the Fusion UI. Its public
selection is deferred to Sprint 16.

## Completed acceptance

- exact Smooth, Weathered, and Rugged regression digests preserved
- deterministic River Stone digest established
- River Stone is rounded, flattened, subtly detailed, and stably grounded
- all tested Rock outputs are finite, nondegenerate, watertight, manifold, and
  single-component
- no River-specific generator, scalar field, mesher, or procedural branch
- no changes to presets, Variants, commands, Preview lifecycle, Fusion API,
  GeneratorFactory, or other generators
- no third-party dependencies
- full automated suite and static validation passed

## Deferred to Sprint 16

- expose Family selection in the Fusion UI
- expose River Stone as a selectable family
- define compatibility between Family and the existing Variant workflow

## Out of scope

- Granite, Basalt, Limestone, Broken Rock, or other additional families
- geological or erosion simulation
- smoothing, decimation, materials, or textures
- changes to Preview and Final generation behavior

See [`docs/SPRINT15_DESIGN.md`](docs/SPRINT15_DESIGN.md) for the complete
architecture and validation record.
