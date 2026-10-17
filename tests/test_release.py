"""Offline checks for GitHub release packaging and version-tag rules."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_release import prepare_release  # noqa: E402


class ReleaseTests(unittest.TestCase):
    def test_release_package_and_checksum(self):
        with tempfile.TemporaryDirectory() as folder:
            archive, checksum, notes = prepare_release('v0.1.1', Path(folder))
            self.assertTrue(archive.exists())
            self.assertTrue(checksum.exists())
            self.assertTrue(notes.exists())
            with ZipFile(archive) as zipped:
                self.assertIsNone(zipped.testzip())
                self.assertIn('custom_components/smsgetaweybridge/manifest.json', zipped.namelist())
                self.assertIn('custom_components/smsgetaweybridge/translations/en.json', zipped.namelist())
                self.assertFalse(any('__pycache__' in name or name.endswith('.pyc') for name in zipped.namelist()))
                self.assertFalse(any(name.startswith('tests/') for name in zipped.namelist()))
            content = checksum.read_text().strip()
            self.assertEqual(content, hashlib.sha256(archive.read_bytes()).hexdigest() + '  ' + archive.name)
            self.assertIn('0.1.1', notes.read_text())

    def test_version_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, 'mismatches'):
                prepare_release('v0.1.0', Path(folder))

    def test_invalid_tag_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            for invalid in ('0.1.1', 'v0.1.1-rc.1', 'v0.1.1/../../tmp', 'v0.1', ''):
                with self.subTest(tag=invalid), self.assertRaisesRegex(ValueError, 'tag format'):
                    prepare_release(invalid, Path(folder))

    def test_english_readme_and_owner_metadata(self):
        import json
        metadata = json.loads((ROOT / 'custom_components/smsgetaweybridge/manifest.json').read_text())
        self.assertEqual(metadata['codeowners'], ['@ILoveMyProjects'])
        self.assertEqual(metadata['documentation'], 'https://github.com/ILoveMyProjects/smsGetaweyBridge#readme')
        self.assertEqual(metadata['issue_tracker'], 'https://github.com/ILoveMyProjects/smsGetaweyBridge/issues')
        readme = (ROOT / 'README.md').read_text()
        self.assertIn('Installation' if 'Installation' in readme else 'Install using HACS', readme)
        self.assertIn('[Polski]', readme)
        self.assertNotIn('TWOJ_LOGIN_GITHUB', readme)
        self.assertTrue((ROOT / 'docs/README_PL.md').exists())

    def test_workflow_contains_tag_gate_and_validators(self):
        workflow = (ROOT / '.github/workflows/tests.yml').read_text()
        for section in ('hacs/action@main', 'home-assistant/actions/hassfest@master',
                        "startsWith(github.ref, 'refs/tags/v')", 'tools/build_release.py',
                        'needs:', 'gh release create', 'contents: write'):
            with self.subTest(check=section):
                self.assertIn(section, workflow)


if __name__ == '__main__':
    unittest.main()
