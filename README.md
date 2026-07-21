# NatureGenerator

NatureGenerator is a Python add-in for Autodesk Fusion 360 that will generate
manufacturable procedural forms inspired by nature.

The project is currently establishing its architecture. The first planned
generator is a gyroid-based form generator, but mesh generation is intentionally
not implemented in this foundation release.

## Planned geometry pipeline

```text
Scalar Field
    -> Voxel Grid
    -> Marching Tetrahedra
    -> Triangle Mesh
    -> Fusion MeshBody / STL
```

Geometry calculations live in `core/` and `generators/` and must remain usable
without Autodesk Fusion 360. Integration code that imports the Fusion API belongs
in `fusion/` or the add-in entry point.

## Repository layout

- `NatureGenerator.py`: Fusion 360 add-in entry point.
- `NatureGenerator.manifest`: add-in metadata.
- `commands/`: command definitions and UI coordination.
- `core/`: Fusion-independent geometry primitives and data structures.
- `generators/`: procedural form generation algorithms.
- `fusion/`: adapters between core meshes and Fusion 360.
- `examples/`: small usage examples.
- `tests/`: dependency-free automated tests.
- `resources/`: icons and other add-in assets.

## Development

NatureGenerator currently requires no third-party Python packages. Run the
foundation tests from the repository root with:

```bash
python3 -m unittest discover -s NatureGenerator/tests
```

For Fusion 360 installation and contribution guidance, see
[`CONTRIBUTING.md`](CONTRIBUTING.md). The planned milestones are documented in
[`ROADMAP.md`](ROADMAP.md).
