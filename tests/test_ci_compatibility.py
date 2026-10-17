"""Prevent previously reported Hassfest / HACS package failures (offline)."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "smsgetaweybridge"


class CompatibilityTests(unittest.TestCase):
    def test_hassfest_manifest_key_order(self):
        data = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
        keys = list(data)
        self.assertEqual(keys[:2], ["domain", "name"])
        self.assertEqual(keys[2:], sorted(keys[2:]))
        self.assertEqual(data["version"], "1.0.1")

    def test_config_entry_only_schema_is_declared(self):
        source = (COMPONENT / "__init__.py").read_text(encoding="utf-8")
        self.assertIn("async def async_setup(", source)
        self.assertIn("CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)", source)

    def test_brand_png_is_valid_and_correct_size(self):
        # Validate basic PNG signature and IHDR without external dependencies.
        for name in ("icon.png", "dark_icon.png"):
            with self.subTest(name=name):
                data = (COMPONENT / "brand" / name).read_bytes()
                self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
                self.assertGreater(len(data), 300)
                self.assertEqual(int.from_bytes(data[16:20], "big"), 256)
                self.assertEqual(int.from_bytes(data[20:24], "big"), 256)

    def test_ci_uses_node24_actions(self):
        workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
        self.assertIn("actions/checkout@v5", workflow)
        self.assertIn("actions/setup-python@v6", workflow)
        self.assertNotIn("actions/checkout@v4", workflow)
        self.assertNotIn("actions/setup-python@v5", workflow)

    def test_documentation_describes_github_only_requirements(self):
        doc = (ROOT / "docs" / "RELEASING.md").read_text(encoding="utf-8")
        self.assertIn("About", doc)
        self.assertIn("Topics", doc)
        self.assertIn("Description", doc)
        self.assertIn("cannot be applied by uploading a ZIP", doc)


if __name__ == "__main__":
    unittest.main()
