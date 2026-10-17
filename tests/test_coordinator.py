"""Coordinator regression tests using small local HA doubles (no HA install)."""
import importlib
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
PKG_ROOT = ROOT / "custom_components" / "smsgetaweybridge"

for module in ("homeassistant", "homeassistant.helpers", "homeassistant.helpers.storage", "homeassistant.helpers.update_coordinator"):
    sys.modules.setdefault(module, types.ModuleType(module))


class FakeStore:
    data = {}

    def __init__(self, hass, version, key):
        self.key = key

    async def async_load(self):
        return self.data.get(self.key)

    async def async_save(self, value):
        self.data[self.key] = value


class FakeUpdateFailed(Exception):
    pass


class FakeCoordinator:
    def __class_getitem__(cls, _):
        return cls

    def __init__(self, hass, *_args, **_kwargs):
        self.hass = hass
        self.last_update_success = True
        self.data = {}


sys.modules["homeassistant.helpers.storage"].Store = FakeStore
sys.modules["homeassistant.helpers.update_coordinator"].DataUpdateCoordinator = FakeCoordinator
sys.modules["homeassistant.helpers.update_coordinator"].UpdateFailed = FakeUpdateFailed
pkg = types.ModuleType("smsgetaweybridge")
pkg.__path__ = [str(PKG_ROOT)]
sys.modules.setdefault("smsgetaweybridge", pkg)
coordinator_module = importlib.import_module("smsgetaweybridge.coordinator")
api = importlib.import_module("smsgetaweybridge.api")
const = importlib.import_module("smsgetaweybridge.const")


class Client:
    def __init__(self, inbox=None, messages=None):
        self.inbox = inbox or []
        self.messages = messages or []
        self.fail = False

    async def get_all_inbox(self, since=None):
        if self.fail:
            raise api.GatewayHttpError(503)
        return self.inbox[:]

    async def get_all_messages(self):
        if self.fail:
            raise api.GatewayHttpError(503)
        return self.messages[:]


class Bus:
    def __init__(self):
        self.events = []

    def async_fire(self, event, data):
        self.events.append((event, data))


def incoming(i, sec):
    return {"id": str(i), "sender": "+4412345", "contentPreview": "hello", "createdAt": f"2026-10-17T10:{sec//60:02d}:{sec%60:02d}Z"}


def outbound(i, states, current):
    return {"id": str(i), "state": current, "createdAt": "2026-10-17T10:00:00Z", "states": states}


class CoordinatorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        FakeStore.data = {}
        self.hass = SimpleNamespace(bus=Bus())
        self.entry = SimpleNamespace(entry_id="demo", title="S9")
        self.client = Client()
        self.co = coordinator_module.SMSGatewayCoordinator(self.hass, self.entry, self.client)
        await self.co.async_load_state()

    async def test_bootstrap_does_not_emit_history(self):
        self.client.inbox = [incoming(i, i) for i in range(150)]
        await self.co._async_update_data()
        self.assertEqual(self.hass.bus.events, [])
        self.assertTrue(self.co._bootstrapped)
        self.assertEqual(len(self.co._seen), 150)

    async def test_downtime_over_100_records_not_dropped(self):
        self.client.inbox = [incoming(0, 0)]
        await self.co._async_update_data()
        self.client.inbox += [incoming(i, i) for i in range(1, 390)]
        await self.co._async_update_data()
        events = [data for name, data in self.hass.bus.events if name == const.EVENT_SMS_RECEIVED]
        self.assertEqual(len(events), 389)
        self.assertEqual(len({e['message_id'] for e in events}), 389)
        await self.co._async_update_data()
        self.assertEqual(len(self.hass.bus.events), 389)

    async def test_restart_and_same_timestamp_boundary(self):
        self.client.inbox = [incoming("a", 3), incoming("b", 3)]
        await self.co._async_update_data()
        restarted = coordinator_module.SMSGatewayCoordinator(self.hass, self.entry, self.client)
        await restarted.async_load_state()
        self.client.inbox.append(incoming("c", 3))
        await restarted._async_update_data()
        self.assertEqual([e['message_id'] for _, e in self.hass.bus.events], ['c'])
        self.assertEqual(restarted._inbox_checkpoint, self.co._inbox_checkpoint)

    async def test_status_history_replays_intermediate_transitions(self):
        self.client.messages = [outbound(1, {'Pending': '2026-10-17T10:00:00Z'}, 'Pending')]
        await self.co._async_update_data()
        self.client.messages = [outbound(1, {
            'Pending': '2026-10-17T10:00:00Z',
            'Sent': '2026-10-17T10:01:00Z',
            'Delivered': '2026-10-17T10:02:00Z',
        }, 'Delivered')]
        await self.co._async_update_data()
        self.assertEqual([e['state'] for name, e in self.hass.bus.events if name == const.EVENT_SMS_STATUS],
                         ['Sent', 'Delivered'])
        await self.co._async_update_data()
        self.assertEqual(len(self.hass.bus.events), 2)

    async def test_failure_does_not_commit_or_emit(self):
        await self.co._async_update_data()
        checkpoint = self.co._inbox_checkpoint
        self.client.fail = True
        with self.assertRaises(FakeUpdateFailed):
            await self.co._async_update_data()
        self.assertEqual(self.hass.bus.events, [])
        self.assertEqual(self.co._inbox_checkpoint, checkpoint)

    async def test_legacy_data_migrates_without_replay(self):
        FakeStore.data['smsgetaweybridge_demo'] = {
            'bootstrapped': True, 'seen': ['1'], 'states': {'x': 'Pending'}
        }
        old = coordinator_module.SMSGatewayCoordinator(self.hass, self.entry, self.client)
        await old.async_load_state()
        self.client.inbox = [incoming(i, i) for i in range(100)]
        await old._async_update_data()
        self.assertEqual(self.hass.bus.events, [])
        self.assertFalse(old._migration_pending)

    async def test_unknown_date_fallback_no_repeat(self):
        self.client.inbox = [{'id': 'a'}]
        await self.co._async_update_data()
        self.client.inbox.append({'id': 'b'})
        await self.co._async_update_data()
        await self.co._async_update_data()
        self.assertEqual([e['message_id'] for _, e in self.hass.bus.events], ['b'])

    async def test_outbound_change_after_restart(self):
        self.client.messages = [outbound(7, {'Pending': '2026-10-17T10:00:00Z'}, 'Pending')]
        await self.co._async_update_data()
        restarted = coordinator_module.SMSGatewayCoordinator(self.hass, self.entry, self.client)
        await restarted.async_load_state()
        self.client.messages = [outbound(7, {
            'Pending': '2026-10-17T10:00:00Z',
            'Sent': '2026-10-17T10:01:00Z'}, 'Sent')]
        await restarted._async_update_data()
        self.assertEqual([e['state'] for _, e in self.hass.bus.events], ['Sent'])


if __name__ == '__main__':
    unittest.main()
