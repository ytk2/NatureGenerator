# Architecture

The current stable product baseline is the immutable `v0.11.0` release tag.
This file is current main-branch documentation describing that architecture;
later documentation edits do not alter the tagged commit. See the
[baseline checklist](docs/V0.5.0_BASELINE.md) and
[release history](docs/RELEASES.md) for validated capabilities and limitations.

## Design goals

NatureGenerator separates procedural geometry from Autodesk Fusion 360 so that
geometry algorithms can be tested with the Python standard library alone. The
core should produce plain Python data that can later be consumed by Fusion 360,
an STL writer, or another adapter.

## Layer boundaries

### Product surfaces

The Fusion add-in exposes two independent command lifecycles. **Generate
Nature** routes a preset request through `GeneratorFactory`. **Procedural Lab**
adapts one existing Fusion body and routes a `ProceduralRequest` through an
operator pipeline. Operators are not presets or Families, and Procedural Lab
does not use `PresetCatalog`.

```text
Fusion BRepBody or MeshBody
    -> FusionSelectionAdapter
    -> ProceduralInputGeometry
    -> OperatorPipeline
    -> ProceduralOperatorRegistry
    -> ProceduralResult
    -> existing TriangleMesh
    -> Fusion MeshBody
```

The `procedural/` package is immutable and Fusion-independent. Sprint 28
registers Pass Through. Sprint 29 adds Noise Displacement using object-space
fractal value noise and area-weighted vertex normals while copying face
connectivity exactly. Sprint 30 adds midpoint Subdivision as the first
topology-changing operator. It creates one shared midpoint per undirected edge
and four winding-preserving children per triangle without smoothing or
projection. Operator parameter definitions own their types, units, defaults,
and ranges; Fusion renders them generically. The ordered pipeline tuple
provides the boundary for later operator stacks without exposing a stack UI
today. Procedural results deliberately do not force natural-material or preset
identity into selected user geometry.

### Nature presets (`presets/`)

Defines the stable user-facing vocabulary of natural forms. Each immutable
`NaturePreset` contains display metadata, default parameters, availability, and
a stable `generator_id`. Presets reference generators only through that string;
they must not import generator implementations, sample scalar fields, or extract
meshes.

`PresetFactory` is the command/UI entry point. It uses explicit built-in
registration rather than filesystem discovery, keeping startup deterministic in
Fusion's Python environment. Sponge maps to the available `gyroid` generator
ID. Coral, Rock, Bark, Root, Bone, and Crystal are released through the
`coral`, `rock`, `bark`, `root`, `bone`, and `crystal` generator IDs. Executable presets describe all
Fusion inputs through ordered parameter metadata.

Sprint 27 adds optional immutable `ParameterGroupDefinition` values. Every
built-in uses the shared **Form** and **Generation** groups, while the empty
default preserves legacy and third-party `NaturePreset` construction. Groups
are presentation metadata only; current Fusion input creation still consumes
the same ordered parameter metadata.

Sprint 18 adds an immutable `PresetDefinition` association around each
`NaturePreset` and its optional Family registry. `PresetCatalog` is the
application composition root: Rock is associated with `RockFamilyRegistry`,
Sprint 19 associates Bark with `BarkFamilyRegistry`, Sprint 20 associates Coral
with `CoralFamilyRegistry`, and Sprint 21 associates Sponge with
`SpongeFamilyRegistry`. Sprint 23 associates Root with `RootFamilyRegistry`,
Sprint 24 adds Classic Bone through `BoneFamilyRegistry`, and Sprint 26 adds
Classic Crystal through `CrystalFamilyRegistry`.
`PresetFactory` remains the stable metadata API used by generators, preserving
existing public contracts and the rule that `presets/` never imports concrete
generator code.

```text
PresetCatalog
    -> PresetRegistry
        -> PresetDefinition
            -> NaturePreset
            -> optional Family registry
```

### Generator runtime (`generators/`)

The Generator Runtime is the resolver and execution layer between presets and
procedural algorithms. `GeneratorFactory` maps a request's preset ID through an
explicit registration table to a `MeshGenerator`, then checks that the
implementation ID matches the preset's stable `generator_id`.
`GenerationRequest` carries a preset ID, immutable parameter overrides, and
samples-per-axis resolution without Fusion types. A `MeshGenerator` implements
`generate(request) -> TriangleMesh`. The factory validates that mesh and returns
an immutable `GeneratorResult` containing the mesh, statistics, warnings, IDs,
elapsed time, and a renderer-neutral `GeneratedAsset`. The asset refers to the
same mesh instance, so this layer does not introduce a second mesh model.

`SpongeGenerator` produces a closed rounded body with deterministic spherical
surface pores. The legacy `GyroidGenerator` remains available through its
stable generator API. `CoralGenerator` produces a closed branching implicit
solid. `RockGenerator`
composes immutable Macro Shape, Facet Layout, and Surface Detail definitions
into a closed deformed ellipsoid with deterministic value noise. The stages
share only an immutable normalized Rock context and remain independently
constructible and testable. `BarkGenerator` produces a closed capped trunk
field with directional periodic detail using the same narrow deterministic
value-noise primitive.
`RootGenerator` first builds an immutable, depth-bounded primary/lateral
skeleton, then thickens it as a hard implicit union of tapered capsule-like
segment fields and a compact crown. Segment count, tip radius, sampling margin,
and resolution are bounded so extraction remains deterministic and connected.
`BoneGenerator` smoothly blends a curved variable-radius shaft, asymmetric
ellipsoidal ends, and secondary lobes, applies shallow deterministic detail,
and intersects the result with a grounding half-space.
`CrystalGenerator` directly constructs a closed indexed polygonal prism with
seeded facet irregularity and a tapered point termination. It uses the existing
`TriangleMesh` model and validation pipeline without adding a second mesh type.
The legacy
generator-ID factory and public result-returning entry points remain compatible.
The runtime uses explicit registration rather than filesystem discovery and
does not introduce `GeneratorDescriptor`.

### Scalar fields and generators (`generators/`)

A scalar field is the mathematical implicit representation of a form. It maps a
three-dimensional point to a scalar value that can be sampled and polygonized.
`GyroidField` returns `abs(g) - thickness` for a periodic gyroid sheet. Rock
builds its bounded callable field through this internal pipeline:

```text
Rock request
    -> Macro Shape
    -> Facet Layout
    -> Surface Detail
    -> composed scalar field
    -> existing mesh pipeline
```

The pipeline has no Variant identity or Fusion dependency. Bark and Root also
supply bounded callable fields directly; Bark closes its finite
cylinder with the maximum of its radial side field and planar cap field. Root's
staged skeleton is a generator-owned intermediate representation rather than a
core geometry dependency.

Rock families are immutable bundles containing current UI parameter values and
one parameter set per Rock stage. `RockFamilyRegistry` resolves those bundles,
and `RockGenerator` feeds them through the same field composition, sampling,
and extraction path. Families do not own algorithms. The Registry-driven
Fusion Family input exposes Classic Rock, Layered Rock, Weathered Rock, River
Rock, and the seven earlier definitions: Smooth, Weathered, Rugged, River
Stone, Granite, Basalt, and Broken Rock. Sprint 25 adds optional object-height
strata parameters to Surface Detail; zero defaults and conditional evaluation
preserve the exact arithmetic and digests of every earlier definition. New
families otherwise change only immutable stage parameters and existing public
Rock defaults.

Sprint 19 applies the same preset-level association to Bark.
`BarkFamilyRegistry` initially exposes Classic Bark, an immutable bundle of the
seven accepted Bark parameter values. `BarkGenerator` still owns the capped
cylindrical scalar field and uses the same extraction path. The registry owns
no geometry and introduces no Bark-specific Fusion branching.

Sprint 20 associates Coral with `CoralFamilyRegistry`. Classic Coral stores the
four accepted Coral parameter values, while `CoralGenerator` owns the connected
capsule-union field. Seed 0 preserves the original branch graph; nonzero Seeds
apply one deterministic transform per shared node, so connected segments keep
identical endpoints and remain a single implicit solid.

Sprint 21 associates Sponge with `SpongeFamilyRegistry`. Classic Sponge stores
Cell Size, Thickness, Seed, and Resolution metadata. `SpongeGenerator` samples
a rounded-box field with exterior-connected spherical cavities, producing a
closed single-component porous mesh through the existing voxel and marching
pipeline.

Sprint 23 completes the migration by associating Root with
`RootFamilyRegistry`. Classic Root stores the nine accepted Root parameter
values, including deterministic Seed and Resolution. Requests without a Family
ID and requests selecting `classic_root` resolve to identical configuration and
the exact accepted mesh.

Sprint 24 makes Bone executable through `BoneFamilyRegistry`. Classic Bone
stores Length, Shaft Radius, End Scale, Curvature, Asymmetry, Surface Detail,
Seed, and Resolution. `BoneGenerator` owns the implicit construction; the
Family owns only immutable parameter values.

Sprint 26 associates Crystal with `CrystalFamilyRegistry`. Classic Crystal
stores Length, Width, Facet Count, Taper, Irregularity, Seed, and Resolution.
`CrystalGenerator` owns the parametric indexed-mesh construction; the Family
owns only immutable parameter values.

Generator implementations may depend on the scalar-field contract and geometry
core, but must remain independent of Fusion 360. They do not contain user-facing
preset metadata.

### Core geometry (`core/`)

Owns scalar-field contracts, voxel sampling, marching-tetrahedra isosurface
extraction, indexed `TriangleMesh` data, optimization, validation, statistics,
and mesh exporters. This layer must not import `adsk` or depend on Fusion 360
runtime state.

The mesh stage includes deterministic construction and vertex welding,
conservative cleanup, face and vertex normals, topology validation and
statistics, plus STL, OBJ, and PLY serialization. Optimization does not alter the
surface through smoothing or decimation.

### Generated assets (`assets/`)

Sprint 22 composes validated geometry into an immutable `GeneratedAsset`:

```text
GeneratedAsset
    -> existing TriangleMesh
    -> MaterialDefinition
    -> MappingDefinition
    -> TextureSet
    -> AssetMetadata
```

`MaterialDefinition` records numeric PBR-like procedural intent without Fusion
appearances or renderer/file-format objects. `MappingDefinition` initially
supports explicit object-space procedural coordinates with scale, rotation,
offset, and optional projection metadata. `TextureSet` can carry typed baked
image resources but is empty in Sprint 22 because no baking pipeline exists.
`AssetMetadata` records stable preset/generator/family identity, generation
request parameters, units, and schema version. Family identity and explicit
overrides remain distinct so provenance does not mislabel Family-owned values.

Sprint 27 introduces `NaturalMaterial` as the shared catalog record around
each existing `MaterialDefinition`. `NaturalMaterialRegistry` provides stable
preset-ID lookup; `AssetBrowserMetadata` carries categories and keywords, and
an optional `ThumbnailReference` reserves a renderer-neutral packaged-resource
boundary. `GeneratedAssetFactory` obtains the same material definitions through
this registry. No thumbnail assets, browser UI, material rendering, or geometry
behavior are added.

`AssetExporter`, `ExportRequest`, `ExportResult`, and `ExporterRegistry`
separate serialization from generation and avoid format-selection branching.
The format vocabulary includes the planned OBJ, glTF, GLB, USD, USDZ, and STL
destinations, but no new production exporter is registered in Sprint 22.

### Application commands (`commands/`)

Commands coordinate user intent without knowing algorithm classes or Autodesk
objects. `generate_nature.py` accepts a `GenerationRequest`, asks the Generator
Runtime to execute it, and passes the resulting mesh to an injected adapter
callable. This keeps orchestration thin and testable outside Fusion.

### Fusion adapter (`fusion/`)

The Fusion Adapter converts a core `TriangleMesh` into a Fusion `MeshBody` and
owns Fusion-specific validation and lifecycle behavior. `MeshBodyBuilder`
flattens indexed mesh data for Fusion and inserts it into the active design's
root component. The adapter converts the core's millimeter-based coordinates to
Fusion Design API database units (centimeters). `fusion.runtime` registers the
interactive **Generate Nature** command, builds its inputs from `PresetFactory`,
retains handlers for the required command lifetime, and removes its UI resources
when the add-in stops.

Functional Autodesk integration is confined to `fusion/`. The add-in entry
point delegates lifecycle calls to this layer and imports `adsk` only for fatal
startup and shutdown reporting. Because Fusion executes the entry-point file
directly, it also adds the directory containing `NatureGenerator.py` to
`sys.path` once before importing sibling packages. This bootstrap is confined to
the entry point. Presets, generators, commands, core, and Fusion modules do not
modify the import path.

Sprint 12 development adds a command-instance `PreviewController` inside the
Fusion boundary. It stores a deterministic request tuple and owns only the
temporary MeshBody reference returned to that command. Pure generation still
flows through `GeneratorFactory`; mesh conversion remains in `MeshBodyBuilder`.
Input changes mark state stale but do not generate automatically. An explicit
Preview click arms generation in Fusion's `executePreview` transaction. Destroy
and add-in stop delete only directly owned preview references; final output is
regenerated in `execute` after Fusion aborts the preview transaction.
This lifecycle passed real Autodesk Fusion acceptance on macOS, including
Browser/viewport insertion, replacement, OK finalization, and Cancel cleanup.

Sprint 13 adds a Fusion-independent `variants/` layer beside `presets/`.
`VariantDefinition` contains only stable IDs, presentation text, and immutable
existing-parameter values. `VariantRegistry` validates definitions against
`PresetFactory` metadata and declarative ratio constraints without importing a
generator. The Fusion runtime maps a selected variant generically onto the
already metadata-generated inputs; request construction, preview execution,
final generation, and concrete-generator routing remain unchanged.

Variants are curated parameter bundles, not separate generators. Geometry is
determined entirely by the normalized current parameters in
`GenerationRequest`; no hidden Variant identity reaches `GeneratorFactory`.
Real Fusion acceptance on macOS verified filtered dropdown rebuilding, generic
parameter application, Custom transitions, Preview replacement, Preset
switching, and OK/Cancel behavior without recursive events or duplicate UI.

Sprint 16 first replaces Variant with Family for Rock. Sprint 18 preserves that
presentation while removing the Fusion runtime's direct Rock registry
dependency. Later migrations register Bark, Coral, Sponge, and finally Root.
The runtime resolves each implemented preset's Family registry from
`PresetCatalog`, applies its immutable parameter values, and stores the selected
stable family ID in `GenerationRequest`. Preview copies that ID while changing
only density; Final uses the requested density. The legacy Variant API remains
available for compatibility, but Fusion no longer uses it for implemented
presets.

## Runtime pipeline

```text
User / Fusion Command
    -> PresetCatalog
    -> Variant or Family Definition
    -> Generation Request
    -> Nature Preset
    -> Generator Runtime
    -> Scalar Field
    -> Voxel Grid
    -> Marching Tetrahedra
    -> Triangle Mesh
    -> Generated Asset
        -> future Asset Exporter
        -> Fusion Adapter
            -> Fusion MeshBody
```

1. A user or Fusion command creates an immutable request identifying a preset,
   parameter overrides, sampling resolution, and an optional Rock family ID.
2. The Generator Runtime resolves the preset ID to a registered mesh generator
   and verifies its stable `generator_id` against the preset metadata.
3. The implementation supplies a scalar field, such as `GyroidField`.
4. The core samples the field into a regular voxel grid.
5. Marching tetrahedra extracts a Fusion-independent indexed triangle mesh.
6. The validated mesh is composed with material, mapping, texture, and
   provenance intent into a `GeneratedAsset`.
7. Existing consumers can still read the same mesh directly; future file
   exporters consume the complete asset, while Fusion inserts its mesh into a
   `MeshBody`.

The sampling, extraction, and mesh stages should use explicit tolerances and
deterministic iteration. Manufacturability checks—such as minimum feature size,
watertightness, and build-volume limits—will be introduced as separate passes so
they do not become implicit side effects of surface extraction.

## Dependency direction

```text
Fusion UI lifecycle
    -> Fusion Adapter runtime
    -> PresetCatalog
    -> PresetDefinition
    -> VariantFactory
    -> Generate Nature command
    -> GenerationRequest
    -> PresetFactory
    -> NaturePreset

Generator Runtime
    -> Generator implementation
    -> ScalarField
    -> core
    -> assets

Fusion Adapter
    -> core

Future File Export Adapter
    -> assets
```

Dependencies point toward the Fusion-independent geometry core. `core/` never
imports from presets, generators, commands, or Fusion integration. Presets
reference generator implementations only through stable `generator_id` strings.
The Generator Runtime owns ID resolution, and the Fusion Adapter depends on core
mesh types rather than the reverse. Autodesk dependencies stop at the
`fusion/` boundary.

Variants depend on preset abstractions for validation. They do not depend on
Fusion, commands, core geometry, or concrete generators. Stable variant IDs are
separate from display names, while Custom remains transient UI state rather
than a registered definition.

`preset_catalog.py` is a narrow composition root allowed to depend on preset
metadata and concrete Family registries. This avoids placing generator imports
inside `presets/` and avoids concrete Family knowledge in `fusion/`. Family
registries provide stable preset identity, deterministic listing, and lookup;
their concrete Family definitions remain preset-specific.

These boundaries keep mathematical geometry testable in ordinary Python and
prevent Autodesk runtime concerns from leaking into presets or algorithms.
