"""Routes: sticker files the user already has, and GIF search. No generation."""
from __future__ import annotations

import httpx2 as httpx  # ships with the openai SDK
from fastapi import FastAPI

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse

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


def register(app: FastAPI, S, user) -> None:
    @app.get("/agents/stickers")
    async def sticker_packs(req: Request):
        return {"packs": S(req).stickers.packs(), "root": S(req).stickers.root.name}

    @app.get("/agents/stickers/file/{pack}/{name}")
    async def sticker_file(pack: str, name: str, req: Request):
        path = S(req).stickers.file(pack, name)
        if not path:
            raise HTTPException(404, "Not found")
        # Builder files can be replaced under the same id (an edited sticker): cache them briefly.
        return FileResponse(path, headers={"Cache-Control": f"public, max-age={60 if pack.startswith('mb-') else 86400}"})

    @app.get("/agents/gifs")
    async def gifs(req: Request, q: str = ""):
        try:
            return await giphy(S(req).cfg.giphy_key, q[:100])
        except Exception as err:  # noqa: BLE001
            raise HTTPException(502, f"GIF search unavailable ({type(err).__name__})") from err
