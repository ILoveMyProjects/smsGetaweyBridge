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


if __name__=='__main__': unittest.main()
