# Sprint 39 Design — TPMS Domain Sizing Modes

## Summary

TPMS Volume now offers two rectangular-domain sizing modes:

- **Dimensions** uses requested Width, Depth, and Height exactly.
- **Cell Count** derives physical dimensions from integer counts and Period.

Dimensions remains the default and follows the released Sprint 38 geometry path
without changing sample coordinates, vertex/face ordering, topology, bounds,
or deterministic digests.

## Architecture

The Fusion-independent domain path is:

```text
TPMSVolumeRequest
    -> resolve_domain(...)
    -> immutable DomainDefinition
        -> requested mode and active inputs
        -> resolved physical dimensions
        -> centered bounds
        -> effective cells
    -> VolumeCostEstimate
        -> effective resolution
        -> sample spacing
        -> intervals per cell
    -> safety validation
    -> field sampling / extraction / optional closure
    -> TPMSVolumeResult
```

`DomainDefinition` is the only authoritative conversion from sizing inputs to
physical dimensions. Sampling, wall-thickness validation, cost estimation,
boundary closure, and result reporting consume its resolved dimensions and do
not branch on Domain Mode. There is no TPMS-type-specific sizing behavior and
the domain core has no Fusion dependency.

The immutable request retains both UI banks as provenance. The active mode
determines which bank is validated and resolved. The immutable result and cost
estimate carry the same `DomainDefinition`.

## Domain-resolution rules

### Dimensions

```text
resolved Width  = requested Width
resolved Depth  = requested Depth
resolved Height = requested Height

Effective Cells X = Width / Period
Effective Cells Y = Depth / Period
Effective Cells Z = Height / Period
```

Effective counts may be fractional. Dimensions are never rounded to whole
periods. Existing ranges remain 1–500 mm.

### Cell Count

```text
Width  = Cells X × Period
Depth  = Cells Y × Period
Height = Cells Z × Period
```

Cells X/Y/Z are integers from 1 through 50. Period retains its 1–500 mm range.
Each calculated physical dimension must also remain within 1–500 mm. Invalid
types, fractional counts, non-finite values, zero, negative, out-of-range
counts, and oversized products are rejected before sampling.

Both modes retain the centered convention:

```text
minimum = (-Width/2, -Depth/2, -Height/2)
maximum = (+Width/2, +Depth/2, +Height/2)
```

Phase remains a field-coordinate offset and does not affect domain size.

## UI and parameter banks

Domain Mode appears with the domain inputs.

Dimensions shows Width, Depth, Height, shared Period, and read-only Effective
Cells X/Y/Z. Cell Count shows Cells X/Y/Z, shared Period, and read-only
Calculated Width/Depth/Height. Hidden controls remain alive; controls are not
recreated during a mode switch. Consequently each bank retains its session
values. Period is deliberately shared between both modes.

Changing Domain Mode, dimensions, cell counts, or Period follows the existing
parameter-change lifecycle: the command deletes its owned Preview, refreshes
visibility and diagnostics, validates the request, and enables Preview only
when valid. Repeated Preview still owns one body. Apply uses the active bank
and creates one permanent type-named MeshBody.

## Resolution and period alignment

Cell Count makes the mathematical rectangular domain span an integer number of
TPMS periods. Resolution X/Y/Z semantics are unchanged. Diagnostics report:

```text
sample spacing axis = resolved dimension / (effective resolution axis - 1)
intervals per cell  = (effective resolution axis - 1) / effective cells axis
```

If intervals per cell is fractional, the period-aligned mathematical bounds do
not imply node-for-node aligned tessellation on opposing boundaries. Sprint 39
does not change Resolution or add Samples per Cell. Automatic per-cell
resolution is future work.

## Safety and cost behavior

Domain resolution occurs while constructing the immutable request, before cost
estimation, scalar-grid allocation, extraction, closure, or Fusion insertion.
Calculated dimensions cannot bypass the existing 500 mm physical limit.

The existing Preview/Apply sample limits, cap-complexity limits, scalar-memory
estimates, Preview Quality scaling, and wall-thickness reliability checks
remain active. Error context now includes Domain Mode, active requested inputs,
Period, resolved dimensions, effective resolution, sample count, violated
limit, and corrective guidance.

## Determinism and compatibility

Requests omitting Domain Mode are Dimensions requests. `GyroidVolumeRequest`,
`TPMSVolumeRequest`, result aliases, generation functions, stable Fusion
command ID, command placement, body naming, timing behavior, and Preview
ownership remain compatible.

Dimensions and Cell Count requests that resolve to identical dimensions and
use identical remaining parameters produce identical indexed geometry and
digests. All released Gyroid, Schwarz P, Diamond, Neovius, Preview Quality, and
Sprint 38 numerical-regression fixtures remain unchanged.

## Representative Cell Count fixtures

All fixtures below use Surface + Cap, Period 20 mm, final 12³ resolution, and
1 × 1 × 1 cells unless noted.

| Type | Vertices | Faces | Components | Signed volume (mm³) | Digest |
| --- | ---: | ---: | ---: | ---: | --- |
| Gyroid | 2,176 | 4,356 | 1 | 4,000.00000000002 | `fe6a087444169a43085f489146137ed85018ded8fb1fadd1289264d819477b49` |
| Schwarz P | 1,954 | 3,924 | 1 | 3,999.020752315776 | `2252448fd26fdb441912636bc81d623a841db9060fe81ff801f47b9caecc23c7` |
| Diamond | 2,372 | 4,764 | 1 | 4,000.0000000000314 | `351af418f4e30599daeb77ba9bd9e9043b015b404ee41c78fc3a2e935845387b` |
| Neovius | 2,590 | 5,220 | 1 | 4,008.07909133754 | `11095ec55be8fca20e83adc75719712df99a0d72b8c4f786e21ba5ba8077ed88` |

Each fixture resolves to 20 × 20 × 20 mm with exact bounds `(-10,-10,-10)`
through `(10,10,10)`. All have zero boundary, nonmanifold,
inconsistent-winding, degenerate, and duplicate counts and measure watertight
and manifold.

The nonuniform Gyroid fixture uses 3 × 2 × 1 cells, 60 × 40 × 20 mm, and
18 × 14 × 10 samples:

```text
vertices: 4,834
faces: 9,740
components: 1
signed volume: 24,000.000000000102 mm³
bounds: (-30,-20,-10) through (30,20,10)
digest: 681ffab54ed8d9ab95c8c16248fff84bba75f0655cc33d0c262e05ad25c7e98a
```

It also has zero boundary, nonmanifold, inconsistent-winding, degenerate, and
duplicate counts.

## Performance

Five local runs compared Surface + Cap requests resolving to 60 × 40 × 20 mm
at 20 × 16 × 12 samples. Both modes produced digest
`25ef1067ce06e731d9993a36237102171946ee5114caed4e62afe609945da347`.
Median development-machine measurements were:

| Stage | Dimensions | Cell Count |
| --- | ---: | ---: |
| Standalone domain resolution | 0.0119 ms | 0.0162 ms |
| Validation and estimation | 0.0360 ms | 0.0423 ms |
| Scalar sampling | 3.418 ms | 3.359 ms |
| Extraction | 238.312 ms | 237.893 ms |
| Boundary closure | 322.805 ms | 322.830 ms |
| Geometry validation | 98.355 ms | 97.610 ms |
| Core total | 660.501 ms | 661.071 ms |

Resolver cost is negligible relative to extraction and closure. These are local
observations rather than universal performance guarantees. Fusion insertion
was not benchmarked outside Fusion.

## Known limitations

- the domain remains an axis-aligned rectangular box centered at the origin
- arbitrary selected-body clipping is not implemented
- Resolution remains independent of cell count
- period-aligned bounds do not guarantee node-aligned boundary tessellation
- no Samples per Cell or automatic resolution mode exists
- generation remains synchronous and non-interruptible
- there is no adaptive octree sampling, GPU acceleration, remeshing, or BRep
  conversion
- output remains a Fusion MeshBody
- no seamless assembly, manufacturing, or structural performance is claimed

## Manual Fusion acceptance checklist

- [x] TPMS Volume command still appears independently
- [x] Domain Mode shows Dimensions and Cell Count
- [x] Dimensions is the default
- [x] existing Dimensions workflow matches Sprint 38
- [x] Width/Depth/Height are visible only in Dimensions mode
- [x] Cells X/Y/Z are visible only in Cell Count mode
- [x] Effective Cells update in Dimensions mode
- [x] Calculated Size updates in Cell Count mode
- [x] 1 × 1 × 1 produces one-period dimensions
- [x] 3 × 2 × 4 produces the expected dimensions
- [x] nonuniform cell counts work
- [x] switching modes preserves both parameter banks
- [x] Period updates calculated dimensions
- [x] all four TPMS types work in Cell Count mode
- [x] Surface and Thickened work
- [x] Open and Cap work
- [x] Draft, Standard, and Final work
- [x] phases remain operational
- [x] repeated Preview leaves one body
- [x] switching modes removes the old Preview
- [x] Apply creates one permanent MeshBody
- [x] Cancel and stop clean owned previews
- [x] oversized calculated dimensions show a clear error
- [x] rejection leaves no stale body
- [x] Procedural Lab remains operational
- [x] Gyroid Surface remains operational
- [x] Generate Nature and Nature Library remain operational
