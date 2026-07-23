# Sprint 18 Design — Preset Registry Architecture

## Summary

Sprint 18 introduces a generic preset-level composition layer around the
existing immutable `NaturePreset` metadata and optional Family registries. It
removes the Fusion runtime's direct dependency on `RockFamilyRegistry` while
leaving every generator, scalar field, mesh path, request, and body lifecycle
unchanged.

## Registry hierarchy

```text
PresetCatalog
    -> PresetRegistry
        -> PresetDefinition
            -> NaturePreset
            -> optional Family registry
                -> RockFamilyRegistry
                    -> Smooth
                    -> Weathered
                    -> Rugged
                    -> River Stone
                    -> Granite
                    -> Basalt
                    -> Broken Rock
            -> Bark (no Family registry yet)
            -> Coral (no Family registry yet)
            -> Sponge (no Family registry yet)
            -> Root (no Family registry yet)
            -> Bone (unavailable; no Family registry)
```

## Architectural decisions

### Preserve the existing preset API

`PresetFactory.get()` and `PresetFactory.list_all()` still return
`NaturePreset`. Generator validation and execution therefore keep their public
contracts and dependency direction.

`PresetDefinition` is a separate immutable association containing one
`NaturePreset` plus an optional registry object. Construction validates that a
Family registry:

- declares the same stable `preset_id`
- provides `get()`
- provides `list_all()`

The definition proxies only stable ID and display name for catalog consumers.
It does not generate geometry or select algorithms.

### Keep composition outside `presets/`

The `presets/` layer must not import concrete generators. `preset_catalog.py`
is the application composition root: it imports immutable preset metadata and
the current Rock Family registry, then builds a deterministic
`PresetRegistry`. This keeps the pre-existing dependency check intact and
places the one concrete association outside both Fusion presentation and
preset metadata.

### Make Fusion a generic catalog client

The Fusion runtime obtains its preset list, preset metadata, and optional
Family registry exclusively from `PresetCatalog`. Its Family UI state:

1. resolves the selected `PresetDefinition`
2. populates the existing Family dropdown from `families.list_all()`
3. resolves stable Family IDs with `families.get()`
4. applies the Family's existing parameter values using preset metadata
5. passes the selected ID through the unchanged `GenerationRequest`

No preset or family label is used for dispatch. The UI retains the same
`natureRockFamily` stable command-input ID for backward compatibility even
though its implementation is now generic.

## Preserved behavior

- Preset ordering and labels are unchanged.
- Rock Family order remains Smooth, Weathered, Rugged, River Stone, Granite,
  Basalt, Broken Rock.
- Rock remains the only preset that shows Family.
- Non-Rock presets continue to show Variant and Custom.
- Family changes still apply Size, Roughness, Seed, and Resolution.
- manual Rock parameter edits retain the selected Family exactly as before
- Preview and Final requests carry the same Family ID and differ only in
  sampling density
- `GeneratorFactory` behavior and concrete registration are unchanged
- all existing geometry modules are unchanged

## Modified files

- `NatureGenerator/presets/preset.py`
- `NatureGenerator/presets/registry.py`
- `NatureGenerator/presets/__init__.py`
- `NatureGenerator/preset_catalog.py`
- `NatureGenerator/fusion/runtime.py`
- `NatureGenerator/tests/test_presets.py`
- `NatureGenerator/tests/test_fusion_integration.py`
- `README.md`
- `ROADMAP.md`
- `ARCHITECTURE.md`
- `SPRINT18_PLAN.md`
- `docs/README.md`
- `docs/SPRINT18_DESIGN.md`

## Validation

- full unit suite: 190 tests passed in 124.673 seconds with warnings treated as
  errors
- focused Preset, Rock pipeline, Rock Family, and Fusion integration suite:
  91 tests passed in 13.549 seconds
- all seven exact Rock Family digest regressions passed unchanged
- Python compilation passed
- `git diff --check` passed
- Fusion dependency and concrete-generator boundary scans passed
- Fusion runtime contains no `RockFamilyRegistry` reference
- threading, async, timer, sleep, and `adsk.doEvents` scan passed
- `sys.path` boundary scan passed
- third-party dependency scan passed
- generated and tracked artifact scan passed after cache cleanup
- documentation headings, code fences, and 66 relative/external links passed
- TODO and debug-code scan passed

## Known limitations

- Only Rock has a Family registry.
- Bark, Coral, Sponge, and Root are explicit placeholders rather than empty
  selectable Family lists.
- `family_id` remains the optional request field name for compatibility.
- the existing Fusion command-input ID remains `natureRockFamily`.
- Family parameter schemas are validated when applied by the existing preset
  metadata; Sprint 18 does not introduce a new generic Family schema language.
- no generator algorithm or geometry abstraction is moved in this Sprint.
