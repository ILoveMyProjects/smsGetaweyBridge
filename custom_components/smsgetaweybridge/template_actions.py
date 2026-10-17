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


def _body_preview(body: str, max_length: int = 400) -> str:
    """Show the literal saved message in an action description, not a rendered SMS."""
    preview = body.strip().replace("\r", " ").replace("\n", " ")
    return preview[:max_length] + ("…" if len(preview) > max_length else "")


def _send_sms_description(hass) -> dict:
    options = template_options(hass)
    return {
        "name": "Send SMS (direct or saved template)",
        "description": "For one-off messages enter the number and message. For saved templates, use the simpler dedicated 'Send SMS: template_name' action: it shows the saved SMS text, group and individual variable fields. No JSON needed there.",
        "fields": {
            "phone_number": {"name": "Phone number (direct send)", "required": False,
                             "description": "For a one-off SMS. Leave blank when using a saved template.",
                             "selector": {"text": {}}},
            "message": {"name": "Message (direct send)", "required": False,
                        "description": "Message text for a one-off SMS. Leave blank when using a template.",
                        "selector": {"text": {"multiline": True}}},
            "template": {"name": "Saved template (optional)", "required": False,
                         "description": "Advanced use: choosing a template ignores direct-send fields. For an easy form without an object/JSON editor, select the separate 'Send SMS: template_name' action instead.",
                         "selector": {"select": {"options": options, "mode": "dropdown"}} if options else {"text": {}}},
            "variables": {"name": "Template variables", "required": False,
                          "description": "Advanced only: a mapping of variable names to values. To avoid this mapping/JSON editor, use the separate 'Send SMS: template_name' action with individual text fields.",
                          "selector": {"object": {}}},
            "entry_id": {"name": "Gateway for direct SMS", "required": False,
                         "description": "Only needed for direct phone/message sends if multiple Android gateways are configured; a saved template already identifies its gateway.",
                         "selector": {"config_entry": {"integration": DOMAIN}}},
        },
    }


def _send_template_description(hass) -> dict:
    options = template_options(hass)
    return {
        "name": "Send saved SMS template (advanced)",
        "description": "Select a saved template from the list. The SMS text and recipient group are saved in SMS Bridge → Templates & Groups; do not re-enter the message. This action uses an advanced variables mapping. To avoid JSON, choose the dedicated 'Send SMS: template_name' action with a separate text field for each variable. SMS may be billed.",
        "fields": {
            "template": {
                "name": "Saved template",
                "description": "Choose a template made in SMS Bridge → Templates & Groups. The choice lists its group and required variables. For a preview of the SMS body and simpler fields, use 'Send SMS: template_name'.",
                "required": True,
                "selector": {"select": {"options": options, "mode": "dropdown"}} if options else {"text": {}},
            },
            "variables": {
                "name": "Variables",
                "description": "Advanced mapping only. If the template needs $host and $status, enter keys host and status with their values. For normal form fields with no JSON, select 'Send SMS: template_name' instead. Leave blank for templates without variables.",
                "required": False,
                "example": {"entity": "server"},
                "selector": {"object": {}},
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
                    "description": f"Enter the value replacing ${v} in the saved SMS text. Example: 'offline' or a Home Assistant template like {{{{ states('sensor.example') }}}}. Do not enter JSON.",
                    "required": True,
                    "selector": {"text": {}},
                } for v in variables
            }
            preview = _body_preview(template["body"])
            vars_desc = ", ".join("$" + v for v in variables) if variables else "none"
            async_set_service_schema(hass, DOMAIN, name, {
                "name": f"Send SMS: {key}",
                "description": (
                    f"Saved SMS text: {preview} | Recipient group: {template['group']} | "
                    f"Required variables: {vars_desc}. Fill in the fields below (no JSON). "
                    "The recipient numbers and message text come from SMS Bridge → Templates & Groups. "
                    "SMS can incur charges."
                ),
                "fields": fields,
            })
    for old in registered - wanted:
        hass.services.async_remove(DOMAIN, old)
    hass.data[f"{DOMAIN}_template_actions"] = wanted
