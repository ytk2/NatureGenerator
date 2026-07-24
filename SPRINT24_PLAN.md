# Sprint 24 Plan — Bone Preset MVP

## Status

Implementation complete; awaiting review and real Autodesk Fusion acceptance.

## Goal

Make Bone executable as a production-ready stylized long-bone preset integrated
through the unified Family Registry and GeneratedAsset architecture.

## Scope

- replace the unavailable Bone placeholder with focused parameter metadata
- add immutable `BoneFamilyDefinition` and `BoneFamilyRegistry`
- register **Classic Bone** as `classic_bone`
- add a deterministic implicit `BoneGenerator`
- register Bone with `PresetCatalog` and `GeneratorFactory`
- expose Bone through the generic Fusion Family, Preview, and OK workflows
- preserve the existing GeneratedAsset material and mapping defaults
- add geometry, topology, digest, performance, lifecycle, and regression tests

## Out of scope

- medical anatomy or a specific species
- cortical/trabecular layer separation or a marrow cavity
- skeleton assembly, joints, or fracture mechanics
- additional Bone Families
- bitmap textures, UVs, Fusion appearances, or asset format exporters
- smoothing, decimation, Geometry Core, or existing generator changes

## Acceptance criteria

- Classic Bone reads as an elongated long bone rather than a capsule or dumbbell
- enlarged rounded asymmetric ends join a narrower curved shaft
- a non-empty planar grounding region is present
- identical inputs are deterministic and different Seeds alter geometry
- the mesh is finite, closed, manifold, watertight, consistently wound,
  nondegenerate, and single-component
- Bone uses the registry-driven Family dropdown, Preview, and OK pipelines
- Preview ownership and cleanup behavior remain unchanged
- GeneratedAsset mesh identity, material, object-space mapping, textures, and
  provenance are correct
- all existing preset digests remain unchanged
- all automated validation passes
