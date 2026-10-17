"""Config flow behavior with Home Assistant API doubles, no HA installation."""
import importlib
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

root = Path(__file__).resolve().parents[1] / 'custom_components' / 'smsgetaweybridge'

# Only enough fake APIs to exercise flow logic; does not replace real HA testing.
vol = types.ModuleType('voluptuous')
class Marker(str):
    pass
vol.Required = lambda key, **kwargs: Marker(key)
vol.Optional = lambda key, **kwargs: Marker(key)
vol.Schema = lambda schema: schema
vol.All = lambda *args: args
vol.Coerce = lambda ty: ty
vol.Range = lambda **kwargs: kwargs
sys.modules.setdefault('voluptuous', vol)

for module in ('homeassistant', 'homeassistant.config_entries', 'homeassistant.helpers',
               'homeassistant.helpers.aiohttp_client', 'homeassistant.helpers.selector'):
    sys.modules.setdefault(module, types.ModuleType(module))

class ConfigFlow:
    def __init_subclass__(cls, **kwargs):
        pass

    async def async_set_unique_id(self, value):
        self.unique_id = value

    def _abort_if_unique_id_configured(self):
        pass

    def _async_current_entries(self):
        return self.others

    def _get_reconfigure_entry(self):
        return self.entry

    def async_show_form(self, **kwargs):
        return {'type': 'form', **kwargs}

    def async_create_entry(self, **kwargs):
        return {'type': 'create', **kwargs}

    def async_update_reload_and_abort(self, entry, data_updates):
        return {'type': 'update', 'entry': entry, 'data': data_updates}

sys.modules['homeassistant.config_entries'].ConfigFlow = ConfigFlow
sys.modules['homeassistant.helpers.aiohttp_client'].async_get_clientsession = lambda hass: object()
s = sys.modules['homeassistant.helpers.selector']
s.TextSelector = lambda options: options
s.TextSelectorConfig = lambda **kwargs: kwargs
s.TextSelectorType = SimpleNamespace(PASSWORD='password')
pkg = sys.modules.get('smsgetaweybridge')
if pkg is None:
    pkg = types.ModuleType('smsgetaweybridge')
    pkg.__path__ = [str(root)]
    sys.modules['smsgetaweybridge'] = pkg
flow_module = importlib.import_module('smsgetaweybridge.config_flow')


class FlowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.flow = flow_module.SMSGatewayConfigFlow()
        self.flow.others = []
        self.flow.entry = SimpleNamespace(entry_id='entry', unique_id='old:8080', data={
            'host':'old', 'port':8080, 'username':'u', 'password':'saved-secret', 'use_ssl':False
        })
        self.updated = []
        self.flow.hass = SimpleNamespace(config_entries=SimpleNamespace(
            async_update_entry=lambda entry, **kwargs: self.updated.append(kwargs)
        ))

    async def test_first_time_manual_config(self):
        with patch.object(flow_module.SMSGatewayConfigFlow, '_check', return_value=None):
            result = await self.flow.async_step_user({
                'host':' phone ', 'port':8080, 'username':'u', 'password':'x', 'use_ssl':False
            })
        self.assertEqual(result['type'], 'create')
        self.assertEqual(result['data']['host'], 'phone')
        self.assertEqual(self.flow.unique_id, 'phone:8080')

    async def test_reconfigure_host_keeps_secret(self):
        with patch.object(flow_module.SMSGatewayConfigFlow, '_check', return_value=None):
            result = await self.flow.async_step_reconfigure({
                'host':'new.local', 'port':8080, 'username':'u', 'password':'', 'use_ssl':True
            })
        self.assertEqual(result['type'], 'update')
        self.assertEqual(result['data']['password'], 'saved-secret')
        self.assertEqual(self.updated, [{'unique_id':'new.local:8080'}])

    async def test_reconfigure_rejects_duplicate(self):
        self.flow.others = [SimpleNamespace(entry_id='other', unique_id='taken:8080')]
        result = await self.flow.async_step_reconfigure({'host':'taken', 'port':8080})
        self.assertEqual(result['errors']['base'], 'already_configured')
        self.assertEqual(self.updated, [])

    async def test_no_old_password_prepopulated(self):
        result = await self.flow.async_step_reconfigure()
        self.assertEqual(result['type'], 'form')
        self.assertNotIn('saved-secret', repr(result))


if __name__ == '__main__':
    unittest.main()
