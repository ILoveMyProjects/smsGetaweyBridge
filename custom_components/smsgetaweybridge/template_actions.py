"""Discoverable, live-updated HA action descriptions for saved SMS templates.

No paid SMS is transmitted during registration. Actions are registered only for
configured template/group pairs. Service names are stable for a gateway entry.
"""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_set_service_schema

from .actions import send_template
from .const import DOMAIN
from .manager import template_variables

_LOGGER = logging.getLogger(__name__)
PREFIX = "send_saved_"


def _action_id(entry_id: str, template_key: str) -> str:
    # Config entry IDs and template keys are generated/validated locally.
    return f"{PREFIX}{entry_id.lower()}_{template_key.lower()}"


def template_options(hass) -> list[dict[str, str]]:
    """Produce options for the standard send_template automation action."""
    options = []
    for entry_id, co in sorted(hass.data.get(DOMAIN, {}).items()):
        for key, template in sorted(co.manager.templates.items()):
            vars_text = ", ".join("$" + v for v in template_variables(template["body"])) or "none"
            options.append({
                "value": f"{entry_id}::{key}",
                "label": f"{key} — {co.entry.title} • group: {template['group']} • variables: {vars_text}"[:250],
            })
    return options


def _send_sms_description(hass) -> dict:
    options = template_options(hass)
    return {
        "name": "Send SMS (direct or saved template)",
        "description": "Either enter a phone number and message, OR choose a saved template from the list. A template uses its saved recipient group.",
        "fields": {
            "phone_number": {"name": "Phone number (direct send)", "required": False,
                             "description": "For a one-off SMS. Leave blank when using a saved template.",
                             "selector": {"text": {}}},
            "message": {"name": "Message (direct send)", "required": False,
                        "description": "Message text for a one-off SMS. Leave blank when using a template.",
                        "selector": {"text": {"multiline": True}}},
            "template": {"name": "Saved template (optional)", "required": False,
                         "description": "Choose a saved template; labels show group and required variables. If selected, direct-send fields are ignored.",
                         "selector": {"select": {"options": options, "mode": "dropdown"}} if options else {"text": {}}},
            "variables": {"name": "Template variables", "required": False,
                          "description": "Map of variable names/values shown in the template list. E.g. {host: nas, state: offline}.",
                          "selector": {"object": {}}},
            "entry_id": {"name": "Gateway entry", "required": False,
                         "description": "Optional if only one gateway is connected or if the template is selected from the list.",
                         "selector": {"config_entry": {"integration": DOMAIN}}},
        },
    }


def _send_template_description(hass) -> dict:
    options = template_options(hass)
    return {
        "name": "Send saved SMS template (choose from list)",
        "description": "Choose a template from the saved list. Its group and required $variables are shown in each option. SMS may be billed.",
        "fields": {
            "template": {
                "name": "Saved template",
                "description": "Templates are created/edited in SMS Bridge → Templates. Each choice lists required variables.",
                "required": True,
                "selector": {"select": {"options": options, "mode": "dropdown"}} if options else {"text": {}},
            },
            "variables": {
                "name": "Variables",
                "description": "Enter a dictionary with the exact $variable names shown in the selected template, e.g. {entity: server, state: offline}. No variables needed if the choice says 'none'.",
                "required": False,
                "example": {"entity": "server"},
                "selector": {"object": {}},
            },
            "entry_id": {
                "name": "Gateway entry (legacy)",
                "description": "Optional for templates selected by ID; used with older plain template keys.",
                "required": False,
                "selector": {"config_entry": {"integration": DOMAIN}},
            },
        },
    }


async def update_template_actions(hass) -> None:
    """Refresh automation editor drop-down and named per-template actions."""
    async_set_service_schema(hass, DOMAIN, "send_template", _send_template_description(hass))
    async_set_service_schema(hass, DOMAIN, "send_sms", _send_sms_description(hass))
    registered = hass.data.setdefault(f"{DOMAIN}_template_actions", set())
    wanted: set[str] = set()
    for entry_id, co in hass.data.get(DOMAIN, {}).items():
        for key, template in co.manager.templates.items():
            name = _action_id(entry_id, key)
            if not name.isascii() or len(name) > 125:
                _LOGGER.warning("SMS template key not usable as an action name")
                continue
            wanted.add(name)
            variables = template_variables(template["body"])
            schema = vol.Schema({vol.Required(v): cv.string for v in variables})

            async def action(call, *, eid=entry_id, tkey=key):
                coordinator = hass.data.get(DOMAIN, {}).get(eid)
                if coordinator is None:
                    raise ServiceValidationError("SMS Gateway is no longer configured")
                if tkey not in coordinator.manager.templates:
                    raise ServiceValidationError("SMS template no longer exists")
                try:
                    await send_template(coordinator, tkey, dict(call.data))
                except ValueError as exc:
                    raise ServiceValidationError(str(exc)) from exc
                except Exception as exc:
                    raise HomeAssistantError(
                        "SMS send status uncertain; check the gateway before retrying"
                    ) from exc

            # Refresh registration after edits; old automations retain stable action IDs.
            hass.services.async_register(DOMAIN, name, action, schema=schema)
            fields = {
                v: {
                    "name": v,
                    "description": f"Required ${v} in the SMS body. Enter text or a Home Assistant template expression.",
                    "required": True,
                    "selector": {"text": {}},
                } for v in variables
            }
            async_set_service_schema(hass, DOMAIN, name, {
                "name": f"Send SMS: {key}",
                "description": f"Saved template '{key}' → recipient group '{template['group']}'. All required variables are separate fields. Sending SMS can incur charges.",
                "fields": fields,
            })
    for old in registered - wanted:
        hass.services.async_remove(DOMAIN, old)
    hass.data[f"{DOMAIN}_template_actions"] = wanted
