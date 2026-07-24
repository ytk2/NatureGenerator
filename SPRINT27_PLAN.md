# Sprint 27 Plan — Natural Material Framework

## Status

Implementation complete; awaiting review and real Autodesk Fusion acceptance.

## Goal

Provide shared, renderer-neutral metadata infrastructure for every natural
preset without changing geometry, requests, or Fusion behavior.

## Scope

- introduce immutable `NaturalMaterial` records and a built-in registry
- retain the exact existing `MaterialDefinition` values used by assets
- centralize Asset Browser discovery metadata
- define optional packaged-thumbnail references without loading image data
- standardize **Form** and **Generation** parameter groups
- keep parameter groups optional for legacy callers and custom presets
- validate every implemented preset against the shared conventions

## Out of scope

- geometry, parameter default, preset ID, Family, or digest changes
- thumbnail images, thumbnail rendering, or asset browsing UI
- UV mapping, texture baking, exporters, or Fusion appearance objects
- Fusion dialog layout changes

## Acceptance criteria

- all seven implemented presets have a registered natural material
- all built-ins declare Form and Generation parameter groups
- GeneratedAsset material output remains identical
- legacy `NaturePreset` construction without groups remains valid
- geometry regression digests, Preview, OK, Fusion boundaries, and the full
  automated suite remain unchanged and passing
