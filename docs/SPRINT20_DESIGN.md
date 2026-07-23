# Sprint 20 Design — Coral Preset MVP

## Summary

Sprint 20 makes Coral the second non-Rock preset to supply a Family registry
through `PresetCatalog` and the first Registry-driven branching natural object.
It reuses the existing connected capsule-union Coral field, preserves the
accepted Seed 0 mesh, and adds deterministic Seed-dependent branch variation.

## Architecture

```text
PresetCatalog
    -> PresetDefinition("coral")
        -> NaturePreset
            -> Cell Size
            -> Thickness
            -> Seed
            -> Resolution
        -> CoralFamilyRegistry
            -> Classic Coral
                -> CoralGenerator
                -> connected branch-node transform
                -> capsule-union Coral field
                -> existing VoxelGrid
                -> existing Marching Tetrahedra
                -> existing mesh validation
                -> Preview or Final MeshBody
```

## Coral Family

`CoralFamilyRegistry` initially contains `classic_coral`, displayed as
**Classic Coral**:

| Parameter | Value |
| --- | ---: |
| Cell Size | 14 mm |
| Thickness | 0.35 |
| Seed | 0 |
| Resolution | 17 |

The registry contains immutable metadata only. Geometry remains owned by
`CoralGenerator`.

## Branching model

Classic Coral is a union of six overlapping capsule segments:

- one upright central trunk
- three primary upward-growing lateral branches
- two upward terminal branches

Shared endpoints ensure the implicit capsules overlap as one connected solid.
The isosurface therefore closes branch tips naturally and does not require
manual caps or topology stitching.

For Seed 0, the normalized segment graph is unchanged. For nonzero Seeds, each
shared node is transformed by the same deterministic value-noise function.
Shared nodes remain identical across connected segments, preserving overlap and
single-component topology while changing branch direction and silhouette.

## Backward compatibility

Requests without `family_id` resolve to Classic Coral. Fusion requests carry
`classic_coral`. Current parameter overrides take precedence over Family
values.

Seed 0 has the exact accepted digest:

`f4c780ffb295c44a96d13311baae4c6987319c67f2dda515451c8ae0845834e4`

At resolution 17 it contains 960 vertices and 1,916 faces.

The existing Coral Variants remain available through `VariantFactory` for API
compatibility and now explicitly carry Seed 0. Fusion presents Family for Coral
once its registry is available.

## Quality

Automated validation requires:

- repeatable vertices and faces for identical Seed
- geometry variation for different Seeds
- finite vertices
- zero boundary and non-manifold counts
- zero degenerate faces
- consistent winding
- one connected component
- closed watertight topology
- quantitative silhouette and mesh-count distinction from Rock and Bark

## Preserved boundaries

- no `core/` change
- no Scalar Field contract change
- no Marching Tetrahedra change
- no mesh or topology implementation change
- no Preview policy or insertion change
- no GeneratorFactory public API or registration change
- no Rock or Bark algorithm, Family, parameter, or digest change
- no third-party dependency

## Test coverage

- Coral Family registry metadata and PresetCatalog association
- backward-compatible default versus `classic_coral` equality
- exact Classic Coral digest
- deterministic same-Seed and different-Seed variation
- watertight, manifold, finite, nondegenerate, single-component topology
- Cell Size, Thickness, Seed, and Resolution validation
- quantitative distinction from Sponge, Rock, and Bark
- metadata-driven Family UI
- Preview and OK requests carry `classic_coral`
- existing Variant compatibility
- exact Rock and Bark digest regressions

## Validation

- full unit suite: 204 tests passed in 130.282 seconds with warnings treated as
  errors
- focused Coral, Preset, Variant, and Fusion suite: 95 tests passed in 38.721
  seconds
- Classic Coral exact digest and accepted Seed 0 mesh counts passed
- deterministic Seed variation remained watertight, manifold, and
  single-component
- all seven Rock Family and Classic Bark exact digest regressions passed
- Coral Registry, PresetCatalog, Preview, OK, validation, and topology tests
  passed
- Python compilation and `git diff --check` passed
- Fusion dependency, concrete-generator, and `sys.path` boundaries passed
- threading, async, timer, sleep, and `adsk.doEvents` scan passed
- third-party dependency scan passed
- documentation heading, code-fence, and relative-link checks passed
- generated/tracked artifact and TODO/debug scans passed

## Known limitations

- Classic Coral is the only Coral Family.
- The branch graph is a compact artistic approximation, not biological growth.
- Seed changes branch placement but not branch count or hierarchy.
- no polyps, porous microstructure, colony aggregation, or species model
- no smoothing, decimation, materials, live Preview, progress, or cancellation
