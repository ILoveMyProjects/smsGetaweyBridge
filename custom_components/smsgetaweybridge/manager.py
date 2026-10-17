"""Persistent configuration and privacy-conscious activity journal per gateway."""
from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from string import Template
from typing import Any

from homeassistant.helpers.storage import Store

MAX_LOGS = 300
MAX_TRACKED = 2000
PHONE_RE = re.compile(r"^\+[1-9]\d{6,14}$")
KEY_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{0,47}$")


def mask_number(number: str) -> str:
    return "***" + number[-3:] if len(number) >= 3 else "***"


def validate_recipients(numbers: list[str]) -> list[str]:
    if not isinstance(numbers, list) or not 1 <= len(numbers) <= 30:
        raise ValueError("A group must contain 1 to 30 numbers")
    values = list(dict.fromkeys(numbers))
    if any(not isinstance(n, str) or not PHONE_RE.fullmatch(n) for n in values):
        raise ValueError("Use international E.164 numbers, such as +441234567890")
    return values


def render_message(body: str, values: dict[str, str]) -> str:
    if not isinstance(body, str) or not body or len(body) > 1500:
        raise ValueError("Template body must contain 1 to 1500 characters")
    if not isinstance(values, dict) or len(values) > 30 or any(
        not isinstance(k, str) or not KEY_RE.fullmatch(k)
        or not isinstance(v, str) or len(v) > 500 for k, v in values.items()
    ):
        raise ValueError("Invalid template variables")
    try:
        result = Template(body).substitute(values)
    except (KeyError, ValueError) as exc:
        raise ValueError("Missing or invalid template variable") from exc
    if not result.strip() or len(result) > 1600:
        raise ValueError("Rendered SMS is empty or too long")
    return result


class BridgeManager:
    """Only administrators may access templates, groups and logs via WebSocket."""

    def __init__(self, hass: Any, entry_id: str):
        self.store = Store(hass, 1, f"smsgetaweybridge_guide_{entry_id}")
        self.groups: dict[str, list[str]] = {}
        self.templates: dict[str, dict[str, str]] = {}
        self.origin: dict[str, str] = {}
        self.logs: list[dict[str, str]] = []
        self.webhook_id: str | None = None
        self.callback_base: str | None = None
        self.lock = asyncio.Lock()

    async def load(self) -> None:
        raw = await self.store.async_load() or {}
        if not isinstance(raw, dict):
            return
        self.groups = raw.get("groups", {}) if isinstance(raw.get("groups"), dict) else {}
        self.templates = raw.get("templates", {}) if isinstance(raw.get("templates"), dict) else {}
        self.origin = raw.get("origin", {}) if isinstance(raw.get("origin"), dict) else {}
        self.logs = raw.get("logs", [])[-MAX_LOGS:] if isinstance(raw.get("logs"), list) else []
        self.webhook_id = raw.get("webhook_id")
        self.callback_base = raw.get("callback_base")

    async def _save(self) -> None:
        await self.store.async_save({
            "groups": self.groups,
            "templates": self.templates,
            "origin": self.origin,
            "logs": self.logs,
            "webhook_id": self.webhook_id,
            "callback_base": self.callback_base,
        })

    async def edit(self, kind: str, name: str, value: Any | None) -> None:
        if not isinstance(name, str) or not KEY_RE.fullmatch(name):
            raise ValueError("Name must use letters, numbers and underscores")
        if kind == "group":
            target = self.groups
            if value is not None:
                value = validate_recipients(value)
        elif kind == "template":
            target = self.templates
            if value is not None:
                if not isinstance(value, dict) or set(value) != {"group", "body"}:
                    raise ValueError("Template needs group and body")
                if value["group"] not in self.groups:
                    raise ValueError("Unknown recipient group")
                if not isinstance(value["body"], str) or not 1 <= len(value["body"]) <= 1500:
                    raise ValueError("Invalid template body")
        else:
            raise ValueError("Unknown item type")
        async with self.lock:
            if value is None:
                if kind == "group" and any(t.get("group") == name for t in self.templates.values()):
                    raise ValueError("Group is used by a template")
                target.pop(name, None)
            else:
                if name not in target and len(target) >= 50:
                    raise ValueError("Maximum of 50 items")
                target[name] = value
            await self._save()

    async def track_ha(self, mid: str, number: str) -> None:
        async with self.lock:
            self.origin[mid] = "homeassistant"
            self.origin = dict(list(self.origin.items())[-MAX_TRACKED:])
            self._append("queued", mid, "homeassistant", mask_number(number))
            await self._save()

    def _append(self, kind: str, mid: str, source: str, detail: str = "") -> None:
        self.logs.append({
            "when": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "type": kind, "message_id": mid, "source": source, "detail": detail[:70],
        })
        self.logs = self.logs[-MAX_LOGS:]

    async def event(self, kind: str, mid: str, detail: str = "") -> str:
        async with self.lock:
            source = self.origin.get(mid, "external/unknown")
            self._append(kind, mid, source, detail)
            await self._save()
        return source

    def summary(self) -> dict[str, Any]:
        return {
            "groups": self.groups, "templates": self.templates,
            "logs": list(reversed(self.logs[-100:])),
            "webhook_enabled": bool(self.webhook_id and self.callback_base),
        }
