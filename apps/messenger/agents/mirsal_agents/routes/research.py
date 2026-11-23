"""Routes: Deep research + the weekly watchlist."""
from __future__ import annotations

from fastapi import FastAPI

from .models import ResearchIn

from fastapi import HTTPException, Request
def register(app: FastAPI, S, user) -> None:
    @app.post("/agents/research")
    async def research(body: ResearchIn, req: Request):
        try:
            return await S(req).research.run(body.topic, force=body.force)
        except RuntimeError as err:
            raise HTTPException(502, str(err)) from err

    @app.get("/agents/research/recent")
    async def research_recent(req: Request):
        return await S(req).store.recent("research:recent", 20)

    @app.get("/agents/watch")
    async def watch_list(req: Request):
        return await S(req).watch.list()

    @app.post("/agents/watch/{wid}/refresh")
    async def watch_refresh(wid: str, req: Request):
        if wid not in {t["id"] for t in S(req).watch.topics()}:
            raise HTTPException(404, "Unknown watch topic")
        return await S(req).watch.refresh(wid)
