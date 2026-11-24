"""Incremental Google authorization for consented E3 sources."""
from __future__ import annotations

import base64
from datetime import timedelta
from hashlib import sha256
import secrets
import time
from urllib.parse import urlencode, urlsplit

from fastapi import HTTPException
import httpx

from ..oauth import AUTH_URL, TOKEN_URL, USERINFO_URL, token_expiry
from .e3_google import SCOPES
from .e3_store import utcnow


class GoogleAuth:
    def __init__(self, store, client_id, secret, redirect_uri, *, transport=None):
        self.store = store
        self.client_id, self.secret, self.redirect_uri = client_id, secret, redirect_uri
        self.transport = transport

    def _check_config(self):
        try:
            uri = urlsplit(self.redirect_uri)
            port = uri.port
            valid_origin = uri.scheme == "https" or (uri.scheme == "http" and uri.hostname in {"localhost", "127.0.0.1"})
            valid = valid_origin and uri.hostname and (port is None or port > 0)
        except ValueError:
            valid = False
        if (not valid or not self.client_id or not self.secret or uri.username or uri.password or uri.query
                or uri.fragment or uri.path != "/api/ingest/google/callback"):
            raise HTTPException(503, "Google source OAuth is not configured")

    def start(self, owner, source, revision, session_id):
        self._check_config()
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(48)
        challenge = base64.urlsafe_b64encode(sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        self.store.authorize_attempt(owner, state, {
            "source": source, "revision": revision, "session_id": session_id, "verifier": verifier,
            "client_id": self.client_id, "redirect_uri": self.redirect_uri,
        }, utcnow() + timedelta(minutes=10))
        return AUTH_URL + "?" + urlencode({
            "client_id": self.client_id, "redirect_uri": self.redirect_uri, "response_type": "code",
            "scope": f"openid {SCOPES[source]}", "state": state, "access_type": "offline",
            "include_granted_scopes": "true", "prompt": "consent", "code_challenge": challenge,
            "code_challenge_method": "S256",
        })

    def _token(self, client, form):
        try:
            response = client.post(TOKEN_URL, data={
                **form, "client_id": self.client_id, "client_secret": self.secret,
            })
            response.raise_for_status()
            token = response.json()
            if (not isinstance(token, dict) or not token.get("access_token")
                    or token.get("token_type", "").lower() != "bearer"):
                raise ValueError("invalid bearer grant")
            return token
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise HTTPException(502, "Google authorization failed; check or reconnect the source") from exc

    def finish(self, owner, session_id, state, code):
        self._check_config()
        attempt = self.store.consume_attempt(owner, state)
        if (attempt["session_id"] != session_id or attempt["client_id"] != self.client_id
                or attempt["redirect_uri"] != self.redirect_uri):
            raise HTTPException(400, "Google authorization belongs to another session or configuration")
        source, revision = attempt["source"], attempt["revision"]
        with self.store.connection() as conn:
            self.store.require(conn, owner, source, revision)
        with httpx.Client(timeout=15, transport=self.transport) as client:
            token = self._token(client, {
                "code": code, "grant_type": "authorization_code", "redirect_uri": self.redirect_uri,
                "code_verifier": attempt["verifier"],
            })
            scopes = set(token.get("scope", f"openid {SCOPES[source]}").split())
            if not {"openid", SCOPES[source]}.issubset(scopes):
                raise HTTPException(403, "Google did not grant the source scope")
            try:
                info = client.get(USERINFO_URL, headers={"Authorization": f"Bearer {token['access_token']}"})
                info.raise_for_status()
                subject = info.json().get("sub")
                if not isinstance(subject, str) or not subject:
                    raise ValueError("invalid subject")
            except (httpx.HTTPError, ValueError, TypeError) as exc:
                raise HTTPException(502, "Google account identity could not be verified") from exc
        with self.store.lock(owner, source) as conn:
            row = self.store.require(conn, owner, source, revision)
            with conn.transaction():
                conn.execute(
                    "INSERT INTO e3_ingest_google_accounts (owner,subject) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                    (owner, subject),
                )
                bound = conn.execute("SELECT subject FROM e3_ingest_google_accounts WHERE owner=%s", (owner,)).fetchone()
                if not bound or bound["subject"] != subject:
                    raise HTTPException(409, "This Google account cannot be connected to this Quest owner")
                previous = self.store.grant(row) or {}
                refresh = token.get("refresh_token") or previous.get("refresh_token")
                self.store.save_grant(conn, owner, source, {
                    "access_token": token["access_token"], "refresh_token": refresh,
                    "expires": token_expiry(token), "scopes": sorted(scopes),
                    "client_id": self.client_id, "subject": subject,
                })
        return source

    def access(self, grant, source):
        self._check_config()
        scope = SCOPES[source]
        if not grant or grant.get("client_id") != self.client_id or scope not in grant["scopes"]:
            raise HTTPException(409, "Connect Google for this source first")
        if grant["expires"] > time.time() + 30:
            return grant
        if not grant.get("refresh_token"):
            raise HTTPException(409, "Google authorization expired; reconnect the source")
        with httpx.Client(timeout=15, transport=self.transport) as client:
            token = self._token(client, {"refresh_token": grant["refresh_token"], "grant_type": "refresh_token"})
        scopes = token.get("scope", " ".join(grant["scopes"])).split()
        if scope not in scopes:
            raise HTTPException(403, "Google no longer grants the source scope")
        return {
            **grant, "scopes": scopes, "access_token": token["access_token"],
            "refresh_token": token.get("refresh_token") or grant["refresh_token"], "expires": token_expiry(token),
        }
