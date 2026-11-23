"""FastAPI application factory, bearer-token authentication, and worker/admin endpoints (WP-A)."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import inspect
import secrets
from typing import Any, Callable, Literal, Optional
import uuid

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from temporal_memory.config import get_settings
from temporal_memory.db.db import Database, get_database, migrate
from temporal_memory.models import (
    Attempt,
    EntityKind,
    ExtractionOutput,
    FactEntity,
    FactOp,
    LinkRel,
    OutEntity,
    OutFact,
    OutLink,
    OwnerKind,
    Pool,
    Relation,
    Worker,
    WorkerKind,
)

Role = Literal["admin", "worker", "owner-device"]
_VALID_ROLES: tuple[str, ...] = ("admin", "worker", "owner-device")


@dataclass(frozen=True)
class AuthInfo:
    """Authenticated caller identity derived from a bearer token."""

    id: str
    role: Role
    owner: Optional[str] = None


# ---------------------------------------------------------------- request schemas
class OwnerCreateIn(BaseModel):
    id: str = Field(..., min_length=1)
    label: str = Field(..., min_length=1)
    kind: OwnerKind = "real"
    display_name: str = ""
    self_aliases: list[str] = Field(default_factory=list)
    timezone: str = "Asia/Dubai"


class TokenCreateIn(BaseModel):
    role: Role
    owner: Optional[str] = None
    label: str = ""


class WorkerOnlineIn(BaseModel):
    id: str = Field(..., min_length=1)
    kind: WorkerKind
    model: str = Field(..., min_length=1)
    model_version: str = ""
    runner: str = Field(..., min_length=1)
    owner: Optional[str] = None
    prompt_versions: list[str] = Field(default_factory=list)
    released: bool = False


class ClaimWorkerIn(BaseModel):
    id: str = Field(..., min_length=1)
    kind: WorkerKind
    model: str = Field(..., min_length=1)
    runner: str = Field(..., min_length=1)
    owner: Optional[str] = None
    released: bool = False


class JobClaimIn(BaseModel):
    worker: ClaimWorkerIn
    pools: list[Pool] = Field(default_factory=lambda: ["internal"])
    owner: Optional[str] = None
    day_from: Optional[str] = None
    day_to: Optional[str] = None
    limit: int = Field(default=1, ge=1, le=100)


class HeartbeatIn(BaseModel):
    fence_token: str = Field(..., min_length=1)


class FactEntityIn(BaseModel):
    entity_id: str
    role: Optional[str] = None


class OutEntityIn(BaseModel):
    ref: str
    kind: EntityKind
    aliases: list[str] = Field(default_factory=list)
    relation_to_user: Optional[Relation] = None


class OutFactIn(BaseModel):
    text: str
    text_orig: Optional[str] = None
    subject_path: str
    entities: list[FactEntityIn] = Field(default_factory=list)
    op: FactOp
    target: Optional[str] = None
    valid_from: str
    evidence: list[str] = Field(default_factory=list)
    sensitive: Optional[str] = None


class OutLinkIn(BaseModel):
    src: str
    rel: LinkRel
    dst: str
    valid_from: Optional[str] = None
    evidence: list[str] = Field(default_factory=list)


class ExtractionOutputIn(BaseModel):
    entities: list[OutEntityIn] = Field(default_factory=list)
    facts: list[OutFactIn] = Field(default_factory=list)
    links: list[OutLinkIn] = Field(default_factory=list)


class AttemptIn(BaseModel):
    job_id: Optional[str] = None
    attempt_no: int
    fence_token: str
    worker_id: str
    worker_kind: WorkerKind
    model: str
    prompt_version: str
    output: Optional[ExtractionOutputIn] = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    model_observed: Optional[str] = None


# ---------------------------------------------------------------- helpers
def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _extract_bearer(header_value: str | None) -> str:
    if not header_value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing authorization header")
    parts = header_value.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid authorization header")
    return parts[1].strip()


def _make_store(db: Database) -> Any:
    try:
        from temporal_memory.core.graph_store import PostgresGraphStore

        return PostgresGraphStore(db)
    except ImportError:
        return None


def _get_jobs(app: FastAPI) -> Any:
    if app.state.jobs is not None:
        return app.state.jobs
    from temporal_memory.queue.jobs import PostgresJobs

    return PostgresJobs(app.state.db, app.state.store)


def _deserialize_attempt(job_id: str, body: AttemptIn) -> Attempt:
    if body.job_id is not None and body.job_id != job_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="job_id mismatch")
    output: Optional[ExtractionOutput] = None
    if body.output is not None:
        output = ExtractionOutput(
            entities=[
                OutEntity(
                    ref=e.ref,
                    kind=e.kind,
                    aliases=list(e.aliases),
                    relation_to_user=e.relation_to_user,
                )
                for e in body.output.entities
            ],
            facts=[
                OutFact(
                    text=f.text,
                    text_orig=f.text_orig,
                    subject_path=f.subject_path,
                    entities=[FactEntity(entity_id=fe.entity_id, role=fe.role) for fe in f.entities],
                    op=f.op,
                    target=f.target,
                    valid_from=f.valid_from,
                    evidence=list(f.evidence),
                    sensitive=f.sensitive,
                )
                for f in body.output.facts
            ],
            links=[
                OutLink(
                    src=lk.src,
                    rel=lk.rel,
                    dst=lk.dst,
                    valid_from=lk.valid_from,
                    evidence=list(lk.evidence),
                )
                for lk in body.output.links
            ],
        )
    cost_usd = 0.0 if body.worker_kind == "owner-hook" else float(body.cost_usd)
    return Attempt(
        job_id=job_id,
        attempt_no=body.attempt_no,
        fence_token=body.fence_token,
        worker_id=body.worker_id,
        worker_kind=body.worker_kind,
        model=body.model,
        prompt_version=body.prompt_version,
        output=output,
        tokens_in=body.tokens_in,
        tokens_out=body.tokens_out,
        cost_usd=cost_usd,
        started_at=body.started_at,
        finished_at=body.finished_at,
        model_observed=body.model_observed,
    )


def _check_job_access(db: Database, auth: AuthInfo, job_id: str) -> None:
    """Enforce pool/owner isolation on an existing job row when present."""
    if auth.role == "admin":
        return
    with db.connection() as conn:
        row = conn.execute("SELECT owner, pool FROM jobs WHERE id = %s", (job_id,)).fetchone()
    if row is None:
        return
    if auth.role == "owner-device" and row["owner"] != auth.owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="owner-device token cannot access another owner's job",
        )
    if auth.role == "worker" and row["pool"] == "owner-device":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="worker token cannot access owner-device pool job",
        )


def _call_configure(fn: Callable[..., Any], **kwargs: Any) -> None:
    """Invoke a router configure helper passing only the parameters it accepts."""
    sig = inspect.signature(fn)
    accepts_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
    filtered = kwargs if accepts_varkw else {k: v for k, v in kwargs.items() if k in sig.parameters}
    fn(**filtered)


def _mount_optional_routers(app: FastAPI, db: Database, store: Any, auth_verifier: Callable[[str | None], AuthInfo]) -> None:
    try:
        from temporal_memory.api.vault import AuthContext

        def _vault_verifier(token: str | None) -> AuthContext | None:
            if not token:
                return None
            info = auth_verifier(token)
            return AuthContext(role=info.role, owner=info.owner, token_id=info.id)
    except ImportError:
        _vault_verifier = auth_verifier  # type: ignore[assignment]

    for mod_name in ("temporal_memory.api.vault", "temporal_memory.api.export_md", "temporal_memory.api.ops", "temporal_memory.reflect"):
        try:
            mod = __import__(mod_name, fromlist=["*"])
        except ImportError:
            continue
        if hasattr(mod, "set_default_store"):
            mod.set_default_store(store)
        if hasattr(mod, "configure"):
            _call_configure(mod.configure, db=db, store=store, auth_verifier=_vault_verifier)
        if hasattr(mod, "router"):
            app.include_router(mod.router)

    try:
        from temporal_memory.mcp import server as mcp_server
    except ImportError:
        return
    mcp_app = getattr(mcp_server, "app", None)
    if mcp_app is None and hasattr(mcp_server, "create_mcp_app"):
        mcp_app = mcp_server.create_mcp_app(db=db, store=store, auth_verifier=auth_verifier)
    if mcp_app is not None:
        app.mount("/mcp", mcp_app)


# ---------------------------------------------------------------- app factory
def create_app(db: Database | None = None, *, admin_token: str | None = None) -> FastAPI:
    """Build and configure the temporal-memory FastAPI application."""
    database = db or get_database()
    migrate(database)
    store = _make_store(database)

    app = FastAPI(title="temporal-memory", version="0.1.0")
    app.state.db = database
    app.state.store = store
    app.state.jobs = None

    def verify_token(token_or_header: str | None) -> AuthInfo:
        if not token_or_header:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
        raw = token_or_header.strip()
        if raw.lower().startswith("bearer "):
            raw = raw[7:].strip()
        if not raw:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="empty bearer token")

        expected_admin = admin_token if admin_token is not None else get_settings().admin_token
        if expected_admin and secrets.compare_digest(raw, expected_admin):
            return AuthInfo(id="admin", role="admin", owner=None)

        token_hash = _hash_token(raw)
        with database.connection() as conn:
            row = conn.execute(
                "SELECT id, role, owner, revoked_at FROM tokens WHERE token_hash = %s",
                (token_hash,),
            ).fetchone()
        if row is None or row["revoked_at"] is not None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or revoked token")
        if row["role"] not in _VALID_ROLES:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token role")
        return AuthInfo(id=row["id"], role=row["role"], owner=row["owner"])

    def require_auth(authorization: str | None = Header(default=None)) -> AuthInfo:
        token = _extract_bearer(authorization)
        return verify_token(token)

    def require_admin(auth: AuthInfo = Depends(require_auth)) -> AuthInfo:
        if auth.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin token required")
        return auth

    app.state.auth_verifier = verify_token

    @app.get("/health")
    def health() -> dict[str, Any]:
        try:
            with database.connection() as conn:
                conn.execute("SELECT 1").fetchone()
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="database unavailable") from exc
        return {"ok": True, "db": "ok"}

    @app.post("/v1/owners")
    def create_owner(body: OwnerCreateIn, _: AuthInfo = Depends(require_admin)) -> dict[str, Any]:
        with database.transaction() as conn:
            row = conn.execute(
                """
                INSERT INTO owners (id, label, kind, display_name, self_aliases, timezone)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    label = EXCLUDED.label,
                    kind = EXCLUDED.kind,
                    display_name = EXCLUDED.display_name,
                    self_aliases = EXCLUDED.self_aliases,
                    timezone = EXCLUDED.timezone
                RETURNING id, label, kind, display_name, self_aliases, timezone
                """,
                (body.id, body.label, body.kind, body.display_name, Jsonb(body.self_aliases), body.timezone),
            ).fetchone()
        return dict(row)

    @app.post("/v1/tokens")
    def create_token(body: TokenCreateIn, _: AuthInfo = Depends(require_admin)) -> dict[str, Any]:
        if body.role == "owner-device" and not body.owner:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="owner-device token requires owner")
        token_id = f"tok_{uuid.uuid4().hex[:12]}"
        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        with database.transaction() as conn:
            conn.execute(
                "INSERT INTO tokens (id, token_hash, role, owner, label) VALUES (%s, %s, %s, %s, %s)",
                (token_id, token_hash, body.role, body.owner, body.label),
            )
        return {
            "id": token_id,
            "token": raw_token,
            "role": body.role,
            "owner": body.owner,
            "label": body.label,
        }

    @app.delete("/v1/tokens/{token_id}")
    def revoke_token(token_id: str, _: AuthInfo = Depends(require_admin)) -> dict[str, Any]:
        with database.transaction() as conn:
            row = conn.execute(
                """
                UPDATE tokens
                SET revoked_at = COALESCE(revoked_at, now())
                WHERE id = %s
                RETURNING id
                """,
                (token_id,),
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="token not found")
        return {"ok": True, "id": token_id}

    @app.post("/v1/workers/online")
    def worker_online(body: WorkerOnlineIn, auth: AuthInfo = Depends(require_auth)) -> dict[str, Any]:
        effective_owner = body.owner
        if auth.role == "owner-device":
            if body.kind != "owner-hook":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="owner-device token may only register kind='owner-hook'",
                )
            if body.owner is not None and body.owner != auth.owner:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="owner-device token cannot register worker for another owner",
                )
            effective_owner = auth.owner

        with database.transaction() as conn:
            row = conn.execute(
                """
                INSERT INTO workers (
                    id, kind, model, model_version, runner, owner, prompt_versions, status, released, last_heartbeat
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'online', %s, now())
                ON CONFLICT (id) DO UPDATE SET
                    kind = EXCLUDED.kind,
                    model = EXCLUDED.model,
                    model_version = EXCLUDED.model_version,
                    runner = EXCLUDED.runner,
                    owner = EXCLUDED.owner,
                    prompt_versions = EXCLUDED.prompt_versions,
                    status = 'online',
                    released = EXCLUDED.released,
                    last_heartbeat = now()
                RETURNING id, kind, model, model_version, runner, owner, prompt_versions, status, released, last_heartbeat
                """,
                (
                    body.id,
                    body.kind,
                    body.model,
                    body.model_version,
                    body.runner,
                    effective_owner,
                    Jsonb(body.prompt_versions),
                    body.released,
                ),
            ).fetchone()
        result = dict(row)
        if result.get("last_heartbeat") is not None:
            result["last_heartbeat"] = result["last_heartbeat"].isoformat()
        return result

    @app.post("/v1/jobs/claim")
    def claim_jobs(body: JobClaimIn, request: Request, auth: AuthInfo = Depends(require_auth)) -> list[dict[str, Any]]:
        pools = list(body.pools)
        effective_owner = body.owner
        worker_owner = body.worker.owner

        if auth.role == "worker":
            if "owner-device" in pools:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="worker token cannot claim owner-device pool",
                )
        elif auth.role == "owner-device":
            if not auth.owner:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="owner-device token missing owner")
            if body.owner is not None and body.owner != auth.owner:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="owner-device token cannot claim jobs for another owner",
                )
            if body.worker.owner is not None and body.worker.owner != auth.owner:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="owner-device token cannot claim jobs as another owner",
                )
            pools = ["owner-device"]
            effective_owner = auth.owner
            worker_owner = auth.owner

        worker = Worker(
            id=body.worker.id,
            kind=body.worker.kind,
            model=body.worker.model,
            runner=body.worker.runner,
            owner=worker_owner,
            released=body.worker.released,
        )
        jobs = _get_jobs(request.app)
        bundles = jobs.claim(
            worker=worker,
            pools=pools,
            owner=effective_owner,
            day_from=body.day_from,
            day_to=body.day_to,
            limit=body.limit,
        )
        return [asdict(b) for b in bundles]

    @app.post("/v1/jobs/{job_id}/heartbeat")
    def job_heartbeat(
        job_id: str,
        body: HeartbeatIn,
        request: Request,
        auth: AuthInfo = Depends(require_auth),
    ) -> dict[str, bool]:
        _check_job_access(database, auth, job_id)
        jobs = _get_jobs(request.app)
        ok = bool(jobs.heartbeat(job_id, body.fence_token))
        return {"ok": ok}

    @app.post("/v1/jobs/{job_id}/result")
    def job_result(
        job_id: str,
        body: AttemptIn,
        request: Request,
        auth: AuthInfo = Depends(require_auth),
    ) -> dict[str, Any]:
        if auth.role == "owner-device" and body.worker_kind != "owner-hook":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="owner-device token must report worker_kind='owner-hook'",
            )
        _check_job_access(database, auth, job_id)
        attempt = _deserialize_attempt(job_id, body)
        jobs = _get_jobs(request.app)
        verdict = jobs.submit(attempt)
        return asdict(verdict)

    _mount_optional_routers(app, database, store, verify_token)
    return app
