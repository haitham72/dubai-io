"""Nadi demo HR connector (leave filing over the memory store or Nadi MCP)."""
from __future__ import annotations

import time

from ..store import Store
class Nadi:
    """HR connector ("Nadi portal"): files and lists annual-leave requests.

    Live: a separate Nadi MCP server (NADI_MCP_URL) with tools `file_leave` and `list_leave` (ARCHITECTURE.md §4.3).
    Demo: requests stored in the memory store (Redis key nadi:<user>) with a 30-day balance.
    """

    def __init__(self, store: Store, balance: int = 30, mcp=None) -> None:
        self.store, self.balance, self.mcp = store, balance, mcp

    @property
    def mode(self) -> str:
        return "live" if self.mcp else "demo"

    async def requests(self, user: str) -> list[dict]:
        if self.mcp:
            out = await self.mcp.call("list_leave", {"user": user})
            return out.get("requests", []) if isinstance(out, dict) else out
        return await self.store.get(f"nadi:{user}") or []

    async def file(self, user: str, start: str, end: str, leave_days: int, note: str) -> dict:
        if self.mcp:
            return await self.mcp.call("file_leave", {"user": user, "type": "annual", "from": start, "to": end,
                                                      "leaveDays": leave_days, "note": note[:200]})
        existing = await self.requests(user)
        same = next((r for r in existing if r["from"] == start and r["to"] == end), None)
        if same:
            return {**same, "duplicate": True}
        used = sum(r["leaveDays"] for r in existing)
        req = {"ref": f"NADI-{start[:4]}-{1400 + len(existing) + 1:04d}", "type": "Annual leave", "from": start, "to": end,
               "leaveDays": leave_days, "status": "Pending manager approval", "approver": "Line manager",
               "balanceBefore": self.balance - used, "balanceAfter": self.balance - used - leave_days,
               "note": note[:200], "filedAt": int(time.time())}
        await self.store.set(f"nadi:{user}", existing + [req])
        return req
