"""Admin-only WebSocket configuration and integrated frontend panel."""
from __future__ import annotations

from pathlib import Path
import logging

import voluptuous as vol
from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig

from .actions import send_template, send_one
from .const import DOMAIN
from .template_actions import update_template_actions

_LOGGER = logging.getLogger(__name__)
PANEL_URL = f"/api/{DOMAIN}/panel.js"
PANEL_PATH = f"{DOMAIN}-sms"


def _coordinator(hass, entry_id):
    return hass.data.get(DOMAIN, {}).get(entry_id)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/list"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_list(hass, connection, msg):
    result = []
    for entry_id, c in hass.data.get(DOMAIN, {}).items():
        result.append({
            "entry_id": entry_id, "title": c.entry.title,
            "online": c.last_update_success,
            "inbox_count": len((c.data or {}).get("inbox", [])),
            "outgoing_count": len((c.data or {}).get("messages", [])),
            **c.manager.summary(),
        })
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/edit",
    vol.Required("entry_id"): str,
    vol.Required("kind"): vol.In(["group", "template"]),
    vol.Required("name"): str,
    vol.Optional("value", default=None): vol.Any(None, list, dict),
})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_edit(hass, connection, msg):
    c = _coordinator(hass, msg["entry_id"])
    if c is None:
        connection.send_error(msg["id"], "unknown_gateway", "Gateway unavailable")
        return
    try:
        await c.manager.edit(msg["kind"], msg["name"], msg["value"])
        await update_template_actions(hass)
    except (ValueError, KeyError, TypeError) as exc:
        connection.send_error(msg["id"], "invalid_config", str(exc))
        return
    connection.send_result(msg["id"], {"saved": True})


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/send_sms",
    vol.Required("entry_id"): str,
    vol.Required("phone_number"): str,
    vol.Required("message"): str,
})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_send_sms(hass, connection, msg):
    c = _coordinator(hass, msg["entry_id"])
    if c is None:
        connection.send_error(msg["id"], "unknown_gateway", "Gateway unavailable")
        return
    try:
        number, message = msg["phone_number"].strip(), msg["message"].strip()
        if not number or not message or len(message) > 1600:
            raise ValueError("Enter a recipient and a message under 1600 characters")
        mid = await send_one(c, number, message)
    except Exception as exc:
        _LOGGER.warning("Direct sending returned an error (%s)", type(exc).__name__)
        connection.send_error(msg["id"], "send_uncertain", "SMS not confirmed. Verify gateway activity before retrying")
        return
    connection.send_result(msg["id"], {"message_id": mid})


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/send_template",
    vol.Required("entry_id"): str,
    vol.Required("template"): str,
    vol.Optional("variables", default={}): dict,
})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_send(hass, connection, msg):
    c = _coordinator(hass, msg["entry_id"])
    if c is None:
        connection.send_error(msg["id"], "unknown_gateway", "Gateway unavailable")
        return
    # Never send automatic retries, even if a timeout is returned.
    try:
        ids = await send_template(c, msg["template"], msg["variables"])
    except Exception as exc:  # Partial sends may have occurred; do not retry.
        _LOGGER.warning("Template sending returned error (some SMS may have been queued): %s", type(exc).__name__)
        connection.send_error(msg["id"], "send_uncertain", "Send not completed; some recipients may have been queued. Check the gateway before retrying")
        return
    connection.send_result(msg["id"], {"message_ids": ids})


async def setup_frontend(hass) -> None:
    """Run exactly once from async_setup, not on entry reload."""
    for handler in (ws_list, ws_edit, ws_send, ws_send_sms):
        websocket_api.async_register_command(hass, handler)
    await hass.http.async_register_static_paths([
        StaticPathConfig(PANEL_URL, str(Path(__file__).parent / "frontend" / "panel.js"), False),
    ])
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name="smsgetaweybridge-panel",
        frontend_url_path=PANEL_PATH,
        module_url=f"{PANEL_URL}?v=1.0.0",
        sidebar_title="SMS Bridge",
        sidebar_icon="mdi:message-processing-outline",
        config_panel_domain=DOMAIN,
        require_admin=True,
    )
