"""Offline webhook configuration and safety: no network calls."""
import importlib
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]/'custom_components/smsgetaweybridge'
package=types.ModuleType('bridge_webhooks_test');package.__path__=[str(ROOT)]
sys.modules['bridge_webhooks_test']=package
components=sys.modules.setdefault('homeassistant.components',types.ModuleType('homeassistant.components'))
webhook_stub=types.ModuleType('homeassistant.components.webhook')
registrations=[]
webhook_stub.async_register=lambda *args,**kwargs: registrations.append((args,kwargs))
webhook_stub.async_unregister=lambda *args,**kwargs: None
webhook_stub.async_generate_id=lambda: 'random-private-token-1234'
sys.modules['homeassistant.components.webhook']=webhook_stub
components.webhook=webhook_stub
Hooks=importlib.import_module('bridge_webhooks_test.webhooks')

class API:
    def __init__(self):self.hooks=[];self.fail_at=None
    async def list_webhooks(self):return self.hooks.copy()
    async def add_webhook(self,id,url,event):
        if self.fail_at and len(self.hooks)+1==self.fail_at:raise RuntimeError('failure')
        self.hooks.append({'id':id,'url':url,'event':event})

class Manager:
    def __init__(self):self.webhook_id=None;self.callback_base=None;self.saved=0
    async def _save(self):self.saved+=1

class HooksTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        registrations.clear()
        self.api=API()
        self.manager=Manager()
        self.c=SimpleNamespace(client=self.api,manager=self.manager,entry=SimpleNamespace(entry_id='ABC',title='S9'))

    async def test_https_only(self):
        for invalid in ('http://192.168.1.3:8123','https://user:pass@my.lan',
                        'https://my.lan/extra','https://my.lan/?x=1','foo'):
            with self.subTest(url=invalid),self.assertRaises(ValueError):Hooks.validate_base(invalid)
        self.assertEqual(Hooks.validate_base('https://ha.example.lan:8123/'),'https://ha.example.lan:8123')

    async def test_first_configuration_registers_all_events(self):
        await Hooks.configure(None,self.c,'https://ha.example.lan:8123')
        self.assertEqual(len(self.api.hooks),4)
        self.assertEqual(len({x['event'] for x in self.api.hooks}),4)
        self.assertTrue(all(x['url'].startswith('https://ha.example.lan:8123/api/webhook/') for x in self.api.hooks))
        self.assertTrue(registrations[0][1]['local_only'])
        await Hooks.configure(None,self.c,'https://ha.example.lan:8123')
        self.assertEqual(len(self.api.hooks),4)

    async def test_partial_registration_id_is_persisted_for_retry(self):
        self.api.fail_at=2
        with self.assertRaises(RuntimeError):await Hooks.configure(None,self.c,'https://ha.example.lan:8123')
        self.assertEqual(len(self.api.hooks),1)
        self.assertEqual(self.manager.webhook_id,'random-private-token-1234')
        self.api.fail_at=None
        await Hooks.configure(None,self.c,'https://ha.example.lan:8123')
        self.assertEqual(len(self.api.hooks),4)
        self.assertTrue(all(x['url'].endswith(self.manager.webhook_id) for x in self.api.hooks))

    async def test_reject_change_origin(self):
        await Hooks.configure(None,self.c,'https://ha.example.lan')
        with self.assertRaises(ValueError):await Hooks.configure(None,self.c,'https://new.example.lan')

if __name__=='__main__': unittest.main()
