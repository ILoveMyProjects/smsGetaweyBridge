"""Periodic inbox and status polling without phone-to-HA webhooks.

Every paginated API result must arrive before state is updated. Checkpoints are
persistent and based on upstream timestamps, not on an arbitrary 100-record page.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import GatewayClient, GatewayError, incoming_event, message_state, utc_timestamp
from .const import DEFAULT_SCAN_INTERVAL, EVENT_SMS_RECEIVED, EVENT_SMS_STATUS, MAX_SEEN

_LOGGER = logging.getLogger(__name__)


class SMSGatewayCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Observe SMS and statuses independently of other gateway clients."""

    def __init__(self, hass, entry, client: GatewayClient):
        super().__init__(
            hass, _LOGGER, name=f"smsGetaweyBridge {entry.title}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        self.manager = None  # Set by async_setup_entry after loading persistent state.
        self._webhook_inbox: set[str] = set()
        self._webhook_status: set[tuple[str, str]] = set()
        self.entry = entry
        self.store = Store(hass, 1, f"smsgetaweybridge_{entry.entry_id}")
        self._seen: list[str] = []
        self._states: dict[str, str] = {}
        self._inbox_checkpoint: float | None = None
        self._inbox_boundary: list[str] = []
        self._status_checkpoint: float | None = None
        self._status_boundary: list[str] = []
        self._bootstrapped = False
        self._migration_pending = False

    async def async_load_state(self) -> None:
        stored = await self.store.async_load()
        if not isinstance(stored, dict) or stored.get("bootstrapped") is not True:
            return
        self._seen = [str(i) for i in stored.get("seen", [])][-MAX_SEEN:]
        states = stored.get("states", {})
        self._states = {str(k): str(v) for k, v in states.items()} if isinstance(states, dict) else {}
        if "inbox_checkpoint" in stored and "status_checkpoint" in stored:
            self._inbox_checkpoint = (float(stored["inbox_checkpoint"])
                                      if stored["inbox_checkpoint"] is not None else None)
            self._inbox_boundary = [str(i) for i in stored.get("inbox_boundary", [])]
            self._status_checkpoint = (float(stored["status_checkpoint"])
                                       if stored["status_checkpoint"] is not None else None)
            self._status_boundary = [str(i) for i in stored.get("status_boundary", [])]
        else:
            # v0.1.0 had no cursor. One-time migration baseline prevents replaying
            # potentially thousands of historical SMS messages in HA automations.
            self._migration_pending = True
        self._bootstrapped = True

    @staticmethod
    def _status_entries(item: dict[str, Any]) -> list[tuple[float, str, str]]:
        mid = str(item.get("id", ""))
        history = item.get("states")
        if not mid or not isinstance(history, dict):
            return []
        entries = []
        for state, occurred_at in history.items():
            timestamp = utc_timestamp(occurred_at)
            if timestamp is not None:
                entries.append((timestamp, f"{mid}|{state}", str(state)))
        return sorted(entries)

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            inbox, outbound = await asyncio.gather(
                self.client.get_all_inbox(since=self._inbox_checkpoint), self.client.get_all_messages()
            )
        except GatewayError as exc:
            raise UpdateFailed(str(exc)) from exc

        # Deduplication within one response also tolerates shifting offset pages.
        inbox_by_id = {str(m["id"]): m for m in inbox if m.get("id") is not None}
        outbound_by_id = {str(m["id"]): m for m in outbound if m.get("id") is not None}
        inbox = list(inbox_by_id.values())
        outbound = list(outbound_by_id.values())

        incoming: list[tuple[float, str, dict[str, Any]]] = []
        seen_set = set(self._seen)
        boundary_set = set(self._inbox_boundary)
        new_inbox_checkpoint = self._inbox_checkpoint
        new_inbox_boundary = set(boundary_set)
        for item in inbox:
            mid = str(item["id"])
            ts = utc_timestamp(item.get("createdAt"))
            if ts is not None:
                if new_inbox_checkpoint is None or ts > new_inbox_checkpoint:
                    new_inbox_checkpoint = ts
                    new_inbox_boundary = {mid}
                elif ts == new_inbox_checkpoint:
                    new_inbox_boundary.add(mid)
                if (self._inbox_checkpoint is None or ts > self._inbox_checkpoint
                        or (ts == self._inbox_checkpoint and mid not in boundary_set)):
                    incoming.append((ts, mid, item))
            elif mid not in seen_set:
                # Non-conforming older gateway without createdAt: best effort.
                incoming.append((float("-inf"), mid, item))

        new_status_checkpoint = self._status_checkpoint
        new_status_boundary = set(self._status_boundary)
        status_events: list[tuple[float, str, str, str | None]] = []
        fallback_events: list[tuple[str, str]] = []
        for item in outbound:
            mid = str(item["id"])
            state = message_state(item)
            history = self._status_entries(item)
            for ts, key, history_state in history:
                if new_status_checkpoint is None or ts > new_status_checkpoint:
                    new_status_checkpoint = ts
                    new_status_boundary = {key}
                elif ts == new_status_checkpoint:
                    new_status_boundary.add(key)
                if (self._status_checkpoint is None or ts > self._status_checkpoint
                        or (ts == self._status_checkpoint and key not in self._status_boundary)):
                    # Find the original RFC3339 timestamp for the outgoing event.
                    occurred_at = item["states"][history_state]
                    status_events.append((ts, mid, history_state, occurred_at))
            if not history and self._bootstrapped and not self._migration_pending:
                before = self._states.get(mid)
                if before is not None and before != state:
                    fallback_events.append((mid, state))
                elif before is None and mid not in self._states:
                    # New message without history; an initial Pending state is
                    # observed, not an event that can be reconstructed reliably.
                    pass

        current_states = {str(m["id"]): message_state(m) for m in outbound}
        current_states = dict(list(current_states.items())[-MAX_SEEN:])
        new_seen = list(dict.fromkeys((self._seen + [mid for _, mid, _ in sorted(incoming)])))[-MAX_SEEN:]

        if not self._bootstrapped or self._migration_pending:
            # First install and old-store migration are explicit baselines.
            # Do not replay old/private messages into automations.
            self._bootstrapped = True
            self._migration_pending = False
            self._seen = list(inbox_by_id)[-MAX_SEEN:]
            self._states = current_states
            self._inbox_checkpoint = new_inbox_checkpoint
            self._inbox_boundary = sorted(new_inbox_boundary)
            self._status_checkpoint = new_status_checkpoint
            self._status_boundary = sorted(new_status_boundary)
            await self._save_state()
            return {"inbox": inbox, "messages": outbound}

        # Delivery is at-least-once: events are queued before the persistent
        # cursor is saved. After an unexpected crash, consumers should dedupe
        # by message_id / (message_id, state, changed_at).
        for _, mid, item in sorted(incoming, key=lambda x: (x[0], x[1])):
            if mid in self._webhook_inbox:
                continue
            if self.manager is not None:
                await self.manager.event("received", mid)
            self.hass.bus.async_fire(EVENT_SMS_RECEIVED, {
                "entry_id": self.entry.entry_id, **incoming_event(item),
            })
        for _, mid, state, changed_at in sorted(status_events):
            if (mid, state) in self._webhook_status:
                continue
            source = (await self.manager.event("status", mid, state)
                      if self.manager is not None else "external/unknown")
            self.hass.bus.async_fire(EVENT_SMS_STATUS, {
                "entry_id": self.entry.entry_id,
                "message_id": mid, "state": state, "changed_at": changed_at,
                "source": source,
            })
        for mid, state in fallback_events:
            if (mid, state) in self._webhook_status:
                continue
            source = (await self.manager.event("status", mid, state)
                      if self.manager is not None else "external/unknown")
            self.hass.bus.async_fire(EVENT_SMS_STATUS, {
                "entry_id": self.entry.entry_id,
                "message_id": mid, "state": state,
                "changed_at": None, "source": source,
            })

        self._seen = new_seen
        self._states = current_states
        self._inbox_checkpoint = new_inbox_checkpoint
        self._inbox_boundary = sorted(new_inbox_boundary)
        self._status_checkpoint = new_status_checkpoint
        self._status_boundary = sorted(new_status_boundary)
        await self._save_state()
        return {"inbox": inbox, "messages": outbound}

    async def _save_state(self) -> None:
        await self.store.async_save({
            "bootstrapped": self._bootstrapped,
            "seen": self._seen,
            "states": self._states,
            "inbox_checkpoint": self._inbox_checkpoint,
            "inbox_boundary": self._inbox_boundary,
            "status_checkpoint": self._status_checkpoint,
            "status_boundary": self._status_boundary,
        })
