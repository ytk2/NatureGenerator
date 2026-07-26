# Sprint 34 Design — TPMS Gyroid Volume Foundation

## Summary

Gyroid Volume is NatureGenerator's first dedicated volumetric scalar-field
pipeline:

```text
GyroidVolumeRequest
    -> GyroidVolumeField
    -> VoxelGrid sampling
    -> marching tetrahedra iso-surface extraction
    -> TriangleMesh
    -> GyroidVolumeResult
    -> Fusion MeshBody
```

It generates geometry from empty space inside requested dimensions. It does not
select or deform an existing body. The earlier Gyroid Surface operator remains
an independent topology-preserving mesh deformation.

## Architecture

The new `volume/` package contains no Autodesk imports. It owns request and
result contracts, parameter metadata, the analytical field, sampling facade,
extraction facade, and centralized size policy. It reuses the stable core
`VoxelGrid`, marching-tetrahedra extractor, `TriangleMesh`, and mesh statistics.

The Fusion layer owns only command controls, Preview/Apply lifecycle, and
MeshBody insertion. `Gyroid Volume`, `Procedural Lab`, and `Generate Nature`
register separate command definitions and maintain separate preview owners.

## Field mapping

For world position `(x, y, z)`, Period `P`, and phases:

```text
gx = 2π x / P + PhaseX
gy = 2π y / P + PhaseY
gz = 2π z / P + PhaseZ

g = sin(gx) cos(gy) + sin(gy) cos(gz) + sin(gz) cos(gx)
```

The function is deterministic and periodic by `P` on each axis.

## Sampling convention

Width, Depth, and Height define a box centered at the origin:

```text
minimum = (-Width/2, -Depth/2, -Height/2)
maximum = ( Width/2,  Depth/2,  Height/2)
```

Resolution values count sample points, not cells. Both endpoints are included.
For `(Rx, Ry, Rz)`:

```text
samples = Rx * Ry * Rz
cells = (Rx - 1) * (Ry - 1) * (Rz - 1)
spacing = dimension / (resolution - 1)
```

Samples use x-fastest, then y, then z ordering. Integer products are calculated
and validated before sample storage is allocated.

## Extraction algorithm

Sprint 34 reuses the repository's dependency-free marching tetrahedra. Each
voxel is split into the same six tetrahedra around a stable body diagonal.
Intersections are linearly interpolated and cached by global sample-edge
identity, producing indexed vertices shared between neighboring cells.

Values below Iso Value are classified inside. Polygon intersections are
ordered deterministically and oriented from lower toward higher field values.
Degenerate triangles are discarded. Traversal and vertex/face ordering are
stable.

Marching tetrahedra was selected because the correct, tested implementation was
already present. No external Marching Cubes table or dependency was introduced.

## Boundary behavior

The result is clipped **open at the rectangular bounds**. Surface branches that
reach a box face terminate there, producing measured boundary edges. Sprint 34
does not cap or thicken the sheet and therefore does not claim a watertight
solid.

This is deliberate correctness, not a simulated closed result. Deterministic
capping or thickened TPMS walls remain a clean future extension.

## Parameters

| Parameter | Default | Range | Unit |
| --- | ---: | ---: | --- |
| Width | 60 | 1–500 | mm |
| Depth | 60 | 1–500 | mm |
| Height | 60 | 1–500 | mm |
| Period | 20 | 1–500 | mm |
| Iso Value | 0 | -1.5–1.5 | field value |
| Resolution X | 40 | 8–160 | samples |
| Resolution Y | 40 | 8–160 | samples |
| Resolution Z | 40 | 8–160 | samples |
| Phase X | 0 | -6.283–6.283 | rad |
| Phase Y | 0 | -6.283–6.283 | rad |
| Phase Z | 0 | -6.283–6.283 | rad |

Fusion controls are rendered directly from this ordered metadata.

## Safety policy

Central limits are:

```text
Preview: 750,000 scalar samples
Apply: 2,000,000 scalar samples
```

The policy also reports cell count and a scalar-payload estimate of eight bytes
per sample. A request above its active limit is rejected before `VoxelGrid`
allocation. Errors identify the three resolutions, requested sample count,
active Preview/Apply limit, and advise reducing resolution.

Counts exactly equal to a limit are accepted.

## Preview and Apply

The command requires no source selection.

- parameter changes delete the command-owned preview
- repeated Preview replaces the previous owned MeshBody
- Apply deletes Preview and inserts one permanent MeshBody
- Cancel/destroy deletes only the owned preview
- add-in stop cleans every remaining Gyroid Volume preview
- invalid metadata values disable Preview and invalidate Apply

Names are:

```text
NatureGenerator Preview — Gyroid Volume
NatureGenerator — Gyroid Volume
```

## Representative default fixture

Default 40 × 40 × 40 sampling produced:

| Statistic | Observed value |
| --- | ---: |
| Scalar samples | 64,000 |
| Cells | 59,319 |
| Scalar payload estimate | 512,000 bytes |
| Vertices | 64,871 |
| Faces | 126,684 |
| Connected components | 1 |
| Boundary edges | 3,456 |
| Nonmanifold edges | 0 |
| Degenerate faces | 0 |
| Inconsistent-winding edges | 0 |
| Surface area | 33,782.310318 mm² |
| Watertight | false |
| Manifold | true |

Bounds were exactly `(-30, -30, -30)` to `(30, 30, 30)` mm. Signed volume was
approximately zero and is not meaningful for this open surface.

Observed generation time was 1.924 seconds on the development machine.

Default digest:

```text
997b710b2675435be9e3c1a15a2bdc5bf4b9938e0cfedfe94e01d867acb67f56
```

Focused 16³ digest:

```text
2a762f15dcc93985901ac77d926357ef0b9d0b697137474bd30216c76992a0ba
```

## Determinism guarantees

- analytical field with no random state
- inclusive regular sampling
- fixed x/y/z traversal
- fixed six-tetrahedra cell decomposition
- stable edge-cache keys
- stable polygon ordering and winding
- canonical SHA-256 digest of indexed vertices and faces

There are no external numerical libraries, threads, asynchronous tasks,
timers, sleeps, or `adsk.doEvents` loops.

## Known limitations

- output is an open zero-thickness sheet clipped at the box
- no caps, thickening, solid conversion, infill, or booleans
- signed volume is not meaningful for open results
- Marching tetrahedra creates more triangles than equivalent Marching Cubes
- generation is synchronous and high resolutions can be expensive within the
  safety limits
- output is a Fusion MeshBody, not a BRep solid

## Manual Fusion acceptance checklist

- [ ] Gyroid Volume command appears independently
- [ ] default Preview creates a visible Gyroid mesh
- [ ] changing Period changes cell scale
- [ ] changing Iso Value changes geometry
- [ ] changing resolution changes detail
- [ ] changing phases shifts the pattern
- [ ] repeated Preview leaves one preview
- [ ] Apply creates one permanent MeshBody
- [ ] Cancel removes only the owned preview
- [ ] no source geometry is required
- [ ] Procedural Lab still works
- [ ] Generate Nature still works
- [ ] Gyroid Surface still works
- [ ] add-in stop leaves no owned previews
- [ ] oversized Preview shows a clear error
- [ ] no stale preview remains after rejection
