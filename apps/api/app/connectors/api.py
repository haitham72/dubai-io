"""HTTP surface. Cookie owner, same as the rest of the API. Tokens are never returned."""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..actions import COOKIE, engine
from .service import ConnectorService
from .store import ConnectorStore
from .types import AuthFailed, ConnectorError, DisabledConnector, PermissionDenied, PermanentFailure, RateLimited, TransientFailure, UnavailableConnector

router = APIRouter(prefix="/api/connectors", tags=["connectors"])


class ConnectIn(BaseModel):
    credentials: dict[str, str | int] = Field(default_factory=dict)


class ImportIn(BaseModel):
    filename: str = Field(default="import", max_length=200)
    content: str = Field(max_length=500_000)


class OutboundIn(BaseModel):
    action: str = Field(max_length=40)
    payload: dict[str, str]


class DecideIn(BaseModel):
    approve: bool


def _service() -> ConnectorService:
    return ConnectorService(ConnectorStore(engine().store.db))


def _owner(request: Request) -> str:
    return engine().store.owner(request.cookies.get(COOKIE))


def _raise(exc: ConnectorError) -> None:
    if isinstance(exc, PermissionDenied):
        status = 403
    elif isinstance(exc, AuthFailed):
        status = 401
    elif isinstance(exc, (UnavailableConnector, DisabledConnector)):
        status = 409
    elif isinstance(exc, RateLimited):
        status = 429
    elif isinstance(exc, TransientFailure):
        status = 503
    elif isinstance(exc, PermanentFailure) and str(exc) == "Unknown connector":
        status = 404
    else:
        status = 422
    raise HTTPException(status, str(exc)) from None


@router.get("")
def list_connectors(request: Request):
    return {"connectors": _service().list_connectors(_owner(request))}


@router.post("/hooks/{connector_id}/{hook_id}")
def webhook(connector_id: str, hook_id: str, payload: dict, x_connector_secret: str = Header(default="")):
    try:
        return _service().ingest_webhook(connector_id, hook_id, x_connector_secret, payload)
    except ConnectorError as exc:
        _raise(exc)


@router.post("/grants/{grant_id}")
def decide(grant_id: str, body: DecideIn, request: Request):
    try:
        return _service().decide_outbound(_owner(request), grant_id, body.approve)
    except ConnectorError as exc:
        _raise(exc)


@router.get("/{connector_id}")
def detail(connector_id: str, request: Request):
    try:
        return _service().describe(connector_id, _owner(request))
    except ConnectorError as exc:
        _raise(exc)


@router.get("/{connector_id}/health")
def health(connector_id: str, request: Request):
    try:
        return _service().health(_owner(request), connector_id)
    except ConnectorError as exc:
        _raise(exc)


@router.get("/{connector_id}/records")
def records(connector_id: str, request: Request, limit: int = Query(default=50, ge=1, le=100)):
    try:
        return _service().records(_owner(request), connector_id, limit)
    except ConnectorError as exc:
        _raise(exc)


@router.post("/{connector_id}/connect")
def connect(connector_id: str, body: ConnectIn, request: Request):
    if len(repr(body.credentials)) > 8000:
        raise HTTPException(422, "Credentials are too large")
    try:
        return _service().connect(_owner(request), connector_id, dict(body.credentials))
    except ConnectorError as exc:
        _raise(exc)


@router.post("/{connector_id}/sync")
def sync(connector_id: str, request: Request, force: bool = False):
    try:
        return _service().sync(_owner(request), connector_id, force=force)
    except ConnectorError as exc:
        _raise(exc)


@router.post("/{connector_id}/import")
def import_file(connector_id: str, body: ImportIn, request: Request):
    try:
        return _service().import_file(_owner(request), connector_id, body.filename, body.content)
    except ConnectorError as exc:
        _raise(exc)


@router.post("/{connector_id}/disconnect")
def disconnect(connector_id: str, request: Request):
    try:
        return _service().disconnect(_owner(request), connector_id)
    except ConnectorError as exc:
        _raise(exc)


@router.post("/{connector_id}/revoke")
def revoke(connector_id: str, request: Request):
    try:
        return _service().revoke(_owner(request), connector_id)
    except ConnectorError as exc:
        _raise(exc)


@router.delete("/{connector_id}/data")
def delete_data(connector_id: str, request: Request):
    try:
        return _service().delete_user_data(_owner(request), connector_id)
    except ConnectorError as exc:
        _raise(exc)


@router.post("/{connector_id}/reconnect")
def reconnect(connector_id: str, request: Request):
    try:
        return _service().reconnect(_owner(request), connector_id)
    except ConnectorError as exc:
        _raise(exc)


@router.post("/{connector_id}/outbound")
def propose(connector_id: str, body: OutboundIn, request: Request):
    try:
        return _service().propose_outbound(_owner(request), connector_id, body.action, body.payload)
    except ConnectorError as exc:
        _raise(exc)


@router.post("/{connector_id}/outbound/{grant_id}")
def execute(connector_id: str, grant_id: str, body: OutboundIn, request: Request):
    try:
        return _service().execute_outbound(_owner(request), connector_id, grant_id, body.payload)
    except ConnectorError as exc:
        _raise(exc)
