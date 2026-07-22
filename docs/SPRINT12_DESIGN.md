# Sprint 12 Design: Interactive Preview Foundation

## Goal and safety policy

Sprint 12 adds an explicit, reversible preview lifecycle to **Generate Nature**.
Fusion stability and cleanup take priority over continuous updates. Preview is
unreleased work until merge, real Fusion acceptance, and a release tag.

The production interaction is an explicit Preview button. The repository has no
demonstrated host-supported timer or debounce primitive, and mesh extraction is
synchronous and cannot be interrupted safely. Sprint 12 therefore does not use
automatic preview, background threads, `asyncio`, busy waiting, or `sleep()` on
the Fusion UI thread. Debounced live preview remains future work.

## Preview state model

Each open command owns exactly one narrowly scoped `PreviewController`. Its
state is one of `idle`, `generating`, `current`, `stale`, `failed`, or
`finalized`. It retains only:

- the deterministic signature of the source request;
- the actual request used for preview generation;
- the directly returned preview body reference;
- the last successful `GeneratorResult`;
- generation and dirty/current state.

The signature is an ordered tuple containing preset ID, sorted parameter IDs,
explicit value types and values, and requested resolution. It does not use
Python `hash()`. Identical source requests reuse a valid current preview.
Changing any command input marks the preview stale. A stale body can remain
visible until Preview, OK, Cancel, Destroy, or stop, but is never promoted as
current geometry.

## Ownership and cleanup

Ownership is by direct object reference: a controller may delete only the body
returned by its own preview insertion call. Cleanup never searches by name and
never scans or deletes user-created bodies, finalized NatureGenerator bodies,
or bodies belonging to another controller. Deletion is idempotent and checks
the Fusion object's validity where that property is available.

Mandatory cleanup occurs before preview replacement, after preview failure,
on Cancel/Destroy, before stale final regeneration, and during add-in stop.
Promotion removes the body from controller ownership before clearing state, so
later cleanup cannot delete a finalized body. Temporary bodies are named
`NatureGenerator Preview — <Preset>`; final bodies retain
`NatureGenerator <Preset>`.

Document close, active-design change, and workspace change do not have a
verified lifecycle hook in the current repository. Direct-reference cleanup is
defensive when a body has already become invalid, while command Destroy and
add-in stop are the guaranteed application cleanup points. A host crash cannot
run Python cleanup; recovery is to remove any clearly named preview body
manually after reopening the document.

## Command event lifecycle

```text
Command inputs
    -> PreviewController
    -> GenerationRequest
    -> GeneratorFactory
    -> GeneratorResult
    -> MeshBodyBuilder
    -> temporary preview MeshBody

OK
    -> abort/remove the preview transaction
    -> generate current final request in execute
    -> final MeshBody
    -> clear preview state

Cancel / Destroy / Add-in Stop
    -> delete only owned temporary body
    -> clear controller and retained handlers
```

The Preview button is a generic boolean action input recognized through
`inputChanged`, which sets only a pending flag. Fusion then fires the documented
`executePreview` event; validation, generation, and MeshBody insertion occur in
that transaction. Other input changes only mark state stale and never request
generation. Re-entry while `generating` is rejected. Exceptions clear owned
temporary geometry, set a recoverable failed state, and use the existing
logging/message pattern.

The command has Execute, InputChanged, ValidateInputs, and Destroy handlers.
Destroy covers Cancel and dialog close. The add-in retains live controller
references separately so stop can clean them before releasing handlers.

## Preview resolution and finalization

Preview resolution is selected without generator IDs:

```text
preview resolution = min(requested resolution,
                         preset Resolution metadata default)
```

This uses the preset's already validated safe default as a generic cap. At
current defaults the caps are 17 for Sponge, Coral, and Rock, 33 for Bark, and
37 for Root. Preview and final meshes may therefore differ in density when the
user requests a higher resolution.

Preview work is created in Fusion's `executePreview` transaction with
`isValidResult` left false. Fusion aborts that transaction before `execute`, and
OK runs the unchanged final-generation path at requested resolution. This avoids
depending on a preview proxy surviving transaction rollback and ensures stale
geometry is never finalized.

## Compatibility and failure risks

- GeneratorFactory, GenerationRequest, generator output, and preset metadata
  contracts remain unchanged.
- Commands and Fusion UI remain independent of concrete generators.
- Mesh conversion and millimetre-to-centimetre conversion stay in
  `MeshBodyBuilder`; preview insertion changes only naming and ownership.
- Fusion MeshBody transaction rollback, replacement, finalization, and Cancel
  cleanup passed real Fusion acceptance on macOS.
- Synchronous preview can block the dialog for several seconds, especially for
  Root, and cannot be cancelled mid-extraction.
- A stale preview remains visibly present until the next lifecycle action; it
  is tracked as stale internally and cannot be promoted.
- Reliable opacity or appearance behavior is not established, so temporary
  naming is the required visual distinction.

## Local performance reference

The following sequential runs use each preset's default parameters. Preview and
final resolution are equal at defaults, so their mesh counts match; timings are
local references rather than guarantees. When a user requests a higher final
resolution, Preview remains capped at the value shown and OK regenerates the
higher-density final mesh.

| Preset | Preview res. | Preview vertices/faces | Preview time | Final res. | Final vertices/faces | Final time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Sponge | 17 | 5,684 / 10,944 | 0.329 s | 17 | 5,684 / 10,944 | 0.304 s |
| Coral | 17 | 960 / 1,916 | 0.144 s | 17 | 960 / 1,916 | 0.145 s |
| Rock | 17 | 1,090 / 2,176 | 0.159 s | 17 | 1,090 / 2,176 | 0.159 s |
| Bark | 33 | 14,422 / 28,840 | 1.057 s | 33 | 14,422 / 28,840 | 1.077 s |
| Root | 37 | 6,568 / 13,136 | 2.815 s | 37 | 6,568 / 13,136 | 2.830 s |

## Real Fusion acceptance

Verified successfully in Autodesk Fusion on macOS:

- **Generate Nature** opened and the explicit Preview button worked.
- Sponge preview appeared in the viewport and Browser as
  `NatureGenerator Preview — Sponge`.
- Changing Cell Size and pressing Preview again replaced rather than duplicated
  the prior preview.
- OK left one final generated MeshBody from current inputs.
- Cancel removed temporary preview geometry.
- Model-changing preview work ran through `executePreview`.
- No orphaned preview body, startup failure, or duplicate command control was
  observed.

The observed Sponge preview at resolution 17 contained 5,684 vertices and
10,944 faces and completed in approximately 0.25–0.27 seconds. Parameter
changes require pressing Preview again; automatic live preview is not included.

## Autodesk API basis

The explicit control uses Autodesk's documented
[`CommandInputs.addBoolValueInput`](https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-fcee3b49-1bf0-415c-9f51-70ab44b20d1b)
button form. Cleanup uses the documented command
[`destroy` event](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Command_destroy.htm),
which is fired when the command is destroyed, and the documented MeshBody
[`isValid` and `deleteMe`](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/MeshBody.htm)
members. No undocumented timer or background Fusion API access is assumed.

## Fusion retest wiring correction

The first real Fusion retest showed a visible Preview button but no preview
generation or diagnostic output. The original handler compared
`InputChangedEventArgs.input` with the retained input using Python object
identity. Fusion can expose the same native command input through a different
Python proxy, so identity is not a reliable dispatch key. Preview dispatch now
compares the documented stable command input ID `naturePreview` instead.

Temporary debugging diagnostics established the failing dispatch path. Normal
logging is now limited to concise Preview started, created, replaced, removed,
and failed messages. Entity tokens, object/class dumps, and routine collection
internals are not exposed. Errors retain complete tracebacks in `app.log` and a
concise modal message.

## Fusion insertion transaction correction

The next real Fusion retest proved that generation and
`MeshBodies.addByTriangleMeshData` completed but no body survived in the Browser
or viewport. Preview and final used the same builder and root-component
collection; the difference was their command event. Autodesk explicitly states
that model changes must not be made from `inputChanged` and that creation belongs
in `execute` or `executePreview`. The Preview click now sets a pending flag in
`inputChanged`, and the same insertion path runs only when Fusion subsequently
fires `executePreview`.

The Preview transaction leaves `isValidResult` false, so Fusion rolls it back
before the next preview or final execute. Final output continues through the
proven `execute` path. `MeshBodyBuilder` sets the new body's light bulb on and
calls the documented active viewport `refresh()` method; no `doEvents`, thread,
timer, or sleep is introduced.
