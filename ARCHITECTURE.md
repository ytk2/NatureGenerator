# Architecture

## Design goals

NatureGenerator separates procedural geometry from Autodesk Fusion 360 so that
geometry algorithms can be tested with the Python standard library alone. The
core should produce plain Python data that can later be consumed by Fusion 360,
an STL writer, or another adapter.

## Layer boundaries

### Core geometry (`core/`)

Defines scalar-field contracts, voxel-grid data, indexed triangle-mesh data, and
STL serialization. This layer must not import `adsk` or depend on Fusion 360
runtime state.

The mesh stage includes deterministic construction and vertex welding,
conservative cleanup, face and vertex normals, topology validation and
statistics, plus STL, OBJ, and PLY serialization. Optimization does not alter the
surface through smoothing or decimation.

### Generators (`generators/`)

Evaluates procedural forms and extracts surfaces. Generator algorithms may use
`core/`, but must remain independent of Fusion 360.

The current `GyroidField` maps world coordinates to a periodic mathematical
gyroid and returns `abs(g) - thickness`. The core marching tetrahedra stage can
extract any sampled scalar field without adding generator-specific mesh logic.

### Application commands (`commands/`)

Coordinates user intent and generation workflows. Commands pass user parameters
to generators and hand the resulting mesh to an output adapter.

### Fusion integration (`fusion/`)

Owns every conversion to Fusion 360 objects, including `MeshBody` creation and
Fusion-specific validation. Imports of Autodesk's `adsk` modules are confined to
this layer and the add-in entry point.

## Planned pipeline

```text
Scalar Field
    -> Voxel Grid
    -> Marching Tetrahedra
    -> Triangle Mesh
    -> Fusion MeshBody / STL
```

1. A scalar field maps each point in space to a value.
2. The field is sampled at regular voxel-grid points.
3. Marching tetrahedra finds the chosen isosurface inside each voxel.
4. The extractor emits a Fusion-independent indexed triangle mesh.
5. The Fusion adapter creates a `MeshBody`, or the core STL writer serializes
   the mesh directly.

The sampling, extraction, and mesh stages should use explicit tolerances and
deterministic iteration. Manufacturability checks—such as minimum feature size,
watertightness, and build-volume limits—will be introduced as separate passes so
they do not become implicit side effects of surface extraction.

## Dependency direction

```text
NatureGenerator.py -> commands -> generators -> core
                            \-> fusion -------> core
```

Dependencies point inward toward plain-Python geometry types. `core/` never
imports from the other project packages.
