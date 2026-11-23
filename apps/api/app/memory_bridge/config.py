"""Environment-driven configuration and client builder for memory_bridge."""
from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Callable, Literal

import httpx

from .models import MemoryBridgeUnavailable, TemporalMemoryClient

BackendKind = Literal["fake", "http"]


@dataclass(frozen=True)
class MemoryBridgeSettings:
    backend: BackendKind
    tm_base_url: str = ""
    tm_service_token: str = ""
    tm_admin_token: str = ""
    tm_timeout_seconds: float = 10.0


def get_memory_bridge_settings() -> MemoryBridgeSettings:
    """Read memory_bridge settings from environment variables (fail-closed on http misconfig)."""
    raw_backend = (os.environ.get("MEMORY_BRIDGE_BACKEND") or "").strip().lower()
    base_url = (os.environ.get("TM_BASE_URL") or "").strip().rstrip("/")
    service_token = (os.environ.get("TM_SERVICE_TOKEN") or "").strip()
    admin_token = (os.environ.get("TM_ADMIN_TOKEN") or "").strip()
    raw_timeout = (os.environ.get("TM_TIMEOUT_SECONDS") or "10.0").strip()

    try:
        timeout_seconds = float(raw_timeout)
    except ValueError as exc:
        raise MemoryBridgeUnavailable(f"invalid TM_TIMEOUT_SECONDS: {raw_timeout!r}") from exc
    if timeout_seconds <= 0:
        raise MemoryBridgeUnavailable("TM_TIMEOUT_SECONDS must be positive")

    if not raw_backend:
        backend: BackendKind = "http" if base_url else "fake"
    elif raw_backend in ("fake", "http"):
        backend = raw_backend  # type: ignore[assignment]
    else:
        raise MemoryBridgeUnavailable(f"unsupported MEMORY_BRIDGE_BACKEND: {raw_backend!r}")

    if backend == "http":
        if not base_url or not service_token:
            raise MemoryBridgeUnavailable(
                "MEMORY_BRIDGE_BACKEND=http requires both TM_BASE_URL and TM_SERVICE_TOKEN"
            )

    return MemoryBridgeSettings(
        backend=backend,
        tm_base_url=base_url,
        tm_service_token=service_token,
        tm_admin_token=admin_token,
        tm_timeout_seconds=timeout_seconds,
    )


def build_temporal_memory_client(
    transport: httpx.BaseTransport | None = None,
    *,
    owner_token_resolver: Callable[[str], str | None] | None = None,
) -> TemporalMemoryClient:
    """Instantiate FakeTemporalMemoryClient or HttpTemporalMemoryClient from env."""
    cfg = get_memory_bridge_settings()
    if cfg.backend == "fake":
        from .fake_client import FakeTemporalMemoryClient

        return FakeTemporalMemoryClient()

    from .client import HttpTemporalMemoryClient

    return HttpTemporalMemoryClient(
        base_url=cfg.tm_base_url,
        service_token=cfg.tm_service_token,
        admin_token=cfg.tm_admin_token or None,
        timeout_seconds=cfg.tm_timeout_seconds,
        transport=transport,
        owner_token_resolver=owner_token_resolver,
    )
