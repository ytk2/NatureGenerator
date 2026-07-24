# Sprint 26 Design — Crystal Preset MVP

## Summary

Sprint 26 adds Classic Crystal as a recognizable fabrication-oriented
procedural crystal. It is the second major inorganic preset after Rock and is
integrated through the same immutable Family metadata and generic request,
asset, Preview, and Fusion insertion paths.

## Architecture

```text
PresetCatalog
    -> CrystalFamilyRegistry
    -> Classic Crystal (`classic_crystal`)
    -> GenerationRequest
    -> GeneratorFactory
    -> CrystalGenerator
    -> existing TriangleMesh
    -> existing validation
    -> GeneratedAsset
    -> Fusion Preview or final MeshBody
```

There is no Crystal-specific command or Fusion branch. Fusion obtains the
Family name, defaults, parameter controls, and Preview tiers from catalog
metadata.

## Parametric construction

`CrystalGenerator` creates indexed geometry directly in the existing
`TriangleMesh` representation:

- a closed polygonal base
- several axial rings defining an elongated prism
- five to ten major longitudinal facets
- a shoulder and single displaced tip defining the termination

Seeded deterministic value noise changes per-facet radius, subtle ring scale,
axial alignment, and tip position. Irregularity scales those deviations.
Resolution controls the number of axial rings, preserving the silhouette while
changing the density of subtle facet variation. The termination remains a
single connected cap and no duplicate mesh representation is introduced.

## Classic Crystal parameters

| Parameter | Default | Range |
| --- | ---: | ---: |
| Length | 80 mm | 40–180 mm |
| Width | 28 mm | 12–70 mm |
| Facet Count | 6 | 5–10 |
| Taper | 0.30 | 0.15–0.50 |
| Irregularity | 0.14 | 0–0.50 |
| Seed | 13 | 0–2,147,483,647 |
| Resolution | 33 | 21–41 |

Explicit request overrides take precedence over Classic Crystal values.
Requests without a Family ID resolve to Classic Crystal for compatibility with
the standard preset API.

## Geometry and topology

At the registered defaults Classic Crystal has:

- 38 vertices
- 72 triangular faces
- bounds of approximately 27.8 × 25.9 × 80.0 mm
- length-to-width ratio above 2.8
- one point at the termination and a closed polygonal base
- one connected component
- zero boundary edges
- zero non-manifold edges and vertices
- zero degenerate faces
- zero inconsistent-winding edges
- finite coordinates and closed, manifold, watertight topology

The accepted deterministic digest is:

`3f66098eaae05c74e20635c320c32b0c2b37a50febd0ef2dd6b8a273fb66f974`

This is a stylized procedural form intended for fabrication, not a mineral
growth or optical simulation.

## GeneratedAsset

Crystal uses renderer-neutral `natural_crystal` material intent:

- pale blue-gray RGBA base color `(0.68, 0.82, 0.88, 1.0)`
- non-metallic
- roughness `0.28`
- crystalline procedural-variation metadata

Mapping remains object-space procedural, `TextureSet` remains empty, and the
asset references the exact validated `TriangleMesh` returned by the generator.

## Fusion and Preview

Selecting Crystal exposes **Classic Crystal** and only its seven focused
parameters. Preview and OK carry `classic_crystal` through
`GenerationRequest`. Preview body ownership, replacement, cleanup, unit
conversion, and final insertion remain handled by the unchanged generic Fusion
pipeline.

## Compatibility

- no existing generator or geometry algorithm is changed
- no Geometry Core, GeneratedAsset model, exporter, or Fusion pipeline changes
- all existing preset and Family IDs remain unchanged
- Rock, Bark, Coral, Sponge, Root, and Bone digests remain regression-protected
- public request and result APIs remain compatible

## Known limitations

- Classic Crystal is a single stylized point rather than a cluster
- it does not simulate mineral lattices, growth, fracture, or inclusions
- material intent does not provide transparency or refraction
- axial subdivisions are intentionally modest for planar fabrication geometry
- there are no texture maps, UV coordinates, smoothing, or decimation
