# Sprint 19 Design — Bark Preset MVP

## Summary

Sprint 19 makes Bark the first non-Rock preset to supply a Family registry
through the Sprint 18 `PresetCatalog` architecture. It deliberately reuses the
existing deterministic Bark scalar field and mesh pipeline, so the accepted
default Bark geometry remains byte-for-byte stable.

## Architecture

```text
PresetCatalog
    -> PresetDefinition("bark")
        -> NaturePreset
            -> seven Bark parameters
        -> BarkFamilyRegistry
            -> Classic Bark
                -> existing BarkGenerator
                -> existing capped Bark scalar field
                -> existing VoxelGrid
                -> existing Marching Tetrahedra
                -> existing mesh validation
                -> Preview or Final MeshBody
```

## Architectural decisions

### Reuse the accepted generator

`BarkGenerator` and `_BarkField` already implement a closed cylindrical trunk
segment with directional periodic grooves, deterministic value noise, twist,
and planar caps. Replacing them would create unnecessary geometry risk.
Sprint 19 changes only how immutable Bark Family metadata supplies the existing
parameter values.

### One MVP Family

`BarkFamilyRegistry` initially contains one selectable definition:
`classic_bark`, displayed as **Classic Bark**. Its parameter bundle exactly
matches the existing Bark defaults:

| Parameter | Value |
| --- | ---: |
| Diameter | 80 mm |
| Height | 120 mm |
| Bark Depth | 4 mm |
| Groove Scale | 18 mm |
| Twist | 0 |
| Seed | 10 |
| Resolution | 33 |

The registry contains metadata only. It does not select a scalar field, branch
inside the generator, or own mesh logic.

### Backward compatibility

Requests without `family_id` resolve to Classic Bark. Requests from the Fusion
Family control carry `classic_bark`. In both cases, current parameter overrides
take precedence, so the seven existing controls behave as before.

The curated pre-Sprint-19 Bark Variants remain available through
`VariantFactory` for API compatibility, but Fusion presents Family for Bark
once its registry is present.

## Geometry and quality

The unchanged field is the maximum of a radially displaced cylindrical side
field and a finite-height planar cap field. Directional grooves combine angular
periodic terms, seeded value noise, and a height-dependent helical phase. The
result remains visually and quantitatively distinct from Rock.

The exact Classic Bark digest is:

`7cd5810b943bcfb4f88537d547ca9dfcce82380048d8bd41c20c309fd69dd6b7`

At the default resolution it contains 14,422 vertices and 28,840 faces,
matching the accepted Bark baseline.

## Preserved boundaries

- no `core/` change
- no Marching Tetrahedra change
- no mesh or topology implementation change
- no Preview policy or insertion change
- no GeneratorFactory API or registration change
- no Rock algorithm, Family definition, or parameter change
- no new third-party dependency

## Test coverage

- Bark Family registry identity, ordering, metadata, and immutability
- PresetCatalog association
- backward-compatible default versus `classic_bark` equality
- exact Classic Bark digest
- Seed and all public parameter responses
- finite, watertight, manifold, nondegenerate, capped, single-component mesh
- quantitative difference from Rock
- metadata-driven Bark Family UI
- Preview request carries `classic_bark`
- OK request carries `classic_bark`
- invalid Family and Bark Depth validation
- exact existing Rock Family digest regression

## Validation

- full unit suite: 196 tests passed in 124.149 seconds with warnings treated as
  errors
- Classic Bark exact digest and accepted mesh counts passed
- all seven Rock Family exact digest regressions passed unchanged
- Bark Registry, PresetCatalog, Preview, OK, validation, and topology tests
  passed
- Python compilation and `git diff --check` passed
- Fusion dependency, concrete-generator, and `sys.path` boundaries passed
- threading, async, timer, sleep, and `adsk.doEvents` scan passed
- third-party dependency scan passed
- documentation heading, code-fence, and relative-link checks passed
- generated/tracked artifact and TODO/debug scans passed

## Known limitations

- Classic Bark is the only Bark Family.
- Bark is an artistic procedural trunk segment, not a species reproduction.
- The surface is closer to directional grooved trunk texture than deeply
  fractured biological bark.
- no longitudinal crack/plate/peeling model
- no branches, knots, roots, hollow shell, or flat bark panel
- no smoothing, decimation, materials, live Preview, progress, or cancellation
