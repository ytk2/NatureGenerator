# Sprint 32 Plan — Procedural Operator Stack

## Status

Implementation complete; awaiting review and real Autodesk Fusion acceptance.

## Goal

Execute up to three Procedural Lab operators sequentially in one Preview or
Apply operation while preserving single-operator compatibility.

## Scope

- replace the single Fusion selector with three fixed operator slots
- allow None or any registered operator in every slot
- give every slot an independent parameter bank
- execute active slots top-to-bottom through the existing OperatorPipeline
- feed each stage's immutable output mesh into the next stage
- preserve the current source adapter, preview ownership, and final insertion
- retain the legacy single-operator request and execution APIs

## Out of scope

- adding, deleting, dragging, or reordering a variable number of slots
- branching graphs, parallel stages, cached intermediate bodies, or stage previews
- automatic parameter transfer between operator types or slots
- changes to Nature Library, operator algorithms, or Fusion mesh insertion

## Acceptance criteria

- one-, two-, and three-stage stacks execute deterministically in slot order
- None slots are skipped
- changing order changes geometry where operations are non-commutative
- each slot retains its own values independently
- Preview creates and owns only the final stack body
- Apply inserts only the final stack result
- all existing single operators and Nature Library regressions remain green
