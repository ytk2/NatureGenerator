# Sprint 30 Design — Subdivision Operator

## Summary

Subdivision is Procedural Lab's first topology-changing operator. It increases
triangle density while leaving the existing piecewise-linear surface in place.
It is registered and executed through the same contracts as Pass Through and
Noise Displacement.

```text
ProceduralInputGeometry
    -> OperatorPipeline
    -> SubdivisionOperator(level)
    -> iterative midpoint subdivision
    -> ProceduralResult
    -> Fusion MeshBody
```

The operator and midpoint kernel are Fusion-independent and reuse the existing
immutable `TriangleMesh`.

## Midpoint algorithm

For each level, the operator:

1. copies the current vertex array
2. visits triangles in their existing order
3. creates one midpoint for each unique undirected edge
4. replaces `(a, b, c)` with:

```text
(a,  ab, ca)
(ab, b,  bc)
(ca, bc, c)
(ab, bc, ca)
```

The child ordering preserves the parent winding. A dictionary keyed by sorted
endpoint indices ensures adjacent triangles share the same midpoint. This
prevents cracks and preserves manifold adjacency.

Levels are applied iteratively rather than recursively. The kernel is written
as `subdivide_once(mesh)`, allowing future level limits to change without
altering the operator contract.

## Parameter and density growth

The registry-defined **Subdivision Level** is an integer with a default of 1
and Sprint 30 range of 1–3. Fusion renders it through the existing generic
operator-parameter UI.

Each level multiplies triangle count by four:

| Level | Faces relative to input |
| ---: | ---: |
| 1 | 4× |
| 2 | 16× |
| 3 | 64× |

Vertices are added once per unique edge at each level. Runtime and memory are
linear in the generated mesh size, but the generated size grows exponentially
with Level.

## Topology and shape policy

Midpoints lie exactly on input edges. Each child triangle lies in its parent
triangle's plane, so bounds, surface area, signed volume, and overall
piecewise-linear shape remain unchanged apart from floating-point arithmetic.

The operator preserves:

- winding and orientation
- connected-component count
- open or closed boundary structure
- manifold adjacency where present
- millimetre units and source provenance

It intentionally changes vertex, edge, and face counts. It does not smooth,
project, weld, split, remesh, or evaluate Fusion geometry.

## Product behavior

The operator dropdown now contains Pass Through, Noise Displacement, and
Subdivision. Selecting Subdivision shows only Subdivision Level. Selecting
another operator hides that control automatically.

Source, operator, and level changes use the existing invalidation path and
remove the command-owned preview. Preview replaces the previous temporary
MeshBody. Apply creates one permanent
`NatureGenerator Procedural — Subdivision` MeshBody and leaves the source
untouched.

## Future direction

Midpoint subdivision establishes a topology-changing operator without
conflating density with smoothing. Future Loop subdivision can add a smoothing
position rule behind a separate operator or explicit mode. Catmull-Clark would
need a polygon-oriented contract or deterministic triangulation policy.
Adaptive subdivision, Relax, Smooth, Voronoi, Gyroid, and Erosion can build on
the denser mesh and ordered operator-stack direction without changing Sprint
30's registry or pipeline boundaries.

## Limitations

- subdivision does not make the surface smoother by itself
- faceted silhouettes remain faceted because existing vertices are not moved
- face count grows by 4^Level and can become expensive on dense Fusion meshes
- there is no adaptive, feature-aware, or curvature-aware refinement
- materials, UVs, textures, normals as separate channels, and per-face
  attributes are not transferred
- output remains MeshBody-only
- Procedural Lab still exposes one operator at a time rather than a stack
