"""Async Local Server client. No Home Assistant dependency."""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from aiohttp import BasicAuth, ClientError, ClientTimeout


class GatewayError(Exception):
    """Gateway failure; never include credentials or SMS content in messages."""


class GatewayAuthError(GatewayError):
    """Credentials rejected."""


class GatewayHttpError(GatewayError):
    """Unexpected HTTP status."""

    def __init__(self, code: int) -> None:
        self.status = code
        super().__init__(f"Gateway returned HTTP {code}")


class GatewayConnectionError(GatewayError):
    """Gateway connection or timeout failure."""


class GatewayResponseError(GatewayError):
    """Gateway returned incompatible data."""


# Explicitly fail a sync rather than silently ignoring data on oversized backlogs.
PAGE_SIZE = 250
MAX_PAGES = 40


class GatewayClient:
    """Use HTTP Basic Auth against the gateway's Local Server."""

    def __init__(self, session: Any, host: str, port: int, username: str,
                 password: str, use_ssl: bool = False) -> None:
        if not host or "/" in host or "@" in host or ":" in host:
            raise ValueError("host must be a hostname or IPv4 address without scheme/port")
        if not 1 <= port <= 65535:
            raise ValueError("invalid port")
        self.base_url = f"{'https' if use_ssl else 'http'}://{host}:{port}"
        self._session = session
        self._auth = BasicAuth(username, password)

    async def _request(
        self, method: str, path: str, *, json: dict | None = None,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        try:
            async with self._session.request(
                method, f"{self.base_url}{path}", auth=self._auth,
                json=json, params=params, timeout=ClientTimeout(total=12),
                allow_redirects=False,
            ) as response:
                if response.status in (401, 403):
                    raise GatewayAuthError("Invalid gateway credentials or permissions")
                if response.status >= 400 or response.status in (301, 302, 303, 307, 308):
                    raise GatewayHttpError(response.status)
                if response.status == 204:
                    return None
                try:
                    return await response.json(content_type=None)
                except (ValueError, TypeError) as exc:
                    raise GatewayResponseError("Gateway did not return valid JSON") from exc
        except (ClientError, asyncio.TimeoutError, OSError) as exc:
            raise GatewayConnectionError("Cannot connect to SMS Gateway") from exc

    async def probe(self) -> None:
        """Verify read permissions; no paid SMS is sent."""
        await self.get_messages(limit=1)
        await self.get_inbox(limit=1)

    async def get_inbox(
        self, limit: int = PAGE_SIZE, offset: int = 0, since: float | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"type": "SMS", "limit": limit, "offset": offset}
        if since is not None:
            params["from"] = datetime.fromtimestamp(since, timezone.utc).isoformat()
        result = await self._request("GET", "/inbox", params=params)
        return self._validate_list(result, "/inbox")

    async def get_messages(self, limit: int = PAGE_SIZE, offset: int = 0) -> list[dict[str, Any]]:
        result = await self._request(
            "GET", "/messages",
            params={"limit": limit, "offset": offset, "sort": "-created_at"},
        )
        return self._validate_list(result, "/messages")

    @staticmethod
    def _validate_list(result: Any, endpoint: str) -> list[dict[str, Any]]:
        if not isinstance(result, list) or not all(isinstance(m, dict) for m in result):
            raise GatewayResponseError(f"Unexpected {endpoint} response format")
        return result

    async def _all_pages(self, fetch) -> list[dict[str, Any]]:
        """Read every page, or fail explicitly if the safety ceiling is exceeded."""
        records: list[dict[str, Any]] = []
        for page in range(MAX_PAGES):
            batch = await fetch(limit=PAGE_SIZE, offset=page * PAGE_SIZE)
            records.extend(batch)
            if len(batch) < PAGE_SIZE:
                return records
        # Even a full last page may be the final page; check before claiming overflow.
        if await fetch(limit=1, offset=MAX_PAGES * PAGE_SIZE):
            raise GatewayResponseError(
                f"Gateway returned over {MAX_PAGES * PAGE_SIZE} records; "
                "pagination safety limit reached (no events emitted)"
            )
        return records

    async def get_all_inbox(self, since: float | None = None) -> list[dict[str, Any]]:
        async def fetch(*, limit: int, offset: int):
            return await self.get_inbox(limit=limit, offset=offset, since=since)
        return await self._all_pages(fetch)

    async def get_all_messages(self) -> list[dict[str, Any]]:
        return await self._all_pages(self.get_messages)

    async def send_sms(self, number: str, message: str) -> dict[str, Any]:
        """Submit ONCE to the documented Local Server route; never retry a POST."""
        payload = {"textMessage": {"text": message}, "phoneNumbers": [number]}
        result = await self._request("POST", "/message", json=payload)
        if not isinstance(result, dict) or not isinstance(result.get("id"), str):
            raise GatewayResponseError("Unexpected send response or missing message ID")
        return result


def message_state(item: dict[str, Any]) -> str:
    """Normalize overall processing state without exposing message contents."""
    state = item.get("state", "Unknown")
    if isinstance(state, dict):
        state = state.get("state", state.get("name", "Unknown"))
    return str(state)


def utc_timestamp(value: Any) -> float | None:
    """Parse upstream RFC3339 string with offsets to a sortable UTC timestamp."""
    if not isinstance(value, str):
        return None
    try:
        value = value.replace("Z", "+00:00")
        date = datetime.fromisoformat(value)
        if date.tzinfo is None:
            return None
        return date.astimezone(timezone.utc).timestamp()
    except (ValueError, OverflowError):
        return None


def incoming_event(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize IncomingMessage; the API may provide only a content preview."""
    return {
        "message_id": str(item["id"]),
        "sender": str(item.get("sender", "")),
        "recipient": item.get("recipient"),
        "message": str(item.get("contentPreview", "")),
        "received_at": item.get("createdAt"),
        "sim_number": item.get("simNumber"),
    }
