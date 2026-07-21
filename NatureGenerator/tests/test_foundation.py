"""Structural checks for the initial project foundation."""

import json
import unittest
from pathlib import Path


class FoundationTests(unittest.TestCase):
    """Verify files that must remain usable outside Fusion 360."""

    def test_manifest_is_valid_json(self):
        manifest = Path(__file__).parents[1] / "NatureGenerator.manifest"
        with manifest.open(encoding="utf-8") as stream:
            data = json.load(stream)

        self.assertEqual(data["autodeskProduct"], "Fusion360")
        self.assertEqual(data["type"], "addin")

    def test_geometry_and_presets_do_not_import_fusion_api(self):
        package_root = Path(__file__).parents[1]
        for folder in ("core", "generators", "presets"):
            for module in (package_root / folder).glob("*.py"):
                self.assertNotIn("import adsk", module.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
