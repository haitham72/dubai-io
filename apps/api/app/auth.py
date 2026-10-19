"""Provider connection metadata and configured Google browser OAuth flow."""
import json
import secrets
from threading import RLock
from typing import Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx
from pydantic import BaseModel

from .actions import COOKIE, engine
from .config import settings
from .oauth import GoogleOAuth, local_key, valid_redirect

router = APIRouter(prefix="/api/auth", tags=["connections"])


class ConnectionProvider(BaseModel):
    id: str
    label: str
    status: Literal["not_configured", "disconnected", "connected"]
    can_connect: bool
    scopes: list[str]
    account_label: str | None = None


class ConnectionsOut(BaseModel):
    providers: list[ConnectionProvider]


_google = None
_google_lock = RLock()


def configured():
    return bool(settings.google_oauth_client_id and settings.google_oauth_client_secret and valid_redirect(settings.google_oauth_redirect_uri))


def same_host(request):
    callback = urlsplit(settings.google_oauth_redirect_uri)
    current = urlsplit(str(request.base_url))
    return (callback.scheme, callback.hostname, callback.port or (443 if callback.scheme == "https" else 80)) == (current.scheme, current.hostname, current.port or (443 if current.scheme == "https" else 80))


def google():
    global _google
    with _google_lock:
        if _google is None:
            try:
                _google = GoogleOAuth(engine().store, settings.google_oauth_client_id, settings.google_oauth_client_secret,
                    settings.google_oauth_redirect_uri, local_key(settings.data_dir / "oauth.key", settings.oauth_token_key))
            except (ValueError, OSError):
                raise HTTPException(503, "Google OAuth configuration or token encryption key is invalid")
        return _google


def require_google(request):
    if not configured() or not same_host(request):
        raise HTTPException(503, "Google OAuth is not configured for this app origin")
    return google()


@router.get("/connections", response_model=ConnectionsOut)
def connections(request: Request):
    provider = {"id": "google", "label": "Google", "status": "not_configured", "can_connect": False,
                "scopes": ["openid", "email", "profile"], "account_label": None}
    if configured() and same_host(request):
        try:
            owner = engine().store.owner(request.cookies.get(COOKIE))
            provider = google().metadata(owner)
        except HTTPException as error:
            if error.status_code != 401:
                raise
            provider.update(status="disconnected", can_connect=True)
    return ConnectionsOut(providers=[ConnectionProvider(**provider)])


@router.get("/{provider}/start")
def start(provider: str, request: Request):
    if provider != "google":
        raise HTTPException(404, "Unknown connection provider")
    connector = require_google(request)
    owner, token = engine().store.session(request.cookies.get(COOKIE))
    response = RedirectResponse(connector.start(owner), status_code=302)
    if token:
        response.set_cookie(COOKIE, token, httponly=True, samesite="lax", secure=request.url.scheme == "https", max_age=30*86400)
    return response


@router.get("/google/callback")
async def callback(request: Request, state: str = "", code: str = "", error: str = ""):
    connector = require_google(request)
    if error or not state or not code or len(state) > 200 or len(code) > 4000:
        raise HTTPException(400, "Google sign-in was not completed")
    owner = engine().store.owner(request.cookies.get(COOKIE))
    try:
        await connector.callback(owner, state, code)
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502, "Google sign-in could not be completed; start again")
    nonce = secrets.token_urlsafe(24)
    origin = json.dumps(str(request.base_url).rstrip("/"))
    # The callback carries a refresh signal only; no grant, code or token in HTML.
    html = '<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>Google connected</title><p>Google is connected. Return to Dubai-io.</p><button id="done">Return to Dubai-io</button><script nonce="' + nonce + '">if(window.opener){window.opener.postMessage({kind:"auth.complete",provider:"google"},' + origin + ');}document.querySelector("#done").onclick=()=>window.close();</script>'
    return HTMLResponse(html, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": "default-src 'none'; script-src 'nonce-" + nonce + "'; frame-ancestors 'none'; base-uri 'none'"})


@router.post("/{provider}/disconnect")
async def disconnect(provider: str, request: Request):
    if provider != "google":
        raise HTTPException(404, "Unknown connection provider")
    connector = require_google(request)
    if request.headers.get("origin") and request.headers["origin"] != str(request.base_url).rstrip("/"):
        raise HTTPException(403, "Invalid app origin")
    try:
        return await connector.disconnect(engine().store.owner(request.cookies.get(COOKIE)))
    except httpx.HTTPError:
        raise HTTPException(502, "Google revocation could not be completed; try again")
