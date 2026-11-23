"""Routes: Sticker generation + GIF search."""
from __future__ import annotations

from fastapi import FastAPI

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse

from ..sticker_builder import giphy
from .models import SkillIn, _ctx
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

    @app.post("/agents/stickers/generate")
    async def sticker_generate(body: SkillIn, req: Request):
        try:
            return await S(req).builder.options(body.request, _ctx(body))
        except Exception as err:  # noqa: BLE001 — the Builder is a separate service; say it is unreachable
            raise HTTPException(502, f"Sticker builder unavailable ({type(err).__name__})") from err

    @app.get("/agents/gifs")
    async def gifs(req: Request, q: str = ""):
        try:
            return await giphy(S(req).cfg.giphy_key, q[:100])
        except Exception as err:  # noqa: BLE001
            raise HTTPException(502, f"GIF search unavailable ({type(err).__name__})") from err
