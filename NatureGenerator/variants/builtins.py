"""Explicit curated built-in variant catalog."""

from .definition import VariantDefinition


def _variant(variant_id, preset_id, display_name, description, **values):
    return VariantDefinition(variant_id, preset_id, display_name, description, values)


BUILT_IN_VARIANTS = (
    _variant("sponge_fine", "sponge", "Fine", "Small, delicate porous cells.",
             cell_size=7.0, thickness=0.14, resolution=21),
    _variant("sponge_balanced", "sponge", "Balanced", "Default porous balance.",
             cell_size=10.0, thickness=0.20, resolution=17),
    _variant("sponge_bold", "sponge", "Bold", "Large, strongly defined cells.",
             cell_size=16.0, thickness=0.32, resolution=17),
    _variant("coral_fine_branching", "coral", "Fine Branching",
             "Slender, closely detailed branching.",
             cell_size=11.0, thickness=0.22, seed=0, resolution=21),
    _variant("coral_balanced", "coral", "Balanced", "Default branching balance.",
             cell_size=14.0, thickness=0.35, seed=0, resolution=17),
    _variant("coral_massive", "coral", "Massive", "Broad, heavy connected growth.",
             cell_size=20.0, thickness=0.55, seed=0, resolution=17),
    _variant("rock_smooth", "rock", "Smooth", "Low-relief rounded stone.",
             size=40.0, roughness=0.10, seed=1, resolution=17),
    _variant("rock_weathered", "rock", "Weathered", "Balanced surface weathering.",
             size=40.0, roughness=0.35, seed=1, resolution=17),
    _variant("rock_rugged", "rock", "Rugged", "Strong irregular surface relief.",
             size=45.0, roughness=0.62, seed=23, resolution=25),
    _variant("bark_subtle", "bark", "Subtle", "Shallow directional grooves.",
             diameter=80.0, height=120.0, bark_depth=2.0, groove_scale=25.0,
             twist=0.0, seed=10, resolution=33),
    _variant("bark_grooved", "bark", "Grooved", "Deeper, more closely spaced grooves.",
             diameter=80.0, height=120.0, bark_depth=7.0, groove_scale=12.0,
             twist=0.10, seed=21, resolution=33),
    _variant("bark_twisted", "bark", "Twisted", "Pronounced directional twist.",
             diameter=75.0, height=150.0, bark_depth=6.0, groove_scale=14.0,
             twist=0.75, seed=33, resolution=37),
    _variant("root_sparse", "root", "Sparse", "Few restrained lateral roots.",
             length=110.0, root_radius=9.0, branch_count=3, branching=0.20,
             spread=0.50, taper=0.72, gravity=0.80, seed=11, resolution=37),
    _variant("root_balanced", "root", "Balanced", "Default root system balance.",
             length=100.0, root_radius=8.0, branch_count=5, branching=0.45,
             spread=0.65, taper=0.65, gravity=0.70, seed=11, resolution=37),
    _variant("root_dense", "root", "Dense", "Dense, strongly branching root system.",
             length=100.0, root_radius=10.0, branch_count=8, branching=0.85,
             spread=0.85, taper=0.55, gravity=0.60, seed=29, resolution=41),
)
