# Sprint 13 Design: Generator Variants

## Goal and scope

Sprint 13 adds curated, named parameter configurations for every executable
generator. A variant changes only existing preset parameters. It does not add a
generator, alter a scalar field, change mesh extraction, or introduce a new
generation request format.

The first catalog contains three variants for each available preset:

- Sponge: Fine, Balanced, Bold
- Coral: Fine Branching, Balanced, Massive
- Rock: Smooth, Weathered, Rugged
- Bark: Subtle, Grooved, Twisted
- Root: Sparse, Balanced, Dense

Names describe parameter configurations and must not be interpreted as claims
of species reproduction or biological realism.

## Variant data model and registry ownership

`VariantDefinition` is a frozen, Fusion-independent value object with:

- `variant_id`: globally stable lowercase identifier;
- `preset_id`: stable owner preset identifier;
- `display_name`: user-facing label;
- `description`: concise intent;
- `parameter_values`: immutable mapping of existing parameter IDs to values.

Construction copies `parameter_values` into a `MappingProxyType`, so later
mutation of the caller's dictionary cannot alter a registered definition.
Variants contain no Fusion objects, generator instances, callables, or runtime
state.

`VariantRegistry` owns explicit registration and deterministic lookup. It
rejects duplicate variant IDs, duplicate display names within one preset,
unknown presets, unknown parameters, unavailable presets, type mismatches,
metadata-bound violations, and declared cross-parameter violations. Built-ins
are imported explicitly rather than discovered from the filesystem.

Cross-parameter rules are immutable declarative preset metadata. They express
relationships such as Bark Depth relative to Diameter and Root Radius relative
to Length without importing `BarkGenerator` or `RootGenerator`. The registry
merges each variant's values over preset defaults before evaluating these
rules. Generator validation remains the final authority for all generated
requests.

## Applying a variant

The generic application path is:

```text
Variant dropdown
    -> stable variant ID
    -> VariantRegistry
    -> immutable parameter_values
    -> existing metadata-generated command inputs
    -> existing GenerationRequest
    -> existing Preview / OK paths
```

The Fusion layer never imports a concrete generator. It converts values using
the same metadata types already used to create and read command inputs. Length
values remain millimetres in variant definitions and are converted to Fusion's
internal centimetres only when written to a `ValueCommandInput`.

Selecting a named variant applies all values listed by that definition. The
built-in catalog specifies every exposed parameter, including Resolution, so a
selection is complete and reproducible. No geometry is generated until the
user explicitly clicks Preview or OK.

## Custom state and manual editing

The command has one generic dropdown with stable input ID `natureVariant`.
`Custom` is a UI state, not a registered variant and has no stable variant ID.

Any manual edit to a visible parameter after a named variant is selected moves
the dropdown to Custom. Programmatic writes made while applying a variant are
tracked by expected input ID and value. Matching `inputChanged` notifications
are consumed as part of application; a different later value is treated as a
manual edit. This avoids an immediate, false transition to Custom when Fusion
reports programmatic updates asynchronously.

Custom values are valid inputs to both Preview and OK. They use the unchanged
request construction and generator validation paths.

## Preset switching and restoration policy

All metadata-generated parameter inputs already live for the command lifetime.
Therefore each preset's last values are naturally retained while its inputs are
hidden. On a preset change:

1. the Variant dropdown is rebuilt for the selected preset;
2. Custom is selected;
3. the selected preset's retained parameter values are shown unchanged;
4. no named variant is applied implicitly.

Returning to a prior preset restores exactly the values last left there and
labels them Custom. This policy avoids surprising value resets and avoids
incorrectly claiming a named variant after a user edit. Re-selecting a named
variant explicitly reapplies its catalog values.

Unavailable presets show only Custom and remain non-generatable through the
existing validation path.

## Preview invalidation and final generation

Selecting a variant, editing a parameter, or switching presets calls the
existing `PreviewController.mark_dirty()`. An existing preview may remain
visible but is stale and cannot be finalized as current geometry. Variant
selection never triggers automatic preview.

The explicit Preview button builds a fresh request from current command input
values. OK likewise builds a fresh request and uses the existing final
generation path. `GenerationRequest`, `GeneratorFactory`, Preview Controller,
mesh insertion, naming, ownership, and cleanup contracts do not require API
migration.

## Compatibility and risks

- Existing generator algorithms and factory routing remain unchanged.
- Default preset parameters remain unchanged, preserving Rock and Root exact
  deterministic digests.
- Existing custom parameter workflows remain available through Custom.
- The Fusion layer depends only on preset and variant abstractions, never a
  concrete generator.
- Programmatic Fusion input events can be synchronous or delayed; expected
  value tracking prevents false Custom transitions.
- Variant values can become invalid if preset metadata changes. Registration
  fails fast so catalog drift is caught by unit tests and startup validation.
- A variant name is presentation metadata, not a promise of realism or a new
  geometry algorithm.

No deprecation or API migration is required in Sprint 13. Future saved variant
state can use stable `variant_id` values without embedding display labels.

## Validation plan

Tests cover immutable definitions, stable ordering, duplicate rejection,
unknown and cross-preset parameter rejection, metadata and cross-parameter
validation, catalog completeness, generic UI population, named application,
Custom transitions, preset restoration, Preview invalidation, and fresh Preview
and OK requests. Every built-in variant is also generated twice to verify
successful deterministic output, with mesh validity checked by the existing
factory pipeline.

Release validation additionally includes the full unit suite, Python
compilation, `git diff --check`, Fusion and concrete-generator dependency
boundaries, unsafe threading/async/sleep and `sys.path` scans, third-party
dependency checks, documentation structure/link checks, generated-artifact
scans, exact Rock and Root default regression digests, and local per-variant
performance measurements.

## Local performance reference

These sequential measurements are local development references, not runtime
guarantees. Every configuration completed through `GeneratorFactory` and the
existing mesh validation pipeline.

| Preset | Variant ID | Resolution | Vertices | Faces | Time | Components | Topology |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Sponge | `sponge_fine` | 21 | 7,964 | 15,552 | 0.467 s | 96 | Open manifold |
| Sponge | `sponge_balanced` | 17 | 5,684 | 10,944 | 0.303 s | 42 | Open manifold |
| Sponge | `sponge_bold` | 17 | 6,788 | 13,152 | 0.339 s | 12 | Open manifold |
| Coral | `coral_fine_branching` | 21 | 1,310 | 2,616 | 0.262 s | 1 | Watertight |
| Coral | `coral_balanced` | 17 | 960 | 1,916 | 0.144 s | 1 | Watertight |
| Coral | `coral_massive` | 17 | 1,118 | 2,232 | 0.148 s | 1 | Watertight |
| Rock | `rock_smooth` | 17 | 1,090 | 2,176 | 0.158 s | 1 | Watertight |
| Rock | `rock_weathered` | 17 | 1,090 | 2,176 | 0.161 s | 1 | Watertight |
| Rock | `rock_rugged` | 25 | 2,548 | 5,092 | 0.481 s | 1 | Watertight |
| Bark | `bark_subtle` | 33 | 15,222 | 30,440 | 1.071 s | 1 | Watertight |
| Bark | `bark_grooved` | 33 | 12,960 | 25,916 | 1.003 s | 1 | Watertight |
| Bark | `bark_twisted` | 37 | 19,312 | 38,620 | 1.471 s | 1 | Watertight |
| Root | `root_sparse` | 37 | 6,472 | 12,940 | 2.174 s | 1 | Watertight |
| Root | `root_balanced` | 37 | 6,568 | 13,136 | 2.951 s | 1 | Watertight |
| Root | `root_dense` | 41 | 8,160 | 16,324 | 5.331 s | 1 | Watertight |

Sponge retains its established finite open-sheet topology and expected boundary
warnings. Coral, Rock, Bark, and Root satisfy their required single-component,
watertight topology.

## Real Fusion acceptance

Tested successfully in Autodesk Fusion on macOS:

- **Generate Nature** opened and one Variant dropdown appeared.
- Choices were filtered correctly for each Preset. Rock displayed Custom,
  Smooth, Weathered, and Rugged; Bark and Root displayed their own catalogs.
- Named Variant selection updated the corresponding parameter inputs without
  generating geometry automatically.
- Preview generated from the current Variant and a later Preview replaced it.
- Manual parameter editing changed the Variant state to Custom.
- Preset switching between Rock, Bark, and Root worked while preserving the
  documented per-preset Custom-value policy.
- Preview cleanup, OK, and Cancel remained functional.
- No duplicate controls, recursive input event loop, startup failure, or crash
  was observed.

Visual checks covered Rock Smooth, Rock Rugged, Rock Custom after manual
editing, Bark Grooved, and Root Dense. This acceptance does not claim that all
15 Variants were visually inspected in Fusion.
