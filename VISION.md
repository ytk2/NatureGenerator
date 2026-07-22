# Vision

> Generate manufacturable natural geometry directly inside Autodesk Fusion.

NatureGenerator addresses a practical gap between conventional CAD primitives
and organic forms. Designers should be able to create editable natural
geometry without leaving Fusion, learning a separate sculpting package, or
depending on a scanned asset whose provenance and dimensions are unclear.

## Product direction

NatureGenerator builds forms procedurally from explicit dimensions, variation
controls, and deterministic seeds. Procedural geometry is complementary to
photogrammetry and scanned meshes: scans reproduce one captured object, while
generators create repeatable families of forms that can be sized and varied for
a design.

The current released generators are Sponge, Coral, Rock, and Bark. Root is the
current unreleased generator. They support experiments in additive
manufacturing, casting patterns, texture studies, props, fixtures, architectural
details, and other fabrication-oriented workflows.

## Principles

- Keep geometry algorithms independent of Autodesk Fusion.
- Make every variation reproducible from parameters and a seed.
- Prefer bounded algorithms and explicit validation over hidden heuristics.
- Expose generator inputs through stable preset metadata.
- Preserve old generator output when shared infrastructure changes.
- Record real Fusion evidence and visual limitations honestly.

Validated closed presets target manifold, watertight output, but that does not
make every parameter combination automatically suitable for every fabrication
process. Wall thickness, scale, tolerances, orientation, machine limits, and
material behavior still require user review.

## Long-term scope

The project can grow toward richer branching and surface models, preview and
cancellation, mesh finishing, more fabrication checks, and straightforward
installation and release packaging. Biological realism and species
reproduction are not implied by the current procedural models.
