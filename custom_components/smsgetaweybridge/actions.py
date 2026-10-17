"""Shared sending logic. Every POST is attempted once; SMS may be billable."""
from __future__ import annotations

from .manager import render_message
from .const import EVENT_SMS_QUEUED


async def send_one(coordinator, number: str, message: str) -> str:
    result = await coordinator.client.send_sms(number, message)
    mid = result["id"]
    await coordinator.manager.track_ha(mid, number)
    coordinator.hass.bus.async_fire(EVENT_SMS_QUEUED, {
        "entry_id": coordinator.entry.entry_id,
        "message_id": mid, "phone_number": number, "source": "homeassistant",
    })
    return mid


async def send_template(coordinator, name: str, variables: dict[str, str]) -> list[str]:
    template = coordinator.manager.templates.get(name)
    if template is None:
        raise ValueError("Unknown template")
    numbers = coordinator.manager.groups.get(template["group"])
    if not numbers:
        raise ValueError("Unknown or empty recipient group")
    text = render_message(template["body"], variables)
    sent = []
    for number in numbers:
        # Do not retry errors: sending may have succeeded without an ACK.
        sent.append(await send_one(coordinator, number, text))
    return sent
