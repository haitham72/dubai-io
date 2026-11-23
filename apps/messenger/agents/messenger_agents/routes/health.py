"""Routes: Service health, connectors, budget, traces."""
from __future__ import annotations

from fastapi import FastAPI, Request

from ..deciders import FastPathDecider, ModelDecider
def register(app: FastAPI, S, user) -> None:
    @app.get("/agents/health")
    async def health(req: Request):
        s = S(req)
        return {"ok": True, "store": s.store.kind, "live": {
            "decisions": isinstance(s.decider, (ModelDecider, FastPathDecider)), "stt": s.cfg.openai_live and s.cfg.stt_live and s.openai is not None,
            "research": s.research.live}, "budget": await s.budget.status(), "mail": s.mail.status()}

    @app.get("/agents/connectors")
    async def connectors(req: Request):
        """Every outside connection, its state, and what it waits for (ARCHITECTURE.md §3)."""
        s, c = S(req), S(req).cfg
        def row(name, kind, live, waits, demo):
            return {"name": name, "kind": kind, "state": "live" if live else "demo", "waitsFor": [] if live else waits, "demoData": demo}
        return {"connectors": [
            row("GIPHY", "http", bool(c.giphy_key), ["GIPHY_API_KEY"], "none (panel shows 'not connected')"),
            row("Gmail", "oauth", s.mail.status()["linked"], ["agents/.secrets/gmail_client.json", "sign-in at /agents/mail/oauth/start"], "src/screens/mail/data.ts"),
            row("OpenAI (streaming STT, Decisions, TTS, transcription)", "http", c.openai_live, ["OPENAI_API_KEY", "AGENTS_LIVE=1"], "rule decider + demo answers (streaming STT needs AGENTS_STT_LIVE=1)"),
            row("Nara (text chat, research, fact check)", "http", c.nara_live, ["NARA_API_KEY", "AGENTS_LIVE=1"], "demo answers"),
            row("Tavily (search)", "http", c.tavily_live, ["TVLY_API_KEY", "AGENTS_LIVE=1"], "demo research briefs"),
            row("Redis (memory)", "redis", s.store.kind == "redis", ["REDIS_URL"], "in-process memory"),
        ]}

    @app.get("/agents/budget")
    async def budget(req: Request):
        return {**await S(req).budget.status(), "log": await S(req).store.recent("spend:log", 30)}

    @app.get("/agents/trace")
    async def trace(req: Request, n: int = 50):
        return await S(req).tracer.recent(min(n, 500))
