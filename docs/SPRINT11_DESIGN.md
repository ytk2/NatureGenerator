# Sprint 11 Design: Root Generator and Public Project Foundation

## Goals

Sprint 11 adds the first deterministic growth-and-branching generator and a
public documentation foundation. Root is unreleased work until merge, real
Fusion acceptance, and an explicit release tag. It is a procedural branching
form, not a botanical simulation or a claim of species reproduction.

## Root parameter model

| Parameter | Default | Bounds | Meaning |
| --- | ---: | ---: | --- |
| Length | 100 mm | 40–180 mm | Primary downward extent |
| Root Radius | 8 mm | 4–20 mm | Primary radius at the crown |
| Branch Count | 5 | 1–8 | Number of lateral roots |
| Branching | 0.45 | 0–1 | Secondary-branch strength and probability |
| Spread | 0.65 | 0.1–1 | Lateral direction strength |
| Taper | 0.65 | 0.2–0.85 | Radius reduction toward tips |
| Gravity | 0.70 | 0–1 | Downward direction bias |
| Seed | 11 | 0–2,147,483,647 | Deterministic variation key |
| Resolution | 37 | 37–41 | Samples per axis |

In addition to metadata bounds, `0.08 * length <= root_radius <= 0.2 * length`
and the computed minimum terminal radius must be at least 0.75 mm. The lower
ratio prevents narrow junctions from separating at the supported samples per
axis. Branch depth is fixed at two and total segment count is capped at 28.
These rules prevent impractical tips, unbounded work, and a crown that consumes
most of the requested length.

## Skeleton generation

The primary root is four connected segments progressing predominantly down the
negative Z axis. Small seeded lateral offsets make it asymmetric without
removing the dominant direction. Each requested lateral root attaches to an
interior primary point. Its azimuth, attachment fraction, length, and small
direction variation come from the existing fixed 32-bit deterministic lattice
mixer. Direction combines a horizontal component controlled by `spread` with a
negative-Z component controlled by `gravity`.

Each lateral root contains two tapered segments. `branching` controls whether a
single secondary segment is added from its interior and how long that segment
is. This staged method has no unbounded recursion: depth is at most two and the
hard segment cap is 28. Segment records are immutable and contain start/end
points, start/end radii, and depth. Tests require no zero-length segment and
positive radii throughout.

No Python `hash()`, global random state, or third-party dependency is used.
Identical inputs therefore produce identical ordered segment tuples. A stable
mesh digest is recorded after the defaults and bounds are finalized.

## Thickening and implicit union

Each skeleton segment becomes a variable-radius capsule-like field. For a point
`p`, the implementation projects onto segment `a -> b`, clamps the interpolation
fraction `t` to `[0, 1]`, linearly interpolates radius `r(t)`, and evaluates:

```text
segment_field(p) = distance(p, closest_point(a, b)) - r(t)
```

The Root field is the minimum of every segment field and a compact sphere at the
origin with radius `1.1 * root_radius`. This hard implicit union is closed and
keeps the crown connected to the primary root. Lateral branches start inside
the primary solid, so their capsules overlap structurally.

Branch self-intersection is acceptable. Overlapping branches are treated as one
implicit union; acceptance depends on the extracted result remaining manifold,
watertight, nondegenerate, and single-component. Detached debris is never added
as a separate primitive.

## Bounds, topology, and performance

Sampling bounds are derived from all skeleton endpoints, expanded on every axis
by the greater of `1.8 * root_radius` and `0.08 * length`. This includes all
capsule radii plus an outside grid layer. Tests exercise supported extremes and
require that no mesh vertex contacts a sampling plane.

Root uses the existing `VoxelGrid`, Marching Tetrahedra extractor, shared mesh
validator/statistics, `GeneratorResult` assembly, and Fusion adapter. Runtime
validation requires a non-empty, manifold, watertight mesh. Tests additionally
require finite coordinates, no degenerate faces, one connected component,
closed tips, bounded segment count, and deterministic topology.

Resolution is narrowed to 37–41. Extreme branch configurations produced
sampling-disconnected thin junctions at 29 and 33, while 37 and 41 preserved a
single extracted component. Default and maximum runs are benchmarked after the
final field is stable because cost scales with both cubic voxel count and the
number of segment fields evaluated per sample.

## Factory, UI, and compatibility

Root uses stable IDs `root` and is registered explicitly as
`root -> RootGenerator`. Existing `GenerationRequest`, `MeshGenerator`, and
factory entry points are unchanged. Root metadata uses only the already
supported `length`, `float`, and `integer` types. The Fusion command therefore
creates Root controls automatically and never imports or branches on
`RootGenerator`.

Coral's fixed capsule union is not changed or generalized. Root owns its narrow
skeleton and tapered-segment implementation because Coral has no generated
skeleton or taper metadata to share. Sponge, Coral, Rock, and Bark routing are
regression-tested; Rock retains its exact published deterministic digest and
bounds.

## Public documentation structure

- `README.md`: concise product entry point, stable/unreleased status, real image
  only when present, and links to deeper documentation.
- `VISION.md`: product problem, direction, fabrication intent, principles, and
  long-term scope.
- `docs/GETTING_STARTED.md`: separate user and developer workflows, Fusion
  loading, parameter guidance, troubleshooting, and v0.8.0 recovery.
- `docs/GALLERY.md`: evidence-based generator gallery plus missing-image capture
  checklist; no fabricated placeholders.
- `docs/RELEASING.md`: the established branch, review, real-Fusion acceptance,
  Draft PR, merge, immutable annotated tag, and optional GitHub Release flow.
- `docs/README.md`: documentation index linking every public entry point and
  Sprint design record.

The only existing generator image is
`docs/images/v0.5.0-generate-nature-dialog.png`. Desired canonical images are
`sponge.png`, `coral.png`, `rock.png`, `bark.png`, and `root.png`; missing files
are documented but not linked as images until supplied.

## Known risks and limitations

- A single samples-per-axis value gives different physical spacing on elongated
  Root bounds.
- Hard capsule union can show blending ridges where branches meet.
- Growth is staged arithmetic, not biological root development.
- Self-intersections are accepted only when final topology remains valid.
- No preview, progress, cancellation, smoothing, decimation, or installer is
  introduced.
- Real Fusion acceptance covered the nine Root controls, parameter effects,
  MeshBody insertion, and command lifecycle; it was not exhaustive across all
  parameter combinations.

## Real Fusion acceptance

Tested successfully with Autodesk Fusion on macOS. NatureGenerator loaded,
**Generate Nature** appeared once, and Root was executable without a Coming Soon
label. The Root preset displayed Length, Root Radius, Branch Count, Branching,
Spread, Taper, Gravity, Seed, and Resolution. MeshBody creation succeeded with
the name `NatureGenerator Root`, and parameter changes produced different
geometry.

Observed runs included:

- 6,568 vertices, 13,136 faces, approximately 2.498 seconds
- 7,452 vertices, 14,900 faces, approximately 3.941 seconds

No startup failure or duplicate command control was observed. This acceptance
records the tested runs and does not claim that every supported parameter
combination was exercised in Fusion.

## Known visual limitation

Root v1 is a deterministic branching implicit solid with a dominant primary
root and lateral branches. Its current visual character can resemble a
simplified branching pipe or stylized root rather than a botanically realistic
root system. More natural branching angles, hierarchical thickness, finer
terminal roots, ground interaction, and space-colonization growth remain future
work. Root v1 does not claim botanical simulation or species reproduction.
