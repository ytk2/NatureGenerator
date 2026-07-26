# Sprint 35 Design — Gyroid Volume Boundary Closure

## Summary

Gyroid Volume now offers two metadata-driven boundary modes:

- **Open** preserves the exact Sprint 34 zero-thickness iso-surface.
- **Cap** closes its intersections with the requested rectangular domain using
  deterministic planar triangles on the six box faces.

The volume core remains Fusion-independent. Cap does not thicken the Gyroid
sheet, create an offset shell, convert it to BRep, or modify Gyroid Surface.

## Pipeline

```text
GyroidVolumeRequest
    -> sample GyroidVolumeField
    -> marching tetrahedra
    -> Open: unchanged TriangleMesh
    -> Cap:
         validate rectangular-boundary contours
         triangulate inside regions on six domain faces
         reuse boundary vertices
         measure and accept only a clean watertight manifold
    -> GyroidVolumeResult
    -> Fusion MeshBody
```

`boundary_closure.py` is a reusable core stage. It imports only core mesh and
voxel-grid contracts and has no Autodesk dependency.

## Boundary metadata

| Parameter | Type | Default | Choices |
| --- | --- | --- | --- |
| Boundary Mode | enum | Open | Open, Cap |

The generic metadata renderer creates the Fusion dropdown. Reading it maps the
display label back to the stable `BoundaryMode` value; no cap-specific UI
branch exists. Changing it uses the same input-change path that deletes the
owned preview for every other volume parameter.

## Boundary detection and validation

Open edges are derived from indexed edge use. Every such edge must lie on
exactly one of the six requested domain planes within a tolerance derived from
the smallest voxel spacing:

```text
tolerance = max(minimum_spacing * 1e-7, 1e-12)
```

Per-plane adjacency is traversed in stable vertex order. A valid contour is
either a closed loop or a chain whose two endpoints lie on edges of that box
face. Branches, interior endpoints, and proper self-intersections are rejected.
The latter chain form is required because a Gyroid contour can pass from one
box face to its neighbor through their shared box edge.

## Planar closure algorithm

Cap triangulation operates on the scalar domain rather than assuming every
per-face contour is already a standalone polygon. Each rectangular boundary
sample cell uses the same deterministic diagonal as the extraction grid and is
split into two planar triangles. Each triangle is clipped against:

```text
field_value < Iso Value
```

The resulting triangle or convex quadrilateral is triangulated in stable order
with fixed outward winding:

| Plane | Outward direction |
| --- | --- |
| X minimum | -X |
| X maximum | +X |
| Y minimum | -Y |
| Y maximum | +Y |
| Z minimum | -Z |
| Z maximum | +Z |

This local planar construction handles concave regions, multiple disconnected
regions, and nested contours with holes without a global fan or a false convex
assumption. It is intentionally scoped to rectangular domains sampled by a
scalar grid; it is not a general arbitrary-mesh hole filler.

Coordinates are cached with the derived tolerance. Existing extracted contour
vertices are reused, and generated box-edge or corner vertices are shared
between adjacent faces. Degenerate local triangles are discarded.

## Measured acceptance

Closure is returned only when `MeshStatistics` measures all of the following:

- zero boundary edges
- zero nonmanifold edges and vertices
- zero inconsistent-winding edges
- zero degenerate and duplicate faces
- finite coordinates
- `is_watertight` and `is_manifold` are true

Failure raises a clear boundary-closure error; no partial mesh is returned.
Preview replacement deletes the previous owned preview before generation, so a
rejected closure cannot leave stale geometry.

## Determinism

- fixed grid, cell, face, and triangle traversal
- stable contour adjacency and path starts
- deterministic scalar clipping and interpolation
- tolerance-quantized vertex identity
- fixed cap-plane winding
- canonical indexed-mesh digest

No external numerical library, randomness, thread, timer, sleep, async work, or
Fusion event loop is used.

## Safety policy

Sprint 34 scalar-sample limits remain unchanged:

```text
Preview: 750,000 samples
Apply: 2,000,000 samples
```

Cap also uses a conservative checked estimate. Each boundary sample triangle
can clip to at most two cap triangles:

```text
estimated cap triangles =
    4 * ((Rx - 1)(Ry - 1)
       + (Rx - 1)(Rz - 1)
       + (Ry - 1)(Rz - 1))
```

Central cap limits are 500,000 triangles for Preview and 1,000,000 for Apply.
Counts equal to a limit are accepted. Oversized requests are rejected before
closure work with an error naming the estimate, active operation, limit, and
resolution-reduction action.

## Representative geometry

Default 40 × 40 × 40 Cap output:

| Statistic | Measured value |
| --- | ---: |
| Vertices | 69,408 |
| Faces | 139,212 |
| Connected components | 1 |
| Boundary edges | 0 |
| Nonmanifold edges | 0 |
| Nonmanifold vertices | 0 |
| Inconsistent-winding edges | 0 |
| Degenerate faces | 0 |
| Duplicate faces | 0 |
| Surface area | 44,582.310318 mm² |
| Signed volume | 108,000.000000 mm³ |
| Watertight | true |
| Manifold | true |

Bounds are exactly `(-30, -30, -30)` to `(30, 30, 30)` mm. Observed generation
time was 4.540 seconds on the development machine.

Default Cap digest:

```text
9c7965d3d43052176fd6e5c94ba0d66767fd8cd0c7b9a9be1beb6f01e1c86fc7
```

Focused 16³ Cap digest:

```text
34279fdbf2842833b4a304de85e809c89890be317cf121216c79be764ea40834
```

The unchanged Sprint 34 Open digests remain:

```text
default 40³:
997b710b2675435be9e3c1a15a2bdc5bf4b9938e0cfedfe94e01d867acb67f56

focused 16³:
2a762f15dcc93985901ac77d926357ef0b9d0b697137474bd30216c76992a0ba
```

## Known limitations

- Cap closes the rectangular boundary but retains a zero-thickness internal
  Gyroid sheet; there is no user-configurable wall thickness.
- The output remains a Fusion MeshBody, not a BRep solid.
- Closure is specialized to the sampled rectangular scalar domain.
- Exact scalar configurations that touch only at a point can create
  nonmanifold vertices; these are rejected rather than reported as watertight.
- Generation is synchronous and Cap adds boundary traversal, triangulation, and
  full topology measurement cost.

## Manual Fusion acceptance checklist

- [ ] Boundary Mode appears with Open and Cap
- [ ] Open remains the default
- [ ] Open Preview matches Sprint 34 behavior
- [ ] Cap Preview creates a visibly closed rectangular-bound result
- [ ] Cap works for non-cubic dimensions
- [ ] Cap works with independent axis resolutions
- [ ] Period, Iso Value, and phase changes remain effective
- [ ] repeated Cap Preview leaves one owned preview
- [ ] changing Boundary Mode removes the prior owned preview
- [ ] Apply creates one permanent capped MeshBody
- [ ] Cancel removes only the owned preview
- [ ] add-in stop removes owned previews
- [ ] oversized Cap Preview shows a clear error
- [ ] a rejected Cap leaves no stale preview
- [ ] no source geometry is required or modified
- [ ] Gyroid Surface still works
- [ ] Procedural Lab still works
- [ ] Generate Nature and Nature Library still work
