"""Unit tests run without Home Assistant or a live SMS gateway."""

import asyncio
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'custom_components/smsgetaweybridge/api.py'
spec = importlib.util.spec_from_file_location('smsgetaweybridge_api', PATH)
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


class Response:
    def __init__(self, status, data):
        self.status = status
        self.data = data

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def json(self, **_):
        return self.data


class Session:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


class APITests(unittest.IsolatedAsyncioTestCase):
    async def test_probe_reads_both_endpoints(self):
        s = Session([Response(200, []), Response(200, [])])
        c = api.GatewayClient(s, '192.168.1.2', 8080, 'u', 'secret')
        await c.probe()
        self.assertEqual([call[1].split('/')[-1] for call in s.calls], ['messages', 'inbox'])
        self.assertFalse(s.calls[0][2]['allow_redirects'])

    async def test_send_payload(self):
        s = Session([Response(202, {'id': 'x'})])
        c = api.GatewayClient(s, '192.168.1.2', 8080, 'u', 'secret')
        result = await c.send_sms('+48123123123', 'Hello')
        self.assertEqual(result['id'], 'x')
        self.assertEqual(s.calls[0][2]['json'], {'phoneNumbers': ['+48123123123'], 'textMessage': {'text': 'Hello'}})

    async def test_http_404_never_retries_paid_sms(self):
        s = Session([Response(404, {})])
        c = api.GatewayClient(s, '192.168.1.2', 8080, 'u', 'secret')
        with self.assertRaises(api.GatewayHttpError):
            await c.send_sms('123', 'hi')
        self.assertEqual(len(s.calls), 1)
        self.assertTrue(s.calls[0][1].endswith('/message'))

    async def test_http_405_never_retries_paid_sms(self):
        s = Session([Response(405, {})])
        c = api.GatewayClient(s, '192.168.1.2', 8080, 'u', 'secret')
        with self.assertRaises(api.GatewayHttpError):
            await c.send_sms('123', 'hi')
        self.assertEqual(len(s.calls), 1)

    async def test_missing_send_id_is_error(self):
        s = Session([Response(202, {'state': 'Pending'})])
        c = api.GatewayClient(s, '192.168.1.2', 8080, 'u', 'secret')
        with self.assertRaises(api.GatewayResponseError):
            await c.send_sms('123', 'hi')
        self.assertEqual(len(s.calls), 1)

    async def test_pagination_over_100_records(self):
        messages = [{'id': str(i)} for i in range(527)]
        s = Session([Response(200, messages[:250]), Response(200, messages[250:500]), Response(200, messages[500:])])
        c = api.GatewayClient(s, '192.168.1.2', 8080, 'u', 'secret')
        result = await c.get_all_inbox()
        self.assertEqual(len(result), 527)
        self.assertEqual([call[2]['params']['offset'] for call in s.calls], [0, 250, 500])
        self.assertEqual([call[2]['params']['limit'] for call in s.calls], [250]*3)

    async def test_inbox_date_cursor_passed_to_api(self):
        since = api.utc_timestamp('2026-10-17T10:00:00Z')
        s = Session([Response(200, [{'id':'new'}])])
        c = api.GatewayClient(s, '192.168.1.2', 8080, 'u', 'secret')
        self.assertEqual(len(await c.get_all_inbox(since=since)), 1)
        self.assertEqual(s.calls[0][2]['params']['from'], '2026-10-17T10:00:00+00:00')

    async def test_pagination_does_not_hide_second_page_failure(self):
        s = Session([Response(200, [{'id': str(i)} for i in range(250)]), Response(500, {})])
        c = api.GatewayClient(s, '192.168.1.2', 8080, 'u', 'secret')
        with self.assertRaises(api.GatewayHttpError):
            await c.get_all_messages()

    async def test_utc_timestamp_offsets(self):
        self.assertEqual(api.utc_timestamp('2026-10-17T12:00:00+02:00'),
                         api.utc_timestamp('2026-10-17T10:00:00Z'))
        self.assertIsNone(api.utc_timestamp('not a time'))

    async def test_does_not_retry_on_server_error(self):
        s = Session([Response(500, {})])
        c = api.GatewayClient(s, '192.168.1.2', 8080, 'u', 'secret')
        with self.assertRaises(api.GatewayHttpError):
            await c.send_sms('123', 'hi')
        self.assertEqual(len(s.calls), 1)

    async def test_invalid_auth(self):
        s = Session([Response(401, {})])
        c = api.GatewayClient(s, '192.168.1.2', 8080, 'u', 'secret')
        with self.assertRaises(api.GatewayAuthError):
            await c.get_inbox()

    async def test_timeout_no_retry(self):
        s = Session([asyncio.TimeoutError()])
        c = api.GatewayClient(s, '192.168.1.2', 8080, 'u', 'secret')
        with self.assertRaises(api.GatewayConnectionError):
            await c.send_sms('123', 'hi')
        self.assertEqual(len(s.calls), 1)

    async def test_never_follow_redirects(self):
        s = Session([Response(302, None)])
        c = api.GatewayClient(s, '192.168.1.2', 8080, 'u', 'secret')
        with self.assertRaises(api.GatewayHttpError):
            await c.get_inbox()

    async def test_parse_inbox(self):
        s = Session([Response(200, [{'id': '1', 'sender': 'abc', 'contentPreview': 'hello'}])])
        c = api.GatewayClient(s, '192.168.1.2', 8080, 'u', 'secret')
        messages = await c.get_inbox()
        self.assertEqual(api.incoming_event(messages[0])['message'], 'hello')

    async def test_reject_bad_format(self):
        s = Session([Response(200, {'items': []})])
        c = api.GatewayClient(s, '192.168.1.2', 8080, 'u', 'secret')
        with self.assertRaises(api.GatewayResponseError):
            await c.get_messages()

    async def test_no_cloud_hosts(self):
        c = api.GatewayClient(Session([]), '192.168.1.2', 8080, 'u', 'secret')
        self.assertEqual(c.base_url, 'http://192.168.1.2:8080')

    def test_normalize_state(self):
        self.assertEqual(api.message_state({'state': 'Delivered'}), 'Delivered')
        self.assertEqual(api.message_state({'state': {'name': 'Pending'}}), 'Pending')


if __name__ == '__main__':
    unittest.main()
