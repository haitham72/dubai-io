"""CM-B6 media: local object storage, HMAC signed URLs, per-user quotas.

Owner comes from the cookie session; callers never set owner/provenance.
Uploaded content is ``user_supplied``. Bytes live under ``CM_MEDIA_DIR``
(default: a temp subdir); metadata lives in ``cm_media``. Signing secret
comes from ``CM_MEDIA_SECRET`` (env only; dev-only fallback for local runs).
No external storage, no messenger, no branding.
"""
import base64
import hashlib
import hmac
import os
import tempfile
import time
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from ..actions import engine
from . import store as cm

router = APIRouter(tags=["community-media"])

DDL = (
    """CREATE TABLE IF NOT EXISTS cm_media (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL, post_id TEXT,
        filename TEXT NOT NULL, content_type TEXT NOT NULL DEFAULT 'application/octet-stream',
        size INTEGER NOT NULL DEFAULT 0, storage_key TEXT NOT NULL,
        provenance TEXT NOT NULL DEFAULT 'user_supplied',
        created_at TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS cm_media_owner ON cm_media(owner, created_at)",
)

_DEFAULT_QUOTA = 1_048_576  # 1 MiB per user
_DEFAULT_MAX_FILE = 524_288  # 512 KiB per file
_DEV_SECRET = "dev-only-cm-media-secret"


def setup(store):
    if getattr(store, "_media_ready", False):
        return
    for statement in DDL:
        store.db.execute(statement)
    store.db.commit()
    store._media_ready = True


def _media_dir() -> Path:
    raw = os.environ.get("CM_MEDIA_DIR") or str(Path(tempfile.gettempdir()) / "dubaiio-cm-media")
    path = Path(raw)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _secret() -> bytes:
    return (os.environ.get("CM_MEDIA_SECRET") or _DEV_SECRET).encode("utf-8")


def _quota_bytes() -> int:
    try:
        return max(0, int(os.environ.get("CM_MEDIA_QUOTA_BYTES") or _DEFAULT_QUOTA))
    except ValueError:
        return _DEFAULT_QUOTA


def _max_file_bytes() -> int:
    try:
        return max(0, int(os.environ.get("CM_MEDIA_MAX_FILE_BYTES") or _DEFAULT_MAX_FILE))
    except ValueError:
        return _DEFAULT_MAX_FILE


def _scope(request: Request):
    from .routes import scope
    return scope(request)


def _sign(media_id: str, exp: int) -> str:
    msg = f"{media_id}:{exp}".encode("utf-8")
    return hmac.new(_secret(), msg, hashlib.sha256).hexdigest()


def _verify(media_id: str, token: str, exp: int) -> bool:
    if not token or exp <= int(time.time()):
        return False
    return hmac.compare_digest(_sign(media_id, exp), token)


def _row(store, media_id: str):
    return store.db.execute(
        "SELECT id,owner,post_id,filename,content_type,size,storage_key,provenance,created_at FROM cm_media WHERE id=?",
        (media_id,)).fetchone()


def _present(row):
    mid, owner, post_id, filename, content_type, size, storage_key, prov, created = row
    return {"id": mid, "owner": owner, "post_id": post_id, "filename": filename,
            "content_type": content_type, "size": size, "storage_key": storage_key,
            "provenance": prov, "as_of": created, "created_at": created}


def _owned_row(store, owner, media_id):
    row = _row(store, media_id)
    if not row or row[1] != owner:
        raise HTTPException(404, "Media not found")
    return row


class MediaIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    filename: str = Field(default="upload.bin", max_length=200)
    content_type: str = Field(default="application/octet-stream", max_length=120)
    content: str | None = Field(default=None, max_length=4_000_000)
    content_base64: str | None = Field(default=None, max_length=4_000_000)
    post_id: str | None = Field(default=None, max_length=100)


@router.post("/api/community/media")
def upload_media(body: MediaIn, request: Request):
    store, owner = _scope(request)
    raw_b64 = body.content_base64 if body.content_base64 is not None else body.content
    if raw_b64 is None or raw_b64 == "":
        raise HTTPException(400, "content (base64) is required")
    try:
        data = base64.b64decode(raw_b64, validate=True)
    except Exception:
        raise HTTPException(400, "content is not valid base64")
    if not data:
        raise HTTPException(400, "content is empty")
    max_file = _max_file_bytes()
    if len(data) > max_file:
        raise HTTPException(413, f"File too large: {len(data)} bytes exceeds max file size {max_file} bytes")
    filename = Path((body.filename or "upload.bin").strip()).name or "upload.bin"
    content_type = (body.content_type or "application/octet-stream").strip() or "application/octet-stream"
    with store.lock:
        cm.setup(store)
        setup(store)
        used = store.db.execute(
            "SELECT COALESCE(SUM(size),0) FROM cm_media WHERE owner=?", (owner,)).fetchone()[0]
        quota = _quota_bytes()
        if int(used) + len(data) > quota:
            raise HTTPException(
                429, f"Media quota exceeded: used {int(used)} of {quota} bytes; "
                     f"upload of {len(data)} bytes would exceed quota")
        media_id = uuid4().hex
        storage_key = media_id
        dest = _media_dir() / storage_key
        dest.write_bytes(data)
        stamp = cm.now()
        store.db.execute(
            "INSERT INTO cm_media (id,owner,post_id,filename,content_type,size,storage_key,provenance,created_at) VALUES (?,?,?,?,?,?,?,'user_supplied',?)",
            (media_id, owner, body.post_id, filename, content_type, len(data), storage_key, stamp))
        store.db.commit()
        return {"media": _present(_row(store, media_id))}


@router.get("/api/community/media/{media_id}")
def media_metadata(media_id: str, request: Request):
    store, owner = _scope(request)
    with store.lock:
        cm.setup(store)
        setup(store)
        return {"media": _present(_owned_row(store, owner, media_id))}


@router.get("/api/community/media/{media_id}/signed")
def signed_url(media_id: str, request: Request, expires: int = Query(default=300, ge=1, le=86400)):
    store, owner = _scope(request)
    with store.lock:
        cm.setup(store)
        setup(store)
        _owned_row(store, owner, media_id)
    exp = int(time.time()) + int(expires)
    token = _sign(media_id, exp)
    url = f"/api/community/media/{media_id}/content?token={token}&exp={exp}"
    return {"url": url, "token": token, "exp": exp, "expires_at": exp, "expires_in": int(expires)}


@router.get("/api/community/media/{media_id}/content")
def media_content(media_id: str, token: str = Query(default=""), exp: int = Query(default=0)):
    if not _verify(media_id, token, exp):
        raise HTTPException(403, "Invalid or expired media signature")
    store = engine().store
    with store.lock:
        cm.setup(store)
        setup(store)
        row = _row(store, media_id)
        if not row:
            raise HTTPException(404, "Media not found")
    path = _media_dir() / row[6]
    if not path.is_file():
        raise HTTPException(404, "Media content not found")
    return Response(content=path.read_bytes(), media_type=row[4] or "application/octet-stream")
