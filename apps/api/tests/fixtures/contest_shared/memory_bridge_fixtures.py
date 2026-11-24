"""Shared fake/live pytest fixtures for `test_memory_bridge_*.py` (CS-1)."""
from __future__ import annotations

from dataclasses import dataclass, field
import os
import threading
from typing import Iterator
import uuid

import pytest

from app.memory_bridge.config import build_temporal_memory_client
from app.memory_bridge.fake_client import FakeTemporalMemoryClient
from app.memory_bridge.models import TemporalMemoryClient


def is_live_mode() -> bool:
    """Return True when tests should run against a live temporal_memory HTTP server."""
    return (os.environ.get("MEMORY_BRIDGE_LIVE") or "").strip() == "1"


fake_only = pytest.mark.skipif(
    is_live_mode(),
    reason="Inspects FakeTemporalMemoryClient internals; skipped when MEMORY_BRIDGE_LIVE=1",
)


@dataclass
class MemoryBridgeTestEnv:
    """Per-test client and isolated owner/record helpers for fake or live mode."""

    client: TemporalMemoryClient
    live: bool
    run_id: str
    primary_owner: str
    _owners: dict[str, str] = field(default_factory=dict)
    _sub_uuids: dict[str, str] = field(default_factory=dict)
    _tracked_records: dict[str, set[str]] = field(default_factory=dict)

    @property
    def is_fake(self) -> bool:
        return isinstance(self.client, FakeTemporalMemoryClient)

    def owner_id(self, tag: str = "alice") -> str:
        """Return a per-test isolated owner ID (prefixed `cs_live_<uuid>` in live mode)."""
        clean = (tag or "owner").strip()
        if clean not in self._owners:
            if self.live:
                self._owners[clean] = f"cs_live_{self.run_id}_{clean}"
            else:
                self._owners[clean] = f"usr_{clean}"
        return self._owners[clean]

    def sub_uuid(self, tag: str = "a") -> str:
        """Return a valid UUID `sub` claim (unique per test in live mode)."""
        clean = (tag or "a").strip()
        if clean not in self._sub_uuids:
            self._sub_uuids[clean] = str(uuid.uuid4())
        return self._sub_uuids[clean]

    def track_record(self, owner_id: str, record_id: str) -> None:
        """Track a record ID for best-effort forget cleanup during live teardown."""
        self._tracked_records.setdefault(owner_id, set()).add(record_id)


@pytest.fixture
def memory_bridge_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[MemoryBridgeTestEnv]:
    """Provide FakeTemporalMemoryClient by default or HttpTemporalMemoryClient when MEMORY_BRIDGE_LIVE=1."""
    run_id = uuid.uuid4().hex[:12]

    if not is_live_mode():
        monkeypatch.setenv("MEMORY_BRIDGE_BACKEND", "fake")
        monkeypatch.delenv("TM_BASE_URL", raising=False)
        monkeypatch.delenv("TM_SERVICE_TOKEN", raising=False)
        client = build_temporal_memory_client()
        assert isinstance(client, FakeTemporalMemoryClient)
        yield MemoryBridgeTestEnv(
            client=client,
            live=False,
            run_id=run_id,
            primary_owner=f"cs_fake_{run_id}",
        )
        return

    monkeypatch.setenv("MEMORY_BRIDGE_BACKEND", "http")
    admin_token = (os.environ.get("TM_ADMIN_TOKEN") or "").strip()

    lock = threading.RLock()
    owner_tokens: dict[str, str] = {}
    minted_tokens: list[tuple[str, str]] = []
    client_holder: list[TemporalMemoryClient] = []

    def _resolve_owner_token(owner_id: str) -> str | None:
        if not admin_token:
            return None
        with lock:
            cached = owner_tokens.get(owner_id)
            if cached is not None:
                return cached
            active_client = client_holder[0]
            active_client.ensure_owner(
                owner_id,
                label=owner_id,
                display_name=owner_id,
                kind="simulated",
            )
            minted = active_client.mint_owner_device_token(owner_id, label="cs-live-test")
            raw_token = str(minted["token"])
            token_id = str(minted["id"])
            owner_tokens[owner_id] = raw_token
            minted_tokens.append((token_id, owner_id))
            return raw_token

    client = build_temporal_memory_client(owner_token_resolver=_resolve_owner_token)
    client_holder.append(client)

    primary_owner = f"cs_live_{run_id}"
    if admin_token:
        client.ensure_owner(
            primary_owner,
            label=primary_owner,
            display_name=primary_owner,
            kind="simulated",
        )
        _resolve_owner_token(primary_owner)

    env = MemoryBridgeTestEnv(
        client=client,
        live=True,
        run_id=run_id,
        primary_owner=primary_owner,
    )
    try:
        yield env
    finally:
        for oid, rids in env._tracked_records.items():
            if not rids:
                continue
            try:
                client.forget_source(oid, sorted(rids))
            except Exception:
                pass
        if admin_token:
            for token_id, _oid in minted_tokens:
                try:
                    client.revoke_token(token_id)
                except Exception:
                    pass
        close_fn = getattr(client, "close", None)
        if callable(close_fn):
            try:
                close_fn()
            except Exception:
                pass


@pytest.fixture
def tm_client(memory_bridge_env: MemoryBridgeTestEnv) -> TemporalMemoryClient:
    """Convenience fixture returning only the TemporalMemoryClient instance."""
    return memory_bridge_env.client
