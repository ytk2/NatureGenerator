# Sprint 23 Plan — Complete Family Registry Migration

## Status

Implementation complete; automated validation and real Autodesk Fusion
acceptance passed.

## Goal

Migrate the final implemented legacy preset to the registry-driven Family
architecture so every executable preset follows one generation flow.

## Existing foundation

Rock, Bark, Coral, and Sponge already provide immutable Family definitions and
registries through `PresetCatalog`. Root is implemented and deterministic but
previously remained a no-Family placeholder. Bone is unavailable because its
generator has not been implemented.

## Scope

- add immutable `RootFamilyDefinition`
- add `RootFamilyRegistry`
- register **Classic Root**
- associate Root with its registry through `PresetCatalog`
- resolve Root Family metadata in `RootGenerator`
- expose Root through the generic Fusion Family dropdown
- carry `classic_root` through Preview and OK requests
- preserve requests without a Family ID
- preserve Root mesh identity inside `GeneratedAsset`
- document completion of the implemented-preset migration

## Out of scope

- new presets or Bone implementation
- new Root geometry, parameters, Families, or growth behavior
- Geometry Core, Marching Tetrahedra, GeneratedAsset, or export changes
- Fusion Preview lifecycle changes
- removal of the backward-compatible Variant API

## Acceptance criteria

- every available implemented preset has a Family registry
- Root exposes exactly one default Family, **Classic Root**
- Classic Root contains all existing Root parameter values
- no-Family and `classic_root` requests produce identical meshes
- the accepted Root digest remains unchanged
- Seed remains deterministic and different Seeds still vary geometry
- Preview and OK carry `classic_root`
- Fusion uses the existing generic Family dropdown and Preview pipeline
- generated assets retain their material and object-space mapping defaults
- all automated validation passes

## Acceptance result

Manual Autodesk Fusion 360 validation passed:

- Root exposed the registry-driven Family dropdown
- **Classic Root** was available and selected
- Classic Root generated successfully through the unified Family Registry path
- no Fusion runtime regression was observed
