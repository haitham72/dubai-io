"""Per-turn traces: what was heard, what was decided (with probabilities), what ran, how long it took, what it cost.

Stored in the memory store (latest 500) and appended to a JSONL file so a session can be replayed. No audio is kept.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .store import Store


class Tracer:
    def __init__(self, store: Store, file: Path | None = None) -> None:
        self.store, self.file = store, file

    async def record(self, kind: str, **data: Any) -> dict:
        entry = {"t": round(time.time(), 3), "kind": kind, **data}
        await self.store.push("trace", entry, keep=500)
        if self.file:
            self.file.parent.mkdir(parents=True, exist_ok=True)
            with self.file.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    async def recent(self, n: int = 50) -> list[dict]:
        return await self.store.recent("trace", n)
