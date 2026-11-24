"""Thread- and asyncio-safe in-process WebSocket fan-out hub for Messenger."""

from __future__ import annotations

import os
from threading import RLock
from typing import Any

from fastapi import WebSocket

from app.identity.models import IdentityError
from app.identity.service import normalize_origin
from app.messenger.store import ChatStore

DEFAULT_DEV_ORIGINS: tuple[str, ...] = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:4173",
    "http://localhost:4173",
)

_HUB_INIT_LOCK = RLock()


def get_allowed_origins() -> list[str]:
    """Return normalized non-empty origins from MESSENGER_ALLOWED_ORIGINS, or [] when unset."""
    raw = os.getenv("MESSENGER_ALLOWED_ORIGINS", "")
    origins: list[str] = []
    for item in raw.split(","):
        cleaned = item.strip().rstrip("/")
        if not cleaned:
            continue
        try:
            normalized = normalize_origin(cleaned)
        except IdentityError:
            normalized = cleaned
        if normalized not in origins:
            origins.append(normalized)
    return origins


class ChatHub:
    """Maps verified user_ids to active WebSocket connections and enforces fail-closed member fan-out."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._sockets: dict[str, set[WebSocket]] = {}

    def register(self, user_id: str, websocket: WebSocket) -> None:
        """Register an accepted WebSocket for a verified user_id."""
        with self._lock:
            self._sockets.setdefault(user_id, set()).add(websocket)

    def unregister(self, user_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket for user_id and prune empty user buckets."""
        with self._lock:
            sockets = self._sockets.get(user_id)
            if not sockets:
                return
            sockets.discard(websocket)
            if not sockets:
                self._sockets.pop(user_id, None)

    def _drop_dead(self, dead: list[tuple[str, WebSocket]]) -> None:
        if not dead:
            return
        with self._lock:
            for user_id, ws in dead:
                self.unregister(user_id, ws)

    async def _send_to_sockets(self, targets: list[tuple[str, list[WebSocket]]], payload: dict) -> None:
        dead: list[tuple[str, WebSocket]] = []
        for user_id, sockets in targets:
            for ws in sockets:
                try:
                    await ws.send_json(payload)
                except Exception:
                    dead.append((user_id, ws))
        self._drop_dead(dead)

    async def broadcast_conversation(
        self,
        chat_store: ChatStore,
        conversation_id: str,
        payload: dict,
        *,
        exclude_user_id: str | None = None,
        exclude_ws: WebSocket | None = None,
    ) -> None:
        """Broadcast payload to active sockets of verified members of conversation_id (fail closed)."""
        with self._lock:
            snapshot = [(user_id, list(sockets)) for user_id, sockets in self._sockets.items()]

        targets: list[tuple[str, list[WebSocket]]] = []
        for user_id, sockets in snapshot:
            if exclude_user_id and user_id == exclude_user_id:
                continue
            try:
                is_member = bool(chat_store.is_member(conversation_id, user_id))
            except Exception:
                is_member = False
            if not is_member:
                continue
            filtered = [ws for ws in sockets if exclude_ws is None or ws is not exclude_ws]
            if filtered:
                targets.append((user_id, filtered))

        await self._send_to_sockets(targets, payload)

    async def send_user_event(self, user_id: str, payload: dict) -> None:
        """Send an event payload to all active sockets of a single user_id."""
        with self._lock:
            sockets = list(self._sockets.get(user_id, ()))
        if sockets:
            await self._send_to_sockets([(user_id, sockets)], payload)


def get_chat_hub(app: Any) -> ChatHub:
    """Return app.state.chat_hub, initializing it lazily if absent."""
    hub = getattr(app.state, "chat_hub", None)
    if hub is not None:
        return hub
    with _HUB_INIT_LOCK:
        hub = getattr(app.state, "chat_hub", None)
        if hub is None:
            hub = ChatHub()
            app.state.chat_hub = hub
        return hub
