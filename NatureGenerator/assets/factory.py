"""Composition of generated meshes into renderer-neutral assets."""

from typing import Any, Mapping, Optional

from core.mesh import TriangleMesh
from presets.preset import NaturePreset

from .definition import (
    AssetMetadata,
    GeneratedAsset,
    MappingDefinition,
    MaterialDefinition,
    TextureSet,
)
from .natural_material import NATURAL_MATERIALS


class GeneratedAssetFactory:
    """Assemble asset intent after geometry generation and validation."""

    @classmethod
    def create(
        cls,
        mesh: TriangleMesh,
        preset: NaturePreset,
        generator_id: str,
        family_id: str = "",
        parameters: Optional[Mapping[str, Any]] = None,
    ) -> GeneratedAsset:
        if not isinstance(mesh, TriangleMesh):
            raise TypeError("mesh must be a TriangleMesh")
        if not isinstance(preset, NaturePreset):
            raise TypeError("preset must be a NaturePreset")
        recorded_parameters = {} if parameters is None else dict(parameters)
        try:
            material = NATURAL_MATERIALS.get(preset.preset_id).definition
        except KeyError:
            material = MaterialDefinition(
                "natural_surface",
                "Natural Surface",
                (0.5, 0.5, 0.5, 1.0),
                roughness=0.8,
            )
        return GeneratedAsset(
            mesh=mesh,
            material=material,
            mapping=MappingDefinition(),
            textures=TextureSet(),
            metadata=AssetMetadata(
                asset_id="{}_asset".format(preset.preset_id),
                display_name="NatureGenerator {}".format(preset.display_name),
                preset_id=preset.preset_id,
                generator_id=generator_id,
                family_id=family_id,
                parameters=recorded_parameters,
            ),
        )
