"""Fusion MeshBody insertion boundary for generated volumes."""

from .mesh_body import MeshBodyBuilder


class VolumeMeshBuilder(MeshBodyBuilder):
    """Semantic volume adapter reusing indexed TriangleMesh insertion."""
