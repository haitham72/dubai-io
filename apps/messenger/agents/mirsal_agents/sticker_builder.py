"""New sticker packs from Mirsal Builder (a separate MCP server), and GIF search.

Builder contract (planned; see docs/stickers-plan.md): tool `create_sticker_pack`
  in:  {"prompt": str, "context": [str], "options": 3, "formats": ["webm", "webp"]}
  out: {"options": [{"id", "title", "stickers": [{"url", "format": "webm|webp|png|svg", "emoji"}]}]}
Three options come back; the person swipes between them and keeps the best one.

Until MIRSAL_BUILDER_MCP_URL is set, the demo returns three of the local packs (best match to the chat first).
GIFs: GIPHY search when GIPHY_API_KEY is set; otherwise the panel shows that GIFs are not connected.
"""
from __future__ import annotations

import random

import httpx2 as httpx

from .chat_skills import Msg, Stickers
from .mcp_client import McpClient


class StickerBuilder:
    def __init__(self, stickers: Stickers, mcp: McpClient | None) -> None:
        self.stickers, self.mcp = stickers, mcp

    @property
    def mode(self) -> str:
        return "builder" if self.mcp else "demo"

    async def options(self, prompt: str, context: list[Msg], rng: random.Random | None = None) -> dict:
        if self.mcp:
            out = await self.mcp.call("create_sticker_pack", {"prompt": prompt, "context": [m.text for m in context][-10:],
                                                              "options": 3, "formats": ["webm", "webp"]})
            return {"options": out.get("options", [])[:3], "mode": "builder"}
        first = self.stickers.pick(context, rng)
        rest = [p for p in self.stickers.packs() if not first or p["id"] != first["id"]]
        (rng or random).shuffle(rest)
        packs = ([first] if first else []) + rest
        return {"mode": "demo", "options": [{
            "id": p["id"], "title": p["title"],
            "stickers": [{"url": f"/agents/stickers/file/{p['id']}/{f}", "format": f.rsplit(".", 1)[-1]} for f in p["stickers"][:8]],
        } for p in packs[:3]]}


async def giphy(key: str, query: str, limit: int = 24, http: httpx.AsyncClient | None = None) -> dict:
    if not key:
        return {"mode": "off", "gifs": []}
    client = http or httpx.AsyncClient(timeout=6)
    endpoint = "search" if query.strip() else "trending"
    res = await client.get(f"https://api.giphy.com/v1/gifs/{endpoint}",
                           params={"api_key": key, "q": query, "limit": limit, "rating": "g"})
    res.raise_for_status()
    gifs = []
    for g in res.json().get("data", []):
        img = g.get("images", {})
        small, full = img.get("fixed_width", {}), img.get("original", {})
        gifs.append({"id": g["id"], "title": g.get("title", ""), "preview": small.get("webp") or small.get("url"),
                     "url": full.get("webp") or full.get("url"), "width": int(small.get("width") or 200),
                     "height": int(small.get("height") or 200)})
    return {"mode": "giphy", "gifs": gifs}
