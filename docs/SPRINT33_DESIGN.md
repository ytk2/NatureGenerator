# Sprint 33 Design — Gyroid Surface Operator

## Summary

Gyroid Surface is a Fusion-independent `TriangleMesh -> TriangleMesh`
deformation. It samples an analytical triply periodic minimal-surface field at
existing vertices and moves them along the shared robust area-weighted normals.
It is a surface pattern, not a true volumetric TPMS solid.

No vertices or faces are added or removed. The operator cannot create gyroid
infill, pores, holes, hollow walls, or a replacement solid volume.

## Mathematical mapping

For object-space position `p = (px, py, pz)`, Period `P`, and phases
`(φx, φy, φz)`, coordinates are:

```text
x = 2π px / P + φx
y = 2π py / P + φy
z = 2π pz / P + φz
```

The field is:

```text
g = sin(x) cos(y) + sin(y) cos(z) + sin(z) cos(x)
```

Distance from the selected isovalue is normalized by Band Width:

```text
t = clamp(abs(g - Threshold) / BandWidth, 0, 1)
mask = 1 - smoothstep(t)
```

where `smoothstep(t) = t²(3 - 2t)`. The compact smooth mask is strongest at the
selected isovalue and reaches zero at the band edge without a hard binary
cutoff.

The final mapping is:

```text
direction = -1 when Invert else +1
output = position + normal * Amplitude * direction * mask
```

Invert therefore reverses displacement direction deterministically. Positive
and negative Amplitude also produce opposite displacement. Amplitude zero
reconstructs every input coordinate exactly.

## Parameters

| Parameter | Type | Default | Range | Meaning |
| --- | --- | ---: | ---: | --- |
| Period | length | 20 mm | 1–500 mm | one full object-space field period |
| Amplitude | length | 2 mm | -50–50 mm | signed maximum normal displacement |
| Threshold | float | 0 | -1.5–1.5 | selected gyroid isovalue |
| Band Width | float | 0.35 | 0.01–2 | field-space feature width |
| Phase X | float | 0 rad | -6.283–6.283 rad | X phase offset |
| Phase Y | float | 0 rad | -6.283–6.283 rad | Y phase offset |
| Phase Z | float | 0 rad | -6.283–6.283 rad | Z phase offset |
| Invert | boolean | false | false/true | reverse displacement direction |

`ParameterDefinition` now supports a generic boolean type. Fusion renders the
Invert checkbox from registry metadata in the same path as every other control;
there is no Gyroid-specific UI conditional.

## Robust topology-preserving deformation

The operator reuses the robust linear-time normal implementation introduced for
Noise and Voronoi. Zero-area triangles make no contribution. Vertices with
cancelled or absent accumulated normals receive deterministic strongest-face,
radial, or global fallbacks. Only a mesh with no usable non-degenerate triangle
normal is rejected.

Faces are copied byte-for-byte as indexed tuples. Consequently the operation
preserves:

- vertex count and face count
- connectivity and winding
- connected-component count
- boundary, manifold, and open/closed topology state
- millimetre units and source provenance
- source mesh immutability

## Operator Stack and lifecycle

`GyroidSurfaceOperator` uses the existing `ProceduralRequest` contract and is
registered as `gyroid_surface`. Registry iteration makes it available in all
three slots automatically. Each slot gets an independent eight-control
parameter bank.

`OperatorPipeline` remains responsible for ordered stage execution. Focused
tests cover:

- Gyroid Surface alone
- Subdivision -> Gyroid Surface
- Gyroid Surface -> Noise Displacement
- Noise Displacement -> Gyroid Surface
- Gyroid Surface -> Voronoi Surface
- Voronoi Surface -> Gyroid Surface
- Subdivision -> Gyroid Surface -> Noise Displacement

Order changes canonical output digests because each later operator evaluates
the geometry produced by the preceding stage.

Preview and Apply are unchanged. Preview owns one temporary final MeshBody and
replacement deletes the previous owned preview. Apply inserts one permanent
final MeshBody. Cancel, destroy, and add-in stop use the existing owned-preview
cleanup path.

## Determinism

The default focused grid fixture produces:

```text
46c987447bd0b9bc9bfc7b32c3851b38b46ac46e6bfd51ed9b667cd7c3ccbb69
```

The algorithm uses only deterministic standard-library scalar math and ordered
mesh traversal. It has no random state, external numerical libraries, threads,
timers, sleeps, or host event loops.

## Complexity and limitations

Field sampling and vertex displacement are `O(V)`. Normal accumulation is
`O(V + F)`. Memory usage is `O(V)` in addition to the immutable output mesh.
There is no voxel grid or volumetric extraction.

The representative dependency-free benchmark used a 40,401-vertex,
80,000-face mesh and completed the default operator in 2.243 seconds. Its
deterministic output digest was:

```text
4f0080991c3c2fc7acbc35e82738475ebf4155754c744c51ce62c7790a0b99c7
```

This is an observed development-machine result rather than a Fusion host
guarantee.

Visible detail remains limited by input vertex density. Subdivision should
precede Gyroid when finer sampling is required. Levels 1–5 are available, and
the exact triangle prediction is `input_face_count * (4 ** level)`. Preview
allows up to 500,000 predicted faces while Apply allows up to 1,000,000. The
policy evaluates the actual mesh entering the Subdivision stack stage and
rejects oversized requests before allocating any partial result. Higher levels
also improve Noise and Voronoi sampling, but become expensive rapidly.

Large Amplitude or coarse triangulation may create self-intersections even
though indexed topology is preserved. A MeshBody remains the only Procedural
Lab output.

## Manual Fusion acceptance checklist

- [ ] Gyroid Surface appears in every Operator Stack slot
- [ ] Solid Body input works
- [ ] Mesh Body input works
- [ ] Sphere -> Gyroid Surface visibly changes the surface
- [ ] Amplitude 0 preserves equivalent geometry
- [ ] Period changes pattern scale
- [ ] Threshold changes the selected isovalue band
- [ ] Band Width changes feature width
- [ ] all three phases visibly shift the pattern
- [ ] Invert changes the result
- [ ] negative and positive Amplitude move oppositely
- [ ] Subdivision -> Gyroid Surface produces finer visible detail
- [ ] Gyroid Surface -> Noise Displacement works
- [ ] Subdivision -> Gyroid Surface -> Noise Displacement works
- [ ] Gyroid Surface and Voronoi Surface work in both orders
- [ ] changing operator order changes output
- [ ] repeated Preview leaves exactly one preview
- [ ] Apply creates exactly one permanent MeshBody
- [ ] original geometry remains unchanged
- [ ] Pass Through, Noise, Subdivision, Voronoi, Generate Nature, and stack
      regressions remain operational
- [ ] Cancel and add-in stop leave no owned preview
- [ ] Subdivision UI permits Levels 1–5
- [ ] Level 4 works on a low-density cube
- [ ] Level 5 works on a low-density cube
- [ ] Level 4 improves Gyroid detail on a sphere
- [ ] Level 5 improves Gyroid detail when within the safety limit
- [ ] oversized Preview reports the limit and leaves no stale preview
- [ ] Apply uses its separate 1,000,000-face limit
- [ ] existing Subdivision Levels 1–3 remain operational
