"""Key-value memory: Redis when it answers, an in-process dict otherwise (same interface, so tests and an offline demo work)."""
from __future__ import annotations

import json
import time
from typing import Any, Protocol

import redis.asyncio as aioredis

PREFIX = "messenger:"


class Store(Protocol):
    kind: str

    async def get(self, key: str) -> Any | None: ...
    async def set(self, key: str, value: Any, ttl_s: int | None = None) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def push(self, key: str, value: Any, keep: int = 200) -> None: ...
    async def recent(self, key: str, n: int = 50) -> list[Any]: ...
    async def add_float(self, key: str, amount: float) -> float: ...
    async def close(self) -> None: ...


class MemoryStore:
    kind = "memory"

    def __init__(self) -> None:
        self._kv: dict[str, tuple[Any, float | None]] = {}
        self._lists: dict[str, list[Any]] = {}

    async def get(self, key: str) -> Any | None:
        hit = self._kv.get(key)
        if not hit:
            return None
        value, expires = hit
        if expires is not None and time.time() > expires:
            self._kv.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: Any, ttl_s: int | None = None) -> None:
        self._kv[key] = (json.loads(json.dumps(value)), time.time() + ttl_s if ttl_s else None)

    async def delete(self, key: str) -> None:
        self._kv.pop(key, None)
        self._lists.pop(key, None)

    async def push(self, key: str, value: Any, keep: int = 200) -> None:
        items = self._lists.setdefault(key, [])
        items.insert(0, json.loads(json.dumps(value)))
        del items[keep:]

    async def recent(self, key: str, n: int = 50) -> list[Any]:
        return list(self._lists.get(key, [])[:n])

    async def add_float(self, key: str, amount: float) -> float:
        current = float(await self.get(key) or 0.0) + amount
        await self.set(key, current)
        return current

    async def close(self) -> None:
        return None


class RedisStore:
    kind = "redis"

    def __init__(self, client: aioredis.Redis) -> None:
        self._r = client

    async def get(self, key: str) -> Any | None:
        raw = await self._r.get(PREFIX + key)
        return json.loads(raw) if raw is not None else None

    async def set(self, key: str, value: Any, ttl_s: int | None = None) -> None:
        await self._r.set(PREFIX + key, json.dumps(value), ex=ttl_s)

    async def delete(self, key: str) -> None:
        await self._r.delete(PREFIX + key)

    async def push(self, key: str, value: Any, keep: int = 200) -> None:
        pipe = self._r.pipeline()
        pipe.lpush(PREFIX + key, json.dumps(value))
        pipe.ltrim(PREFIX + key, 0, keep - 1)
        await pipe.execute()

    async def recent(self, key: str, n: int = 50) -> list[Any]:
        return [json.loads(x) for x in await self._r.lrange(PREFIX + key, 0, n - 1)]

    async def add_float(self, key: str, amount: float) -> float:
        # INCRBYFLOAT stores a plain number, which is also valid JSON for get().
        return float(await self._r.incrbyfloat(PREFIX + key, amount))

    async def close(self) -> None:
        await self._r.aclose()


async def connect(url: str) -> Store:
    """Redis if it answers a PING within a second, otherwise memory (logged by the caller via `.kind`)."""
    try:
        client = aioredis.from_url(url, decode_responses=True, socket_connect_timeout=1, socket_timeout=2)
        await client.ping()
        return RedisStore(client)
    except Exception:  # noqa: BLE001 — any connection problem means the offline fallback
        return MemoryStore()
