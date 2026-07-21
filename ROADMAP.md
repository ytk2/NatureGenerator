# Roadmap

## Phase 1: Project foundation

- Establish the Fusion 360 add-in structure and manifest.
- Document package boundaries and contribution conventions.
- Add dependency-free placeholder modules and structural tests.

## Phase 2: Geometry core

- Define scalar-field and voxel-grid representations.
- Define indexed triangle-mesh types and mesh validation.
- Provide standard-library ASCII and binary STL serialization.
- Add deterministic geometry unit tests.

## Phase 3: Gyroid surface generation

- Implement configurable gyroid scalar-field sampling.
- Extract the isosurface with marching tetrahedra.
- Validate orientation, watertightness, and numerical tolerances.

## Phase 4: Fusion 360 integration

- Add Fusion command inputs and progress reporting.
- Convert generated meshes to Fusion `MeshBody` objects.
- Connect generated core meshes to Fusion-side export workflows.

## Phase 5: Manufacturability

- Add wall-thickness and minimum-feature controls.
- Add build-volume and mesh-quality checks.
- Provide presets and practical examples for common fabrication workflows.

This roadmap is directional. Each phase should remain small enough to review and
should add tests before expanding the public API.
