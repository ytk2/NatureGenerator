"""Small, dependency-free marching tetrahedra benchmark.

Run from the repository root:

    PYTHONPATH=NatureGenerator python3 NatureGenerator/examples/benchmark_marching_tetrahedra.py
"""

import argparse
from time import perf_counter

from core.marching_tetrahedra import extract_isosurface
from core.mesh_optimizer import optimize_mesh
from core.mesh_validator import MeshValidator
from core.voxel_grid import VoxelGrid


def sphere(x, y, z):
    """Unit-sphere scalar field."""

    return x * x + y * y + z * z - 1.0


def run(resolution: int) -> None:
    """Sample and extract a sphere, reporting separate timings and statistics."""

    shape = (resolution, resolution, resolution)
    started = perf_counter()
    grid = VoxelGrid.sample(sphere, (-1.25, -1.25, -1.25), (1.25, 1.25, 1.25), shape)
    sampled = perf_counter()
    mesh = extract_isosurface(grid)
    extracted = perf_counter()
    mesh = optimize_mesh(mesh)
    optimized = perf_counter()
    validation = MeshValidator(require_watertight=True).validate(mesh)
    validated = perf_counter()
    statistics = mesh.statistics()

    print("grid: {} x {} x {}".format(*shape))
    print("sampling: {:.6f} s".format(sampled - started))
    print("extraction: {:.6f} s".format(extracted - sampled))
    print("optimization: {:.6f} s".format(optimized - extracted))
    print("validation: {:.6f} s".format(validated - optimized))
    print("vertices: {}".format(statistics.vertex_count))
    print("triangles: {}".format(statistics.face_count))
    print("watertight: {}".format(validation.watertight))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolution", type=int, default=24, help="samples per axis (default: 24)")
    arguments = parser.parse_args()
    if arguments.resolution < 2:
        parser.error("resolution must be at least 2")
    run(arguments.resolution)
