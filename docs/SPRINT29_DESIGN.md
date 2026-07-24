# Sprint 29 Design — Noise Displacement Operator

## Summary

Noise Displacement is the first Procedural Lab operator that changes geometry.
It accepts the immutable mesh produced by `FusionSelectionAdapter`, computes
normals and object-space noise without Autodesk dependencies, and returns a new
mesh through the Sprint 28 pipeline.

```text
ProceduralInputGeometry
    -> area-weighted vertex normals
    -> normalized fractal value noise(position)
    -> position + normal * amplitude * noise
    -> ProceduralResult
```

Pass Through remains registered and unchanged. Neither operator uses
`PresetCatalog`, `GeneratorFactory`, natural-material semantics, or Fusion
objects.

## Normal generation

For each triangle, the unnormalized face cross product is added to its three
vertices. Cross-product magnitude is twice triangle area, so the normalized
sum is an area-weighted vertex normal. Construction is O(vertices + faces).
Zero-area faces make no contribution. When a vertex's accumulated normal is
unusable, the operator deterministically falls back to its strongest adjacent
non-degenerate face, then its direction from the mesh centroid, and finally
the mesh's strongest non-degenerate face. This accommodates duplicated,
isolated, degenerate, and cancellation-prone vertices found in imported Fusion
meshes without producing a zero vector or NaN. A mesh containing no usable
non-degenerate triangle is still rejected.

Reversing face winding reverses its normal contribution predictably. Face
indices are copied without modification.

## Object-space fractal noise

Noise is smoothstep-interpolated 3D lattice value noise. Lattice values are
derived from integer coordinates and Seed using fixed integer mixing. Sampling
uses vertex positions in millimetres, not vertex indices, so behavior does not
depend on traversal order.

Each octave increases frequency by Lacunarity and reduces weight by
Persistence. The weighted sum is divided by total weight, keeping Amplitude
reasonably stable as octave count changes.

| Parameter | Meaning | Default | Supported range |
| --- | --- | ---: | --- |
| Amplitude | maximum nominal signed displacement | 2 mm | 0–50 mm |
| Scale | first-octave feature size | 20 mm | 0.1–1000 mm |
| Octaves | fractal detail levels | 3 | 1–6 |
| Persistence | successive octave weight | 0.5 | 0–1 |
| Lacunarity | successive frequency multiplier | 2 | greater than 1, up to 4 |
| Seed | deterministic lattice variation | 0 | signed 32-bit-safe range |

The Fusion UI renders these definitions generically by value type, units,
ranges, and defaults. Pass Through has no definitions, so selecting it hides
all operator parameter controls. Source, operator, and parameter changes
remove the command-owned preview.

## Topology policy

Noise Displacement creates one output vertex for each input vertex and copies
the face tuple exactly. It does not subdivide, remesh, weld, split, or run a
boolean. Vertex count, face count, indices, winding, boundary-edge topology,
and connected-component count therefore remain unchanged.

This policy keeps the first transforming operator small and predictable.
Future Smooth and Erode operators can reuse adjacency and normals. Remesh will
require an explicitly topology-changing contract. Gyroid will require a
separate volumetric or implicit conversion boundary.

## Fusion and tessellation

BRep input is displaced after Fusion tessellation. The adapter accepts both
Point3D and flat double/float coordinate arrays returned by Fusion's
`TriangleMeshCalculator`. Consequently, output detail cannot exceed source
tessellation density.

For MeshBody input, the adapter prefers Fusion's triangulated `displayMesh`.
When only the original `PolygonMesh` is available, triangles are retained and
quads or arbitrary polygons are deterministically fan-triangulated. Preview
and final routes use the existing adapter quality policies and both create
MeshBody output while leaving the source untouched.

## Limitations

- low-poly inputs remain low-poly and show limited noise detail
- large Amplitude may self-intersect even though connectivity remains valid
- shared averaged normals can visually round or pull sharp edges
- materials, UVs, textures, normals as separate channels, and per-face
  attributes are not transferred
- output remains MeshBody-only
- no modifier-stack UI, subdivision, remeshing, or smoothing is provided
