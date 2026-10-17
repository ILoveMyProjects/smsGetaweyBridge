"""Gateway connectivity indication."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([GatewayOnline(hass.data[DOMAIN][entry.entry_id])])


class GatewayOnline(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Gateway online"
    _attr_icon = "mdi:cellphone-message"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.entry.entry_id)},
            "name": "smsGetaweyBridge Galaxy SMS Gateway",
            "manufacturer": "ILoveMyProjects",
            "model": "SMS Gateway Local Server",
        }
        self._attr_unique_id = f"{coordinator.entry.entry_id}_online"

    @property
    def is_on(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def available(self) -> bool:
        # Unlike a normal CoordinatorEntity, show offline instead of unavailable.
        return True
