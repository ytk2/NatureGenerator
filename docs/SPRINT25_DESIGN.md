# Sprint 25 Design — Rock Family Expansion

## Summary

Sprint 25 expands the existing Rock pipeline without adding another generator
or a preset-specific execution path. Four immutable definitions lead the Rock
Family catalog: Classic Rock, Layered Rock, Weathered Rock, and River Rock.
The seven previously shipped Rock definitions remain registered under their
stable IDs for backward compatibility.

## Architecture

```text
PresetCatalog
    -> RockFamilyRegistry
        -> immutable RockFamilyDefinition
            -> Macro Shape parameters
            -> Facet Layout parameters
            -> Surface Detail parameters
    -> GenerationRequest
    -> GeneratorFactory
    -> RockGenerator
    -> GeneratedAsset
```

Fusion obtains Family labels and defaults from `PresetCatalog`; it contains no
Rock Family names or procedural branches. Preview and OK send the selected
stable ID through the same request path.

## Family catalog

| Family | ID | Procedural intent |
| --- | --- | --- |
| Classic Rock | `classic_rock` | exact accepted canonical Rock |
| Layered Rock | `layered_rock` | horizontal strata and broken layered edges |
| Weathered Rock | `weathered_rock` | broad erosion, cavities, rounded form |
| River Rock | `river_rock` | smooth worn form with very low-frequency noise |

Smooth, Weathered, Rugged, River Stone, Granite, Basalt, and Broken Rock remain
selectable with their existing IDs, defaults, and geometry.

## Layered surface detail

The existing Surface Detail parameter model gains optional strata frequency,
amplitude, warp frequency, and warp amplitude values. The strata evaluator
uses object-normalized height to form horizontal bands and seeded
low-frequency value noise to break their edges.

Every pre-Sprint-25 definition receives zero strata amplitude through immutable
defaults. `RockGenerator` evaluates and adds strata only when amplitude is
nonzero. This preserves both the old floating-point operation order and all
legacy mesh digests.

## Family shaping

Layered Rock combines modest broad deformation, near-horizontal fracture
planes, weak ordinary detail, and warped height bands. Weathered Rock removes
most planar cutting and emphasizes broad, low-frequency displacement for a
softer eroded silhouette. River Rock uses no facet planes, weak broad
deformation, very low-frequency FBM, and no ridge contribution.

These are procedural design approximations, not geological simulations.

## Determinism and topology

At their registered defaults:

| Family | Vertices | Faces | Digest |
| --- | ---: | ---: | --- |
| Classic Rock | 1,074 | 2,144 | `30a709c32fb7dd16b87f0388f21c6e24e12b6ad990b2872dd31f9549956e7c1d` |
| Layered Rock | 2,742 | 5,480 | `fb12347ba4fd3beddc7d9fda0677e995bb47922017c8510592143c7515748121` |
| Weathered Rock | 3,250 | 6,496 | `311163e791bbe31b52ab647b5814c03933f4957c41cb183eed25180bc774509e` |
| River Rock | 2,962 | 5,920 | `e9695ac624cf0d42a804598bd62d8b17139c3ff504432fee5553e7d653af7f88` |

All four default meshes are finite, closed, manifold, watertight,
nondegenerate, consistently wound, single-component, and have zero boundary
edges. Repeated requests are byte-identical; changing Seed changes vertices.

## Compatibility

- requests without a Family ID retain the canonical Rock geometry
- Classic Rock is byte-identical to that canonical result
- all seven legacy Rock Family IDs and digests remain unchanged
- Size, Roughness, Seed, and Resolution remain the only public Rock parameters
- no Geometry Core, Marching Tetrahedra, GeneratedAsset, exporter, or Preview
  ownership changes are made
- Bark, Coral, Sponge, Root, and Bone continue through their existing paths

## Known limitations

- strata are object-height based and do not model folded geology
- cavities are scalar-field deformation rather than physical erosion
- River Rock does not simulate transport or collisions
- no smoothing, decimation, texture maps, or UV coordinates are produced
