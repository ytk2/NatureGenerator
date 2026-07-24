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


def _mesh_coordinates(mesh) -> Tuple[Tuple[float, float, float], ...]:
    """Read either Point3D coordinates or Fusion's flat numeric arrays."""

    coordinates = getattr(mesh, "nodeCoordinates", None)
    point_coordinates = (
        tuple(_point_coordinates(point) for point in coordinates)
        if coordinates is not None else None
    )
    if point_coordinates:
        return point_coordinates
    for attribute in ("nodeCoordinatesAsDouble", "nodeCoordinatesAsFloat"):
        flat = getattr(mesh, attribute, None)
        if flat:
            values = tuple(float(value) for value in flat)
            if len(values) % 3:
                raise FusionSelectionError(
                    "Fusion tessellation coordinates are incomplete"
                )
            return tuple(
                tuple(
                    values[index + axis] * CENTIMETERS_TO_MILLIMETERS
                    for axis in range(3)
                )
                for index in range(0, len(values), 3)
            )
    if point_coordinates is not None:
        return point_coordinates
    raise FusionSelectionError("Fusion tessellation coordinates are unavailable")


def _triangulated_indices(mesh) -> Tuple[int, ...]:
    """Read TriangleMesh indices or triangulate PolygonMesh faces."""

    direct = getattr(mesh, "nodeIndices", None)
    if direct is not None:
        return tuple(int(value) for value in direct)

    triangles = [
        int(value) for value in (
            getattr(mesh, "triangleNodeIndices", None) or ()
        )
    ]
    quads = tuple(
        int(value) for value in (
            getattr(mesh, "quadNodeIndices", None) or ()
        )
    )
    if len(quads) % 4:
        raise FusionSelectionError("Fusion quad indices are incomplete")
    for index in range(0, len(quads), 4):
        a, b, c, d = quads[index:index + 4]
        triangles.extend((a, b, c, a, c, d))

    polygon_indices = tuple(
        int(value) for value in (
            getattr(mesh, "polygonNodeIndices", None) or ()
        )
    )
    polygon_counts = tuple(
        int(value) for value in (
            getattr(mesh, "nodeCountPerPolygon", None) or ()
        )
    )
    offset = 0
    for count in polygon_counts:
        polygon = polygon_indices[offset:offset + count]
        if count < 3 or len(polygon) != count:
            raise FusionSelectionError("Fusion polygon indices are incomplete")
        for index in range(1, count - 1):
            triangles.extend((polygon[0], polygon[index], polygon[index + 1]))
        offset += count
    if offset != len(polygon_indices):
        raise FusionSelectionError("Fusion polygon counts do not match indices")
    return tuple(triangles)


def _polygon_mesh_data(polygon_mesh) -> TriangleMesh:
    if polygon_mesh is None:
        raise FusionSelectionError("Fusion produced no tessellation")
    vertices = _mesh_coordinates(polygon_mesh)
    flat_indices = _triangulated_indices(polygon_mesh)
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
        result = calculate() if callable(calculate) else None
        # Some Fusion Python builds wrap returned API objects in a one-value
        # or success/object tuple. Accept that without weakening validation.
        if isinstance(result, (tuple, list)):
            candidates = [
                item for item in result
                if item is not None and not isinstance(item, bool)
            ]
            result = candidates[-1] if candidates else None
        return result
    display_meshes = getattr(manager, "displayMeshes", None)
    return getattr(display_meshes, "bestMesh", None)


def _mesh_body_polygon_mesh(body):
    # displayMesh is always triangular. The original mesh may contain
    # triangles, quads, and arbitrary polygons.
    for attribute in ("displayMesh", "mesh", "polygonMesh"):
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
