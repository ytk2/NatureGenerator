# Sprint 17 Design: Rock Diversity

## Objective

Sprint 17 adds Granite, Basalt, and Broken Rock as immutable parameter bundles
for the existing three-stage Rock pipeline:

```text
RockFamilyRegistry
    -> RockFamilyDefinition
        -> MacroShapeParameters
        -> FacetLayoutParameters
        -> SurfaceDetailParameters
    -> existing Rock scalar field
    -> existing sampling and mesh pipeline
```

These families are procedural design approximations. They do not simulate
geology, minerals, erosion history, volcanic column joints, or fracture
mechanics.

## Registry and UI

The required Registry order is:

1. Smooth
2. Weathered
3. Rugged
4. River Stone
5. Granite
6. Basalt
7. Broken Rock

Fusion reads labels, order, defaults, and stable IDs from
`RockFamilyRegistry.list_all()`. No family label or family default is
hardcoded in Fusion runtime code. Manual parameter edits retain the selected
Family.

## Family parameterization

| Family | Size | Roughness | Seed | Resolution |
| --- | ---: | ---: | ---: | ---: |
| Granite | 50 mm | 0.45 | 37 | 25 |
| Basalt | 50 mm | 0.25 | 61 | 25 |
| Broken Rock | 50 mm | 0.55 | 97 | 25 |

### Granite

- Macro Shape uses a wide primary radius, unequal secondary radii, moderate
  seeded axis variation, broad deformation, and low-frequency mass breakup.
- Facet Layout uses four medium/small planes for restrained planar breaks.
- Surface Detail uses four coarse FBM octaves and moderate ridged variation.

At the default, normalized X/Y/Z spans are approximately
`1.126 / 0.781 / 0.692`, producing a broad heavy mass without River Stone's
horizontal flattening.

### Basalt

- Macro Shape makes Z the dominant axis and suppresses organic bulging.
- Facet Layout uses six mostly side-oriented planes for a dense block-like
  profile.
- Surface Detail uses low-amplitude FBM and weak ridges so the planar macro
  form remains dominant.

The default Z/X span ratio is approximately `1.30`, clearly separating Basalt
from every rounded or horizontally biased family.

### Broken Rock

- Macro Shape uses unequal axes, strong asymmetric directional terms, and
  restrained low-frequency breakup.
- Facet Layout uses seven large/medium clipping planes with deep deterministic
  intersections.
- Surface Detail remains subordinate to the fracture planes while preserving
  Roughness response.

At default resolution, Broken Rock has six large non-ground planar regions and
more than twice Granite's repeated planar-face count. Its wedge-like silhouette
and fracture planes are the dominant features.

## Geometry safeguards

All families remain one implicit solid. Facets intersect the same continuous
field with half-spaces; they do not create fragments or internal shells. The
existing sampling margin, Marching Tetrahedra extraction, vertex welding, and
mesh validation remain unchanged.

Automated acceptance requires:

- finite vertices
- nondegenerate faces and consistent winding
- zero boundary and non-manifold counts
- one connected component
- closed watertight topology
- a nonempty horizontal grounding region

The continuous implicit-solid construction and topology validation are the
practical protection against obvious self-intersection and detached fragments.
No general-purpose triangle self-intersection solver is added.

## Preview and Final

All three defaults request resolution 25. The unchanged adaptive Rock policy
uses resolution 21 for Preview and resolution 25 for Final. Family identity,
Seed, Roughness, stage definitions, facet placement, grounding, and all other
parameters are identical; only sampling density differs.

| Family | Preview resolution | Preview vertices/faces | Preview median | Final resolution | Final vertices/faces | Final median |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Granite | 21 | 1,994 / 3,984 | 0.478 s | 25 | 2,880 / 5,756 | 0.788 s |
| Basalt | 21 | 1,824 / 3,644 | 0.473 s | 25 | 2,650 / 5,296 | 0.789 s |
| Broken Rock | 21 | 1,596 / 3,188 | 0.474 s | 25 | 2,270 / 4,536 | 0.791 s |

Times are medians of three sequential local runs and are not performance
guarantees. Every Preview measurement remains below one second.

## Deterministic digests

| Family | Preview digest | Final digest |
| --- | --- | --- |
| Granite | `a8e3c4a23d6ff24ba24ee36cbc7b269a3e32064bd695ce29edf466ef8666e72f` | `492f9ca68798ff6a7913193677289a6f4a1c525a37cd06eefba1c28c81aea228` |
| Basalt | `d8b4581efb280ce492baa2d7ea2c94d1d1234f9cb7537d8cde9f8ed896d55de3` | `fb73c7efee28f34fe3f266a9ec68afd266b49b73cab0798d6e854c50b21b84fa` |
| Broken Rock | `d608eb39a957c8215656e29d882d32f831571e31fe289f61ba740b1145beedc3` | `5a260c62a457b9b0b9782d223f9c9bf6ed9c512490c7c70091443bd5c2623d96` |

Existing family digests remain protected separately by exact regression tests.

## Test coverage

- exact seven-family Registry order and immutable metadata
- defaults use only Size, Roughness, Seed, and Resolution
- deterministic repeat generation
- Seed and Roughness geometry response
- exact new and existing family digests
- finite, nondegenerate, consistently wound topology
- watertight, manifold, single-component output
- nonempty grounding regions
- bounding-box and planar-region differentiation
- Registry-driven Fusion list and default application
- adaptive Preview resolution and retained Final resolution
- Preview signature, replacement, OK, Cancel, destroy, and stop regressions
- non-Rock generator and Variant regressions
- absence of family-name hardcoding in Fusion

## Real Autodesk Fusion retest checklist

- Open Generate Nature and select Rock.
- Confirm Family order is Smooth, Weathered, Rugged, River Stone, Granite,
  Basalt, Broken Rock.
- Select Granite and verify a broad, heavy, irregular rounded-mass silhouette.
- Select Basalt and verify a tall/block-like directional silhouette with
  planar sides and restrained surface noise.
- Select Broken Rock and verify the strongest angular wedge-like silhouette
  with several large fracture planes.
- Confirm all three are distinguishable from silhouette alone at Preview
  resolution.
- For each family, Preview twice and confirm replacement leaves one Preview
  body.
- Compare Preview and Final for matching silhouette, facets, ridges, grounding,
  and Seed; density alone should differ.
- Confirm OK creates a fresh final `NatureGenerator Rock` MeshBody.
- Confirm Cancel removes only the owned Preview.
- Confirm command destroy and add-in stop leave no Preview body.
- Generate Sponge, Coral, Bark, and Root once each and confirm existing
  Variant, Preview, Final, and cleanup behavior.
- Confirm no duplicate controls or Fusion runtime errors.

## Real Autodesk Fusion acceptance

Sprint 17 passed real Autodesk Fusion acceptance:

- Granite, Basalt, and Broken Rock produced clearly distinct silhouettes.
- the new families generated and behaved correctly.
- Smooth, Weathered, Rugged, and River Stone remained unchanged.
- Sponge, Coral, Bark, and Root remained functional.
- no additional Sprint 17 geometry changes were requested.

## Known limitations

- Family names describe artistic procedural intent, not reproduced materials.
- Basalt does not create column joints.
- Broken Rock clipping planes are surface facets, not simulated cracks or
  detached fracture pieces.
- Sampling resolution limits the smallest visible feature.
- There is no smoothing, decimation, material system, live Preview, progress,
  or cancellation.
