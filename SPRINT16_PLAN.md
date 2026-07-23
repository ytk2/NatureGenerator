# Sprint 16 Plan: Fusion Rock Family Selection

## Status

Complete. Phase 1 passed automated validation and manual Autodesk Fusion 360
acceptance.

## Objective

Expose the Sprint 15 Rock Family architecture to Autodesk Fusion users while
preserving Preview, Final generation, saved/default behavior, and existing
Rock results.

## Initial goals

- Add a metadata-driven Family selection input for Rock in the Fusion UI.
- Make Family the primary Rock configuration workflow instead of the current
  Variant-centric presentation.
- Expose the existing default Rock family and River Stone as selectable
  families.
- Keep explicit Preview dispatch, adaptive Preview resolution, preview
  replacement, Final generation, Cancel cleanup, and command lifecycle
  unchanged.
- Preserve full backward compatibility for existing Rock parameters and the
  Smooth, Weathered, Rugged, and Custom configurations.
- Keep family selection out of concrete geometry logic: the selected stable
  family ID must resolve through the Rock Family registry and then use the
  existing three-stage pipeline.

## Phase 1 implementation

- replace the Rock Variant dropdown with a Registry-driven Family dropdown
- expose Smooth, Weathered, Rugged, and River Stone
- keep Variants available for non-Rock presets
- carry the stable family ID in the immutable `GenerationRequest`
- preserve family identity when deriving the lower-density Preview request
- route both Preview and Final through `GeneratorFactory.generate_request`
- retain Size, Roughness, Seed, Resolution, Preview, OK, and Cancel
- add UI, request, digest, topology, and lifecycle regression tests

## Design decisions

- Define the user-facing names and ordering for the default family and River
  Stone in `RockFamilyRegistry`, not in Fusion.
- Smooth, Weathered, and Rugged retain their accepted parameter values and use
  the default Sprint 15 stage configuration.
- River Stone retains its Sprint 15 stage configuration and digest.
- Manual parameter edits retain the selected Family and alter only the exposed
  parameter values.
- Requests without a family ID continue to use the accepted default Rock
  definition.
- Unknown family IDs are rejected by the Registry before mesh extraction.

## Required regression coverage

- existing requests without a family select the accepted default Rock family
- Smooth, Weathered, Rugged, and Custom digests remain unchanged
- River Stone remains deterministic, watertight, manifold, and
  single-component
- Preview and Final use the same family and parameter values
- Preview density remains the only Preview/Final geometry difference
- preset switching, manual edits, OK, Cancel, destroy, and add-in stop retain
  their current behavior
- Sponge, Coral, Bark, Root, and Bone availability are unaffected

## Out of scope

- No new Rock family beyond River Stone.
- No changes to Macro Shape, Facet Layout, or Surface Detail algorithms.
- No changes to mesh extraction, smoothing, decimation, or export.
- No automatic/live Preview, background work, progress, or cancellation.

## Acceptance

Manual Autodesk Fusion 360 validation confirmed:

- Rock displays the Family dropdown.
- Smooth, Weathered, Rugged, and River Stone appear once in the expected order.
- Preview updates when switching families.
- River Stone Preview generates correctly.
- existing Rock family geometry remains unchanged.
- the UI layout is correct.
- no Fusion runtime errors were observed.

Sprint 16 is complete. Additional Rock diversity work is deferred to Sprint 17.
