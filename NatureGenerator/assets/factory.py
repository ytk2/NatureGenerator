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


_MATERIALS = {
    "rock": MaterialDefinition(
        "natural_rock", "Natural Rock", (0.34, 0.32, 0.28, 1.0),
        roughness=0.86,
        procedural_parameters={"pattern": "mineral_variation"},
    ),
    "bark": MaterialDefinition(
        "natural_bark", "Natural Bark", (0.24, 0.12, 0.055, 1.0),
        roughness=0.92,
        normal_strength=1.2,
        procedural_parameters={"pattern": "directional_ridges"},
    ),
    "coral": MaterialDefinition(
        "natural_coral", "Natural Coral", (0.78, 0.36, 0.28, 1.0),
        roughness=0.7,
        procedural_parameters={"pattern": "branch_gradient"},
    ),
    "sponge": MaterialDefinition(
        "natural_sponge", "Natural Sponge", (0.78, 0.58, 0.16, 1.0),
        roughness=0.88,
        procedural_parameters={"pattern": "porous_variation"},
    ),
    "root": MaterialDefinition(
        "natural_root", "Natural Root", (0.29, 0.16, 0.075, 1.0),
        roughness=0.9,
        procedural_parameters={"pattern": "fibrous_variation"},
    ),
    "bone": MaterialDefinition(
        "natural_bone", "Natural Bone", (0.82, 0.79, 0.68, 1.0),
        roughness=0.72,
        procedural_parameters={"pattern": "porous_variation"},
    ),
}


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
        material = _MATERIALS.get(
            preset.preset_id,
            MaterialDefinition(
                "natural_surface",
                "Natural Surface",
                (0.5, 0.5, 0.5, 1.0),
                roughness=0.8,
            ),
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
