"""Messenger agents service (FastAPI). Every route lives under /agents so the Vite dev server can proxy it as-is.

    uvicorn messenger_agents.app:app --port 8787        # or: docker compose up (service + Redis)

Without AGENTS_LIVE=1 nothing paid is called: rules decide, research returns the labelled demo brief, voice streaming
reports `stt: "fake"` and the browser keeps its batch voice path.
"""
from __future__ import annotations

import asyncio
import contextlib

import logging
from contextlib import asynccontextmanager


from fastapi import FastAPI, Request, WebSocket



from .chat_skills import FactChecker, Planner, Stickers
from .config import ROOT, Settings
from .routes import health as routes_health
from .routes import mail as routes_mail
from .routes import memory as routes_memory
from .routes import messenger as routes_messenger
from .routes import research as routes_research
from .routes import stickers as routes_stickers
from .routes import voice as routes_voice

from .deciders import FastPathDecider, ModelDecider, RuleDecider
from .engine import Policy
from .mail import Gmail
from .memory import Memory
from .research import DeepResearch, FakeLLM, FakeSearch, OpenAILLM, TavilySearch
from .session import Conversations, VoiceSession
from .spend import Budget, BudgetExceeded
from .store import connect
from .stt import FakeTranscriber, OpenAITranscriber
from .trace import Tracer
from .watch import Watch

log = logging.getLogger("messenger.agents")




class Services:
    """Everything the routes need, built once at startup (tests build their own with fakes)."""

    def __init__(self, cfg: Settings, store, openai_client=None, nara_client=None) -> None:
        self.cfg, self.store = cfg, store
        self.budget = Budget(store, cfg.prices, cfg.budget_usd, cfg.data_dir / "spend.json")
        self.tracer = Tracer(store, cfg.data_dir / "trace.jsonl")
        self.memory = Memory(store)
        self.openai = openai_client
        self.nara = nara_client
        live_text = (cfg.openai_live and openai_client is not None) or (cfg.nara_live and nara_client is not None)
        llm_client = openai_client if cfg.openai_live and openai_client is not None else nara_client
        # A failed classifier must not spend the SDK's long default timeout/retries on
        # every speech partial. Other tools retain their own normal client settings.
        decision_client = openai_client.with_options(timeout=3.0, max_retries=0) if cfg.openai_live and openai_client is not None else None
        self.decider = (FastPathDecider(ModelDecider(decision_client, cfg.decision_model, self.budget)) if decision_client is not None and cfg.fast_path
                        else ModelDecider(decision_client, cfg.decision_model, self.budget) if decision_client is not None else RuleDecider())
        self.policy = Policy(threshold=cfg.act_threshold, margin=cfg.act_margin, stable_s=cfg.stable_s)
        self.conversations = Conversations(self.decider, self.policy)
        self.research = DeepResearch(
            OpenAILLM(llm_client, cfg.research_model, self.budget, cfg.vision_model) if live_text else FakeLLM(),
            TavilySearch(cfg.tavily_key, self.budget) if cfg.tavily_live else FakeSearch(),
            store, self.tracer, live=live_text and cfg.tavily_live)
        self.watch = Watch(self.research, store, cfg.data_dir)
        live_search = self.research.searcher if cfg.tavily_live else None
        self.factcheck = FactChecker(self.research.llm if live_text and live_search else None, live_search, ROOT / "public")
        self.idea_llm = self.research.llm if live_text else None
        self.stickers = Stickers(cfg.stickers_dir)
        self.planner = Planner(store, approver=cfg.leave_approver)
        self.mail = Gmail(cfg.gmail_client_file, cfg.gmail_token_file, f"{cfg.public_url}/agents/mail/oauth/callback")

    def transcriber(self, keywords: list[str] | None = None):
        if self.cfg.openai_live and self.cfg.stt_live and self.openai is not None:
            return OpenAITranscriber(self.openai, self.cfg.stt_model, self.cfg.stt_delay, self.budget, keywords)
        return FakeTranscriber()


def build_app(services: Services | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if services is None:
            cfg = Settings()
            store = await connect(cfg.redis_url)
            openai_client, nara_client = None, None
            if cfg.openai_live:
                from openai import AsyncOpenAI
                # Pinned: the SDK otherwise reads OPENAI_BASE_URL from the environment (the router) and sends the OpenAI key there.
                openai_client = AsyncOpenAI(api_key=cfg.openai_key, base_url="https://api.openai.com/v1")
            if cfg.nara_live:
                from openai import AsyncOpenAI
                nara_client = AsyncOpenAI(api_key=cfg.nara_key, base_url=cfg.nara_base_url or None)
            app.state.s = Services(cfg, store, openai_client, nara_client)
            log.warning("agents: store=%s live=%s nara=%s budget=$%.2f", store.kind, cfg.live, cfg.nara_live, cfg.budget_usd)
        else:
            app.state.s = services
        s: Services = app.state.s
        task = asyncio.create_task(s.watch.loop()) if s.cfg.watch_enabled else None
        yield
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        await s.store.close()

    app = FastAPI(title="Messenger agents", lifespan=lifespan, docs_url="/agents/docs", openapi_url="/agents/openapi.json")

    def S(req: Request | WebSocket) -> Services:
        return req.app.state.s

    def user(req: Request) -> str:
        return (req.headers.get("x-messenger-user") or "demo")[:40]

    @app.exception_handler(BudgetExceeded)
    async def _budget(_: Request, err: BudgetExceeded):
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": str(err), "budget": True}, status_code=402)

    routes_health.register(app, S, user)
    routes_voice.register(app, S, user)
    routes_research.register(app, S, user)
    routes_mail.register(app, S, user)
    routes_messenger.register(app, S, user)
    routes_stickers.register(app, S, user)
    routes_memory.register(app, S, user)

    return app


app = build_app()
