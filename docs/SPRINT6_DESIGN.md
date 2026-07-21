# Sprint 6 — First Fusion Integration

Sprint 6 demonstrates the complete NatureGenerator pipeline inside Autodesk
Fusion 360 while preserving the existing separation between the application,
generator runtime, and geometry core.

The current pipeline ends at a Fusion-independent mesh:

```text
NaturePreset
    |
    v
Generator Runtime
    |
    v
TriangleMesh
```

Sprint 6 extends that pipeline through the first Fusion boundary:

```text
Fusion Command
    |
    v
NaturePreset
    |
    v
Generator Runtime
    |
    v
TriangleMesh
    |
    v
Fusion Adapter
    |
    v
Fusion MeshBody
```

## Goal

Produce the first working NatureGenerator demonstration inside Fusion 360.

A user should be able to:

- start the add-in;
- execute one command;
- generate the Sponge preset; and
- create a `MeshBody` in the active design.

## Deliverables

### 1. Fusion Adapter

The Fusion Adapter converts a core `TriangleMesh` into an
`adsk.fusion.MeshBody`. It owns all Fusion-specific object creation, command
registration, error translation, and active-design integration. Autodesk API
calls and imports remain isolated here so every other layer stays importable and
testable in ordinary Python.

The adapter accepts completed mesh data; it does not generate scalar fields,
sample voxels, or implement triangulation. It converts the current
millimeter-based geometry coordinates to Fusion's centimeter database units at
the boundary.

### 2. Fusion Command

Add one minimal command named **Generate Sponge**. The command obtains the
available Sponge definition from `PresetFactory`, executes it through
`GeneratorFactory`, passes the resulting `TriangleMesh` to the Fusion Adapter,
and reports a concise success or failure message.

No parameter dialog is required. The command uses the Sponge preset defaults and
keeps orchestration thin rather than duplicating runtime or adapter behavior.

### 3. End-to-End Pipeline

```text
Fusion Command
    |
    v
Preset
    |
    v
Generator Runtime
    |
    v
TriangleMesh
    |
    v
Fusion Adapter
    |
    v
MeshBody
```

The command selects user intent, the Generator Runtime produces validated mesh
data, and the Fusion Adapter performs the only conversion into Autodesk runtime
objects.

### 4. Package Structure

Sprint 6 should extend the existing packages rather than introduce parallel
abstractions with overlapping names:

```text
NatureGenerator/
    NatureGenerator.py              # Delegate add-in start and stop
    commands/
        generate_sponge.py          # Fusion-independent command orchestration
    fusion/
        mesh_body.py                # TriangleMesh -> Fusion MeshBody adapter
        runtime.py                  # Fusion command registration and lifecycle
```

The existing `fusion/mesh_body.py` placeholder is the natural adapter location.
Using it avoids confusion with the already implemented core `MeshBuilder`.
`commands/generate_sponge.py` is intentionally specific to the first demo; a
generic command can be introduced later when parameter and preset selection UI
exists.

## Out of Scope

- Voronoi
- Gray-Scott
- Bone
- Bark
- Rock
- Preview rendering
- Live updates
- GPU support
- Parameter editor
- Performance optimization

## Design Principles

- The Geometry Core remains Fusion-independent.
- The Fusion API exists only inside the Fusion Adapter layer.
- Generator Runtime must not import `adsk`.
- Commands stay thin and delegate generation and conversion.
- Future presets reuse the same preset-to-runtime-to-adapter pipeline.
- `TriangleMesh` is the data contract across the Fusion boundary.
- Fusion failures are translated into clear command-level messages without
  changing geometry behavior.

## Definition of Done

- [ ] Add-in loads.
- [ ] Command appears.
- [ ] Sponge generates.
- [ ] `MeshBody` is created in the active design.
- [ ] No `adsk` leakage enters the Geometry Core.
- [ ] Tests pass.
- [ ] Documentation is updated.
- [ ] Draft PR is created.
- [ ] Sprint is ready for review.

## Future Roadmap

Later Sprints will add Voronoi and Gray-Scott generators, preview workflows,
editable generation parameters, additional natural-form presets, and targeted
performance optimization. Those capabilities should extend the same command,
preset, Generator Runtime, Geometry Core, and Fusion Adapter boundaries rather
than bypass them.
