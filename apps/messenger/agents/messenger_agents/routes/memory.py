"""Routes: Memory facts + persisted tasks."""
from __future__ import annotations

from fastapi import FastAPI, Request

from .models import FactsIn, TasksIn

def register(app: FastAPI, S, user) -> None:
    @app.get("/agents/memory/facts")
    async def facts(req: Request):
        return {"facts": await S(req).memory.facts(user(req))}

    @app.put("/agents/memory/facts")
    async def set_facts(body: FactsIn, req: Request):
        return {"facts": await S(req).memory.set_facts(user(req), body.facts)}

    @app.get("/agents/memory/tasks")
    async def tasks(req: Request):
        return {"tasks": await S(req).memory.tasks(user(req))}

    @app.put("/agents/memory/tasks")
    async def set_tasks(body: TasksIn, req: Request):
        return {"saved": await S(req).memory.set_tasks(user(req), body.tasks)}
