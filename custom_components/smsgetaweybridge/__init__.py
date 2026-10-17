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
from .const import (
    CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_SSL, CONF_USERNAME,
    DOMAIN, EVENT_SMS_QUEUED, SERVICE_SEND_SMS,
)
from .coordinator import SMSGatewayCoordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]

SEND_SCHEMA = vol.Schema({
    vol.Required("phone_number"): cv.string,
    vol.Required("message"): cv.string,
    vol.Optional("entry_id"): cv.string,
})


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register once; each configured gateway remains independent."""
    hass.data.setdefault(DOMAIN, {})

    async def send_sms(call: ServiceCall) -> None:
        coordinators: dict = hass.data[DOMAIN]
        entry_id = call.data.get("entry_id")
        if entry_id:
            coordinator = coordinators.get(entry_id)
            if coordinator is None:
                raise ServiceValidationError("Unknown SMS Gateway entry ID")
        elif len(coordinators) == 1:
            coordinator = next(iter(coordinators.values()))
        else:
            raise ServiceValidationError(
                "Specify entry_id if more than one gateway is configured"
            )
        number = call.data["phone_number"].strip()
        body = call.data["message"]
        if not number or not body.strip():
            raise ServiceValidationError("Recipient and message must not be empty")
        try:
            result = await coordinator.client.send_sms(number, body)
        except GatewayError as exc:
            raise HomeAssistantError(str(exc)) from exc
        hass.bus.async_fire(EVENT_SMS_QUEUED, {
            "entry_id": coordinator.entry.entry_id,
            "message_id": result.get("id"),
            "phone_number": number,
        })

    if not hass.services.has_service(DOMAIN, SERVICE_SEND_SMS):
        hass.services.async_register(
            DOMAIN, SERVICE_SEND_SMS, send_sms, schema=SEND_SCHEMA,
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    client = GatewayClient(
        async_get_clientsession(hass),
        entry.data[CONF_HOST], entry.data[CONF_PORT],
        entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD],
        entry.data[CONF_SSL],
    )
    coordinator = SMSGatewayCoordinator(hass, entry, client)
    await coordinator.async_load_state()
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
