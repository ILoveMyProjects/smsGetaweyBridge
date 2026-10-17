"""Offline regression coverage for dynamic Home Assistant service descriptions."""
import unittest
from types import SimpleNamespace

# Shared test fixtures install fake homeassistant modules; no packages installed.
from test_service import integration, Services, Bus, Client
from smsgetaweybridge.template_actions import update_template_actions, template_options
from smsgetaweybridge.manager import BridgeManager, template_variables
import smsgetaweybridge.template_actions as actions


class TemplateActionsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.services = Services()
        self.bus = Bus()
        self.hass = SimpleNamespace(data={}, services=self.services, bus=self.bus)
        await integration.async_setup(self.hass, {})
        self.manager = BridgeManager(self.hass, 'gateway_x')
        self.manager.groups = {'ops': ['+441234567890']}
        self.manager.templates = {'server_alert': {'group': 'ops', 'body': 'Server $host is ${status} / $$'}}
        self.client = Client()
        self.co = SimpleNamespace(client=self.client, manager=self.manager, hass=self.hass,
                                  entry=SimpleNamespace(entry_id='gateway_x', title='Samsung Galaxy S9'))
        self.hass.data['smsgetaweybridge']['gateway_x'] = self.co
        self.description_log = []
        self.original_schema_setter = actions.async_set_service_schema
        actions.async_set_service_schema = lambda hass, domain, name, desc: self.description_log.append((name, desc))

    async def asyncTearDown(self):
        actions.async_set_service_schema = self.original_schema_setter

    async def test_group_and_variables_appear_in_picker(self):
        await update_template_actions(self.hass)
        self.assertEqual(template_options(self.hass)[0]['value'], 'gateway_x::server_alert')
        send_template_desc = next(d for name,d in self.description_log if name=='send_template')
        opts=send_template_desc['fields']['template']['selector']['select']['options']
        self.assertIn('ops', opts[0]['label'])
        self.assertIn('$host', opts[0]['label'])
        self.assertIn('$status', opts[0]['label'])
        self.assertEqual(template_variables('$$ $host and ${status}'), ['host','status'])

    async def test_individual_action_fields_and_sends_once(self):
        await update_template_actions(self.hass)
        action_id=next(name for domain,name in self.services.handlers if name.startswith('send_saved_'))
        desc=next(d for name,d in self.description_log if name==action_id)
        self.assertEqual(set(desc['fields']), {'host','status'})
        self.assertTrue(all(desc['fields'][k]['required'] for k in ('host','status')))
        await self.services.handlers[('smsgetaweybridge',action_id)](
            SimpleNamespace(data={'host':'NAS','status':'offline'}))
        self.assertEqual(self.client.calls,[('+441234567890','Server NAS is offline / $')])

    async def test_both_send_actions_support_selected_template(self):
        await update_template_actions(self.hass)
        send=self.services.handlers[('smsgetaweybridge','send_sms')]
        await send(SimpleNamespace(data={
            'template':'gateway_x::server_alert','phone_number':'+441111111111',
            'message':'SHOULD_NOT_BE_SENT','variables':{'host':'NAS','status':'down'},
        }))
        self.assertEqual(len(self.client.calls),1)
        self.assertEqual(self.client.calls[0][0],'+441234567890')
        send_saved=self.services.handlers[('smsgetaweybridge','send_template')]
        await send_saved(SimpleNamespace(data={
            'template':'gateway_x::server_alert','variables':{'host':'NAS','status':'down'},
        }))
        self.assertEqual(len(self.client.calls),2)

    async def test_delete_template_removes_old_action(self):
        await update_template_actions(self.hass)
        old=next(name for domain,name in self.services.handlers if name.startswith('send_saved_'))
        self.manager.templates={}
        await update_template_actions(self.hass)
        self.assertNotIn(('smsgetaweybridge',old),self.services.handlers)
        options=template_options(self.hass)
        self.assertEqual(options, [])

    async def test_invalid_placeholder_detected_before_save(self):
        with self.assertRaises(ValueError):
            template_variables('Bad $')
        with self.assertRaises(ValueError):
            template_variables('Bad $123')
    async def test_dedicated_action_includes_exact_saved_body_and_group(self):
        await update_template_actions(self.hass)
        name = next(n for n in self.services.handlers if n[1].startswith('send_saved_'))[1]
        desc = next(d for action_name, d in self.description_log if action_name == name)
        self.assertIn('Server $host is ${status} / $$', desc['description'])
        self.assertIn('Recipient group: ops', desc['description'])
        self.assertIn('Required variables: $host, $status', desc['description'])
        self.assertIn('no JSON', desc['description'])
        self.assertEqual(set(desc['fields']), {'host', 'status'})
        self.assertEqual(desc['fields']['host']['selector'], {'text': {}})
        self.assertIn('Do not enter JSON', desc['fields']['status']['description'])

    async def test_legacy_gateway_field_is_not_in_saved_template_action(self):
        await update_template_actions(self.hass)
        descriptions = dict(self.description_log)
        self.assertNotIn('entry_id', descriptions['send_template']['fields'])
        self.assertNotIn('legacy', str(descriptions['send_template']).lower())
        self.assertIn('entry_id', descriptions['send_sms']['fields'])  # still needed for direct sending to multiple phones
        # The service schema itself must reject entry_id, not merely hide it in the GUI.
        schema = integration.TEMPLATE_SCHEMA
        keys = [str(key) for key in schema.keys()]
        self.assertNotIn('entry_id', keys)

    async def test_unqualified_old_template_name_is_rejected_before_sending(self):
        await update_template_actions(self.hass)
        handler = self.services.handlers[('smsgetaweybridge', 'send_template')]
        from homeassistant.exceptions import ServiceValidationError
        with self.assertRaisesRegex(ServiceValidationError, 'no longer supported'):
            await handler(SimpleNamespace(data={
                'template': 'server_alert',
                'entry_id': 'gateway_x',
                'variables': {'host': 'nas', 'status': 'offline'},
            }))
        self.assertEqual(self.client.calls, [])

    async def test_unqualified_template_is_rejected_in_mixed_send_action(self):
        handler = self.services.handlers[('smsgetaweybridge', 'send_sms')]
        from homeassistant.exceptions import ServiceValidationError
        with self.assertRaises(ServiceValidationError):
            await handler(SimpleNamespace(data={
                'template': 'server_alert',
                'entry_id': 'gateway_x',
                'variables': {'host': 'nas', 'status': 'offline'},
            }))
        self.assertEqual(self.client.calls, [])

    async def test_template_without_variables_has_no_form_fields(self):
        self.manager.templates['static_message'] = {'group': 'ops', 'body': 'Static SMS'}
        await update_template_actions(self.hass)
        name = next(n for d,n in self.services.handlers if n.endswith('_static_message'))
        desc = next(v for k,v in self.description_log if k == name)
        self.assertEqual(desc['fields'], {})
        self.assertIn('Required variables: none', desc['description'])
        await self.services.handlers[('smsgetaweybridge', name)](SimpleNamespace(data={}))
        self.assertEqual(self.client.calls, [('+441234567890', 'Static SMS')])

    async def test_message_preview_is_bounded_for_large_templates(self):
        self.manager.templates['long'] = {'group': 'ops', 'body': 'X' * 700}
        await update_template_actions(self.hass)
        name = next(n for d,n in self.services.handlers if n.endswith('_long'))
        desc = next(v for k,v in self.description_log if k == name)
        self.assertIn('X' * 400 + '…', desc['description'])
        self.assertNotIn('X' * 401, desc['description'])


if __name__=='__main__': unittest.main()
