"""Sending actions: IDs, sources and failure handling (no network)."""
import importlib
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace

root = Path(__file__).resolve().parents[1] / 'custom_components' / 'smsgetaweybridge'
package = types.ModuleType('bridge_actions_test')
package.__path__ = [str(root)]
sys.modules['bridge_actions_test'] = package
stub = sys.modules.setdefault('homeassistant.helpers.storage', types.ModuleType('homeassistant.helpers.storage'))
class FakeStore:
    data = {}
    def __init__(self, hass, ver, key): self.key = key
    async def async_load(self): return self.data.get(self.key)
    async def async_save(self, data): self.data[self.key] = data
stub.Store = FakeStore
Actions = importlib.import_module('bridge_actions_test.actions')
Manager = importlib.import_module('bridge_actions_test.manager')

class FakeAPI:
    def __init__(self, fail_on=None): self.calls = [];self.fail_on = fail_on
    async def send_sms(self, number, text):
        self.calls.append((number,text))
        if len(self.calls) == self.fail_on: raise RuntimeError('uncertain')
        return {'id': f'msg{len(self.calls)}'}

class Bus:
    def __init__(self): self.events=[]
    def async_fire(self, key, payload): self.events.append((key,payload))

class ActionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        FakeStore.data={}
        self.bus=Bus()
        self.api=FakeAPI()
        self.manager=Manager.BridgeManager(None,'demo_actions')
        await self.manager.load()
        self.co=SimpleNamespace(
            client=self.api,manager=self.manager,
            entry=SimpleNamespace(entry_id='demo_actions'),hass=SimpleNamespace(bus=self.bus),
        )
        await self.manager.edit('group','admins',['+48123123123','+441234567890'])
        await self.manager.edit('template','alert',{'group':'admins','body':'Warning $device'})

    async def test_send_saved_template_once_each(self):
        ids=await Actions.send_template(self.co,'alert',{'device':'nas'})
        self.assertEqual(ids,['msg1','msg2'])
        self.assertEqual(self.api.calls,[('+48123123123','Warning nas'),('+441234567890','Warning nas')])
        self.assertEqual(self.manager.origin['msg1'],'homeassistant')
        self.assertEqual(len(self.bus.events),2)

    async def test_send_error_is_not_retried(self):
        self.api.fail_on=2
        with self.assertRaisesRegex(RuntimeError,'uncertain'):
            await Actions.send_template(self.co,'alert',{'device':'nas'})
        self.assertEqual(len(self.api.calls),2)
        self.assertEqual(list(self.manager.origin), ['msg1'])

    async def test_missing_vars_sends_nothing(self):
        with self.assertRaises(ValueError):
            await Actions.send_template(self.co,'alert',{})
        self.assertEqual(self.api.calls,[])

if __name__=='__main__': unittest.main()
