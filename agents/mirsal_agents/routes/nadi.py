"""Routes: Nadi demo HR leave connector."""
from __future__ import annotations

from fastapi import FastAPI, Request

from .models import LeaveIn

def register(app: FastAPI, S, user) -> None:
    @app.get("/agents/nadi/leave")
    async def nadi_list(req: Request):
        return {"requests": await S(req).nadi.requests(user(req)), "connector": "demo"}

    @app.post("/agents/nadi/leave")
    async def nadi_file(body: LeaveIn, req: Request):
        return await S(req).nadi.file(user(req), body.start, body.end, body.leaveDays, body.note)
