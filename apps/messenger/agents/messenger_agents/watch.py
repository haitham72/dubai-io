"""Watchlist: research topics that refresh on a schedule (like a cron), so the newest brief is ready before anyone asks.

Topics live in agents/watchlist.json. Each refreshes when its last brief is older than `every_hours`. Runs are
budget-checked like any other research; offline they produce the labelled demo brief.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path

from .research import DeepResearch
from .spend import BudgetExceeded
from .store import Store

log = logging.getLogger("messenger.watch")
WATCHLIST = Path(__file__).resolve().parents[1] / "watchlist.json"


class Watch:
    def __init__(self, research: DeepResearch, store: Store, data_dir: Path, file: Path = WATCHLIST) -> None:
        self.research, self.store, self.dir, self.file = research, store, data_dir / "watch", file
        self._lock = asyncio.Lock()

    def topics(self) -> list[dict]:
        return json.loads(self.file.read_text(encoding="utf-8")) if self.file.exists() else []

    async def latest(self, wid: str) -> dict | None:
        hit = await self.store.get(f"watch:{wid}")
        path = self.dir / f"{wid}.json"
        if hit is None and path.exists():  # survives a restart without Redis
            raw = path.read_bytes()
            try:
                hit = json.loads(raw.decode("utf-8"))
            except UnicodeDecodeError:  # written by an older build in the Windows codepage: read it, store it as UTF-8
                hit = json.loads(raw.decode("cp1252"))
                path.write_text(json.dumps(hit, ensure_ascii=False), encoding="utf-8")
        return hit

    async def list(self) -> list[dict]:
        out = []
        for t in self.topics():
            brief = await self.latest(t["id"])
            out.append({**t, "brief": brief, "due": self._due(t, brief)})
        return out

    @staticmethod
    def _due(topic: dict, brief: dict | None) -> bool:
        return not brief or time.time() - brief.get("createdAt", 0) > topic.get("every_hours", 168) * 3600

    async def refresh(self, wid: str) -> dict:
        topic = next(t for t in self.topics() if t["id"] == wid)
        async with self._lock:  # one watch run at a time keeps spend predictable
            brief = await self.research.run(topic["topic"], ttl_s=int(topic.get("every_hours", 168) * 3600), force=True)
        brief = {**brief, "watch": wid}
        await self.store.set(f"watch:{wid}", brief)
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / f"{wid}.json").write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
        return brief

    async def run_due(self) -> list[str]:
        done = []
        for t in self.topics():
            if self._due(t, await self.latest(t["id"])):
                try:
                    await self.refresh(t["id"])
                    done.append(t["id"])
                except BudgetExceeded as err:
                    log.warning("watch %s skipped: %s", t["id"], err)
                    break
                except Exception as err:  # noqa: BLE001 — a failed run is retried at the next check
                    log.warning("watch %s failed: %s", t["id"], err)
        return done

    async def loop(self, every_s: int = 3600) -> None:
        while True:
            await self.run_due()
            await asyncio.sleep(every_s)
