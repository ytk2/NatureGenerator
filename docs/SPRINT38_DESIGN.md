# Sprint 38 Design — TPMS Family

## Summary

The independent volume command is now **TPMS Volume**. Its existing stable
Fusion command ID and toolbar placement remain unchanged, preventing duplicate
controls during reload. The command adds a metadata-driven TPMS Type selector:

1. Gyroid (`gyroid`)
2. Schwarz P (`schwarz_p`)
3. Diamond / Schwarz D (`diamond`)
4. Neovius (`neovius`)

Gyroid remains the default. Preview bodies use
`NatureGenerator Preview — TPMS — {Type}` and permanent bodies use
`NatureGenerator — TPMS — {Type}`.

The existing Gyroid Surface operator remains a separate mesh-deformation
operator and is not renamed or modified.

## Architecture

```text
TPMSVolumeRequest
    -> Preview/Apply effective-resolution policy
    -> immutable cost estimate and centralized safety validation
    -> TPMSFieldFactory
         -> released GyroidVolumeField
         -> AnalyticalTPMSField
    -> Surface or paired Thickened scalar fields
    -> regular voxel sampling
    -> deterministic marching tetrahedra
    -> optional rectangular boundary closure
    -> measured geometry validation
    -> TPMSVolumeResult with estimate and timings
    -> separately timed Fusion MeshBody insertion
```

There is one shared pipeline. `GyroidVolumeRequest`,
`GyroidVolumeResult`, `generate_gyroid_volume`, and
`execute_gyroid_volume` remain compatibility names without warnings. They
delegate to the generalized TPMS implementation and default to Gyroid.

## Coordinates

World millimetres map independently to normalized TPMS coordinates:

```text
k = 2π / Period
X = kx + PhaseX
Y = ky + PhaseY
Z = kz + PhaseZ
```

All fields are periodic by `Period` on each world axis. Phases are radians.
Traversal, interpolation, vertex ordering, face ordering, and winding remain
deterministic.

## Formulas and normalization

Gyroid retains its raw released field exactly:

```text
G = sin X cos Y + sin Y cos Z + sin Z cos X
normalization = 1
```

Schwarz P:

```text
Praw = cos X + cos Y + cos Z
P = Praw / 3
```

Diamond / Schwarz D:

```text
Draw = sin X sin Y sin Z
     + sin X cos Y cos Z
     + cos X sin Y cos Z
     + cos X cos Y sin Z
D = Draw / 2
```

Neovius:

```text
Nraw = 3(cos X + cos Y + cos Z)
     + 4 cos X cos Y cos Z
N = Nraw / 13
```

Positive constants preserve every conventional zero isosurface. Gyroid is not
rescaled, protecting released geometry. The shared Iso Value range remains
`-1.5` to `1.5`; unsupported values are rejected without clamping. Equal Iso
Values improve UI-scale comparability but do not imply equal volume fractions.

## Analytical gradients

Each normalized-coordinate derivative is multiplied by `k` to obtain the
world-space gradient in inverse millimetres and by its field normalization.

```text
∇Praw = (-sin X, -sin Y, -sin Z)
```

For Diamond:

```text
∂Draw/∂X =
  cos X sin Y sin Z + cos X cos Y cos Z
  - sin X sin Y cos Z - sin X cos Y sin Z

∂Draw/∂Y =
  sin X cos Y sin Z - sin X sin Y cos Z
  + cos X cos Y cos Z - cos X sin Y sin Z

∂Draw/∂Z =
  sin X sin Y cos Z - sin X cos Y sin Z
  - cos X sin Y sin Z + cos X cos Y cos Z
```

For Neovius:

```text
∂Nraw/∂X = -3 sin X - 4 sin X cos Y cos Z
∂Nraw/∂Y = -3 sin Y - 4 cos X sin Y cos Z
∂Nraw/∂Z = -3 sin Z - 4 cos X cos Y sin Z
```

Central finite-difference tests validate every analytical world gradient.

## Physical Wall Thickness

Thickened mode still constructs two scalar boundaries, never mesh-normal
offsets. For normalized TPMS field `f`, Iso Value `i`, wall thickness `T`, and
world gradient `∇f`:

```text
ε = (2π / Period) × 1e-9
h = 0.5 T sqrt(|∇f|² + ε²)
upper = f - i - h
lower = -f + i - h
```

Both fields are sampled in one coordinate traversal and extracted separately.
The regularization prevents division or collapse at exact critical points.
Accuracy remains a first-order, resolution-dependent approximation.

## Geometry behavior

- Surface+Open extracts one iso-surface and retains intersections with bounds.
- Surface+Cap closes measured rectangular-domain openings.
- Thickened+Open extracts both wall sides and leaves boundary intersections.
- Thickened+Cap clips the scalar wall region on all six domain faces.

Capped thickened representative fixtures are accepted only when measured
watertight, manifold, consistently wound, finite, and positive-volume. Multiple
connected components are preserved and reported.

### Near-degenerate boundary sliver policy

Manual validation exposed one valid 30³ Gyroid wall request where marching
tetrahedra created a nonzero boundary-adjacent source face with doubled area
`1.0831011364020455e-12 mm²`. The face was already present in the combined
Open wall mesh; band clipping and fan triangulation did not create it.

The final mesh validator treats doubled areas at or below `2e-12 mm²` as
degenerate, while cap insertion previously used `boundary_tolerance⁴`, a much
smaller unrelated threshold. The policy is now explicit:

- point welding uses the spacing-derived boundary tolerance
- cap triangle acceptance uses the validator's
  `MINIMUM_VALID_DOUBLED_AREA`
- boundary-adjacent extracted slivers are considered only when the validator
  already marks them degenerate
- exactly two vertices must define an unchanged rectangular-plane boundary edge
- the third vertex must lie within
  `max(64 × boundary tolerance, domain diagonal × 1e-10)`
- that third vertex is moved deterministically inward only far enough to exceed
  the validator threshold by ten percent

This preserves indices, winding, connectivity, boundary coverage, and source
immutability. Ambiguous or larger defects are rejected instead of repaired.
Ordinary meshes bypass the repair and retain every released digest.

### Exact-isovalue extraction classification

A second manual case exposed a distinct, earlier ambiguity for Schwarz P.
Pure-Python reproduction showed that the requested Standard Preview correctly
uses 30³ and is already clean; the reported face `2865` occurs when the same
request uses Final Preview or Apply at 40³. It was created during marching
tetrahedra, before deduplication completed and before boundary closure:

```text
indices: (1706, 1705, 1039)
doubled area: 1.4261072965499199e-15 mm²
validator threshold: 2e-12 mm²
```

Its vertices were interior to the rectangular domain:

```text
1706: (9.743589743589741, -3.589743589743591, -16.923076923076927)
1705: (9.01098901098901,  -4.322344322344324, -17.655677655677657)
1039: (8.717948717948715, -4.6153846153846185, -17.94871794871795)
```

Vertices `1706` and `1039` lie within `3.6e-15 mm` of grid samples;
`1705` is an extraction-edge intersection. None lies on a rectangular domain
plane. Their analytical values were between approximately `-1.5e-16` and
`+7.4e-17`, so floating-point cancellation assigned different inside/outside
signs to samples mathematically on `Schwarz P = 0`.

All three face edges had exactly two incident faces:

```text
(1705, 1706): 2864, 2865
(1039, 1705): 2863, 2865
(1039, 1706): 2865, 2866
```

Vertex incidence was:

```text
1706: 2864, 2865, 2866, 2870, 2871, 4396, 4399, 4441, 4447, 4448, 4449
1705: 2863, 2864, 2865
1039: 1560, 1561, 1565, 1596, 2814, 2862, 2863, 2865, 2866
```

The raw 40³ extraction contained ten collapsed faces, fourteen samples
evaluating exactly to zero, and two nonmanifold vertices. The defect therefore
pre-existed vertex deduplication and boundary closure.

The extractor first runs the unchanged legacy marching-tetrahedra path. If
that result contains a degenerate face or a nonmanifold vertex, it repeats the
extraction with deterministic symbolic scalar classification:

```text
scalar scale = max(1, |iso|, maximum |sample|)
equality tolerance = 8 × ulp(scalar scale)
```

Samples within that tolerance are classified as exactly equal to the requested
isovalue. The existing rule remains that only values strictly below Iso Value
are inside, so symbolic equality is consistently outside. Intersection
fractions use the same classified values, ensuring all tetrahedra sharing a
sample make the same decision. The sampled grid and analytical field values
remain immutable; no formula, Iso Value, phase, or coordinate is perturbed.

The fallback is field-independent and removes the ambiguity before polygon
ordering or mesh assembly. Valid legacy results are returned directly, so
ordinary canonical fixtures never enter the fallback and retain their recorded
digests.

The exact Schwarz P 40 mm Cap results are:

```text
Standard Preview 30³:
89a2b5b3308767bca015a00abaa27dfd59e9f7ffd075ca666f444c098e5bf8c2
19,156 vertices; 38,328 faces; signed volume 31,999.82351345476 mm³

Final Preview / Apply 40³:
56a568e21f4b1644c8142a465e6d0e5f1cc70808f51926a9b2744b185e79806c
32,746 vertices; 65,508 faces; signed volume 32,000.05214571684 mm³
```

Both results have zero boundary, nonmanifold, inconsistent-winding,
degenerate, and duplicate faces/edges, are watertight and manifold, and retain
the exact requested bounds `(-20, -20, -20)` through `(20, 20, 20)`.

## Preview, cost, safety, and diagnostics

Sprint 37 behavior remains:

```text
Draft = 0.50
Standard = 0.75
Final = 1.00
effective axis = max(8, floor(final axis × scale + 0.5))
```

Apply always uses final resolution. Estimates continue to count one scalar
field for Surface and two for Thickened, plus cells, known grid payload, and
Cap complexity. TPMS Type is now recorded in the immutable estimate and all
actionable safety context. Type cannot bypass limits.

Timings remain validation/estimate, sampling, extraction, closure, geometry
validation, total core, and separate Fusion insertion. Diagnostics add TPMS
Type. Timings remain excluded from geometry equality and digests.

## Released Gyroid compatibility

Final Preview and Apply preserve the Sprint 36/37 40³ digests:

```text
Surface + Open
997b710b2675435be9e3c1a15a2bdc5bf4b9938e0cfedfe94e01d867acb67f56

Surface + Cap
9c7965d3d43052176fd6e5c94ba0d66767fd8cd0c7b9a9be1beb6f01e1c86fc7

Thickened + Open
5ba3480988ccbda7809df98aa33159497e68b8eb2751214b4a6093ad52e9279c

Thickened + Cap
b47c0c5f21819b2b9f5cb06996fe3e3cb71102b10985b0bf70618165dcfe1121
```

## Representative benchmark

All 64 requested 40³ Preview/Apply combinations completed. Times below are
development-machine observations, not universal guarantees.

| Type | Mode | Draft | Standard | Final | Apply |
| --- | --- | ---: | ---: | ---: | ---: |
| Gyroid | Surface Open | 0.555s | 1.462s | 2.876s | 2.902s |
| Gyroid | Surface Cap | 1.251s | 3.090s | 5.826s | 5.803s |
| Gyroid | Thickened Open | 1.254s | 3.158s | 6.258s | 6.249s |
| Gyroid | Thickened Cap | 3.132s | 7.677s | 14.323s | 14.287s |
| Schwarz P | Surface Open | 0.460s | 1.209s | 2.363s | 2.353s |
| Schwarz P | Surface Cap | 0.915s | 2.235s | 4.262s | 4.298s |
| Schwarz P | Thickened Open | 0.976s | 2.576s | 5.190s | 5.164s |
| Schwarz P | Thickened Cap | 1.986s | 5.043s | 9.263s | 9.373s |
| Diamond | Surface Open | 0.624s | 1.661s | 3.139s | 3.145s |
| Diamond | Surface Cap | 1.671s | 4.109s | 6.670s | 6.713s |
| Diamond | Thickened Open | 1.377s | 3.587s | 7.259s | 7.530s |
| Diamond | Thickened Cap | 5.603s | 13.324s | 24.260s | 24.064s |
| Neovius | Surface Open | 0.590s | 1.568s | 3.108s | 3.156s |
| Neovius | Surface Cap | 1.252s | 3.238s | 6.535s | 6.486s |
| Neovius | Thickened Open | 1.229s | 3.380s | 6.667s | 6.757s |
| Neovius | Thickened Cap | 2.772s | 7.526s | 14.256s | 14.224s |

Draft, Standard, and Final use 20³/8,000, 30³/27,000, and
40³/64,000 samples for Surface. Thickened stores two fields and therefore uses
16,000, 54,000, and 128,000 scalar samples. Every 40³ case uses 59,319 cells.

Final 40³ topology:

| Type | Mode | Vertices | Faces | Boundary | Components | Watertight |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Gyroid | Surface Open | 64,871 | 126,684 | 3,456 | 1 | no |
| Gyroid | Surface Cap | 69,408 | 139,212 | 0 | 1 | yes |
| Gyroid | Thickened Open | 128,448 | 250,776 | 6,912 | 4 | no |
| Gyroid | Thickened Cap | 129,692 | 260,172 | 0 | 3 | yes |
| Schwarz P | Surface Open | 48,006 | 93,960 | 2,268 | 1 | no |
| Schwarz P | Surface Cap | 55,406 | 111,132 | 0 | 1 | yes |
| Schwarz P | Thickened Open | 98,388 | 192,456 | 4,752 | 2 | no |
| Schwarz P | Thickened Cap | 99,252 | 198,936 | 0 | 1 | yes |
| Diamond | Surface Open | 73,781 | 144,180 | 4,212 | 1 | no |
| Diamond | Surface Cap | 77,994 | 156,816 | 0 | 1 | yes |
| Diamond | Thickened Open | 157,392 | 305,208 | 11,232 | 4 | no |
| Diamond | Thickened Cap | 158,852 | 319,356 | 0 | 3 | yes |
| Neovius | Surface Open | 70,758 | 138,672 | 3,672 | 1 | no |
| Neovius | Surface Cap | 78,374 | 157,788 | 0 | 1 | yes |
| Neovius | Thickened Open | 138,816 | 272,808 | 6,480 | 2 | no |
| Neovius | Thickened Cap | 139,248 | 280,152 | 0 | 1 | yes |

All measured meshes are manifold. Capped thickened signed volumes are
33,532.787, 25,602.895, 41,856.083, and 40,060.731 mm³ respectively.

## New default 40³ digests

```text
Schwarz P
Surface Open:    abb49b825925112354da76425fe675a6db3ca2eac700360608a249550c0eb54f
Surface Cap:     385cd6cecbb995ab2bb28cb54f5807ddc013e4bbaf9a5457e2f6e85ef581ef74
Thickened Open:  cb454fce5840b3899872c5b4927c6505891b12109f440784bc7ba70e8ced05f7
Thickened Cap:   e32e329900af6cff18a4f1327796c28c559ef05a485c2f6207411263dc02e662

Diamond
Surface Open:    d00d0d6c0cecba8fb9e513659cfbb57768064fb08f03a6c3faead6e486a3497c
Surface Cap:     7b27544a693bf3a5010aac09b8bb91da5302ea91fce42263326112d4620f7fa7
Thickened Open:  f4dcab0120b27735136a496e7a66e718c28e54acfa5e061b093e7cd6d988a6e3
Thickened Cap:   e7b398beca79a7365bf3d3f7bb1595603ac0975b847d68adc74b774a817d42a5

Neovius
Surface Open:    95dae538731017e54cd9916370de9c0d5deae89632d69b5a5066a78b1779bb99
Surface Cap:     52a8f2079ccdada74da01b73580d34b1cc46db8c2dcbdfb6ad527cce97493c5c
Thickened Open:  9c6b35ff339cffa63e88d79932bf0f48c26fb6b7d11a2a095f33bb4e163a68d4
Thickened Cap:   04534d7f2de99e7f7cda57078a5fc4fab55aece918ae1d11e15661a494ed1d8c
```

## Known limitations

- mathematical isosurfaces are sampled approximations
- thickness accuracy remains resolution-dependent
- topology can change with Iso Value or Wall Thickness
- critical-gradient regions remain challenging
- output can contain multiple connected components
- generation is synchronous and non-interruptible
- there is no adaptive octree sampling or GPU acceleration
- there is no remeshing or decimation
- there is no arbitrary-body clipping or automatic BRep conversion
- output remains a Fusion MeshBody
- equal Iso Values do not imply equal volume fractions
- no biological equivalence or structural benefit is claimed

## Manual Fusion acceptance checklist

- [x] independent TPMS Volume command appears once
- [ ] command displays TPMS Type
- [x] Gyroid, Schwarz P, Diamond, and Neovius appear in deterministic order
- [ ] Gyroid is the default
- [x] each type produces a visibly distinct Preview
- [x] changing type removes the previous Preview
- [x] Preview Quality works for each type
- [x] Surface + Open works for each type
- [x] Surface + Cap works for each type
- [x] Thickened + Open works for each type
- [x] Thickened + Cap works for each type
- [x] capped thickened results appear closed
- [x] Wall Thickness visibly changes each thickened TPMS
- [x] Period changes cell scale
- [x] Iso Value changes geometry
- [x] Phase X/Y/Z shift geometry
- [x] non-cubic dimensions work
- [x] independent axis resolutions work
- [x] Draft Preview is faster and coarser
- [x] Final Preview uses requested resolution
- [x] Apply after Draft or Standard uses final resolution
- [ ] diagnostics include TPMS Type, resolution, samples, faces, and timings
- [x] repeated Preview leaves exactly one Preview body
- [x] Apply creates exactly one permanent type-named MeshBody
- [x] Cancel removes only the owned Preview
- [x] add-in stop leaves no owned Preview
- [ ] command reload creates no duplicate controls
- [x] Gyroid output visually matches previous behavior
- [x] Gyroid Surface operator still works
- [x] Procedural Lab and Operator Stack still work
- [x] Generate Nature and Nature Library still work
- [ ] no source geometry is required or modified
- [ ] oversized requests show actionable errors
- [ ] rejection leaves no stale Preview
- [x] exact Gyroid Phase X `0.12566` reproduction no longer raises an error
- [ ] Fusion-displayed Phase X approximately `0.126 rad` succeeds
- [x] corrected Thickened + Cap Preview appears visibly closed
- [ ] Phase X immediately below and above the reproduction succeeds
- [ ] no stale body remains from the original failure
- [x] Apply succeeds at final 40³ resolution
- [x] Schwarz P, Diamond, and Neovius still work after the correction
- [x] TPMS Type switching still removes the previous Preview
- [x] exact 40 mm Schwarz P Surface + Cap request succeeds
- [x] Schwarz P Standard 30³ Preview succeeds
- [x] Schwarz P Final 40³ Preview and Apply succeed
- [x] Schwarz P Surface + Open succeeds
- [ ] neighboring Schwarz P Iso Values succeed
- [ ] neighboring Schwarz P Phase X values succeed
- [x] repeated Schwarz P Preview leaves one body
- [ ] no stale body remains after Schwarz P failure or replacement
- [x] corrected Gyroid Phase X `0.12566` case still succeeds
