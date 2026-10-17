"""Optional local-only receiver for phone→Home Assistant SMS events.

The local HTTPS URL is opt-in. No cloudhook, public IP, or opening router ports.
"""
from __future__ import annotations

from urllib.parse import urlsplit

from aiohttp import web
from homeassistant.components import webhook

from .const import DOMAIN, EVENT_SMS_RECEIVED, EVENT_SMS_STATUS

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


async def configure(hass, coordinator, base: str) -> None:
    """Configure remote phone webhook registrations. Never touch other clients' IDs."""
    base = validate_base(base)
    manager = coordinator.manager
    if manager.callback_base and manager.callback_base != base:
        raise ValueError("Changing the webhook HTTPS origin requires explicit deregistration of old remote subscriptions")
    is_new = manager.webhook_id is None
    secret = manager.webhook_id or webhook.async_generate_id()
    if is_new:
        # Receiver must exist before Android registration can emit callbacks.
        webhook.async_register(
            hass, DOMAIN, coordinator.entry.title, secret,
            _handler(coordinator), local_only=True, allowed_methods=["POST"],
        )
    if is_new:
        # Persist ID first so partial remote registration can safely be retried.
        manager.webhook_id = secret
        await manager._save()
    url = f"{base}/api/webhook/{secret}"
    try:
        existing = await coordinator.client.list_webhooks()
        ids = {str(x.get("id")) for x in existing}
        for kind in EVENTS:
            key = f"{DOMAIN}_{coordinator.entry.entry_id}_{kind.split(':')[1]}"
            if key not in ids:
                await coordinator.client.add_webhook(key, url, kind)
    except Exception:
        # Some remote subscriptions may already exist. Keep the stable local
        # endpoint and secret so the administrator may explicitly retry.
        raise
    manager.webhook_id = secret
    manager.callback_base = base
    await manager._save()
