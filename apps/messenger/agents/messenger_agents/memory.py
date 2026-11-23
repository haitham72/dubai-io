"""Long-lived memory the person can see and edit: facts about them, and Messenger Updates tasks so they survive a reload."""
from __future__ import annotations

import time

from .store import Store

MAX_FACTS = 30
MAX_TASKS = 100


class Memory:
    def __init__(self, store: Store) -> None:
        self.store = store

    async def facts(self, user: str) -> list[str]:
        return await self.store.get(f"facts:{user}") or []

    async def set_facts(self, user: str, facts: list[str]) -> list[str]:
        clean = [f.strip()[:200] for f in facts if f and f.strip()][:MAX_FACTS]
        await self.store.set(f"facts:{user}", clean)
        return clean

    async def tasks(self, user: str) -> list[dict]:
        return await self.store.get(f"tasks:{user}") or []

    async def set_tasks(self, user: str, tasks: list[dict]) -> int:
        # Newest first; only finished or failed results are worth keeping (running ones restart in the browser).
        keep = sorted(tasks, key=lambda t: -float(t.get("startedAt", 0)))[:MAX_TASKS]
        await self.store.set(f"tasks:{user}", keep, ttl_s=30 * 24 * 3600)
        return len(keep)

    async def log_turn(self, user: str, role: str, text: str) -> None:
        await self.store.push(f"thread:{user}", {"role": role, "text": text[:2000], "at": int(time.time())}, keep=200)

    async def thread(self, user: str, n: int = 50) -> list[dict]:
        return list(reversed(await self.store.recent(f"thread:{user}", n)))
