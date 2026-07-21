"""Fusion-independent geometry contracts and data structures."""

from .marching_tetrahedra import extract_field, extract_isosurface
from .mesh import Face, MeshStatistics, Point3, Triangle, TriangleMesh, Vector3
from .mesh_builder import MeshBuilder
from .mesh_optimizer import optimize_mesh
from .mesh_validator import MeshValidation, MeshValidator, ValidationIssue
from .scalar_field import ScalarField
from .voxel_grid import GridShape, VoxelGrid

__all__ = [
    "Face",
    "GridShape",
    "MeshStatistics",
    "MeshBuilder",
    "MeshValidation",
    "MeshValidator",
    "Point3",
    "ScalarField",
    "Triangle",
    "TriangleMesh",
    "Vector3",
    "VoxelGrid",
    "ValidationIssue",
    "extract_field",
    "extract_isosurface",
    "optimize_mesh",
]
