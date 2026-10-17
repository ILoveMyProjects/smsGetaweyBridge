"""Non-sensitive gateway statistics."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import message_state
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        GatewayCount(coordinator, "inbox", "Recent inbox SMS", "mdi:email-receive"),
        GatewayCount(coordinator, "messages", "Recent outgoing SMS", "mdi:email-send"),
        LatestStatus(coordinator),
    ])


class GatewayCount(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "messages"

    def __init__(self, coordinator, field, name, icon):
        super().__init__(coordinator)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.entry.entry_id)},
            "name": "smsGetaweyBridge Galaxy SMS Gateway",
            "manufacturer": "ILoveMyProjects",
            "model": "SMS Gateway Local Server",
        }
        self._field = field
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{field}_count"

    @property
    def native_value(self):
        return len((self.coordinator.data or {}).get(self._field, []))


class LatestStatus(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Latest outgoing status"
    _attr_icon = "mdi:message-check"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.entry.entry_id)},
            "name": "smsGetaweyBridge Galaxy SMS Gateway",
            "manufacturer": "ILoveMyProjects",
            "model": "SMS Gateway Local Server",
        }
        self._attr_unique_id = f"{coordinator.entry.entry_id}_latest_status"

    @property
    def native_value(self):
        messages = (self.coordinator.data or {}).get("messages", [])
        return message_state(messages[0]) if messages else "none"
