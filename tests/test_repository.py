"""Offline repository invariants (do not require HA or a phone)."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'custom_components' / 'smsgetaweybridge'

class RepositoryTests(unittest.TestCase):
    def test_manifest_and_hacs_json(self):
        manifest = json.loads((DIR / 'manifest.json').read_text())
        self.assertEqual(manifest['name'], 'smsGetaweyBridge')
        self.assertEqual(manifest['domain'], DIR.name)
        self.assertTrue(manifest['config_flow'])
        self.assertEqual(manifest['iot_class'], 'local_polling')
        self.assertEqual(json.loads((ROOT / 'hacs.json').read_text())['name'], 'smsGetaweyBridge')

    def test_translations_have_config_fields(self):
        for language in ('en', 'pl'):
            data = json.loads((DIR / 'translations' / f'{language}.json').read_text())
            fields = data['config']['step']['user']['data']
            self.assertEqual(set(fields), {'host', 'port', 'username', 'password', 'use_ssl'})

    def test_no_cloud_or_ssh_in_runtime(self):
        code = '\n'.join(p.read_text() for p in DIR.glob('*.py'))
        self.assertNotIn('api.sms-gate.app', code)
        self.assertNotIn('paramiko', code)
        self.assertNotIn('subprocess', code)

if __name__ == '__main__':
    unittest.main()
