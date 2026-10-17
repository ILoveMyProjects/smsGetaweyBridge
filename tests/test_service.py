"""Offline test of HA action dispatch; genuine Home Assistant still untested."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace

path = Path(__file__).resolve().parents[1] / 'custom_components/smsgetaweybridge'

for mod in ('voluptuous', 'homeassistant', 'homeassistant.const', 'homeassistant.core',
            'homeassistant.exceptions', 'homeassistant.helpers',
            'homeassistant.helpers.config_validation', 'homeassistant.helpers.aiohttp_client',
            'homeassistant.helpers.storage', 'homeassistant.helpers.service'):
    sys.modules.setdefault(mod, types.ModuleType(mod))

v = sys.modules['voluptuous']
if not hasattr(v, 'Schema'):
    v.Schema = lambda v: v
    v.Required = lambda v: v
    v.Optional = lambda v: v
sys.modules['homeassistant.const'].Platform = SimpleNamespace(BINARY_SENSOR='binary_sensor', SENSOR='sensor')
core = sys.modules['homeassistant.core']
core.HomeAssistant = object
core.ServiceCall = object
errors = sys.modules['homeassistant.exceptions']
errors.HomeAssistantError = type('HomeAssistantError', (Exception,), {})
errors.ServiceValidationError = type('ServiceValidationError', (Exception,), {})
sys.modules['homeassistant.helpers.config_validation'].string = str
sys.modules['homeassistant.helpers.config_validation'].config_entry_only_config_schema = lambda domain: {'config_entry_only': domain}
sys.modules['homeassistant.helpers.service'].async_set_service_schema = lambda *args, **kwargs: None
sys.modules['homeassistant.helpers.aiohttp_client'].async_get_clientsession = lambda h: object()
# Simulate only the GUI/webhook bootstrap: the actual services and manager run.
frontend_stub = types.ModuleType('smsgetaweybridge.frontend')
async def setup_frontend(_hass): pass
frontend_stub.setup_frontend = setup_frontend
sys.modules['smsgetaweybridge.frontend'] = frontend_stub
webhook_stub = types.ModuleType('smsgetaweybridge.webhooks')
async def auto_configure(*args): pass
webhook_stub.auto_configure = auto_configure
webhook_stub.setup_webhook = lambda *args: None
webhook_stub.unload_webhook = lambda *args: None
sys.modules['smsgetaweybridge.webhooks'] = webhook_stub
class Store:
    def __init__(self,*args): pass
    async def async_load(self): return None
    async def async_save(self, data): pass
sys.modules['homeassistant.helpers.storage'].Store = Store

spec = importlib.util.spec_from_file_location('smsgetaweybridge', path/'__init__.py', submodule_search_locations=[str(path)])
integration = importlib.util.module_from_spec(spec)
sys.modules['smsgetaweybridge'] = integration
spec.loader.exec_module(integration)


class Services:
    def __init__(self):
        self.handlers = {}

    def has_service(self, domain, name):
        return (domain, name) in self.handlers

    def async_register(self, domain, name, handler, schema=None):
        self.handlers[(domain, name)] = handler

    def async_remove(self, domain, name):
        self.handlers.pop((domain, name), None)


class Client:
    def __init__(self):
        self.calls = []

    async def send_sms(self, number, message):
        self.calls.append((number, message))
        return {'id':'123'}


class Bus:
    def __init__(self):
        self.events = []

    def async_fire(self, name, data):
        self.events.append((name, data))


class ServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = Client()
        self.services = Services()
        self.bus = Bus()
        self.hass = SimpleNamespace(data={}, services=self.services, bus=self.bus)
        await integration.async_setup(self.hass, {})
        self.handler = self.services.handlers[('smsgetaweybridge','send_sms')]
        manager = SimpleNamespace(track_ha=self.track_ha, origin={})
        self.hass.data['smsgetaweybridge']['gateway'] = SimpleNamespace(
            client=self.client, entry=SimpleNamespace(entry_id='gateway'),
            manager=manager, hass=self.hass)

    async def track_ha(self, mid, number):
        self.hass.data['smsgetaweybridge']['gateway'].manager.origin[mid] = 'homeassistant'

    async def test_send_once(self):
        await self.handler(SimpleNamespace(data={'phone_number':' +44123 ','message':'Alarm'}))
        self.assertEqual(self.client.calls, [('+44123','Alarm')])
        self.assertEqual(self.bus.events[0][1]['message_id'], '123')

    async def test_reject_empty_message(self):
        with self.assertRaises(errors.ServiceValidationError):
            await self.handler(SimpleNamespace(data={'phone_number':'123','message':'   '}))
        self.assertEqual(self.client.calls, [])

    async def test_multiple_clients_need_entry_id(self):
        self.hass.data['smsgetaweybridge']['another'] = SimpleNamespace(client=Client())
        with self.assertRaises(errors.ServiceValidationError):
            await self.handler(SimpleNamespace(data={'phone_number':'123','message':'Hi'}))
        self.assertEqual(self.client.calls, [])


if __name__ == '__main__':
    unittest.main()
