"""Google server flow. Credentials/grants never leave this module for cards."""
import asyncio
import base64
from hashlib import sha256
import json
import secrets
import time
from urllib.parse import urlencode, urlsplit

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
import httpx

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
SCOPES = ("openid", "email", "profile")

def token_expiry(token):
    lifetime = token.get("expires_in")
    if not isinstance(lifetime, int) or isinstance(lifetime, bool) or lifetime <= 0:
        raise HTTPException(502, "Google returned an invalid token expiry")
    return time.time() + lifetime


def valid_redirect(uri):
    try:
        url = urlsplit(uri)
        port = url.port  # validate malformed ports before exposing a Connect control
        if port is not None and not 1 <= port <= 65535:
            return False
        return bool(url.hostname and not url.username and not url.password and not url.query and not url.fragment
                    and url.path == "/api/auth/google/callback"
                    and (url.scheme == "https" or url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1"}))
    except ValueError:
        return False


def local_key(path, configured_key=""):
    if configured_key:
        return configured_key.encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as file:
            file.write(Fernet.generate_key())
        path.chmod(0o600)
    except FileExistsError:
        pass
    return path.read_bytes()


class GoogleOAuth:
    def __init__(self, store, client_id, secret, redirect_uri, key, transport=None):
        if not client_id or not secret or not valid_redirect(redirect_uri):
            raise ValueError("Google OAuth configuration is incomplete")
        self.store, self.client_id, self.secret, self.redirect_uri = store, client_id, secret, redirect_uri
        self.cipher, self.transport = Fernet(key), transport
        self.refresh_locks = {}
        with store.lock:
            store.db.execute("CREATE TABLE IF NOT EXISTS oauth_attempts (state_hash TEXT PRIMARY KEY, owner TEXT, expires REAL, data BLOB)")
            store.db.execute("CREATE TABLE IF NOT EXISTS oauth_grants (owner TEXT, provider TEXT, data BLOB, PRIMARY KEY(owner,provider))")
            store.db.commit()

    def client(self):
        return httpx.AsyncClient(timeout=15, transport=self.transport, follow_redirects=False)

    def start(self, owner):
        state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
        challenge = base64.urlsafe_b64encode(sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        payload = self.cipher.encrypt(json.dumps({"verifier": verifier, "client_id": self.client_id, "redirect_uri": self.redirect_uri}).encode())
        with self.store.lock:
            self.store.db.execute("DELETE FROM oauth_attempts WHERE expires < ?", (time.time(),))
            self.store.db.execute("INSERT INTO oauth_attempts VALUES (?,?,?,?)", (sha256(state.encode()).hexdigest(), owner, time.time()+600, payload))
            self.store.db.commit()
        return AUTH_URL + "?" + urlencode({"client_id": self.client_id, "redirect_uri": self.redirect_uri, "response_type": "code",
            "scope": " ".join(SCOPES), "state": state, "access_type": "offline", "prompt": "consent",
            "code_challenge": challenge, "code_challenge_method": "S256"})

    async def callback(self, owner, state, code):
        with self.store.lock:
            row = self.store.db.execute("SELECT owner,expires,data FROM oauth_attempts WHERE state_hash=?", (sha256(state.encode()).hexdigest(),)).fetchone()
            if not row or row[0] != owner or row[1] < time.time():
                raise HTTPException(400, "Sign-in attempt expired or does not match this session")
            attempt = json.loads(self.cipher.decrypt(row[2]))
            if attempt["client_id"] != self.client_id or attempt["redirect_uri"] != self.redirect_uri:
                raise HTTPException(400, "Sign-in configuration changed; start again")
            self.store.db.execute("DELETE FROM oauth_attempts WHERE state_hash=?", (sha256(state.encode()).hexdigest(),))
            self.store.db.commit()  # consume once before exchanging any code
        async with self.client() as client:
            response = await client.post(TOKEN_URL, data={"client_id": self.client_id, "client_secret": self.secret,
                "redirect_uri": self.redirect_uri, "code_verifier": attempt["verifier"], "code": code, "grant_type": "authorization_code"})
            if not response.is_success:
                raise HTTPException(502, "Google did not complete sign-in")
            token = response.json()
            if not isinstance(token.get("access_token"), str) or token.get("token_type", "").lower() != "bearer":
                raise HTTPException(502, "Google returned an invalid grant")
            profile = await client.get(USERINFO_URL, headers={"Authorization": "Bearer " + token["access_token"]})
            if not profile.is_success:
                raise HTTPException(502, "Google account could not be verified")
            user = profile.json()
            if not isinstance(user.get("sub"), str) or not user["sub"]:
                raise HTTPException(502, "Google account could not be verified")
        previous = self.grant(owner)
        if previous and previous.get("subject") != user["sub"]:
            previous = None  # a new account must not inherit another account's refresh grant
        scopes = token.get("scope", " ".join(SCOPES)).split()
        if not set(SCOPES).issubset(scopes):
            raise HTTPException(502, "Google did not grant the requested identity scopes")
        grant = {"access_token": token["access_token"], "refresh_token": token.get("refresh_token") or (previous or {}).get("refresh_token"),
            "expires": token_expiry(token), "scopes": scopes,
            "subject": user["sub"], "account_label": user.get("email") if user.get("email_verified") is True else "Google account",
            "client_id": self.client_id}
        self.save(owner, grant)
        return self.metadata(owner)

    def grant(self, owner):
        with self.store.lock:
            row = self.store.db.execute("SELECT data FROM oauth_grants WHERE owner=? AND provider='google'", (owner,)).fetchone()
        if not row:
            return None
        try:
            grant = json.loads(self.cipher.decrypt(row[0]))
            return grant if grant.get("client_id") == self.client_id else None
        except (InvalidToken, ValueError):
            return None

    def save(self, owner, grant):
        encrypted = self.cipher.encrypt(json.dumps(grant).encode())
        with self.store.lock:
            self.store.db.execute("INSERT INTO oauth_grants VALUES (?,'google',?) ON CONFLICT(owner,provider) DO UPDATE SET data=excluded.data", (owner, encrypted))
            self.store.db.commit()

    def metadata(self, owner):
        grant = self.grant(owner)
        connected = bool(grant and (grant["expires"] > time.time() or grant.get("refresh_token")))
        return {"id": "google", "label": "Google", "status": "connected" if connected else "disconnected", "can_connect": not connected,
                "scopes": grant["scopes"] if connected else list(SCOPES), "account_label": grant["account_label"] if connected else None}

    async def access_token(self, owner, required_scopes):
        # Backend-only: there is deliberately no HTTP endpoint returning this value.
        lock = self.refresh_locks.setdefault(owner, asyncio.Lock())
        async with lock:
            grant = self.grant(owner)
            if not grant or not set(required_scopes).issubset(grant["scopes"]):
                raise HTTPException(403, "Connect Google with the required permissions first")
            if grant["expires"] > time.time()+30:
                return grant["access_token"]
            if not grant.get("refresh_token"):
                raise HTTPException(401, "Reconnect Google")
            async with self.client() as client:
                response = await client.post(TOKEN_URL, data={"grant_type": "refresh_token", "refresh_token": grant["refresh_token"], "client_id": self.client_id, "client_secret": self.secret})
            if not response.is_success:
                if response.status_code == 400 and response.json().get("error") == "invalid_grant":
                    self.delete(owner)
                    raise HTTPException(401, "Google connection expired; reconnect")
                raise HTTPException(502, "Google refresh is temporarily unavailable")
            token = response.json()
            if not isinstance(token.get("access_token"), str) or token.get("token_type", "").lower() != "bearer":
                raise HTTPException(502, "Google returned an invalid refresh result")
            grant.update(access_token=token["access_token"], expires=token_expiry(token), refresh_token=token.get("refresh_token") or grant["refresh_token"])
            if token.get("scope"):
                grant["scopes"] = token["scope"].split()
            self.save(owner, grant)
            if not set(required_scopes).issubset(grant["scopes"]):
                raise HTTPException(403, "Google did not grant these permissions")
            return grant["access_token"]

    def delete(self, owner):
        with self.store.lock:
            self.store.db.execute("DELETE FROM oauth_grants WHERE owner=? AND provider='google'", (owner,))
            self.store.db.commit()

    async def disconnect(self, owner):
        async with self.refresh_locks.setdefault(owner, asyncio.Lock()):
            grant = self.grant(owner)
            if grant:
                async with self.client() as client:
                    response = await client.post(REVOKE_URL, data={"token": grant.get("refresh_token") or grant["access_token"]})
                if response.status_code not in {200, 400}:
                    raise HTTPException(502, "Google revocation did not complete; try again")
                self.delete(owner)
            return {"disconnected": True}
