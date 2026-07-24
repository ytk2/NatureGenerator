# Sprint 27 Design — Natural Material Framework

## Summary

Sprint 27 separates reusable natural-material catalog metadata from asset
generation. It also gives all implemented presets the same declarative
parameter grouping convention. Both additions are passive metadata: generator
algorithms, normalized requests, mesh construction, Preview, and final Fusion
insertion are unchanged.

## Architecture

```text
NaturalMaterialRegistry
    -> NaturalMaterial
        -> existing MaterialDefinition
        -> AssetBrowserMetadata
        -> optional ThumbnailReference
        -> extension metadata

NaturePreset
    -> ParameterGroupDefinition("form")
    -> ParameterGroupDefinition("generation")
```

`GeneratedAssetFactory` resolves a `NaturalMaterial` by preset ID and uses its
existing `MaterialDefinition`. Unknown third-party presets retain the previous
generic natural-surface fallback.

## Natural materials

`NaturalMaterial` is an immutable renderer-neutral catalog record. It contains
the stable preset ID, procedural material definition, discovery metadata, an
optional thumbnail reference, and small extension metadata. It contains no
Fusion appearances, file-format objects, renderer state, image decoding, or
geometry.

The built-in registry covers Rock, Bark, Coral, Sponge, Root, Bone, and
Crystal. Their material identifiers, colors, roughness, normal strength, and
procedural parameters are identical to Sprint 26.

`AssetBrowserMetadata` provides a stable category and keywords for future
search and filtering. `ThumbnailReference` identifies a future packaged
resource and accessible alternative text; no thumbnail asset or UI is added in
this sprint.

## Parameter groups

Every built-in preset declares two immutable groups:

- **Form** contains parameters that directly describe shape.
- **Generation** contains deterministic Seed and mesh Resolution.

Groups reference existing parameter IDs and cannot duplicate a parameter or
refer to missing metadata. The `NaturePreset.parameter_groups` field defaults
to an empty tuple, preserving callers that construct legacy or third-party
presets without groups. Fusion continues to consume the original ordered
parameter metadata, so its current control layout and behavior do not change.

## Compatibility

- no generator, Geometry Core, Family definition, request, or Preview code is
  changed
- all preset, generator, Family, material, and parameter IDs remain stable
- all defaults and validation ranges remain stable
- GeneratedAsset retains its exact model and existing TriangleMesh instance
- object-space mapping and empty TextureSet behavior remain stable
- unknown presets still receive the generic natural-surface material

## Validation

Automated coverage verifies registry completeness, immutable metadata,
thumbnail readiness without image loading, standardized group coverage,
legacy presets without groups, and GeneratedAsset material identity. Existing
digest, Preview, Fusion integration, topology, dependency-boundary, and
warnings-as-errors suites provide regression coverage for unchanged behavior.
