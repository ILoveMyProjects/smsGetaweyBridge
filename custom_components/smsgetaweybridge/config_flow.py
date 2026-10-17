"""Manual Home Assistant UI configuration for Local Server (no SSH)."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .api import (
    GatewayAuthError, GatewayClient, GatewayConnectionError, GatewayError,
    GatewayHttpError,
)
from .const import (
    CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_SSL, CONF_USERNAME,
    DEFAULT_PORT, DOMAIN, NAME,
)


def _schema(defaults: dict | None = None, *, reconfigure: bool = False):
    defaults = defaults or {}
    schema: dict = {
        vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
        vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
        vol.Required(CONF_USERNAME, default=defaults.get(CONF_USERNAME, "")): str,
        vol.Required(CONF_SSL, default=defaults.get(CONF_SSL, False)): bool,
    }
    # Never return a saved secret in a UI form. Blank password during reconfigure
    # means "keep previous password".
    password = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
    if reconfigure:
        schema[vol.Optional(CONF_PASSWORD)] = password
    else:
        schema[vol.Required(CONF_PASSWORD)] = password
    return vol.Schema(schema)


class SMSGatewayConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure and reconfigure the phone's local gateway manually."""

    VERSION = 1

    async def _check(self, data: dict[str, Any]) -> str | None:
        try:
            client = GatewayClient(
                async_get_clientsession(self.hass),
                data[CONF_HOST], data[CONF_PORT], data[CONF_USERNAME],
                data[CONF_PASSWORD], data[CONF_SSL],
            )
            await client.probe()
        except GatewayAuthError:
            return "invalid_auth"
        except (GatewayConnectionError, GatewayHttpError):
            return "cannot_connect"
        except (GatewayError, ValueError, TypeError):
            return "invalid_response"
        return None

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            data = dict(user_input)
            data[CONF_HOST] = data[CONF_HOST].strip()
            problem = await self._check(data)
            if problem is not None:
                errors["base"] = problem
            else:
                await self.async_set_unique_id(f"{data[CONF_HOST].lower()}:{data[CONF_PORT]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=f"{NAME} ({data[CONF_HOST]})", data=data)
        return self.async_show_form(step_id="user", data_schema=_schema(), errors=errors)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data = dict(entry.data)
            data.update(user_input)
            if not user_input.get(CONF_PASSWORD):
                data[CONF_PASSWORD] = entry.data[CONF_PASSWORD]
            data[CONF_HOST] = data[CONF_HOST].strip()
            new_uid = f"{data[CONF_HOST].lower()}:{data[CONF_PORT]}"
            # Unlike HA core's default _abort_if_unique_id_mismatch, changing
            # host/port is intentional here (e.g. DHCP-renumbered phone).
            for existing in self._async_current_entries():
                if existing.entry_id != entry.entry_id and existing.unique_id == new_uid:
                    errors["base"] = "already_configured"
                    break
            if not errors:
                problem = await self._check(data)
                if problem is not None:
                    errors["base"] = problem
                else:
                    # Keep uniqueness in sync when host/port changes.
                    if entry.unique_id != new_uid:
                        self.hass.config_entries.async_update_entry(entry, unique_id=new_uid)
                    return self.async_update_reload_and_abort(entry, data_updates=data)
        return self.async_show_form(
            step_id="reconfigure", data_schema=_schema(entry.data, reconfigure=True),
            errors=errors,
        )
