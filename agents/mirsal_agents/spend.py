"""Spend meter with a hard cap. Every paid provider call is priced *before* it runs; past the cap it is refused.

The running total lives in the store (Redis survives restarts) and is mirrored to a file so a memory-only run keeps it too.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .config import Prices
from .store import Store

KEY = "spend:usd"


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class Usage:
    stt_seconds: float = 0.0
    decision_in: int = 0
    decision_out: int = 0
    llm_in: int = 0
    llm_out: int = 0
    search_credits: int = 0

    def cost(self, p: Prices) -> float:
        return (
            self.stt_seconds / 60 * p.stt_per_minute
            + self.decision_in / 1e6 * p.decision_in_per_m
            + self.decision_out / 1e6 * p.decision_out_per_m
            + self.llm_in / 1e6 * p.llm_in_per_m
            + self.llm_out / 1e6 * p.llm_out_per_m
            + self.search_credits * p.search_credit
        )


class Budget:
    def __init__(self, store: Store, prices: Prices, cap_usd: float, ledger: Path | None = None) -> None:
        self.store, self.prices, self.cap = store, prices, cap_usd
        self.ledger = ledger
        self._seeded = False

    async def _seed(self) -> None:
        # A fresh memory store starts from the file ledger, so restarting without Redis does not reset the cap.
        if self._seeded:
            return
        self._seeded = True
        if await self.store.get(KEY) is None and self.ledger and self.ledger.exists():
            try:
                await self.store.set(KEY, float(json.loads(self.ledger.read_text(encoding="utf-8"))["spent"]))
            except (ValueError, KeyError):
                pass

    async def spent(self) -> float:
        await self._seed()
        return float(await self.store.get(KEY) or 0.0)

    async def remaining(self) -> float:
        return max(0.0, self.cap - await self.spent())

    async def ensure(self, estimate: Usage | float) -> None:
        """Refuse a call whose estimated cost would cross the cap."""
        cost = estimate.cost(self.prices) if isinstance(estimate, Usage) else estimate
        if await self.spent() + cost > self.cap:
            raise BudgetExceeded(f"Budget of ${self.cap:.2f} reached (spent ${await self.spent():.4f})")

    async def charge(self, usage: Usage | float, what: str) -> float:
        await self._seed()
        cost = usage.cost(self.prices) if isinstance(usage, Usage) else usage
        total = await self.store.add_float(KEY, cost)
        await self.store.push("spend:log", {"what": what, "usd": round(cost, 6), "total": round(total, 6)})
        if self.ledger:
            self.ledger.parent.mkdir(parents=True, exist_ok=True)
            self.ledger.write_text(json.dumps({"spent": total, "cap": self.cap}), encoding="utf-8")
        return total

    async def status(self) -> dict:
        spent = await self.spent()
        return {"spentUsd": round(spent, 4), "capUsd": self.cap, "stopped": spent >= self.cap}
