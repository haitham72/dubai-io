"""Owner-authenticated source consent and real-data ingest."""
from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import RLock
from typing import Annotated, Literal
from urllib.parse import urlsplit, urlunsplit
import importlib
import logging
import os
import sys
import zipfile

import httpx
import psycopg
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, Field

from .config import settings
from .connectors import e3_google
from .connectors.crypto import cipher_for
from .connectors.e3_oauth import GoogleAuth
from .connectors.e3_store import Bridge, State, measured, utcnow
from .identity.deps import get_identity_service, require_app_principal
from .identity.memory_tokens import MemoryTokenService
from .identity.models import IdentityError, VerifiedPrincipal
from .memory_bridge.client import HttpTemporalMemoryClient
from .memory_bridge.models import MemoryBridgeError

Source = Literal["gmail", "calendar", "youtube", "takeout", "whatsapp", "browser", "agent_sessions"]
GoogleSource = Literal["gmail", "calendar", "youtube"]
DesktopSource = Literal["browser", "agent_sessions"]
Principal = Annotated[VerifiedPrincipal, Depends(require_app_principal("quest", frozenset({"memory:device_token"})))]
router = APIRouter(prefix="/api/ingest", tags=["ingest"])
_setup_lock = RLock()

_CALLBACK_PATH = "/api/ingest/google/callback"


class _CallbackQueryFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Uvicorn's access record includes the URL including single-use OAuth credentials.
        args = record.args
        if isinstance(args, tuple) and len(args) == 5 and str(args[2]).startswith(f"{_CALLBACK_PATH}?"):
            record.args = (*args[:2], _CALLBACK_PATH, *args[3:])
        return True


logging.getLogger("uvicorn.access").addFilter(_CallbackQueryFilter())


class Consent(BaseModel):
    enabled: bool


class DesktopRecord(BaseModel):
    id: str = Field(min_length=1, max_length=256)
    at: str = Field(min_length=10, max_length=50)
    text: str = Field(min_length=1, max_length=8000)


class DesktopBatch(BaseModel):
    records: list[DesktopRecord] = Field(min_length=1, max_length=500)


class Ingest:
    def __init__(self, state, bridge, auth, *, google_transport=None):
        self.state, self.bridge, self.auth = state, bridge, auth
        self.google_transport = google_transport

    def require(self, owner, source):
        with self.state.connection() as conn:
            return self.state.require(conn, owner, source)

    def commit(self, owner, source, revision, records, *, device_token=None):
        rules = _memory_module("live.triples")
        safe = [record for record in records if not rules.quarantine_category(record["text"])]
        now = utcnow()
        with self.state.lock(owner, source) as conn:
            self.state.require(conn, owner, source, revision)
            imported, skipped, jobs = self.bridge.ingest(conn, owner, safe, device_token=device_token)
            self.state.mark_pulled(conn, owner, source, now)
        return {
            "source": source, "records_added": measured(imported, now=now),
            "records_already_seen": measured(skipped, now=now), "jobs_enqueued": measured(jobs, now=now),
            "held_back": measured(len(records) - len(safe), now=now),
        }


def get_ingest(request: Request) -> Ingest:
    with _setup_lock:
        current = getattr(request.app.state, "e3_ingest", None)
        if current is not None:
            return current

        base_url = os.environ.get("TM_BASE_URL", "").strip().rstrip("/")
        if not base_url:
            raise HTTPException(503, "The memory service is not configured")
        target = os.environ.get("TM_DATABASE_URL", "postgresql://tm:tm@localhost:5442/tm")
        try:
            state = State(target, cipher_for())
        except (psycopg.Error, ValueError, OSError) as exc:
            raise HTTPException(503, "Ingest storage is unavailable") from exc

        memory = getattr(request.app.state, "memory_token_service", None)
        if memory is None:
            identity = get_identity_service(request)
            admin = HttpTemporalMemoryClient(
                base_url=base_url, service_token=os.environ.get("TM_SERVICE_TOKEN", ""),
                admin_token=os.environ.get("TM_ADMIN_TOKEN") or None,
            )
            memory = MemoryTokenService(identity.store, admin)

        def owner_token(owner):
            try:
                return memory.ensure_bridge_token(owner)
            except (MemoryBridgeError, IdentityError) as exc:
                raise HTTPException(503, "Could not authorize this owner with memory") from exc

        redirect = os.environ.get("GOOGLE_INGEST_REDIRECT_URI", "").strip()
        if not redirect and settings.google_oauth_redirect_uri:
            origin = urlsplit(settings.google_oauth_redirect_uri)
            redirect = urlunsplit((origin.scheme, origin.netloc, _CALLBACK_PATH, "", ""))
        auth = GoogleAuth(state, settings.google_oauth_client_id, settings.google_oauth_client_secret, redirect)
        request.app.state.e3_ingest = Ingest(state, Bridge(base_url, owner_token), auth)
        return request.app.state.e3_ingest


Service = Annotated[Ingest, Depends(get_ingest)]


@lru_cache
def _memory_module(name):
    try:
        return importlib.import_module(f"temporal_memory.{name}")
    except ModuleNotFoundError as exc:
        if exc.name != "temporal_memory":
            raise
        source = Path(__file__).resolve().parents[2] / "memory" / "src"
        if not (source / "temporal_memory").is_dir():
            raise HTTPException(503, "Install the temporal_memory package for source ingest") from exc
        with _setup_lock:
            if str(source) not in sys.path:
                sys.path.insert(0, str(source))
            return importlib.import_module(f"temporal_memory.{name}")


@router.put("/consent/{source}")
def consent(source: Source, body: Consent, principal: Principal, ingest: Service):
    with ingest.state.lock(principal.user_id, source) as conn:
        ingest.state.set_consent(conn, principal.user_id, source, body.enabled)
    return {"source": source, "enabled": body.enabled}


@router.post("/google/{source}/connect")
def connect_google(source: GoogleSource, principal: Principal, ingest: Service, response: Response):
    owner = principal.user_id
    with ingest.state.lock(owner, source) as conn:
        row = ingest.state.require(conn, owner, source)
        url = ingest.auth.start(owner, source, row["revision"], principal.session_id)
    response.headers["Cache-Control"] = "no-store"
    return {"source": source, "authorization_url": url}


@router.get("/google/callback")
def google_callback(principal: Principal, ingest: Service, response: Response, state: str, code: str | None = None):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    if not code:
        ingest.state.consume_attempt(principal.user_id, state)
        raise HTTPException(400, "Google authorization was declined or cancelled")
    source = ingest.auth.finish(principal.user_id, principal.session_id, state, code)
    return {"source": source, "connected": True}


@router.post("/google/{source}/pull")
def pull_google(source: GoogleSource, principal: Principal, ingest: Service):
    owner = principal.user_id
    row = ingest.require(owner, source)
    before = ingest.state.grant(row)
    grant = ingest.auth.access(before, source)
    try:
        records = e3_google.pull(source, grant["access_token"], utcnow(), transport=ingest.google_transport)
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise HTTPException(502, "Google source is temporarily unavailable") from exc
    if grant != before:
        with ingest.state.lock(owner, source) as conn:
            current = ingest.state.require(conn, owner, source, row["revision"])
            if current["grant_cipher"] == row["grant_cipher"]:
                ingest.state.save_grant(conn, owner, source, grant)
    return ingest.commit(owner, source, row["revision"], records)


def _upload(upload, principal, ingest, source, extension, limit):
    owner = principal.user_id
    row = ingest.require(owner, source)
    filename = upload.filename or ""
    if not filename.lower().endswith(extension):
        raise HTTPException(400, f"Upload a {extension} file")
    try:
        with TemporaryDirectory(prefix="dubaiio-ingest-") as temp:
            target = Path(temp) / f"upload{extension}"
            size = 0
            with target.open("wb") as handle:
                while chunk := upload.file.read(1024 * 1024):
                    size += len(chunk)
                    if size > limit:
                        raise HTTPException(413, "Upload exceeds the source size limit")
                    handle.write(chunk)
            if source == "takeout":
                imported = _memory_module("ingest.takeout").takeout_records(owner, target)
            else:
                basename = filename.replace("\\", "/").rsplit("/", 1)[-1].casefold()
                chat = sha256(basename.encode()).hexdigest()[:16]
                imported = _memory_module("ingest.whatsapp").parse_whatsapp_file(target, owner, source_name=chat)
    except (ValueError, UnicodeError, OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise HTTPException(400, f"Invalid {source} export") from exc
    if not imported:
        raise HTTPException(422, f"No supported records were found in the {source} export")

    records = []
    for item in imported:
        fingerprint = sha256(f"{item.source}\0{item.at}\0{item.author}\0{item.text}".encode()).hexdigest()
        records.append({"id": f"e3:{source}:{fingerprint}", "source": item.source, "at": item.at,
                        "author": item.author, "text": item.text[:8000]})
    return ingest.commit(owner, source, row["revision"], records)


@router.post("/takeout")
def upload_takeout(file: UploadFile, principal: Principal, ingest: Service):
    return _upload(file, principal, ingest, "takeout", ".zip", 100 * 1024 * 1024)


@router.post("/whatsapp")
def upload_whatsapp(file: UploadFile, principal: Principal, ingest: Service):
    return _upload(file, principal, ingest, "whatsapp", ".txt", 15 * 1024 * 1024)


@router.post("/desktop/{source}")
def desktop_ingest(
    source: DesktopSource, body: DesktopBatch, principal: Principal, ingest: Service,
    device_token: Annotated[str, Header(alias="X-Memory-Device-Token", min_length=1, max_length=512)],
):
    owner = principal.user_id
    row = ingest.require(owner, source)
    ingest.bridge.request(owner, "GET", "onboarding-status", device_token=device_token)
    prefix = "browser" if source == "browser" else "agent:desktop"
    records = [
        {"id": f"e3:{source}:{sha256(item.id.encode()).hexdigest()}", "source": prefix,
         "at": item.at, "text": item.text, "author": "desktop"}
        for item in body.records
    ]
    return ingest.commit(owner, source, row["revision"], records, device_token=device_token)


@router.post("/{source}/lower")
@router.delete("/{source}/data", include_in_schema=False)
def lower_source(source: Source, principal: Principal, ingest: Service):
    return _source_weight(source, principal, ingest, "lower")


@router.post("/{source}/restore")
def restore_source(source: Source, principal: Principal, ingest: Service):
    return _source_weight(source, principal, ingest, "restore")


def _source_weight(source: Source, principal: VerifiedPrincipal, ingest: Ingest, action: str):
    owner = principal.user_id
    with ingest.state.lock(owner, source):
        result = ingest.bridge.request(owner, "POST", action, body={"source": source})
    from .today_feed import clear_today_cache
    clear_today_cache(owner)
    return {"source": source, "lowered": action == "lower", "records": measured(result["records"])}


@router.get("/status")
def status(principal: Principal, ingest: Service):
    from .connectors.e3_store import SOURCES

    owner = principal.user_id
    now = utcnow()
    progress = ingest.bridge.request(owner, "GET", "onboarding-status")
    with ingest.state.connection() as conn:
        metrics = {source: ingest.state.statistics(conn, owner, source, now) for source in SOURCES}
        recent = conn.execute(
            """
            SELECT a.worker_kind,COALESCE(a.model_observed,a.model) AS model
            FROM job_attempts a JOIN jobs j ON j.id=a.job_id AND j.owner=a.owner
            WHERE a.owner=%s AND j.kind='extract.day' ORDER BY a.finished_at DESC LIMIT 1
            """, (owner,),
        ).fetchone()
        total = conn.execute(
            """SELECT COALESCE(sum(a.cost_usd),0) AS cost FROM job_attempts a
               JOIN jobs j ON j.id=a.job_id AND j.owner=a.owner WHERE a.owner=%s AND j.kind='extract.day'""",
            (owner,),
        ).fetchone()["cost"]
    configured = os.environ.get("TM_WORKER_RUNNER") or None
    runner = {"internal-local": "lmstudio", "internal-cloud": "anthropic",
              "owner-hook": "owner-hook", "agent-cli": "agent-cli"}
    estimate = float(total) if configured in {"claude-cli", "lmstudio"} else None
    return {
        "sources": metrics,
        "onboarding_percent": measured(progress.get("completeness_pct"), now=now),
        "runner": runner.get(recent["worker_kind"]) if recent else None,
        "model": recent["model"] if recent else None,
        "configured_runner": configured,
        "recorded_backfill_cost_usd": measured(float(total), now=now),
        "estimated_backfill_cost_usd": measured(estimate, provenance="estimate", now=now),
    }
