# Sprint 32 Design — Procedural Operator Stack

## Summary

Sprint 32 turns the ordered pipeline foundation into a fixed three-slot
Procedural Lab stack. It changes orchestration and presentation, not operator
algorithms or the Fusion adapter.

```text
Fusion source
    -> ProceduralInputGeometry
    -> Operator 1
    -> immutable stage mesh
    -> Operator 2
    -> immutable stage mesh
    -> Operator 3
    -> final ProceduralResult
    -> Preview or permanent MeshBody
```

Only active slots execute. None slots are omitted while the relative order of
the remaining operators is preserved.

## Immutable stack contracts

`OperatorInvocation` owns one operator ID and one immutable parameter mapping.
`ProceduralStackRequest` owns the original input, one to three ordered
invocations, and Preview/Final execution context.

`OperatorPipeline.execute_stack` validates that invocation order matches its
ordered operator-ID tuple. After each non-final stage it creates a new
`ProceduralInputGeometry` around the stage mesh while retaining original source
type, name, identifier, units, and provenance. Operators therefore remain
unaware of stacks and continue to implement the same single-request contract.

The final result records the original input digest plus scalar stack metadata:
operator count and the ordered `>`-separated operator IDs. No intermediate
Fusion bodies are created.

The legacy `ProceduralRequest`, `OperatorPipeline.execute`, and
`execute_procedural` APIs remain available and execute one operator through the
same stack engine.

## Fixed Fusion UI

Procedural Lab exposes:

- Operator 1
- Operator 2
- Operator 3

Each selector contains None, Pass Through, Noise Displacement, Subdivision, and
Voronoi Surface. Operator 1 defaults to Pass Through to preserve the previous
single-operator startup behavior. Operators 2 and 3 default to None.

Every slot has its own metadata-rendered parameter controls for all registered
operators. Only controls belonging to the selected operator and slot are
visible. Hidden controls retain their values, so changing Operator 2 cannot
reset Operator 1 or Operator 3. No operator-specific UI conditional exists.

Source, selector, or parameter changes call the same command-owned preview
cleanup path. An all-None stack is invalid.

## Execution order

Active invocations always execute from the lowest slot number to the highest.
Order is intentionally observable:

```text
Subdivision -> Noise Displacement
```

evaluates Noise at newly introduced midpoint positions, while:

```text
Noise Displacement -> Subdivision
```

subdivides the already displaced piecewise-linear surface. Focused tests
confirm that these results have different canonical digests.

Mixed two- and three-stage tests cover:

- Subdivision -> Noise Displacement
- Subdivision -> Voronoi Surface
- Voronoi Surface -> Noise Displacement
- Subdivision -> Voronoi Surface -> Noise Displacement

## Preview and Apply

Fusion geometry is adapted once per Preview or Apply. The full stack executes
in the procedural core. Preview inserts one temporary final MeshBody and uses
the unchanged `ProceduralPreviewController` replacement and cleanup behavior.
Apply removes Preview and inserts one permanent final MeshBody.

A single active slot retains its operator display name. Multiple active slots
use `NatureGenerator Procedural Preview — Operator Stack` and
`NatureGenerator Procedural — Operator Stack`.

Cancel, destroy, and add-in stop still remove only the body directly owned by
the current Procedural Lab command.

## Architecture boundaries

- operators remain independent of `adsk`
- OperatorRegistry remains the source of operator and parameter metadata
- OperatorPipeline owns ordering and stage-to-stage adaptation
- Fusion owns only selection, controls, lifecycle, and MeshBody insertion
- Nature Library, GeneratorFactory, presets, and GeneratedAsset are unchanged

## Limitations

- the stack has exactly three UI slots
- there is no drag-and-drop, insertion, deletion, or variable-length stack
- None slots do not produce explicit pipeline stages
- there are no intermediate previews, bodies, caches, or per-stage timing views
- each Preview and Apply recomputes the complete stack
- expensive combinations can grow quickly, especially high Subdivision levels
- errors stop execution and produce no partial Fusion output
- Procedural Lab still produces MeshBody output only
