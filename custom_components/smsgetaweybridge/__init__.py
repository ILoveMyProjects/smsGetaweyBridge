"""smsGetaweyBridge custom Home Assistant integration."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import GatewayClient, GatewayError
from .actions import send_one, send_template
from .frontend import setup_frontend
from .manager import BridgeManager
from .webhooks import auto_configure, setup_webhook, unload_webhook
from .template_actions import update_template_actions
from .const import (
    CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_SSL, CONF_USERNAME,
    DOMAIN, EVENT_SMS_QUEUED, SERVICE_SEND_SMS,
)
from .coordinator import SMSGatewayCoordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]

# This integration is configured exclusively through Home Assistant config entries.
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

TEMPLATE_SCHEMA = vol.Schema({
    vol.Required("template"): cv.string,
    vol.Optional("variables", default={}): dict,
    vol.Optional("entry_id"): cv.string,
})

SEND_SCHEMA = vol.Schema({
    vol.Optional("phone_number"): cv.string,
    vol.Optional("message"): cv.string,
    vol.Optional("template"): cv.string,
    vol.Optional("variables", default={}): dict,
    vol.Optional("entry_id"): cv.string,
})


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register once; each configured gateway remains independent."""
    hass.data.setdefault(DOMAIN, {})
    await setup_frontend(hass)

    def target(entry_id: str | None):
        coordinators = hass.data[DOMAIN]
        if entry_id:
            co = coordinators.get(entry_id)
            if co is None:
                raise ServiceValidationError("Unknown SMS Gateway entry ID")
            return co
        if len(coordinators) == 1:
            return next(iter(coordinators.values()))
        raise ServiceValidationError("Specify entry_id if zero or multiple gateways are configured")

    async def send_sms(call: ServiceCall) -> None:
        # Both actions show a live template list. A selected template always wins
        # over direct phone/message fields (no accidental double-send).
        selected = (call.data.get("template") or "").strip()
        if selected:
            entry_id, key = (selected.split("::", 1) if "::" in selected else
                             (call.data.get("entry_id"), selected))
            coordinator = target(entry_id)
            try:
                await send_template(coordinator, key, call.data.get("variables", {}))
            except ValueError as exc:
                raise ServiceValidationError(str(exc)) from exc
            except GatewayError as exc:
                raise HomeAssistantError("SMS send status uncertain; check gateway before retrying") from exc
            return
        number = (call.data.get("phone_number") or "").strip()
        body = (call.data.get("message") or "")
        if not number or not body.strip():
            raise ServiceValidationError("Enter a recipient and message, or choose a saved SMS template")
        coordinator = target(call.data.get("entry_id"))
        try:
            await send_one(coordinator, number, body)
        except GatewayError as exc:
            raise HomeAssistantError(str(exc)) from exc

    async def send_named_template(call: ServiceCall) -> None:
        template_key = call.data["template"]
        entry_id = call.data.get("entry_id")
        if "::" in template_key:
            entry_id, template_key = template_key.split("::", 1)
        coordinator = target(entry_id)
        try:
            await send_template(coordinator, template_key, call.data["variables"])
        except ValueError as exc:
            raise ServiceValidationError(str(exc)) from exc
        except GatewayError as exc:
            raise HomeAssistantError(
                "SMS send status uncertain. Some recipients may have been queued; check gateway before retrying"
            ) from exc

    if not hass.services.has_service(DOMAIN, SERVICE_SEND_SMS):
        hass.services.async_register(
            DOMAIN, SERVICE_SEND_SMS, send_sms, schema=SEND_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, "send_template"):
        hass.services.async_register(DOMAIN, "send_template", send_named_template, schema=TEMPLATE_SCHEMA)
    return True


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    client = GatewayClient(
        async_get_clientsession(hass),
        entry.data[CONF_HOST], entry.data[CONF_PORT],
        entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD],
        entry.data[CONF_SSL],
    )
    coordinator = SMSGatewayCoordinator(hass, entry, client)
    manager = BridgeManager(hass, entry.entry_id)
    await manager.load()
    coordinator.manager = manager
    await coordinator.async_load_state()
    await coordinator.async_config_entry_first_refresh()
    setup_webhook(hass, coordinator)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await update_template_actions(hass)
    # Local HTTPS-only, never external cloud or manual pasted URL.
    await auto_configure(hass, coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id, None)
        if coordinator is not None:
            unload_webhook(hass, coordinator)
            await update_template_actions(hass)
    return unload_ok
