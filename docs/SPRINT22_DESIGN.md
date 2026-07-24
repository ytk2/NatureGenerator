# Sprint 22 Design — Generated Asset and Export Architecture

## Summary

Sprint 22 introduces a renderer-neutral asset boundary after existing geometry
generation and validation. It does not change any generator or create another
mesh representation. `GeneratorResult.mesh` remains compatible, and
`GeneratorResult.asset.mesh` is the identical `TriangleMesh` object.

## Asset model

```text
GenerationRequest
    -> existing Generator
    -> existing TriangleMesh
    -> existing MeshValidator
    -> GeneratedAssetFactory
        -> GeneratedAsset
            -> TriangleMesh
            -> MaterialDefinition
            -> MappingDefinition
            -> TextureSet
            -> AssetMetadata
    -> GeneratorResult
```

All definitions are immutable, standard-library-only Python data.

## Material intent

`MaterialDefinition` carries:

- stable identifier and display name
- normalized RGBA base color
- metallic and roughness values
- normal and ambient-occlusion strengths
- optional scalar/string procedural parameters

These values communicate intent. They do not contain Fusion appearances,
shader nodes, MTL properties, glTF structures, USD schemas, or engine objects.
Sprint 22 supplies conservative preset-level defaults without evaluating or
baking them.

## Mapping intent

`MappingMode.OBJECT_SPACE` is the only supported mode. A
`MappingDefinition` also carries positive three-axis scale, Euler rotation,
offset, and optional projection metadata. The enum provides an explicit
extension point for future UV, triplanar, and cylindrical modes without
pretending those algorithms exist today.

## Texture resources

`TextureResource` identifies one image payload by semantic role, media type,
dimensions, bytes, and optional metadata. `TextureSet` enforces one resource
per semantic and stable unique resource IDs. Generated assets have an empty
set in Sprint 22 because there is no texture evaluator or baker.

## Provenance

`AssetMetadata` records stable asset, preset, generator, and optional selected
Family IDs; the explicit generation request parameters; millimeter coordinate
units; and an asset-schema version. Family identity remains separate from
overrides, avoiding a duplicated or inaccurate copy of Family-owned values.
This metadata is export-neutral and immutable.

## Export boundary

```text
GeneratedAsset
    -> ExportRequest(format, destination)
    -> ExporterRegistry
    -> AssetExporter
    -> ExportResult(files, warnings)
```

The format vocabulary reserves OBJ, glTF, GLB, USD, USDZ, and STL. No exporter
implementation is registered in this Sprint. Existing low-level mesh writers
remain unchanged and are not presented as full generated-asset exporters.

## Compatibility

- no generator implementation changed
- no scalar field, voxel grid, marching-tetrahedra, mesh, or validation code
  changed
- `GeneratorResult` keeps its original fields and constructor compatibility
- legacy results constructed without an asset receive a neutral default asset
- Generate Nature keeps inserting `result.mesh`; the asset references that mesh
- existing mesh statistics, warnings, timing, Preview, and Final behavior stay
  unchanged

## Dependency rules

- `assets` may depend on `core.mesh` and preset metadata for composition
- generators may compose assets after geometry validation
- format adapters may depend on `assets`
- assets must not depend on Fusion, file-format libraries, renderers, or engines
- core geometry remains independent of assets

## Test coverage

- immutable definitions and defensive metadata copies
- numeric and vector validation
- explicit object-space mode
- texture uniqueness and semantic lookup
- runtime asset composition and mesh identity
- export registry routing and missing-exporter failure
- existing generator-runtime and Preview compatibility

## Known limitations

- material defaults are intent only and are not visible in Fusion
- no texture resources are generated
- no UVs or alternate projection modes are generated
- no complete asset format can be exported through the new registry yet
