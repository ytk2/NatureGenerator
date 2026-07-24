# Sprint 24 Design — Bone Preset MVP

## Summary

Sprint 24 replaces the conceptual unavailable Bone placeholder with Classic
Bone: a deterministic, grounded, printable procedural interpretation of a long
bone. It is integrated through Family metadata from its first executable
version and uses the existing voxel, marching-tetrahedra, validation,
GeneratedAsset, Fusion Preview, and final insertion paths.

## Architecture

```text
PresetCatalog
    -> BoneFamilyRegistry
    -> Classic Bone (`classic_bone`)
    -> GenerationRequest
    -> GeneratorFactory
    -> BoneGenerator
    -> existing VoxelGrid
    -> existing Marching Tetrahedra
    -> existing TriangleMesh
    -> GeneratedAsset
```

There is no Bone-specific UI branch and no legacy-only execution path.

## Implicit construction

`_BoneField` is a smooth union of:

- a curved shaft whose radius is narrowest at the midpoint and increases toward
  both ends
- two anisotropic ellipsoidal epiphyses
- two offset secondary end lobes that avoid a simple sphere-and-cylinder shape
- low-amplitude seeded value-noise displacement

The centerline has a modest deterministic bow and asymmetric lateral/vertical
end placement. A shallow half-space intersection creates a small planar base.
All primitives overlap the shaft and remain a single implicit solid.

## Classic Bone parameters

| Parameter | Default | Range |
| --- | ---: | ---: |
| Length | 100 mm | 60–180 mm |
| Shaft Radius | 12 mm | 8–22 mm |
| End Scale | 1.6 | 1.2–2.1 |
| Curvature | 0.28 | 0–1 |
| Asymmetry | 0.22 | 0–1 |
| Surface Detail | 0.12 | 0–0.40 |
| Seed | 7 | 0–2,147,483,647 |
| Resolution | 33 | 21–41 |

Explicit request overrides take precedence over Classic Bone values. Requests
without a Family ID resolve to Classic Bone for API compatibility.

## Shape evidence

At the accepted defaults:

- bounds are approximately 113.0 × 40.2 × 35.1 mm
- length-to-width ratio is approximately 2.81
- both end cross-sections are more than twice the midshaft cross-section
- the left and right end proportions differ measurably
- the curved midshaft is laterally displaced from a straight centerline
- 19 mesh vertices lie on the planar grounding region

This is a procedural design interpretation, not an anatomical reconstruction.

## Topology and manufacturing

The default Classic Bone mesh has:

- 7,490 vertices
- 14,976 faces
- one connected component
- zero boundary edges
- zero non-manifold edges and vertices
- zero degenerate faces
- zero inconsistent-winding edges
- finite coordinates
- closed, manifold, watertight topology

The accepted digest is:

`cd9e140272b39890105e9b17ab50befaa62dd59d73f8dee91d7bfe174f995eb0`

## GeneratedAsset

Bone uses the existing `natural_bone` material intent:

- warm off-white RGBA base color `(0.82, 0.79, 0.68, 1.0)`
- non-metallic
- roughness `0.72`
- procedural porous-variation metadata

Mapping remains object-space procedural, `TextureSet` remains empty, and
`GeneratedAsset.mesh` is the exact validated `TriangleMesh` in
`GeneratorResult`.

## Fusion and Preview

Selecting Bone shows only **Classic Bone** in the generic Family dropdown and
the eight metadata-driven Bone inputs. Preview and OK carry `classic_bone`
through `GenerationRequest` and use the same generator. Preview replacement,
Cancel, destroy, and add-in-stop cleanup remain owned by the existing generic
Preview controller.

Resolution 25 is a supported lower-density request for silhouette comparison;
the UI default remains 33 so default Preview and Final preserve the accepted
mesh density. Higher user-selected final tiers are reduced by the existing
adaptive Preview policy.

## Performance

Local dependency-free benchmark results:

| Resolution | Vertices | Faces | Elapsed |
| ---: | ---: | ---: | ---: |
| 25 | 4,158 | 8,312 | 0.452 s |
| 33 | 7,490 | 14,976 | 0.997 s |

Runtime varies by host. Topology validation is retained at all supported tiers.

## Regression and compatibility

- no Geometry Core or Marching Tetrahedra change
- no GeneratedAsset or exporter change
- no existing generator or Family Registry change
- no Preview ownership change
- existing Rock, Bark, Coral, Sponge, and Root digests remain protected by the
  unchanged regression suite
- public request and result APIs remain compatible

## Known limitations

- Classic Bone is stylized and not medically accurate.
- It does not model cortical and trabecular layers separately.
- It has no marrow cavity or internal porous structure.
- It does not reproduce a species or named anatomical bone.
- It does not simulate joints or fracture mechanics.
- It has no procedural texture maps, bitmap textures, or UV unwrap.
- Classic Bone is the only Bone Family.
