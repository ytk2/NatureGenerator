# Sprint 37 Design — Gyroid Volume Preview Optimization

## Summary

Gyroid Volume now separates the final resolution entered by the user from the
effective resolution used for Preview. Apply always uses final resolution.
Preview Quality is metadata-driven and supports Draft, Standard, and Final.

```text
GyroidVolumeRequest
    -> deterministic resolution policy
    -> immutable cost estimate
    -> centralized pre-allocation safety validation
    -> sampling
    -> extraction
    -> optional boundary closure
    -> topology validation
    -> immutable result, estimate, and stage timings
    -> separately timed Fusion MeshBody insertion
```

The entire policy, estimate, safety, geometry, and timing pipeline is
Fusion-independent.

## Preview resolution

The displayed Resolution X/Y/Z values always remain the Apply values. Preview
uses these scale factors:

| Quality | Scale |
| --- | ---: |
| Draft | 0.50 |
| Standard | 0.75 |
| Final | 1.00 |

Each axis is independent:

```text
effective = max(8, floor(final × scale + 0.5))
```

This is explicit round-half-up behavior rather than Python banker's rounding.
The metadata restricts final axes to 8–160, so every effective value remains
in that range. Apply selects scale 1.0 regardless of Preview Quality.

## Immutable cost estimate

For effective resolution `(Rx, Ry, Rz)`:

```text
samples_per_field = Rx × Ry × Rz
field_count = 1 for Surface, 2 for Thickened
total_scalar_samples = samples_per_field × field_count
cells = (Rx - 1)(Ry - 1)(Rz - 1)
scalar_grid_bytes = total_scalar_samples × 8
known_grid_metadata_bytes = field_count × 72
```

The metadata estimate covers nine numeric origin, spacing, and shape values.
It does not claim exact Python object overhead. Regular grids do not store
separate coordinate arrays. Memory estimates exclude extracted meshes, Python
container/object overhead, Fusion conversion, and MeshBody storage.

Cap estimates retain the centralized conservative formulas:

```text
Surface Cap = 4 × [XY cells + XZ cells + YZ cells]
Thickened Cap = 6 × [XY cells + XZ cells + YZ cells]
```

The estimate records final and effective resolution, modes, Preview quality,
execution context, active sample/cap limits, and exact generation counts.

## Safety behavior

Preview retains the 750,000 scalar-sample and 500,000 cap-triangle limits.
Apply retains the 2,000,000 scalar-sample and 1,000,000 cap-triangle limits.
Validation occurs before field construction or grid allocation and uses the
effective resolution. Thickened charges both simultaneously stored fields.

Errors name Preview or Apply, quality when relevant, final and effective
resolutions, scalar count, estimated known memory, active limit, and corrective
action. Existing Preview ownership cleanup ensures rejection leaves no stale
body.

## Timing stages

`VolumeGenerationTimings` is immutable and excluded from result equality:

- `validation_and_estimation`: resolution policy, estimate, safety, and wall
  resolution checks
- `scalar_field_sampling`: field construction and scalar-grid evaluation
- `iso_surface_extraction`: marching-tetrahedra extraction and wall combination
- `boundary_closure`: rectangular closure; exactly `0.0` for Open
- `geometry_validation`: mesh statistics and required topology checks
- `total_core`: the complete Fusion-independent call

All stages use `perf_counter`. Fusion insertion is measured at the command
boundary and logged separately; it is not part of the core result or digest.

## Diagnostics

Successful Preview and Apply write one concise application-log summary with
quality where relevant, effective resolution, samples, faces, core time,
Fusion insertion time, and total time. Normal Preview has no modal dialog.

## Cache decision

Runtime caching is intentionally deferred. Cap closure requires the sampled
scalar grid as well as the extracted Open mesh. Retaining paired Thickened
grids would keep the largest allocations alive for the command session, while
caching only the mesh cannot reproduce closure. Safe bounded reuse therefore
needs a broader ownership and memory-budget design. Sprint 37 does not pretend
reuse exists, and there is no new cache state to clear.

## Determinism and compatibility

No field, wall-band, marching-tetrahedra, boundary-triangulation, winding, or
statistics mathematics changed. Apply and Final Preview preserve:

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

## Representative 40³ benchmark

Measured on the development machine with final resolution 40³. Known memory is
scalar payload plus regular-grid metadata. Times are seconds and are
machine-specific diagnostics, not performance contracts.

| Mode | Run | Effective | Samples | Cells | Known bytes | Vertices | Faces | Boundary | Components | Sample | Extract | Close | Validate | Total |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Surface Open | Draft | 20³ | 8,000 | 6,859 | 64,072 | 15,347 | 29,412 | 1,680 | 1 | 0.006 | 0.352 | 0 | 0.199 | 0.557 |
| Surface Open | Standard | 30³ | 27,000 | 24,389 | 216,072 | 35,868 | 69,516 | 2,616 | 1 | 0.021 | 0.950 | 0 | 0.529 | 1.500 |
| Surface Open | Final | 40³ | 64,000 | 59,319 | 512,072 | 64,871 | 126,684 | 3,456 | 1 | 0.049 | 1.867 | 0 | 0.982 | 2.898 |
| Surface Open | Apply | 40³ | 64,000 | 59,319 | 512,072 | 64,871 | 126,684 | 3,456 | 1 | 0.050 | 1.889 | 0 | 1.010 | 2.949 |
| Surface Cap | Draft | 20³ | 8,000 | 6,859 | 64,072 | 16,428 | 33,252 | 0 | 1 | 0.006 | 0.355 | 0.654 | 0.248 | 1.263 |
| Surface Cap | Standard | 30³ | 27,000 | 24,389 | 216,072 | 38,388 | 77,172 | 0 | 1 | 0.021 | 0.944 | 1.553 | 0.621 | 3.139 |
| Surface Cap | Final | 40³ | 64,000 | 59,319 | 512,072 | 69,408 | 139,212 | 0 | 1 | 0.049 | 1.879 | 2.775 | 1.093 | 5.796 |
| Surface Cap | Apply | 40³ | 64,000 | 59,319 | 512,072 | 69,408 | 139,212 | 0 | 1 | 0.050 | 1.859 | 2.738 | 1.109 | 5.756 |
| Thick Open | Draft | 20³ | 16,000 | 6,859 | 128,144 | 30,504 | 58,416 | 3,384 | 4 | 0.019 | 0.770 | 0 | 0.441 | 1.230 |
| Thick Open | Standard | 30³ | 54,000 | 24,389 | 432,144 | 70,944 | 137,496 | 5,184 | 4 | 0.061 | 2.017 | 0 | 1.080 | 3.159 |
| Thick Open | Final | 40³ | 128,000 | 59,319 | 1,024,144 | 128,448 | 250,776 | 6,912 | 4 | 0.146 | 4.000 | 0 | 1.980 | 6.127 |
| Thick Open | Apply | 40³ | 128,000 | 59,319 | 1,024,144 | 128,448 | 250,776 | 6,912 | 4 | 0.146 | 4.015 | 0 | 1.987 | 6.148 |
| Thick Cap | Draft | 20³ | 16,000 | 6,859 | 128,144 | 30,776 | 62,340 | 0 | 3 | 0.018 | 0.766 | 1.816 | 0.459 | 3.059 |
| Thick Cap | Standard | 30³ | 54,000 | 24,389 | 432,144 | 71,600 | 143,988 | 0 | 3 | 0.062 | 2.023 | 4.380 | 1.162 | 7.627 |
| Thick Cap | Final | 40³ | 128,000 | 59,319 | 1,024,144 | 129,692 | 260,172 | 0 | 3 | 0.145 | 4.034 | 7.787 | 2.107 | 14.074 |
| Thick Cap | Apply | 40³ | 128,000 | 59,319 | 1,024,144 | 129,692 | 260,172 | 0 | 3 | 0.145 | 4.046 | 7.843 | 2.186 | 14.219 |

## Known limitations

- generation remains synchronous and cannot be interrupted during core work
- Draft and Standard are lower-resolution approximations
- timings vary by machine and Fusion environment
- total Python and Fusion memory cannot be predicted exactly
- there is no adaptive octree sampling or GPU acceleration
- there is no remeshing or decimation
- runtime cache reuse is deferred for the ownership and memory reasons above
- output remains a Fusion MeshBody

## Manual Fusion acceptance checklist

- [ ] Preview Quality shows Draft, Standard, and Final
- [ ] Standard is the default
- [ ] Resolution X/Y/Z retain final Apply values
- [ ] Draft Preview is visibly faster and coarser
- [ ] Standard Preview balances speed and detail
- [ ] Final Preview uses requested resolution
- [ ] Final Preview and Apply appear geometrically identical
- [ ] Apply after Draft Preview uses final resolution
- [ ] Surface + Open works at all qualities
- [ ] Surface + Cap works at all qualities
- [ ] Thickened + Open works at all qualities
- [ ] Thickened + Cap works at all qualities
- [ ] effective resolution is displayed correctly in diagnostics
- [ ] sample count matches the active quality
- [ ] completion summary reports mesh counts and timing
- [ ] changing Preview Quality removes the previous Preview
- [ ] repeated Preview leaves exactly one owned Preview
- [ ] Apply creates exactly one permanent MeshBody
- [ ] Cancel removes only the owned Preview
- [ ] add-in stop removes Preview and session state
- [ ] invalid or oversized requests show actionable errors
- [ ] rejection leaves no stale Preview
- [ ] dimensions, Period, Iso Value, phases, and Wall Thickness still work
- [ ] no source geometry is required or modified
- [ ] Gyroid Surface still works
- [ ] Procedural Lab and Operator Stack still work
- [ ] Generate Nature and Nature Library still work
- [ ] cache comparison is not applicable because runtime caching was deferred
