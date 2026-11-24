"""MCP StreamableHTTP server exposing the 7 temporal-memory tools (WP-D)."""
from __future__ import annotations

from collections import deque
from contextvars import ContextVar
from dataclasses import asdict
from datetime import datetime, timezone
import functools
import inspect
from itertools import islice
import threading
import time
from typing import Any, Callable

from fastapi import HTTPException
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from temporal_memory.api.app import AuthInfo
from temporal_memory.core.extract import PROMPT_VERSION
from temporal_memory.core.graph_store import PostgresGraphStore
from temporal_memory.db.db import Database, fold_text, get_database
from temporal_memory.live.context import context_pack
from temporal_memory.mcp.tokens import verify_token as _default_verify_token
from temporal_memory.models import (
    Attempt,
    ExtractionOutput,
    FactEntity,
    OutEntity,
    OutFact,
    OutLink,
    Pool,
    Worker,
    WorkerKind,
)
from temporal_memory.queue.jobs import PostgresJobs

_VALID_WORKER_KINDS: frozenset[str] = frozenset(
    {"internal-cloud", "internal-local", "agent-cli", "owner-hook"}
)

_AUTH_CTX: ContextVar[AuthInfo | None] = ContextVar("tm_mcp_auth", default=None)

# Module-level inspectable audit log (mirrors app.state.mcp_call_log for convenience).
mcp_call_log: list[dict[str, Any]] = []
_LOG_LOCK = threading.Lock()


def _normalize_auth(raw_auth: Any) -> AuthInfo | None:
    if raw_auth is None:
        return None
    if isinstance(raw_auth, AuthInfo):
        return raw_auth
    role = getattr(raw_auth, "role", None)
    if not role:
        return None
    token_id = getattr(raw_auth, "id", None) or getattr(raw_auth, "token_id", "") or ""
    owner = getattr(raw_auth, "owner", None)
    return AuthInfo(id=str(token_id), role=role, owner=owner)


def _extract_bearer_token(scope: Scope) -> str | None:
    for key, val in scope.get("headers") or ():
        if key.lower() == b"authorization":
            text = val.decode("latin-1").strip()
            parts = text.split(None, 1)
            if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1].strip():
                return parts[1].strip()
            return None
    return None


def _require_auth() -> AuthInfo:
    auth = _AUTH_CTX.get()
    if auth is None:
        raise ToolError("authentication required")
    return auth


def _scoped_owner(auth: AuthInfo, requested_owner: str | None) -> str:
    if auth.role == "owner-device":
        if not auth.owner:
            raise ToolError("permission denied: owner-device token missing owner")
        if requested_owner is not None and requested_owner != auth.owner:
            raise ToolError("permission denied: owner-device token cannot access another owner's data")
        return auth.owner
    if not requested_owner:
        raise ToolError("owner is required")
    return requested_owner


def _check_job_access(db: Database, auth: AuthInfo, job_id: str) -> str | None:
    if auth.role == "admin":
        with db.connection() as conn:
            row = conn.execute("SELECT prompt_version FROM jobs WHERE id = %s", (job_id,)).fetchone()
        return str(row["prompt_version"]) if row else None

    with db.connection() as conn:
        row = conn.execute("SELECT owner, pool, prompt_version FROM jobs WHERE id = %s", (job_id,)).fetchone()
    if row is None:
        return None
    if auth.role == "owner-device" and row["owner"] != auth.owner:
        raise ToolError("permission denied: owner-device token cannot access another owner's job")
    if auth.role == "worker" and row["pool"] == "owner-device":
        raise ToolError("permission denied: worker token cannot access owner-device pool job")
    return str(row["prompt_version"])


def _dict_to_extraction_output(output: dict[str, Any] | None) -> ExtractionOutput | None:
    if output is None:
        return None
    if not isinstance(output, dict):
        raise ToolError("output must be a JSON object")

    entities: list[OutEntity] = []
    for raw in output.get("entities") or []:
        if not isinstance(raw, dict):
            raise ToolError("invalid entity entry in output")
        entities.append(
            OutEntity(
                ref=str(raw.get("ref") or ""),
                kind=raw.get("kind") or "person",
                aliases=[str(a) for a in (raw.get("aliases") or []) if a is not None],
                relation_to_user=raw.get("relation_to_user"),
            )
        )

    facts: list[OutFact] = []
    for raw in output.get("facts") or []:
        if not isinstance(raw, dict):
            raise ToolError("invalid fact entry in output")
        fact_entities: list[FactEntity] = []
        for fe in raw.get("entities") or []:
            if isinstance(fe, dict):
                fact_entities.append(
                    FactEntity(
                        entity_id=str(fe.get("entity_id") or ""),
                        role=str(fe["role"]) if fe.get("role") is not None else None,
                    )
                )
            elif isinstance(fe, str):
                fact_entities.append(FactEntity(entity_id=fe, role=None))
        facts.append(
            OutFact(
                text=str(raw.get("text") or ""),
                text_orig=str(raw["text_orig"]) if raw.get("text_orig") is not None else None,
                subject_path=str(raw.get("subject_path") or ""),
                entities=fact_entities,
                op=raw.get("op") or "new",
                target=str(raw["target"]) if raw.get("target") is not None else None,
                valid_from=str(raw.get("valid_from") or ""),
                evidence=[str(ev) for ev in (raw.get("evidence") or []) if ev is not None],
                sensitive=str(raw["sensitive"]) if raw.get("sensitive") is not None else None,
            )
        )

    links: list[OutLink] = []
    for raw in output.get("links") or []:
        if not isinstance(raw, dict):
            raise ToolError("invalid link entry in output")
        links.append(
            OutLink(
                src=str(raw.get("src") or ""),
                rel=raw.get("rel") or "RELATED_TO",
                dst=str(raw.get("dst") or ""),
                valid_from=str(raw["valid_from"]) if raw.get("valid_from") is not None else None,
                evidence=[str(ev) for ev in (raw.get("evidence") or []) if ev is not None],
            )
        )

    return ExtractionOutput(entities=entities, facts=facts, links=links)


class _RateLimiter:
    """Thread-safe per-token 60-second sliding-window rate limiter."""

    def __init__(self, limit_per_min: int) -> None:
        self.limit_per_min = limit_per_min
        self._lock = threading.Lock()
        self._buckets: dict[str, deque[float]] = {}

    def allow(self, key: str) -> bool:
        if self.limit_per_min <= 0:
            return True
        now = time.monotonic()
        cutoff = now - 60.0
        with self._lock:
            q = self._buckets.setdefault(key, deque())
            while q and q[0] <= cutoff:
                q.popleft()
            if len(q) >= self.limit_per_min:
                return False
            q.append(now)
            return True


class _MCPAuthAndLifecycleMiddleware:
    """ASGI middleware enforcing bearer auth, rate limiting, ContextVar auth, and lazy lifespan."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        mcp_server: MCPServer,
        build_fallback_app: Callable[[], Starlette],
        verifier: Callable[[str | None], Any],
        rate_limiter: _RateLimiter,
    ) -> None:
        self.app = app
        self._mcp = mcp_server
        self._build_fallback_app = build_fallback_app
        self._verifier = verifier
        self._rate_limiter = rate_limiter

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        token = _extract_bearer_token(scope)
        if not token:
            resp = JSONResponse({"detail": "missing or invalid bearer token"}, status_code=401)
            await resp(scope, receive, send)
            return

        auth: AuthInfo | None = None
        try:
            auth = _normalize_auth(self._verifier(token))
        except HTTPException:
            auth = None
        if auth is None:
            resp = JSONResponse({"detail": "invalid or revoked bearer token"}, status_code=401)
            await resp(scope, receive, send)
            return

        rate_key = auth.id or token
        if not self._rate_limiter.allow(rate_key):
            resp = JSONResponse({"detail": "rate limit exceeded"}, status_code=429)
            await resp(scope, receive, send)
            return

        ctx_token = _AUTH_CTX.set(auth)
        try:
            sm = getattr(self._mcp._lowlevel_server, "_session_manager", None)
            if sm is not None and sm._task_group is not None:
                await self.app(scope, receive, send)
            else:
                # Mounted sub-apps in FastAPI do not receive parent lifespan events automatically.
                fallback_app = self._build_fallback_app()
                fallback_sm = self._mcp._lowlevel_server._session_manager
                async with fallback_sm.run():
                    await fallback_app(scope, receive, send)
        finally:
            _AUTH_CTX.reset(ctx_token)


def create_mcp_app(
    db: Database | None = None,
    store: PostgresGraphStore | None = None,
    auth_verifier: Callable[[str | None], Any] | None = None,
    *,
    rate_limit_per_min: int = 120,
) -> Starlette:
    """Build the stateless StreamableHTTP MCP Starlette app with 7 temporal-memory tools."""
    database = db or get_database()
    graph_store = store or PostgresGraphStore(database)
    jobs = PostgresJobs(database, graph_store)
    verifier = auth_verifier or (lambda tok: _default_verify_token(database, tok or ""))

    call_log: list[dict[str, Any]] = []
    call_log_lock = threading.Lock()

    def _record_audit(tool_name: str, auth: AuthInfo | None, ok: bool) -> None:
        entry = {
            "tool": tool_name,
            "token_id": auth.id if auth else "",
            "role": auth.role if auth else "",
            "owner": auth.owner if auth else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ok": ok,
        }
        with call_log_lock:
            call_log.append(entry)
        with _LOG_LOCK:
            mcp_call_log.append(entry)

    mcp = MCPServer("temporal-memory")

    def _audited(name: str):
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            @functools.wraps(fn)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                auth = _AUTH_CTX.get()
                ok = True
                try:
                    return fn(*args, **kwargs)
                except Exception:
                    ok = False
                    raise
                finally:
                    _record_audit(name, auth, ok)

            wrapper.__signature__ = inspect.signature(fn)  # type: ignore[attr-defined]
            return wrapper

        return decorator

    @mcp.tool(description="Inspect authenticated token identity, role, owner scope, and pending job count.")
    @_audited("memory_whoami")
    def memory_whoami() -> dict[str, Any]:
        auth = _require_auth()
        with database.connection() as conn:
            if auth.role == "owner-device":
                row = conn.execute(
                    """
                    SELECT COUNT(*)::int AS cnt
                    FROM jobs
                    WHERE state = 'queued'
                      AND pool = 'owner-device'
                      AND owner = %s
                      AND sensitive_flag = FALSE
                    """,
                    (auth.owner,),
                ).fetchone()
            elif auth.role == "worker":
                row = conn.execute(
                    "SELECT COUNT(*)::int AS cnt FROM jobs WHERE state = 'queued' AND pool = 'internal'"
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*)::int AS cnt FROM jobs WHERE state = 'queued'").fetchone()

        return {
            "token_id": auth.id,
            "role": auth.role,
            "owner": auth.owner,
            "pending_jobs": int(row["cnt"]) if row else 0,
            "prompt_version": PROMPT_VERSION,
        }

    @mcp.tool(description="Claim queued extraction jobs scoped to caller role and optional owner/day range.")
    @_audited("memory_claim_job")
    def memory_claim_job(
        owner: str | None = None,
        day_from: str | None = None,
        day_to: str | None = None,
        limit: int = 1,
        model: str = "claude-code-hook",
        runner: str = "mcp",
        worker_id: str | None = None,
    ) -> dict[str, Any]:
        auth = _require_auth()
        clamped_limit = max(1, min(int(limit), 100))

        if auth.role == "owner-device":
            if not auth.owner:
                raise ToolError("permission denied: owner-device token missing owner")
            if owner is not None and owner != auth.owner:
                raise ToolError("permission denied: owner-device token cannot claim jobs for another owner")
            pools: list[Pool] = ["owner-device"]
            effective_owner: str | None = auth.owner
            worker_kind: WorkerKind = "owner-hook"
            worker_owner: str | None = auth.owner
        else:
            pools = ["internal"]
            effective_owner = owner
            worker_kind = "agent-cli"
            worker_owner = None

        wid = worker_id or f"{worker_kind}:{auth.id}"
        worker = Worker(
            id=wid,
            kind=worker_kind,
            model=model,
            runner=runner,
            owner=worker_owner,
        )
        bundles = jobs.claim(
            worker=worker,
            pools=pools,
            owner=effective_owner,
            day_from=day_from,
            day_to=day_to,
            limit=clamped_limit,
        )
        return {
            "jobs": [asdict(b) for b in bundles],
            "count": len(bundles),
        }

    @mcp.tool(description="Extend lease on an active job using its fence token.")
    @_audited("memory_heartbeat")
    def memory_heartbeat(job_id: str, fence_token: str) -> dict[str, bool]:
        auth = _require_auth()
        _check_job_access(database, auth, job_id)
        ok = bool(jobs.heartbeat(job_id, fence_token))
        return {"ok": ok}

    @mcp.tool(description="Submit extraction output for a leased job and return the validator/applier verdict.")
    @_audited("memory_submit_result")
    def memory_submit_result(
        job_id: str,
        fence_token: str,
        attempt_no: int,
        output: dict[str, Any],
        model: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost_usd: float = 0.0,
        worker_id: str | None = None,
        worker_kind: str | None = None,
        model_observed: str | None = None,
    ) -> dict[str, Any]:
        auth = _require_auth()
        prompt_ver = _check_job_access(database, auth, job_id) or PROMPT_VERSION

        if auth.role == "owner-device":
            effective_kind: WorkerKind = "owner-hook"
            effective_cost = 0.0
        else:
            effective_kind = (
                worker_kind if worker_kind in _VALID_WORKER_KINDS else "agent-cli"  # type: ignore[assignment]
            )
            effective_cost = 0.0 if effective_kind == "owner-hook" else float(cost_usd)

        parsed_output = _dict_to_extraction_output(output)
        wid = worker_id or f"{effective_kind}:{auth.id}"
        attempt = Attempt(
            job_id=job_id,
            attempt_no=int(attempt_no),
            fence_token=fence_token,
            worker_id=wid,
            worker_kind=effective_kind,
            model=model,
            prompt_version=prompt_ver,
            output=parsed_output,
            tokens_in=int(tokens_in),
            tokens_out=int(tokens_out),
            cost_usd=effective_cost,
            model_observed=model_observed,
        )
        verdict = jobs.submit(attempt)
        res = asdict(verdict)
        res["processed_by"] = "your Claude" if effective_kind == "owner-hook" else model
        return res

    @mcp.tool(description="Search visible facts for an owner using SQL multi-channel retrieval.")
    @_audited("memory_search")
    def memory_search(query: str, owner: str | None = None, limit: int = 10) -> dict[str, Any]:
        auth = _require_auth()
        target_owner = _scoped_owner(auth, owner)
        clamped_limit = max(1, min(int(limit), 100))
        q_clean = (query or "").strip()

        if not q_clean:
            facts = list(islice(graph_store.iter_visible_facts(target_owner, page_size=clamped_limit), clamped_limit))
            return {
                "owner": target_owner,
                "query": query,
                "facts": [asdict(f) for f in facts],
                "count": len(facts),
            }

        cands = graph_store.search_candidates(target_owner, q_clean, limit=clamped_limit)
        matched = graph_store.get_facts(target_owner, [c.fact_id for c in cands])[:clamped_limit]
        return {
            "owner": target_owner,
            "query": query,
            "facts": [asdict(f) for f in matched],
            "count": len(matched),
        }

    @mcp.tool(description="Build an L1 context pack for a message/query using live.context.context_pack.")
    @_audited("memory_context")
    def memory_context(text: str, owner: str | None = None, max_tokens: int = 1500) -> dict[str, Any]:
        auth = _require_auth()
        target_owner = _scoped_owner(auth, owner)
        return context_pack(target_owner, text, max_tokens=int(max_tokens), store=graph_store)

    @mcp.tool(description="Return owner subject/people counts and a visible memory summary.")
    @_audited("memory_vault")
    def memory_vault(owner: str | None = None) -> dict[str, Any]:
        auth = _require_auth()
        target_owner = _scoped_owner(auth, owner)
        counts_by_subj = graph_store.fact_counts_by_subject(target_owner)
        confirmed_by_subj = (
            graph_store.confirmed_fact_counts_by_subject(target_owner)
            if hasattr(graph_store, "confirmed_fact_counts_by_subject")
            else {}
        )
        subjects = graph_store.list_subjects(target_owner)
        visible_subjects = [
            s for s in subjects
            if (s.sensitive_cat is None and (s.path or "").split("/")[0].lower() not in ("health", "faith"))
            or confirmed_by_subj.get(s.id, 0) > 0
        ]
        vis_sids = {s.id for s in visible_subjects}
        visible_fact_count = sum(cnt for sid, cnt in counts_by_subj.items() if sid in vis_sids or not subjects)

        vis_eids = (
            graph_store.visible_entity_ids(target_owner)
            if hasattr(graph_store, "visible_entity_ids")
            else None
        )
        entities = graph_store.list_entities(target_owner)
        active_entities = [
            e for e in entities
            if e.status != "merged"
            and (
                vis_eids is None
                or e.id in vis_eids
                or e.relation_to_user == "self"
                or getattr(e, "provenance", "inferred") in ("user_supplied", "provider_confirmed")
            )
        ]
        recent_facts = list(islice(graph_store.iter_visible_facts(target_owner, page_size=20), 20))
        quarantine_counts = graph_store.get_quarantine_counts(target_owner)

        people = [e for e in active_entities if e.kind == "person"]
        places = [e for e in active_entities if e.kind == "place"]
        orgs = [e for e in active_entities if e.kind == "org"]

        return {
            "owner": target_owner,
            "subject_count": len(visible_subjects),
            "people_count": len(people),
            "entity_counts": {
                "person": len(people),
                "place": len(places),
                "org": len(orgs),
                "total": len(active_entities),
            },
            "visible_fact_count": visible_fact_count,
            "subjects": [
                {
                    "id": s.id,
                    "path": s.path,
                    "label": s.label,
                    "kind": s.kind,
                    "fact_count": counts_by_subj.get(s.id, s.fact_count),
                }
                for s in visible_subjects[:50]
            ],
            "people": [
                {
                    "id": e.id,
                    "name": e.name,
                    "relation_to_user": e.relation_to_user,
                    "closeness_tier": e.closeness_tier,
                }
                for e in people[:50]
            ],
            "recent_facts": [
                {
                    "id": f.id,
                    "text": f.text,
                    "subject_id": f.subject_id,
                    "valid_from": f.valid_from,
                    "status": f.status,
                }
                for f in recent_facts
            ],
            "quarantine_counts": quarantine_counts,
        }

    transport_security = TransportSecuritySettings(enable_dns_rebinding_protection=False)

    def _build_streamable_app() -> Starlette:
        return mcp.streamable_http_app(
            streamable_http_path="/",
            json_response=True,
            stateless_http=True,
            transport_security=transport_security,
        )

    starlette_app = _build_streamable_app()
    starlette_app.state.mcp_call_log = call_log
    starlette_app.state.mcp_server = mcp

    rate_limiter = _RateLimiter(rate_limit_per_min)
    starlette_app.add_middleware(
        _MCPAuthAndLifecycleMiddleware,
        mcp_server=mcp,
        build_fallback_app=_build_streamable_app,
        verifier=verifier,
        rate_limiter=rate_limiter,
    )
    return starlette_app
