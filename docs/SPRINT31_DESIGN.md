# Sprint 31 Design — Voronoi Surface Operator

## Summary

Voronoi Surface is the first cell-based Procedural Lab operator. It deforms an
existing `TriangleMesh` near virtual Voronoi boundaries without changing face
connectivity.

```text
vertex position
    -> deterministic nearby lattice sites
    -> nearest distance d1 and second-nearest distance d2
    -> edge measure d2 - d1
    -> boundary mask
    -> position + normal * mask * Depth
```

The operator remains Fusion-independent and executes through the existing
registry and `OperatorPipeline`.

## Deterministic lattice sites

Object space is divided into cubic cells of Cell Size. Each virtual cell owns
one site. With Jitter zero, the site is at the cell center. Jitter moves each
axis by a deterministic hash-derived fraction while keeping the site inside
its lattice cell.

The integer cell coordinate, Seed, and axis channel are mixed using fixed
32-bit integer operations. No random module, mutable global state, or
third-party dependency is used. Site placement therefore depends on object
position rather than mesh vertex index or traversal order.

Sites are evaluated on demand rather than stored as a global list. For each
vertex, only its containing cell and the 26 immediate neighbors are examined.
Focused tests compare this 27-cell search with a 729-cell reference on regular,
fully jittered, negative-coordinate, and boundary-adjacent samples.

The virtual lattice extends around the mesh bounds, preventing artificial edge
conditions while retaining bounded per-vertex work and constant site memory.

## Boundary measure and displacement

Euclidean distances to the nearest and second-nearest sites are `d1` and `d2`.
Their non-negative difference is zero where the two cells are equidistant and
increases toward cell interiors.

```text
raw = max(0, 1 - (d2 - d1) / Edge Width)
mask = raw ^ Falloff
displacement = Depth * mask
```

The mask is one at an ideal Voronoi boundary and zero when the distance
difference reaches Edge Width. Falloff controls the transition shape. Positive
Depth creates ridges; negative Depth creates grooves. Depth zero creates a
separate result mesh whose canonical digest exactly matches the input.

## Parameters

| Parameter | Meaning | Default | Range |
| --- | --- | ---: | --- |
| Cell Size | approximate lattice spacing | 20 mm | 1–500 mm |
| Depth | signed normal displacement | 2 mm | -20–20 mm |
| Edge Width | boundary influence width | 3 mm | 0.1–50 mm |
| Falloff | boundary sharpness exponent | 2 | 0.25–8 |
| Jitter | site irregularity | 0.75 | 0–1 |
| Seed | deterministic site variation | 0 | signed 32-bit-safe range |

Fusion renders these definitions through the generic operator-parameter UI.
Selecting Voronoi Surface shows only these six controls. Source, operator, or
parameter changes use the existing preview invalidation path.

## Normals and topology

Voronoi Surface reuses Sprint 29's robust area-weighted normals. Degenerate
triangles are ignored, and unusable vertex accumulations receive deterministic
adjacent-face, radial, or global fallbacks.

The output creates exactly one position per input vertex and copies the face
tuple unchanged. It therefore preserves vertex count, face count, indices,
winding, connected components, open/closed boundary structure, and
manifold/non-manifold connectivity state. The source mesh is never mutated.

## Fusion behavior

Solid Body and Mesh Body inputs continue through `FusionSelectionAdapter`.
Preview creates or replaces one temporary
`NatureGenerator Procedural Preview — Voronoi Surface` MeshBody. Apply removes
that preview and creates one permanent
`NatureGenerator Procedural — Voronoi Surface` MeshBody. No BRep output or
export is produced.

## Performance

Nearest-site evaluation has constant work per vertex: 27 sites, each generated
on demand. Normal construction and output assembly are linear in mesh size.
There is no recursion, voxelization, SDF conversion, boolean, threading,
asynchronous work, timer, sleep, or `adsk.doEvents`.

## Future direction

This surface mask can inform later Voronoi Crack, Cell Extrusion, Porous
Surface, and Honeycomb operators. Lloyd Relaxation would change site placement
but can preserve the object-space site contract. Volumetric Voronoi requires a
separate topology-changing or solid-field boundary and is intentionally not
modeled as this surface deformation.

## Limitations

- visible detail depends on input tessellation density
- low-poly meshes show only coarse cell deformation
- no actual cell edges, separated cells, holes, cuts, or booleans are created
- large Depth can self-intersect
- averaged normals can soften sharp edges
- materials, UVs, textures, and per-face attributes are not transferred
- output remains MeshBody-only
- Procedural Lab still exposes one operator at a time
