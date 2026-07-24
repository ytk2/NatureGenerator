# Sprint 28 Design — Procedural Lab Foundation

## Product surfaces

NatureGenerator now has two intentionally separate Fusion commands:

- **Generate Nature** creates geometry from a registered `NaturePreset`.
- **Procedural Lab** accepts geometry the user already created and executes a
  registered `ProceduralOperator`.

An operator is not a preset, Family, or generator. Procedural Lab does not use
`PresetCatalog` or `GeneratorFactory`.

## Dependency direction

```text
Procedural Lab Fusion command
    -> FusionSelectionAdapter
        -> ProceduralInputGeometry
    -> OperatorPipeline
        -> ProceduralOperatorRegistry
        -> PassThroughOperator
    -> ProceduralResult
    -> MeshBodyBuilder
    -> Fusion MeshBody

Procedural models and operators
    -> existing core.TriangleMesh
```

Only `fusion/` imports `adsk`. The procedural application command and
`procedural/` contracts use plain immutable Python data. The selected Fusion
entity is snapshotted at the adapter boundary; no Autodesk object enters the
operator core.

## Input adapter

Exactly one `BRepBody` or `MeshBody` is accepted. A solid is tessellated with
Fusion's mesh calculator. Preview requests use a coarser controlled surface
tolerance than final execution. This means a BRep Preview and final mesh can
differ in tessellation density while each remains equivalent to its own
adapted input. Tessellation is Fusion-version-dependent and does not preserve
analytic BRep surfaces.

A `MeshBody` uses its available polygon/display mesh. Fusion centimetres are
converted to the core's millimetres. Empty, non-triangular, out-of-range, or
non-finite data is rejected by the adapter and existing `TriangleMesh`
validation. Source name, entity token/runtime identifier, type, units, and
tessellation provenance are captured without modifying the source.

## Pass Through and pipeline

The immutable registry contains exactly `pass_through`. Dropdown labels come
from this registry. Pass Through constructs a separate `TriangleMesh` with the
same ordered vertices and faces, so winding and topology remain unchanged and
the canonical SHA-256 digest matches exactly.

`OperatorPipeline` stores operator IDs as an ordered tuple. Sprint 28 validates
exactly one entry, while the representation and execution boundary permit a
later ordered operator stack without changing operator contracts.

## Result and GeneratedAsset decision

`ProceduralResult` directly owns the common `TriangleMesh` payload plus
statistics, digests, operator metadata, source provenance, execution context,
and units. It does not create a `GeneratedAsset` in Sprint 28: that model
requires natural preset and generator identity and would force Nature Library
semantics onto selected user geometry. A future neutral asset composition
layer may wrap the same mesh without changing this result contract.

## Preview ownership

Each Procedural Lab command instance owns at most one temporary body through
its own controller. Repeated Preview deletes that body before replacement.
Source or operator changes invalidate and remove it. Cancel, command destroy,
and add-in stop delete only bodies referenced by Procedural Lab controllers.
OK first removes the preview, re-adapts at final quality, executes the pipeline,
and inserts a permanent mesh named
`NatureGenerator Procedural — Pass Through`.

The Nature Library preview controller and names are not shared, scanned, or
deleted.

## Non-goals and limitations

Sprint 28 performs no geometric transformation. It does not preserve BRep
analytic surfaces, source materials, appearances, UVs, per-face attributes, or
mesh normals as separate channels. It creates MeshBody output only and exposes
no modifier stack, background execution, progress, cancellation, or exporter.
