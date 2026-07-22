# Generator Gallery

This gallery links only real project images that are present in the repository.
It does not use generated or substitute screenshots as acceptance evidence.

## Sponge

![Generate Nature dialog and generated Sponge mesh](images/v0.5.0-generate-nature-dialog.png)

The released Sponge preset creates a finite gyroid sheet. The image is a real
macOS Autodesk Fusion acceptance capture from v0.5.0.

## Coral

Coral creates a closed branching implicit solid. A canonical `coral.png`
Fusion capture has not yet been added.

## Rock

Rock creates a deterministic watertight deformed ellipsoid. A canonical
`rock.png` Fusion capture has not yet been added.

## Bark

Bark v1 creates a closed directional-groove trunk segment. Its appearance is
closer to an irregular or twisted trunk than realistic fractured bark. A
canonical `bark.png` Fusion capture has not yet been added.

## Root (unreleased)

Root creates a deterministic connected system of tapered primary and lateral
roots. It passed real Autodesk Fusion acceptance on macOS, including all nine
inputs, MeshBody creation, and parameter variation, but remains unreleased
Sprint 11 work and is not part of stable v0.8.0. Observed runs produced 6,568
vertices and 13,136 faces in approximately 2.498 seconds, and 7,452 vertices and
14,900 faces in approximately 3.941 seconds.

Root v1 can resemble a simplified branching pipe or stylized root rather than a
botanically realistic root system. More natural branching angles, hierarchical
thickness, finer terminal roots, ground interaction, and space-colonization
growth remain future work. A canonical `root.png` Fusion capture has not yet
been added.

## Manual capture checklist

Capture missing images in Autodesk Fusion on macOS after the relevant real
Fusion acceptance test:

- `docs/images/sponge.png`
- `docs/images/coral.png`
- `docs/images/rock.png`
- `docs/images/bark.png`
- `docs/images/root.png` after Root acceptance

Each capture should show the preset selection, its inputs, the resulting named
MeshBody, and enough Fusion UI to establish that it is a real run. Record the
parameters, vertex and face counts, elapsed time, Fusion version, and known
limitations alongside the image. Do not add placeholder or AI-generated
acceptance images.
