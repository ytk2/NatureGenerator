# Sprint 36 Design — Gyroid Volume Wall Thickness

## Summary

Gyroid Volume now has two geometry modes:

- **Surface** is the unchanged Sprint 35 zero-thickness iso-surface.
- **Thickened** constructs a finite wall around the requested iso-surface from
  analytical scalar fields. It does not offset an extracted mesh.

Both modes support Open and Cap boundary behavior. Output remains a Fusion
MeshBody and is not automatically converted to a BRep solid.

## Pipeline

```text
GyroidVolumeRequest
    -> centralized allocation and resolution policy
    -> GyroidVolumeField
    -> Surface:
         one scalar grid
         extract g = Iso Value
    -> Thickened:
         analytical world gradient
         paired wall-boundary fields
         two scalar grids sampled in one coordinate pass
         extract both zero sets
         combine indexed wall sides
    -> Open: retain rectangular intersections
    -> Cap: triangulate the scalar inside region on six box faces
    -> measured MeshStatistics validation
    -> GyroidVolumeResult
    -> Fusion MeshBody
```

All field, sampling, extraction, combination, closure, safety, and statistics
work remains Fusion-independent.

## Parameters

| Parameter | Type | Default | Range / choices |
| --- | --- | --- | --- |
| Geometry Mode | enum | Surface | Surface, Thickened |
| Wall Thickness | length | 1.0 mm | 0.1–20.0 mm |

Wall Thickness carries a generic metadata visibility dependency:

```text
visible when Geometry Mode = Thickened
```

The Fusion command evaluates this metadata without thickness-specific UI
branching. Switching modes hides or shows the existing control without
recreating it, so the session value is preserved.

## Physical thickness mapping

World coordinates are mapped to dimensionless Gyroid coordinates using:

```text
k = 2π / Period
gx = kx + PhaseX
gy = ky + PhaseY
gz = kz + PhaseZ
```

The field is:

```text
g = sin(gx) cos(gy) + sin(gy) cos(gz) + sin(gz) cos(gx)
```

Its analytical world-space gradient, in inverse millimetres, is:

```text
∂g/∂x = k [cos(gx) cos(gy) - sin(gz) sin(gx)]
∂g/∂y = k [-sin(gx) sin(gy) + cos(gy) cos(gz)]
∂g/∂z = k [-sin(gy) sin(gz) + cos(gz) cos(gx)]
```

For requested thickness `T`, the local first-order field-space half-band is:

```text
h(x,y,z) = 0.5 T sqrt(|∇g_world|² + ε²)
ε = (2π / Period) × 1e-9
```

The very small scale-aware regularization keeps critical points finite without
meaningfully changing ordinary gradients.

The wall is the intersection:

```text
upper =  g - Iso Value - h <= 0
lower = -g + Iso Value - h <= 0
```

Equivalently, the conceptual inside field is:

```text
max(upper, lower)
    = abs(g - Iso Value) - h <= 0
```

The mapping is a first-order signed-distance approximation: multiplying the
world gradient by millimetres produces a dimensionless field band. Period and
phase are included analytically; dimensions affect the world-space sample
coordinates and spacing.

## Why two scalar grids are extracted

Sampling only `abs(g - iso) - h` can miss a thin negative band when both sides
fall between adjacent vertices. That produces false disconnected fragments.

Sprint 36 therefore samples `upper` and `lower` together at every coordinate
and extracts both zero sets independently. This preserves each wall side even
when no grid vertex lands inside a thin band. The two indexed meshes are
combined deterministically without mutating either side.

The duplication is limited to the two required scalar arrays. Trigonometric
field and gradient evaluation occurs once per coordinate.

## Open and Cap behavior

### Thickened + Open

Both wall sides terminate where they intersect the six rectangular domain
planes. Boundary edges are measured and watertightness is false.

### Thickened + Cap

Each boundary sample triangle is clipped against both inequalities:

```text
upper < 0 and lower < 0
```

This directly triangulates the physical wall strip on the box face. It handles
concavity, disconnected regions, nested contours, and holes through local
convex clipping. Generated cap triangles retain the Sprint 35 fixed outward
winding. Existing contour classification rejects malformed, branching, or
self-intersecting boundary topology.

The result is accepted only when measured as watertight and manifold.

## Determinism

- analytical field and gradient with no random state
- one stable x-fastest coordinate traversal
- stable paired scalar arrays
- fixed marching-tetrahedra decomposition for each wall side
- upper-side vertices/faces followed by lower-side vertices/faces
- deterministic two-inequality box-face clipping
- stable tolerance-based boundary vertex reuse
- canonical indexed-mesh SHA-256 digest

## Safety policy

Existing spatial sampling limits remain:

```text
Preview: 750,000 scalar values
Apply: 2,000,000 scalar values
```

Surface uses one scalar value per spatial sample. Thickened requires two scalar
values, so `2 × Rx × Ry × Rz` is charged against the same active limit before
allocation. `GyroidVolumeResult.sample_count` remains the number of spatial
sample positions; `scalar_bytes` reports both stored arrays.

Thin-wall resolution validation requires:

```text
Wall Thickness >= max(axis spacing) / 16
```

This is a minimum safety floor, not an accuracy guarantee. Requests below it
must increase resolution or thickness.

Cap limits remain:

```text
Preview: 500,000 estimated cap triangles
Apply: 1,000,000 estimated cap triangles
```

A Surface face triangle clips to at most two cap triangles. A Thickened face
triangle clipped by two inequalities can produce at most three. The conservative
Thickened estimate is:

```text
6 × ((Rx - 1)(Ry - 1)
   + (Rx - 1)(Rz - 1)
   + (Ry - 1)(Rz - 1))
```

The pipeline also rejects empty extraction, all-consuming sampled bands,
nonmanifold output, and failed capped topology with actionable request context.

## Representative 40³ results

All fixtures use 60 × 60 × 60 mm dimensions, Period 20 mm, Iso Value 0,
zero phases, and 1.0 mm Wall Thickness.

| Mode | Vertices | Faces | Boundary edges | Components | Time |
| --- | ---: | ---: | ---: | ---: | ---: |
| Surface + Open | 64,871 | 126,684 | 3,456 | 1 | 2.900 s |
| Surface + Cap | 69,408 | 139,212 | 0 | 1 | 5.794 s |
| Thickened + Open | 128,448 | 250,776 | 6,912 | 4 | 6.092 s |
| Thickened + Cap | 129,692 | 260,172 | 0 | 3 | 13.920 s |

Each fixture uses 64,000 spatial samples and 59,319 cells. Surface stores an
estimated 512,000 scalar bytes; Thickened stores 1,024,000 bytes.

Default Thickened+Cap measures:

- zero nonmanifold edges and vertices
- zero inconsistent-winding edges
- zero degenerate and duplicate faces
- watertight and manifold
- signed volume `33,532.787159 mm³`

Disconnected components are preserved rather than joined artificially. A
fabrication workflow must inspect whether every component is desired and
physically printable.

## Geometry digests

Unchanged Sprint 35 Surface:

```text
Surface + Open:
997b710b2675435be9e3c1a15a2bdc5bf4b9938e0cfedfe94e01d867acb67f56

Surface + Cap:
9c7965d3d43052176fd6e5c94ba0d66767fd8cd0c7b9a9be1beb6f01e1c86fc7
```

Sprint 36 default 40³ Thickened:

```text
Thickened + Open:
5ba3480988ccbda7809df98aa33159497e68b8eb2751214b4a6093ad52e9279c

Thickened + Cap:
b47c0c5f21819b2b9f5cb06996fe3e3cb71102b10985b0bf70618165dcfe1121
```

## Known limitations

- Physical thickness is a first-order gradient approximation and remains
  resolution-dependent.
- Accuracy degrades in narrow regions and near Gyroid critical points.
- Increasing thickness can merge, split, remove, or create topology.
- The rectangular domain can contain multiple disconnected wall components.
- Marching tetrahedra produces more triangles and different faceting than
  Marching Cubes.
- There is no adaptive sampling, remeshing, smoothing, or decimation.
- High resolutions are synchronous and computationally expensive.
- Output is a Fusion MeshBody, not an automatically converted BRep solid.
- The add-in performs no slicing, support generation, minimum-feature analysis,
  or print validation.

## Manual Fusion acceptance checklist

- [x] Geometry Mode shows Surface and Thickened
- [x] Surface remains the default
- [x] Wall Thickness appears only in Thickened mode
- [x] switching modes preserves the Wall Thickness session value
- [x] Surface + Open matches Sprint 35 behavior
- [x] Surface + Cap matches Sprint 35 behavior
- [x] Thickened + Open visibly creates a wall with two sides
- [x] Thickened + Cap visibly closes rectangular boundaries
- [x] Wall Thickness visibly changes the result
- [x] Period changes cell scale
- [x] Iso Value changes geometry
- [x] Phase X, Y, and Z shift the pattern
- [x] non-cubic dimensions work
- [x] independent X, Y, and Z resolutions work
- [x] repeated Preview leaves one owned preview
- [x] switching Geometry Mode removes the previous preview
- [x] changing Wall Thickness removes the previous preview
- [x] Apply creates one permanent MeshBody
- [x] Cancel removes only the owned preview
- [x] add-in stop removes owned previews
- [x] capped Thickened output reports watertight and manifold
- [x] Gyroid Surface still works
- [x] Procedural Lab still works
- [x] Generate Nature and Nature Library still work
- [x] no source geometry is required or modified
- [x] oversized requests show actionable errors
- [x] rejection leaves no stale preview
