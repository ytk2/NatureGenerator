"""Adapt one Fusion body selection into immutable procedural geometry."""

from typing import Iterable, Sequence, Tuple

from core.mesh import TriangleMesh
from procedural import ProceduralInputGeometry, SourceType


CENTIMETERS_TO_MILLIMETERS = 10.0


class FusionSelectionError(ValueError):
    pass


def _point_coordinates(point) -> Tuple[float, float, float]:
    if hasattr(point, "asArray"):
        values = point.asArray()
    else:
        values = (
            getattr(point, "x"),
            getattr(point, "y"),
            getattr(point, "z"),
        )
    return tuple(
        float(value) * CENTIMETERS_TO_MILLIMETERS for value in values
    )  # type: ignore[return-value]


def _polygon_mesh_data(polygon_mesh) -> TriangleMesh:
    if polygon_mesh is None:
        raise FusionSelectionError("Fusion produced no tessellation")
    coordinates = getattr(polygon_mesh, "nodeCoordinates", None)
    indices = getattr(polygon_mesh, "nodeIndices", None)
    if coordinates is None or indices is None:
        raise FusionSelectionError("Fusion tessellation data is unavailable")
    vertices = tuple(_point_coordinates(point) for point in coordinates)
    flat_indices = tuple(int(value) for value in indices)
    if len(flat_indices) % 3:
        raise FusionSelectionError("Fusion tessellation indices are not triangular")
    faces = tuple(
        (flat_indices[index], flat_indices[index + 1], flat_indices[index + 2])
        for index in range(0, len(flat_indices), 3)
    )
    if not vertices or not faces:
        raise FusionSelectionError("Fusion tessellation is empty")
    try:
        return TriangleMesh(vertices, faces)
    except (TypeError, ValueError) as error:
        raise FusionSelectionError(
            "Fusion tessellation contains invalid geometry: {}".format(error)
        ) from error


def _brep_polygon_mesh(body, preview: bool):
    manager = getattr(body, "meshManager", None)
    if manager is None:
        raise FusionSelectionError("the selected solid cannot be tessellated")
    create = getattr(manager, "createMeshCalculator", None)
    if callable(create):
        calculator = create()
        if calculator is None:
            raise FusionSelectionError("Fusion could not create a tessellator")
        # Fusion uses centimetres internally. Preview permits a coarser surface
        # tolerance; final execution asks for a tighter deterministic default.
        if hasattr(calculator, "surfaceTolerance"):
            calculator.surfaceTolerance = 0.02 if preview else 0.005
        calculate = getattr(calculator, "calculate", None)
        return calculate() if callable(calculate) else None
    display_meshes = getattr(manager, "displayMeshes", None)
    return getattr(display_meshes, "bestMesh", None)


def _mesh_body_polygon_mesh(body):
    for attribute in ("mesh", "displayMesh", "polygonMesh"):
        value = getattr(body, attribute, None)
        if value is not None:
            return value
    manager = getattr(body, "meshManager", None)
    display_meshes = getattr(manager, "displayMeshes", None)
    return getattr(display_meshes, "bestMesh", None)


def selection_entities(selection_input) -> Tuple[object, ...]:
    count = getattr(selection_input, "selectionCount", 0)
    if count == 0:
        raise FusionSelectionError("select exactly one Solid Body or Mesh Body")
    if count != 1:
        raise FusionSelectionError("select exactly one entity; multiple selections are unsupported")
    selection = selection_input.selection(0)
    entity = getattr(selection, "entity", None)
    if entity is None:
        raise FusionSelectionError("the selected Fusion entity is unavailable")
    return (entity,)


class FusionSelectionAdapter:
    """Validate and snapshot one selected BRepBody or MeshBody."""

    def classify(self, entity) -> SourceType:
        import adsk.fusion  # type: ignore[import-not-found]

        if adsk.fusion.BRepBody.cast(entity) is not None:
            return SourceType.SOLID_BODY
        if adsk.fusion.MeshBody.cast(entity) is not None:
            return SourceType.MESH_BODY
        raise FusionSelectionError(
            "unsupported selection; select a Solid Body or Mesh Body"
        )

    def adapt_selection(
        self, selection_input, preview: bool = False
    ) -> ProceduralInputGeometry:
        return self.adapt(selection_entities(selection_input)[0], preview)

    def adapt(self, entity, preview: bool = False) -> ProceduralInputGeometry:
        source_type = self.classify(entity)
        polygon_mesh = (
            _brep_polygon_mesh(entity, preview)
            if source_type is SourceType.SOLID_BODY
            else _mesh_body_polygon_mesh(entity)
        )
        mesh = _polygon_mesh_data(polygon_mesh)
        name = getattr(entity, "name", None) or "Unnamed Body"
        identifier = (
            getattr(entity, "entityToken", None)
            or getattr(entity, "tempId", None)
            or "{}:{}".format(source_type.value, id(entity))
        )
        return ProceduralInputGeometry(
            source_type=source_type,
            mesh=mesh,
            source_name=str(name),
            source_identifier=str(identifier),
            units="mm",
            provenance={
                "adapter": "fusion_selection",
                "tessellation_quality": "preview" if preview else "final",
            },
        )

    def source_label(self, selection_input) -> str:
        entities = selection_entities(selection_input)
        source_type = self.classify(entities[0])
        return {
            SourceType.SOLID_BODY: "Solid Body",
            SourceType.MESH_BODY: "Mesh Body",
        }[source_type]
