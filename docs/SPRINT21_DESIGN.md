# Sprint 21 Design — Sponge Preset MVP

## Summary

Sprint 21 makes Sponge the fourth Registry-driven Nature preset. Classic
Sponge replaces the previous boundary-clipped Gyroid sheet with a closed,
rounded solid containing deterministic spherical surface pores.

## Architecture

```text
PresetCatalog
    -> PresetDefinition("sponge")
        -> SpongeFamilyRegistry
            -> Classic Sponge
        -> GenerationRequest
        -> GeneratorFactory
        -> SpongeGenerator
        -> rounded body and spherical pore field
        -> existing VoxelGrid
        -> existing Marching Tetrahedra
        -> existing mesh validation
        -> Preview or Final MeshBody
```

## Classic Sponge

`SpongeFamilyRegistry` initially contains `classic_sponge`, displayed as
**Classic Sponge**:

| Parameter | Value |
| --- | ---: |
| Cell Size | 10 mm |
| Thickness | 0.20 |
| Seed | 0 |
| Resolution | 17 |

The Family definition contains immutable metadata only. Geometry remains owned
by `SpongeGenerator`.

## Porous field

The outer form is a rounded-box signed-distance field. Twelve spherical
cavities are placed near its six faces. Every cavity intersects the exterior,
so the pore walls remain connected to the outer surface instead of creating
isolated internal shells.

Deterministic value noise controls the tangential location and radius of each
pore. The same Seed produces the same scalar field, sampling, vertices, and
faces. Different Seeds vary pore placement without changing the topology
construction path.

## Compatibility

Requests without a Family ID resolve to Classic Sponge. Fusion Preview and OK
requests carry `classic_sponge`. Explicit parameter overrides take precedence
over Family values.

The existing Sponge Variants remain available through `VariantFactory` for API
compatibility and explicitly carry Seed 0. Fusion presents Family for Sponge.

No Rock, Bark, Coral, Geometry Core, Marching Tetrahedra, Preview pipeline, or
GeneratorFactory public API implementation is changed.

## Quality requirements

- repeatable vertices and faces for identical Seed
- different pore layout for different Seeds
- finite coordinates
- zero boundary edges
- zero non-manifold edges and vertices
- zero degenerate and duplicate faces
- one connected component
- closed watertight topology

## Validation

- full unit suite: 210 tests passed in 129.360 seconds with warnings treated as
  errors
- focused Sponge and Fusion integration suite: 70 tests passed in 3.238 seconds
- focused Fusion integration suite: 58 tests passed in 0.472 seconds
- Classic Sponge digest:
  `92fbd5d78f6797049fbafada00819d4cafa247e106be159a90d890cd6b502786`
- Classic Sponge at resolution 17: 2,984 vertices and 5,964 faces
- deterministic Seed variation remained watertight, manifold, finite,
  nondegenerate, and single-component
- existing Rock, Bark, and Coral exact digest regressions passed unchanged
- Python compilation, diff, dependency-boundary, documentation, artifact, and
  TODO/debug checks passed

## Known limitations

- Classic Sponge is the only Sponge Family.
- The form is an artistic porous block, not simulated biological growth.
- Pores are rounded surface cavities rather than a multiscale internal network.
- There is no species model, skeletal fiber structure, smoothing, or
  decimation.
