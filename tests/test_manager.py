"""Regression checks for template rendering, groups, persisted origin and privacy."""
import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace

PKG = Path(__file__).resolve().parents[1] / 'custom_components/smsgetaweybridge'

store_stub = sys.modules.setdefault('homeassistant.helpers.storage', types.ModuleType('homeassistant.helpers.storage'))
class Store:
    data = {}
    def __init__(self, hass, version, key): self.key = key
    async def async_load(self): return self.data.get(self.key)
    async def async_save(self, value): self.data[self.key] = value
store_stub.Store = Store
spec = importlib.util.spec_from_file_location('bridge_manager_test', PKG/'manager.py')
manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manager)

class ManagerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        Store.data = {}
        self.m = manager.BridgeManager(SimpleNamespace(), 'test1')
        await self.m.load()

    async def test_safe_variable_interpolation(self):
        self.assertEqual(manager.render_message('Alert $host: $$5', {'host':'nas'}),'Alert nas: $5')
        with self.assertRaises(ValueError): manager.render_message('Hi $missing', {})
        with self.assertRaises(ValueError): manager.render_message('', {})

    async def test_group_format_and_no_duplicates(self):
        await self.m.edit('group','admins',['+441234567890','+441234567890'])
        self.assertEqual(self.m.groups['admins'], ['+441234567890'])
        with self.assertRaises(ValueError): await self.m.edit('group','bad',['1234'])

    async def test_template_requires_group(self):
        with self.assertRaises(ValueError):
            await self.m.edit('template','alert',{'group':'nonexistent','body':'Hi'})
        await self.m.edit('group','ops',['+48123123123'])
        await self.m.edit('template','alert',{'group':'ops','body':'Alert: $service'})
        with self.assertRaises(ValueError): await self.m.edit('group','ops',None)

    async def test_id_persists_across_restart_and_no_body_in_log(self):
        await self.m.track_ha('msg_1','+48123123123')
        await self.m.event('status','msg_1','Delivered')
        await self.m.event('status','ubuntu_x','Sent')
        newer=manager.BridgeManager(SimpleNamespace(),'test1')
        await newer.load()
        self.assertEqual(newer.origin['msg_1'],'homeassistant')
        self.assertEqual(newer.logs[-1]['source'],'external/unknown')
        self.assertEqual(newer.logs[0]['detail'],'***123')
        self.assertNotIn('+48123123123',repr(newer.summary()['logs']))

    async def test_cap_history(self):
        for i in range(320): self.m._append('status', str(i),'external/unknown')
        self.assertEqual(len(self.m.logs),300)
        self.assertEqual(len(self.m.summary()['logs']),100)

    async def test_reject_invalid_name(self):
        with self.assertRaises(ValueError): await self.m.edit('group','../../etc',['+441234567890'])

    async def test_status_log_safe_truncation(self):
        await self.m.event('status','id_1','X'*400)
        self.assertLessEqual(len(self.m.logs[-1]['detail']),70)

if __name__ == '__main__': unittest.main()
