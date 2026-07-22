"""Convert core triangle meshes into MeshBodies in the active Fusion design."""

from typing import List, Optional, Tuple

from core.mesh import TriangleMesh


MILLIMETERS_TO_CENTIMETERS = 0.1


class FusionAdapterError(RuntimeError):
    """Raised when a core mesh cannot be inserted into Fusion."""


def triangle_mesh_data(mesh: TriangleMesh) -> Tuple[List[float], List[int]]:
    """Flatten a millimeter-based mesh into Fusion's centimeter coordinates."""

    if not isinstance(mesh, TriangleMesh):
        raise TypeError("mesh must be a TriangleMesh")
    if not mesh.faces:
        raise ValueError("mesh must contain at least one triangle")

    coordinates = [
        coordinate * MILLIMETERS_TO_CENTIMETERS
        for vertex in mesh.vertices
        for coordinate in vertex
    ]
    indices = [index for face in mesh.faces for index in face]
    return coordinates, indices


class MeshBodyBuilder:
    """Insert a completed TriangleMesh into a Fusion design."""

    def build(
        self,
        mesh: TriangleMesh,
        name: str = "NatureGenerator Sponge",
        design: Optional[object] = None,
    ) -> object:
        """Create and return a MeshBody in *design* or the active design."""

        import adsk.core  # type: ignore[import-not-found]
        import adsk.fusion  # type: ignore[import-not-found]

        coordinates, indices = triangle_mesh_data(mesh)
        target_design = design
        app = None
        if target_design is None:
            app = adsk.core.Application.get()
            target_design = adsk.fusion.Design.cast(
                app.activeProduct if app else None
            )
        if target_design is None:
            raise FusionAdapterError("an active Fusion design is required")

        root_component = getattr(target_design, "rootComponent", None)
        mesh_bodies = getattr(root_component, "meshBodies", None)
        if mesh_bodies is None:
            raise FusionAdapterError("the active design has no root mesh collection")

        body = mesh_bodies.addByTriangleMeshData(coordinates, indices, [], [])
        if body is None:
            raise FusionAdapterError("Fusion failed to create the MeshBody")
        try:
            if name:
                body.name = name
            if hasattr(body, "isLightBulbOn"):
                body.isLightBulbOn = True
        except Exception:
            delete = getattr(body, "deleteMe", None)
            if callable(delete):
                try:
                    delete()
                except Exception:
                    pass
            raise

        if app is not None:
            viewport = getattr(app, "activeViewport", None)
            refresh = getattr(viewport, "refresh", None)
            if callable(refresh):
                refresh()
        return body
