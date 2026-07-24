# Sprint 23 Design — Complete Family Registry Migration

## Summary

Sprint 23 migrates Root, the final implemented legacy preset, to the existing
Family Registry architecture. Bone remains unavailable and intentionally has no
Family registry because there is no Bone generator to route.

No geometry or asset model changes are included.

## Completed architecture

```text
Preset
    -> PresetCatalog
    -> FamilyRegistry
    -> GenerationRequest
    -> GeneratorFactory
    -> existing TriangleMesh
    -> GeneratedAsset
```

The flow now applies to every implemented preset:

| Preset | Family registry | Default presentation |
| --- | --- | --- |
| Rock | `RockFamilyRegistry` | Smooth |
| Bark | `BarkFamilyRegistry` | Classic Bark |
| Coral | `CoralFamilyRegistry` | Classic Coral |
| Sponge | `SpongeFamilyRegistry` | Classic Sponge |
| Root | `RootFamilyRegistry` | Classic Root |

Bone remains visible but unavailable and therefore does not claim a Family or
generation path.

## Classic Root

`RootFamilyRegistry` contains one immutable `RootFamilyDefinition`:

| Field | Value |
| --- | --- |
| Family ID | `classic_root` |
| Display name | Classic Root |
| Length | 100 mm |
| Root Radius | 8 mm |
| Branch Count | 5 |
| Branching | 0.45 |
| Spread | 0.65 |
| Taper | 0.65 |
| Gravity | 0.70 |
| Seed | 11 |
| Resolution | 37 |

These are the accepted Root preset defaults. Family selection changes metadata
routing only.

## Runtime behavior

`RootGenerator` resolves the requested Family before applying explicit request
overrides. An empty Family ID selects `CLASSIC_ROOT_FAMILY`, preserving legacy
API callers. Unknown Root Family IDs fail as invalid generator parameters.

The effective precedence is:

```text
Preset defaults
    -> Classic or requested Family values
    -> explicit GenerationRequest overrides
```

The existing resolution field remains owned by `GenerationRequest`, matching
the other Family-backed generators.

## Fusion behavior

Root uses the generic registry-driven Family UI already used by Rock, Bark,
Coral, and Sponge:

- selecting Root shows **Classic Root**
- the legacy Variant dropdown is hidden for Root
- Family values populate the existing metadata-generated inputs
- Preview carries `classic_root`
- OK carries `classic_root`
- Preview density and lifecycle behavior are unchanged

No Root-specific Fusion branch or concrete registry import is introduced.

## Geometry and compatibility

- the Root scalar field and skeleton are unchanged
- Geometry Core, voxel sampling, and Marching Tetrahedra are unchanged
- Seed 11 remains the default deterministic result
- the accepted Root digest remains
  `889e8603de8b33404d6d1939cfb53dfd3bd9d1fa0abf7f21e2b7efe7de1e8b59`
- no-Family and `classic_root` requests have identical vertices and faces
- current Root parameters and validation bounds are unchanged
- the existing Variant API remains available for external compatibility

## GeneratedAsset compatibility

`GeneratorFactory` continues composing the validated Root mesh through the
Sprint 22 `GeneratedAssetFactory`. Family identity is recorded as
`classic_root` when selected. The existing Root `MaterialDefinition`,
object-space `MappingDefinition`, empty `TextureSet`, and mesh identity are
unchanged.

## Dependency boundaries

- presets contain no generator imports
- the application composition root associates Root and its registry
- the Root generator imports only its own Family metadata
- Fusion remains registry-generic
- no `adsk` dependency enters generators, presets, assets, or core
- no third-party dependency is added

## Test coverage

- all available implemented presets have a Family registry
- Bone remains the sole unavailable no-Family definition
- Classic Root metadata and parameter ordering
- legacy versus `classic_root` mesh equality
- stable Root digest and deterministic Seed variation
- unknown Family rejection
- generated-asset mesh identity and Family provenance
- Root Family dropdown, Preview request, and OK request
- complete existing Fusion, Preview, generator, and digest regression coverage

## Validation

- full warnings-as-errors suite: 221 tests passed
- generator runtime suite: 62 tests passed
- Fusion integration suite: 59 tests passed
- preset and catalog suite: 22 tests passed
- Preview suite: 10 tests passed
- Variant compatibility suite: 8 tests passed
- GeneratedAsset suite: 7 tests passed
- accepted Root digest passed unchanged
- Python compilation, dependency boundaries, `sys.path`, `git diff --check`,
  and TODO/debug scans passed

Manual Autodesk Fusion 360 acceptance also passed. Root exposed the Family
dropdown, **Classic Root** was selectable, and generation completed
successfully through the unified Family Registry pipeline.

## Known limitations

- Classic Root is the only Root Family.
- The migration adds no new Root morphology.
- Bone remains unavailable until a future generator sprint.
- The backward-compatible Variant API still contains Root configurations, but
  Fusion now presents Family for every implemented preset.
