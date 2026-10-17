"""Optional local-only receiver for phone→Home Assistant SMS events.

The local HTTPS URL is opt-in. No cloudhook, public IP, or opening router ports.
"""
from __future__ import annotations

from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid5
import logging

from homeassistant.helpers.network import get_url, NoURLAvailableError

from aiohttp import web
from homeassistant.components import webhook

from .const import DOMAIN, EVENT_SMS_RECEIVED, EVENT_SMS_STATUS

_LOGGER = logging.getLogger(__name__)

EVENTS = ("sms:received", "sms:sent", "sms:delivered", "sms:failed")


def validate_base(url: str) -> str:
    try:
        parts = urlsplit(url)
        if (parts.scheme != "https" or not parts.hostname or parts.username or
                parts.password or parts.query or parts.fragment or parts.path not in ("", "/")):
            raise ValueError
    except ValueError as exc:
        raise ValueError("Enter a local HTTPS origin (no path, query or password)") from exc
    return url.rstrip("/")


def _handler(coordinator):
    async def handle(hass, webhook_id, request):
        if request.content_length is not None and request.content_length > 16384:
            return web.Response(status=413)
        try:
            data = await request.json()
        except (ValueError, TypeError):
            return web.Response(status=400)
        if not isinstance(data, dict) or data.get("event") not in EVENTS:
            return web.Response(status=400)
        item = data.get("payload")
        if not isinstance(item, dict) or not isinstance(item.get("messageId"), str):
            return web.Response(status=400)
        mid = item["messageId"]
        if not 1 <= len(mid) <= 150:
            return web.Response(status=400)
        kind = data["event"]
        if kind == "sms:received":
            if mid in coordinator._webhook_inbox:
                return web.Response(status=204)
            # A recent webhook may be seen by the next polling cycle; suppress duplicate.
            coordinator._webhook_inbox.add(mid)
            coordinator._webhook_inbox = set(list(coordinator._webhook_inbox)[-2000:])
            await coordinator.manager.event("received", mid)
            hass.bus.async_fire(EVENT_SMS_RECEIVED, {
                "entry_id": coordinator.entry.entry_id,
                "message_id": mid,
                "sender": str(item.get("phoneNumber", ""))[:40],
                "message": str(item.get("message", ""))[:2000],
                "received_at": item.get("receivedAt"),
                "source": "mobile_network",
            })
        else:
            state = kind.split(":", 1)[1].capitalize()
            if (mid, state) in coordinator._webhook_status:
                return web.Response(status=204)
            coordinator._webhook_status.add((mid, state))
            coordinator._webhook_status = set(list(coordinator._webhook_status)[-2000:])
            source = await coordinator.manager.event("status", mid, state)
            hass.bus.async_fire(EVENT_SMS_STATUS, {
                "entry_id": coordinator.entry.entry_id,
                "message_id": mid, "state": state,
                "changed_at": item.get("sentAt") or item.get("deliveredAt") or item.get("failedAt"),
                "source": source,
            })
        return web.Response(status=204)
    return handle


def setup_webhook(hass, coordinator) -> None:
    if coordinator.manager.webhook_id:
        webhook.async_register(
            hass, DOMAIN, coordinator.entry.title, coordinator.manager.webhook_id,
            _handler(coordinator), local_only=True, allowed_methods=["POST"],
        )


def unload_webhook(hass, coordinator) -> None:
    if coordinator.manager.webhook_id:
        webhook.async_unregister(hass, coordinator.manager.webhook_id)


def registration_id(entry_id: str, event: str) -> str:
    """Stable 36-character webhook ID, unique per HA gateway and event."""
    return str(uuid5(NAMESPACE_URL, f"{DOMAIN}:{entry_id}:{event}"))


async def auto_configure(hass, coordinator) -> None:
    """Register Android-side subscriptions after a successful local login.

    Never use an external/cloud Home Assistant URL, request a user-entered URL,
    or switch off Android's HTTPS security. Polling continues when unavailable.
    """
    manager = coordinator.manager
    try:
        origin = get_url(
            hass, allow_internal=True, allow_external=False, allow_cloud=False,
            prefer_external=False, require_ssl=True,
        )
        base = validate_base(origin)
    except (NoURLAvailableError, ValueError, TypeError) as exc:
        manager.webhook_status = "unavailable_local_https"
        manager._append("webhook", "system", "homeassistant", "unavailable_local_https")
        await manager._save()
        _LOGGER.info("Local trusted HTTPS Home Assistant URL unavailable; polling remains enabled")
        return
    try:
        await configure(hass, coordinator, base)
        manager.webhook_status = "registered"
        manager._append("webhook", "system", "homeassistant", "registered")
    except Exception as exc:
        manager.webhook_status = "registration_failed"
        manager._append("webhook", "system", "homeassistant", "registration_failed")
        _LOGGER.warning("Android SMS webhook auto-registration failed (%s); polling remains enabled", type(exc).__name__)
    await manager._save()


async def configure(hass, coordinator, base: str) -> None:
    """Idempotently register this HA integration's events (never Ubuntu's)."""
    base = validate_base(base)
    manager = coordinator.manager
    is_new = manager.webhook_id is None
    secret = manager.webhook_id or webhook.async_generate_id()
    if is_new:
        # Receiver exists before Android can deliver any event.
        webhook.async_register(
            hass, DOMAIN, coordinator.entry.title, secret,
            _handler(coordinator), local_only=True, allowed_methods=["POST"],
        )
        # Persist secret before remote registration, including partial failures.
        manager.webhook_id = secret
        await manager._save()
    url = f"{base}/api/webhook/{secret}"
    existing = await coordinator.client.list_webhooks()
    current = {str(x.get("id")): x for x in existing if isinstance(x, dict)}
    for kind in EVENTS:
        key = registration_id(coordinator.entry.entry_id, kind)
        hook = current.get(key)
        if hook is None or hook.get("url") != url or hook.get("event") != kind:
            await coordinator.client.add_webhook(key, url, kind)
    manager.callback_base = base
    manager.webhook_status = "registered"
    await manager._save()
