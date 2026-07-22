# Sprint 9 Design: Rock Generator

## Goal

Sprint 9 makes Rock an executable preset and changes Generate Nature from a
fixed Sponge-shaped dialog into a preset-driven command. The command reads
immutable `NaturePreset.parameter_metadata`, constructs a `GenerationRequest`,
and never imports or selects a concrete generator.

## Implementation plan

1. Extend parameter metadata with the UI types `length` and `integer` while
   retaining the existing types for source compatibility.
2. Give Sponge, Coral, and Rock complete ordered metadata, including the stable
   `resolution` key. Rock exposes `size`, `roughness`, `seed`, and `resolution`.
3. Add generic Fusion input helpers that create, read, validate, and show the
   appropriate inputs from metadata. A preset-change handler updates visibility
   only; it does not generate geometry.
4. Implement `RockGenerator` using an ellipsoid signed field, deterministic
   low-frequency directional deformation, and dependency-free multi-octave
   trilinear value noise. Sample it with `VoxelGrid` and extract it with the
   shared Marching Tetrahedra pipeline.
5. Register `rock -> RockGenerator` in `GeneratorFactory` and rely on the
   existing shared mesh validation, statistics, result assembly, and Fusion
   adapter.
6. Add preset, generator, routing, topology, determinism, and UI lifecycle
   tests, then run the full suite and dependency-boundary checks.

## API migrations

`ParameterMetadata.value_type` gains `length` and `integer`. Existing `float`,
`int`, `bool`, and `str` metadata remains accepted, so callers constructing old
metadata do not break. `length` is a finite numeric value displayed with a
Fusion unit; `integer` is an integral spinner value.

Resolution remains the dedicated immutable `GenerationRequest.resolution`
field. This preserves the public request constructor and all existing factory
entry points. Executable presets also describe resolution in their parameter
metadata so the UI has no hard-coded shared controls. The generic request
builder recognizes the stable key `resolution`, removes it from parameter
overrides, and supplies it to the request field. Generator parameter merging
likewise treats preset resolution as request-level metadata rather than a
scalar-field argument.

## Backward compatibility and risks

- `GenerationRequest(preset_id, overrides, resolution)` remains unchanged.
- `GeneratorFactory.generate(preset, parameters)` keeps its default resolution;
  a `resolution` entry in `parameters` is accepted as a convenience migration.
- Sponge and Coral retain their stable scalar-field keys and defaults. Their
  labels are still appropriate to those forms, while Rock receives distinct
  labels.
- Preset definitions remain frozen and their mappings remain defensive,
  read-only copies.
- Fusion length inputs expose internal centimetres, so generic UI reading must
  convert them back to the metadata unit (millimetres here). This conversion is
  isolated at the Fusion boundary.
- Dynamic inputs are created once per dialog and switched with `isVisible`,
  avoiding reliance on input deletion and naturally preserving per-preset
  values. The command retains exactly one execute, input-change, validate, and
  destroy handler group per open dialog and removes the group on destroy.

## Generator-independent preset UI

The Fusion command iterates metadata in definition order and dispatches only on
metadata type (`length`, `float`, or `integer`). It does not branch on preset or
generator IDs. Each dialog creates all available preset inputs once and toggles
their visibility on preset changes, preserving values without duplicate input
creation. Input changes never call the generation command. Execute reads the
same metadata, validates bounds, maps the
stable `resolution` key into `GenerationRequest.resolution`, and passes all
other values as overrides.

## Rock field and sampling bounds

Rock uses a rounded asymmetric ellipsoid base. Its radius is modified by broad
fixed directional terms and deterministic multi-octave lattice value noise.
The lattice values come from a documented integer mixer using the explicit
seed; Python's randomized `hash()` and `random` module are not used. Smoothstep
trilinear interpolation makes the field continuous between lattice points.

Defaults and supported bounds are:

| Parameter | Default | Bounds | Meaning |
| --- | ---: | ---: | --- |
| Size | 40 mm | 10–120 mm | Nominal maximum stone diameter |
| Roughness | 0.35 | 0–0.70 | Dimensionless surface variation |
| Seed | 1 | 0–2,147,483,647 | Deterministic variation key |
| Resolution | 17 | 9–41 | Samples per axis |

The maximum radial deformation is conservatively bounded. Sampling uses a
larger cubic domain than that bound, leaving at least one outer layer with a
positive (outside) field value at every supported roughness and seed. A valid
rock is therefore closed before extraction and cannot be cropped by the grid.
The generator rejects unknown, missing, non-finite, out-of-range, empty, or
invalid extraction inputs with domain-specific errors.
