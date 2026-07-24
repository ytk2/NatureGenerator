# NatureGenerator

> Generate manufacturable natural geometry directly inside Autodesk Fusion.

NatureGenerator v0.11.0 is the stable Generator Variants release. Sponge,
Coral, Rock, Bark, Root, Bone, and Crystal are executable on current main. Sprint 15 adds an internal Rock
Family architecture while preserving the released UI.

![Generate Nature dialog and generated Sponge mesh](docs/images/v0.5.0-generate-nature-dialog.png)

**Stable baseline:** `v0.11.0 — Generator Variants`

[Getting started](docs/GETTING_STARTED.md) · [Gallery](docs/GALLERY.md) ·
[Vision](VISION.md) · [Architecture](ARCHITECTURE.md) · [Roadmap](ROADMAP.md) ·
[Releases](docs/RELEASES.md) · [Releasing](docs/RELEASING.md) ·
[Contributing](CONTRIBUTING.md)

The project includes a Fusion-independent procedural geometry pipeline and a
user-facing nature preset framework. Sponge is backed by the configurable
gyroid scalar field, Coral uses a closed branching implicit solid, and Rock
uses a deformed ellipsoid with dependency-free value noise. Bark uses a closed
finite cylinder with directional, anisotropic surface variation. Root uses a
bounded deterministic skeleton and a union of tapered segment fields. Bone uses
a curved variable-radius shaft smoothly joined to asymmetric rounded ends.
Crystal uses a seeded irregular polygonal prism with a tapered termination.

Sprint 28 adds **Procedural Lab** as a separate Fusion command. Unlike Generate
Nature, it selects one existing solid or mesh, adapts it to `TriangleMesh`, and
runs a registered operator pipeline. The initial Pass Through operator proves
Preview and permanent MeshBody insertion without changing the source. See
[`docs/SPRINT28_DESIGN.md`](docs/SPRINT28_DESIGN.md).

Sprint 15 refactors Rock internally into immutable Macro Shape, Facet Layout,
and Surface Detail stages, then adds River Stone as a parameter-only proof of
the family architecture. It preserves the accepted Sprint 14 geometry and all
public workflows; River Stone is not yet exposed in Fusion. See
[`docs/SPRINT15_DESIGN.md`](docs/SPRINT15_DESIGN.md).

## Geometry pipeline

```text
Nature Preset
    -> Generator Runtime
    -> Procedural Geometry
        -> Scalar Field -> Voxel Grid -> Marching Tetrahedra
        -> Direct Indexed Construction (Crystal)
    -> Triangle Mesh
    -> Generated Asset
        -> Material Intent
        -> Object-space Mapping
        -> Texture Resources (currently empty)
        -> Asset Metadata
        -> Future Asset Exporters
        -> Fusion Adapter
            -> Fusion MeshBody
```

Geometry calculations live in `core/` and `generators/` and remain usable
without Autodesk Fusion 360. Functional Autodesk API integration belongs in
`fusion/`; the add-in entry point uses `adsk` only to report fatal startup and
shutdown diagnostics. Command orchestration delegates to the adapter boundary.

## Repository layout

- `NatureGenerator.py`: Fusion 360 add-in entry point.
- `NatureGenerator.manifest`: add-in metadata.
- `commands/`: command definitions and UI coordination.
- `core/`: Fusion-independent geometry primitives, sampled grids, meshes, and
  STL serialization.
- `assets/`: renderer-neutral generated assets, material and mapping intent,
  shared natural-material discovery metadata, future thumbnail references,
  texture resources, provenance metadata, and future exporter contracts.
- `generators/`: procedural form generation algorithms.
- `procedural/`: Fusion-independent selected-geometry contracts, operator
  registry, Pass Through operator, and pipeline.
- `presets/`: user-facing natural-form definitions and availability metadata.
- `preset_catalog.py`: application composition of presets and optional Family
  registries.
- `variants/`: immutable curated parameter configurations and registry.
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

Sprint 27 standardizes immutable **Form** and **Generation** parameter groups
for every built-in while keeping groups optional for legacy presets. Shared
`NaturalMaterial` records pair the existing renderer-neutral material values
with Asset Browser categories, search keywords, and an optional future
thumbnail reference. No thumbnail UI or image resources are introduced. See
[`docs/SPRINT27_DESIGN.md`](docs/SPRINT27_DESIGN.md).

Sprint 18 adds `PresetDefinition` and `PresetCatalog` above the existing API.
The catalog associates each `NaturePreset` with an optional Family registry.
Rock points to `RockFamilyRegistry`, and Sprint 19 promotes Bark from a
placeholder to `BarkFamilyRegistry`. Sprint 20 promotes Coral to
`CoralFamilyRegistry`, and Sprint 21 promotes Sponge to
`SpongeFamilyRegistry`. Sprint 23 associates Root with `RootFamilyRegistry`,
Sprint 24 introduces Bone through `BoneFamilyRegistry`, and Sprint 26 introduces
Crystal through `CrystalFamilyRegistry`. Fusion reads these associations generically and
does not import concrete Family registries directly. See
[`docs/SPRINT18_DESIGN.md`](docs/SPRINT18_DESIGN.md).

```text
PresetCatalog
    -> PresetDefinition
        -> NaturePreset
        -> optional Family registry
```

## Generator variants and Rock families

Sprint 13 development adds three curated parameter configurations for each
executable preset. Variants are immutable, Fusion-independent data and use only
existing preset parameters; they do not change generator algorithms.

| Preset | Variants |
| --- | --- |
| Sponge | Fine, Balanced, Bold |
| Coral | Fine Branching, Balanced, Massive |
| Bark | Subtle, Grooved, Twisted |
| Root | Sparse, Balanced, Dense |

The generic **Variant** dropdown also contains **Custom**. Selecting a named
variant updates the current inputs; editing any value changes the selection to
Custom. Switching presets retains each preset's last values and restores them
as Custom. Preview and OK always read current values through the unchanged
`GenerationRequest` path. Variant names describe parameter configurations and
do not claim species reproduction or biological realism. See
[`docs/SPRINT13_DESIGN.md`](docs/SPRINT13_DESIGN.md).

Sprint 16 Phase 1 replaces the Rock Variant presentation with a Family
dropdown populated by the Rock Family Registry. Smooth, Weathered, Rugged,
River Stone, Granite, Basalt, and Broken Rock are selectable; manual Size,
Roughness, Seed, and Resolution edits remain available. Preview and Final
retain the same generation paths and differ only in sampling resolution. Other
presets keep their existing Variant workflow. See
[`docs/SPRINT16_DESIGN.md`](docs/SPRINT16_DESIGN.md).

Sprint 16 passed manual Autodesk Fusion 360 validation: the Rock Family
dropdown displayed all four families, family switching updated Preview, River
Stone generated correctly, existing Rock results remained unchanged, and no
runtime errors were observed.

Sprint 17 adds Granite, Basalt, and Broken Rock through three-stage parameter
tuning only. Granite is broad and heavy, Basalt is vertically directional and
planar, and Broken Rock is an angular wedge dominated by fracture faces. These
are procedural design approximations, not geological simulations. See
[`docs/SPRINT17_DESIGN.md`](docs/SPRINT17_DESIGN.md).

Real Autodesk Fusion acceptance confirmed that all three new silhouettes are
visually distinct and behave correctly, while existing Rock families and
non-Rock presets remain functional.

Sprint 19 registers Bark through the same preset-level Family architecture.
The initial **Classic Bark** Family preserves the accepted cylindrical,
directionally grooved Bark geometry and all seven existing parameters. Preview
and OK carry the stable `classic_bark` ID through the unchanged request path.
See [`docs/SPRINT19_DESIGN.md`](docs/SPRINT19_DESIGN.md).

Sprint 20 registers **Classic Coral** through `CoralFamilyRegistry`. It
preserves the accepted Seed 0 branching mesh and adds a metadata-driven Seed
control for deterministic connected branch variation. Preview and OK carry
`classic_coral` through the existing request path. See
[`docs/SPRINT20_DESIGN.md`](docs/SPRINT20_DESIGN.md).

Sprint 21 registers **Classic Sponge** through `SpongeFamilyRegistry`. It
creates a closed rounded porous solid whose exterior-connected spherical pores
vary deterministically with Seed. Preview and OK use the same
`GenerationRequest` and mesh pipeline. See
[`docs/SPRINT21_DESIGN.md`](docs/SPRINT21_DESIGN.md).

Sprint 23 registers **Classic Root** through `RootFamilyRegistry`. The existing
Root parameters, deterministic Seed behavior, Preview/OK pipeline,
`GeneratedAsset` defaults, and accepted geometry digest remain unchanged.
Requests without a Family ID continue to resolve to the same geometry. Every
implemented preset now follows the PresetCatalog → Family Registry →
GenerationRequest → GeneratorFactory → GeneratedAsset path. See
[`docs/SPRINT23_DESIGN.md`](docs/SPRINT23_DESIGN.md).

Sprint 24 registers **Classic Bone** through `BoneFamilyRegistry`. It generates
a grounded, watertight stylized long bone with a curved narrow shaft, enlarged
asymmetric ends, deterministic surface detail, and the existing GeneratedAsset
defaults. See [`docs/SPRINT24_DESIGN.md`](docs/SPRINT24_DESIGN.md).

Sprint 25 expands `RockFamilyRegistry` with **Classic Rock**, **Layered Rock**,
**Weathered Rock**, and **River Rock**. Classic Rock is byte-identical to the
accepted canonical result; all seven earlier Rock Family IDs and digests remain
available. The new families use the same generic dropdown, Preview, OK,
`GenerationRequest`, `RockGenerator`, and `GeneratedAsset` paths. See
[`docs/SPRINT25_DESIGN.md`](docs/SPRINT25_DESIGN.md).

Sprint 26 introduces **Classic Crystal** through `CrystalFamilyRegistry`. The
new deterministic generator produces a closed elongated prism with major
facets, a slightly irregular cross section, and a tapered point termination.
It uses the generic Family, Preview, OK, validation, and GeneratedAsset paths.
See [`docs/SPRINT26_DESIGN.md`](docs/SPRINT26_DESIGN.md).

Sprint 13 passed real Autodesk Fusion acceptance on macOS. One filtered Variant
dropdown appeared, named selections updated parameters, Preview used and
replaced the current configuration, manual edits selected Custom, Preset
switching worked, and OK/Cancel remained functional. No event recursion or
duplicate controls were observed. Sprint 13 is released in `v0.11.0`.

| Preset | Category | Generator ID | Status |
| --- | --- | --- | --- |
| Coral | Aquatic | `coral` | Available |
| Sponge | Aquatic | `gyroid` | Available |
| Bone | Biological | `bone` | Available |
| Bark | Botanical | `bark` | Available |
| Root | Botanical | `root` | Available |
| Rock | Geological | `rock` | Available |

## Generator runtime

`GeneratorFactory` is the execution boundary between user-facing presets and
algorithm implementations. It resolves an available preset's stable
`generator_id` through an explicit registry and returns a fresh `Generator`.
There is no filesystem discovery or algorithm selection chain.

```python
from generators import GenerationRequest, GeneratorFactory

request = GenerationRequest(
    preset_id="sponge",
    parameter_overrides={"cell_size": 12.0, "thickness": 0.25},
    resolution=21,
)
result = GeneratorFactory.generate_request(request)

print(result.statistics.face_count)
print(result.asset.material.display_name)
print(result.elapsed_time)
print(result.warnings)
```

`GyroidGenerator` constructs `GyroidField`, samples a `VoxelGrid`,
extracts a `TriangleMesh` with marching tetrahedra, validates it, and returns an
immutable `GeneratorResult`. The legacy finite Gyroid crop remains available
through this stable API. Classic Sponge instead uses a closed porous field and
requires watertight validation.

Sprint 22 adds a `GeneratedAsset` to every `GeneratorResult`. The asset
references the exact same `TriangleMesh` instance as `result.mesh`, then
associates renderer-neutral material intent, object-space procedural mapping,
an initially empty baked texture set, and immutable generation provenance.
Existing mesh consumers and Fusion insertion remain compatible. An explicit
exporter interface and registry establish the future file-export boundary, but
Sprint 22 does not add OBJ/MTL, glTF/GLB, USD/USDZ, UV unwrapping, texture
baking, or new STL production behavior.

`CoralGenerator` uses the same Geometry Core to extract a connected union of
branch capsules. Its surface stays inside the sampled domain and must pass
watertight validation. `GeneratorFactory.create_for_preset(preset_id)` resolves
both forms through explicit preset and generator registration. The
request-oriented `SpongeGenerator`, `CoralGenerator`, `RockGenerator`, and
`BarkGenerator`, and `RootGenerator` each return a
`TriangleMesh`; the factory preserves the public immutable `GeneratorResult`
API. Sponge geometry uses a closed rounded-body and spherical-pore field.

`GeneratorFactory.generate(preset, parameters)` remains available for existing
callers and uses the original resolution of 17 samples per axis.

## Interactive Fusion generation

The **Generate Nature** command appears in the Design workspace's Add-Ins panel.
Its dialog selects Sponge, Coral, Rock, Bark, or Root and builds each
form's inputs from immutable preset parameter metadata before it runs the
Generator Runtime and inserts the resulting `TriangleMesh` as a `MeshBody` in
the active design.

```text
Generate Nature
    -> GenerationRequest
    -> PresetFactory
    -> GeneratorFactory
    -> TriangleMesh
    -> Fusion Adapter
    -> MeshBody
```

The dialog exposes each preset's metadata-defined inputs:

- **Cell Size:** physical form scale; the overall Sponge body and Coral branch
  branching scale for Coral.
- **Thickness:** relative Sponge pore size and Coral branch radius
  for Coral.
- **Coral Seed:** deterministic shared-node variation of the connected branch
  silhouette.
- **Sponge Seed:** deterministic rounded pore placement and size variation.
- **Resolution:** samples per axis; higher values increase mesh quality and
  pure-Python runtime cost. The supported range is 9–41 and the default is 17.
- **Rock Size, Roughness, and Seed:** physical scale, bounded surface variation,
  and a repeatable deterministic variation key.
- **Bark Diameter, Height, Bark Depth, Groove Scale, Twist, and Seed:** trunk
  dimensions and repeatable directional ridge controls. Bark resolution is
  constrained to 29–41, with a default of 33.
- **Root Length, Root Radius, Branch Count, Branching, Spread, Taper, Gravity,
  and Seed:** dimensions and repeatable staged branching controls. Root
  resolution is constrained to 37–41, with a default of 37.
- **Bone Length, Shaft Radius, End Scale, Curvature, Asymmetry, Surface Detail,
  and Seed:** dimensions and deterministic controls for a stylized long bone.
  Bone resolution is constrained to 21–41, with a default of 33.

Sponge, Coral, Rock, Bark, Root, and Bone are executable on current main.
Cancel creates no geometry. Command orchestration remains Fusion-independent; Autodesk command
inputs, event handling, and `MeshBody` construction are isolated in `fusion/`.
See [`docs/SPRINT8_DESIGN.md`](docs/SPRINT8_DESIGN.md) for the multi-generator
contract and the successful macOS Autodesk Fusion acceptance result. The
observed Coral run created `NatureGenerator Coral` with 820 vertices and 1,636
faces in approximately 0.148 seconds; this is one verified configuration rather
than an exhaustive parameter test.
See [`docs/SPRINT9_DESIGN.md`](docs/SPRINT9_DESIGN.md) for Rock's field,
sampling-margin, and preset-driven UI decisions.
See [`docs/SPRINT10_DESIGN.md`](docs/SPRINT10_DESIGN.md) for Bark's exact capped
cylinder field, anisotropic value-noise construction, bounds, and limitations.
See [`docs/SPRINT11_DESIGN.md`](docs/SPRINT11_DESIGN.md) for Root's bounded
skeleton, tapered implicit union, topology safeguards, and acceptance plan.
See [`docs/SPRINT24_DESIGN.md`](docs/SPRINT24_DESIGN.md) for Bone's implicit
composition, parameters, topology, performance, and limitations.

Root passed real Autodesk Fusion acceptance on macOS: all nine metadata-driven
inputs displayed, `NatureGenerator Root` MeshBodies were created, and parameter
changes produced different geometry. Observed runs produced 6,568 vertices and
13,136 faces in approximately 2.498 seconds, and 7,452 vertices and 14,900 faces
in approximately 3.941 seconds. Root is included in the stable baseline.

Root v1 has a dominant primary root and lateral branches, but can resemble a
simplified branching pipe or stylized root rather than a botanically realistic
root system. It does not claim botanical simulation or species reproduction.

### Interactive preview

The stable preview workflow provides an explicit **Preview** button. It inserts
a temporary body named
`NatureGenerator Preview — <Preset>`. Pressing Preview again replaces the body;
OK lets Fusion abort the preview transaction and regenerates the current final
request; Cancel, command close, and add-in stop remove owned preview
geometry. Final bodies keep the established `NatureGenerator <Preset>` name.

Preview resolution is capped generically at the preset's default Resolution, so
a high-resolution final request can produce a lower-density preview. There is
no automatic/live preview, background execution, progress, or mid-generation
cancellation. See [Sprint 12 design](docs/SPRINT12_DESIGN.md).

Real Fusion acceptance on macOS verified viewport and Browser preview display,
replacement after parameter changes, OK finalization, Cancel cleanup, and the
absence of orphaned bodies or duplicate controls. The observed Sponge preview
at resolution 17 contained 5,684 vertices and 10,944 faces and completed in
approximately 0.25–0.27 seconds. Sprint 12 is included in the stable baseline.

Bark v1 is intentionally a closed procedural trunk segment with directional
grooves. Its current visual character is closer to an irregular or twisted
trunk than realistic deeply fractured bark. Adjusting depth, spacing, twist,
and variation cannot add longitudinal cracks, peeling plates, knots, or
species-specific structure; those remain future work.

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

## Development Workflow

NatureGenerator uses a review-driven workflow that separates product direction,
architecture, implementation, and release decisions:

```text
Plan
  |
  v
Architecture Review (ChatGPT)
  |
  v
Implementation (Codex)
  |
  v
Code and Design Review (ChatGPT)
  |
  v
Commit
  |
  v
Draft Pull Request
  |
  v
Final Review
  |
  v
Merge to main
  |
  v
Version Tag
```

### Roles

- **Product Owner:** Defines goals, priorities, user value, and approves major
  direction.
- **ChatGPT:** Helps define architecture, Sprint scope, APIs, and review criteria,
  then reviews the implementation and documentation.
- **Codex:** Inspects the repository, implements changes, runs tests, prepares
  commits, and creates draft pull requests.

### Sprint Definition of Done

- Sprint goal and exclusions are documented.
- Architecture impact is reviewed.
- Implementation is complete.
- The full test suite passes.
- Compilation and `git diff --check` pass.
- Documentation is updated.
- No unintended dependencies or generated artifacts are added.
- The draft pull request is reviewed.
- Changes are merged to `main`.
- A version tag is created for a meaningful milestone.

### Branch and release conventions

- Create feature branches from the latest `main`.
- Use descriptive names such as `feature/generator-runtime`,
  `feature/fusion-adapter`, and `feature/fusion-command`.
- Never implement directly on `main`.
- Use draft pull requests during development.
- Use annotated semantic-version tags such as `v0.1.0`, `v0.2.0`, and `v0.3.0`.
- Only tag merged commits on `main`.
- Do not tag every small documentation or maintenance change; reserve tags for
  meaningful milestones.
