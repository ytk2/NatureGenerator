# Sprint 16 Phase 1 Design: Fusion Rock Family Selection

## Objective

Expose the Sprint 15 Rock Family architecture in Generate Nature without
changing scalar fields, stage tuning, mesh extraction, Preview density policy,
or command lifecycle.

## UI behavior

The command creates both generic selection inputs:

- Variant remains visible for Sponge, Coral, Bark, and Root.
- Family is visible for Rock and replaces Variant in the Rock workflow.

The Family list is populated in registry order:

1. Smooth
2. Weathered
3. Rugged
4. River Stone

Fusion contains no hardcoded family labels or stage parameters. It reads
`RockFamilyRegistry.list_all()` and applies the immutable parameter metadata
from the selected `RockFamilyDefinition`.

Size, Roughness, Seed, Resolution, Preview, OK, and Cancel remain unchanged.
Manual parameter edits retain the chosen Family while allowing a custom
configuration of that family.

## Request flow

```text
Fusion Family input
    -> RockFamilyRegistry
    -> selected stable family_id
    -> GenerationRequest
        -> Preview request (same family_id, lower density only)
        -> Final request (same family_id, requested density)
    -> unchanged GeneratorFactory
    -> RockGenerator
    -> selected RockFamilyDefinition
    -> unchanged three-stage Rock field and mesh pipeline
```

`GenerationRequest.family_id` is optional and defaults to an empty value.
Existing callers therefore retain the accepted default Rock behavior. The
Preview signature includes the family ID, so changing Family invalidates the
current Preview even when ordinary parameter values happen to match.

## Family compatibility

Smooth, Weathered, and Rugged use the accepted Sprint 15 default stage
parameters plus their unchanged Size, Roughness, Seed, and Resolution values.
River Stone uses its existing Sprint 15 family definition and parameter values.

| Family | Resolution | Expected digest |
| --- | ---: | --- |
| Smooth | 17 | `29d6402a0148637fd00cbc1274d8f6be6c9f8901b2b856e2de75dc43f91bdc3e` |
| Weathered | 17 | `30a709c32fb7dd16b87f0388f21c6e24e12b6ad990b2872dd31f9549956e7c1d` |
| Rugged | 25 | `040bd703ef44549b418fdb5fd6804b9e36ce93e372cbbea00e5e63a8b8ffadde` |
| River Stone | 25 | `61264e6e929229247ac7b4d89f2916f5c5cb875dc985c5c258fa79334c18abd4` |

## Preview and Final

Both paths construct a fresh immutable request from current inputs and call
`GeneratorFactory.generate_request`. `preview_request` copies the family ID and
changes only resolution according to the existing adaptive policy. Final
generation does not reuse the Preview MeshBody.

Preview replacement, owned-body cleanup, unrelated-body protection, Cancel,
destroy, and add-in stop retain the existing controller behavior.

## Architecture boundaries

- Fusion imports family metadata but no concrete Rock generator class.
- `GeneratorFactory` is unchanged.
- Rock scalar-field evaluation and all three stage builders are unchanged.
- Marching Tetrahedra, mesh validation, insertion, and Preview policy are
  unchanged.
- No background task, timer, thread, or hidden switch is added.
- Other presets retain their existing Variant workflow and generation paths.

## Automated coverage

- Registry-driven Family labels and ordering
- Rock Family visibility and Variant hiding
- non-Rock Variant visibility
- immutable family parameter metadata
- Family parameter application
- manual parameter editing
- Preview family identity and adaptive resolution
- River Stone Preview and full-resolution Final requests
- deterministic family request signatures
- exact four-family digest regression
- existing Preview replacement, fresh Final body, Cancel, destroy, stop, and
  unrelated-body behavior
- all existing preset generation

## Real Fusion acceptance checklist

- Generate Nature opens with one command control.
- Sponge initially shows Variant and hides Family.
- Selecting Rock hides Variant and shows Family.
- Family contains Smooth, Weathered, Rugged, and River Stone once each.
- Each selection updates Size, Roughness, Seed, and Resolution.
- Preview creates the selected family and replacement removes only the prior
  Preview.
- River Stone is rounded, flattened, subtly detailed, and grounded.
- Final creates a fresh `NatureGenerator Rock` MeshBody at requested density.
- Preview and Final share silhouette and feature placement.
- Cancel removes only the owned Preview.
- Sponge, Coral, Bark, and Root Variant workflows still work.

## Real Fusion acceptance

Sprint 16 passed manual Autodesk Fusion 360 validation:

- the Family dropdown displayed for Rock
- Smooth, Weathered, Rugged, and River Stone were available
- Preview updated correctly when switching families
- River Stone Preview generated correctly
- existing Rock families remained unchanged
- UI layout was correct
- no Fusion runtime errors were observed

## Limitations

Phase 1 exposes only the four registered families. It does not add automatic
Preview, family thumbnails, materials, smoothing, additional geological
families, or new geometry algorithms.
