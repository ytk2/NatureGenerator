# NatureGenerator

NatureGenerator is a Python add-in for Autodesk Fusion 360 that will generate
manufacturable procedural forms inspired by nature.

The project includes a Fusion-independent procedural geometry pipeline and a
user-facing nature preset framework. The first available form is Sponge, backed
by the configurable gyroid scalar field.

## Planned geometry pipeline

```text
Nature Preset
    -> Generator Runtime
    -> Scalar Field
    -> Voxel Grid
    -> Marching Tetrahedra
    -> Triangle Mesh
        -> STL Export
        -> Future Fusion Adapter
```

Geometry calculations live in `core/` and `generators/` and must remain usable
without Autodesk Fusion 360. Integration code that imports the Fusion API belongs
in `fusion/` or the add-in entry point.

## Repository layout

- `NatureGenerator.py`: Fusion 360 add-in entry point.
- `NatureGenerator.manifest`: add-in metadata.
- `commands/`: command definitions and UI coordination.
- `core/`: Fusion-independent geometry primitives, sampled grids, meshes, and
  STL serialization.
- `generators/`: procedural form generation algorithms.
- `presets/`: user-facing natural-form definitions and availability metadata.
- `fusion/`: adapters between core meshes and Fusion 360.
- `examples/`: small usage examples.
- `tests/`: dependency-free automated tests.
- `resources/`: icons and other add-in assets.

## Development

NatureGenerator currently requires no third-party Python packages. Run the
foundation tests from the repository root with:

```bash
PYTHONPATH=NatureGenerator python3 -m unittest discover -s NatureGenerator/tests
```

For Fusion 360 installation and contribution guidance, see
[`CONTRIBUTING.md`](CONTRIBUTING.md). The planned milestones are documented in
[`ROADMAP.md`](ROADMAP.md).

## Nature presets

Commands and future UI code select a `NaturePreset` instead of importing or
naming mathematical algorithm classes. A preset contains immutable presentation
metadata, parameter defaults, a stable generator ID, and an explicit availability
status. It never samples a field or extracts a mesh.

```python
from presets import PresetFactory

for preset in PresetFactory.list_all():
    print(preset.display_name, preset.available)

sponge = PresetFactory.get("sponge")
```

Built-ins are registered explicitly for predictable Fusion behavior; the
framework does not scan directories or dynamically import arbitrary files.

| Preset | Category | Generator ID | Status |
| --- | --- | --- | --- |
| Coral | Aquatic | `gray_scott` | Unavailable — generator not implemented |
| Sponge | Aquatic | `gyroid` | Available |
| Bone | Biological | `cellular` | Unavailable — generator not implemented |
| Bark | Botanical | `noise` | Unavailable — generator not implemented |
| Rock | Geological | `voronoi` | Unavailable — generator not implemented |

## Generator runtime

`GeneratorFactory` is the execution boundary between user-facing presets and
algorithm implementations. It resolves an available preset's stable
`generator_id` through an explicit registry and returns a fresh `Generator`.
There is no filesystem discovery or algorithm selection chain.

```python
from generators import GeneratorFactory
from presets import PresetFactory

preset = PresetFactory.get("sponge")
result = GeneratorFactory.generate(preset)

print(result.statistics.face_count)
print(result.elapsed_time)
print(result.warnings)
```

The current `GyroidGenerator` constructs `GyroidField`, samples a `VoxelGrid`,
extracts a `TriangleMesh` with marching tetrahedra, validates it, and returns an
immutable `GeneratorResult`. The finite gyroid crop normally has boundary edges,
so that expected open-mesh condition is returned as a warning rather than being
misrepresented as watertight.

## Gyroid scalar field

`GyroidField` evaluates the dimensionless gyroid function after mapping one
world-space `cell_size` to a full `2π` period:

```text
g(x, y, z) = sin(x)cos(y) + sin(y)cos(z) + sin(z)cos(x)
field(x, y, z) = abs(g(x, y, z)) - thickness
```

Negative field values are inside the gyroid sheet band, zero values describe its
two boundaries, and positive values are outside. `thickness` is a field-value
half-band rather than a world-space distance.

```python
from generators.gyroid import GyroidField
from generators.visualization import render_ascii_slice

field = GyroidField(cell_size=10.0, thickness=0.2)
value = field.sample(1.0, 2.0, 3.0)

preview = render_ascii_slice(
    field,
    (-10.0, 10.0),
    (-10.0, 10.0),
    z=0.0,
)
print(preview)
```

The preview helper samples text only; it does not create triangles or meshes.

## Marching tetrahedra

The dependency-free extractor accepts a sampled `VoxelGrid` and returns an
indexed `TriangleMesh`:

```python
from core.marching_tetrahedra import extract_isosurface
from core.voxel_grid import VoxelGrid

grid = VoxelGrid.sample(field, (-10, -10, -10), (10, 10, 10), (32, 32, 32))
mesh = extract_isosurface(grid, iso_value=0.0)
print(mesh.statistics())
```

It interpolates edge crossings, shares vertices across cached grid edges,
orients normals toward increasing field values, and uses a consistent six-part
tetrahedral decomposition. A closed isosurface whose exterior fits inside the
sampling bounds should be watertight; surfaces touching the bounds remain open.

Run the simple benchmark with:

```bash
PYTHONPATH=NatureGenerator python3 NatureGenerator/examples/benchmark_marching_tetrahedra.py
```

## Mesh processing and export

`MeshBuilder` incrementally creates indexed meshes while welding exact or
tolerance-close vertices. `optimize_mesh()` conservatively welds duplicates and
removes duplicate triangles, degenerate faces, and unused vertices; it does not
decimate or smooth geometry.

`MeshValidator` reports boundary edges, nonmanifold edges and vertex fans,
inconsistent winding, degenerate and duplicate faces, unused vertices, and
connected components.
`TriangleMesh.statistics()` also supplies surface area, signed volume, bounds,
and watertight/manifold status.

Meshes can be written as binary or ASCII STL, Wavefront OBJ, or ASCII PLY:

```python
from core.mesh_optimizer import optimize_mesh
from core.mesh_validator import MeshValidator
from core.obj_writer import write_obj
from core.ply_writer import write_ply
from core.stl_writer import write_binary

mesh = optimize_mesh(mesh, weld_tolerance=1e-9)
report = MeshValidator(require_watertight=True).validate(mesh)
if not report.valid:
    raise ValueError(report.issues)

write_binary(mesh, "form.stl")
write_obj(mesh, "form.obj")
write_ply(mesh, "form.ply")
```
