import asyncio
import json
import time
from urllib.parse import parse_qs, urlsplit

from cryptography.fernet import Fernet
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import httpx
import pytest

from app import actions, auth
from app.actions import ActionEngine, ActionStore
from app.oauth import GoogleOAuth, SCOPES, TOKEN_URL, valid_redirect


@pytest.fixture
def connection(tmp_path):
    store = ActionStore(tmp_path / "oauth.sqlite3")
    calls = []
    mode = {"subject": "google-alice", "refresh": True, "revoked": False, "scopes": "openid email profile"}
    def response(request):
        calls.append(request)
        if request.url.path == "/token":
            data = parse_qs(request.content.decode())
            if data["grant_type"] == ["refresh_token"]:
                if mode["revoked"]:
                    return httpx.Response(400, json={"error": "invalid_grant"})
                return httpx.Response(200, json={"access_token": "refreshed-test-access", "token_type": "Bearer", "expires_in": 3600})
            token = {"access_token": "test-access", "token_type": "Bearer", "expires_in": 3600, "scope": mode["scopes"]}
            if mode["refresh"]:
                token["refresh_token"] = "test-refresh-secret"
            return httpx.Response(200, json=token)
        if request.url.path == "/v1/userinfo":
            return httpx.Response(200, json={"sub": mode["subject"], "email": "alice@example.test", "email_verified": True})
        if request.url.path == "/revoke":
            return httpx.Response(200)
        raise AssertionError(str(request.url))
    service = GoogleOAuth(store, "test-client", "test-client-secret", "http://localhost:8000/api/auth/google/callback", Fernet.generate_key(), httpx.MockTransport(response))
    yield service, calls, mode
    store.db.close()


def attempt(service, owner="alice"):
    url = service.start(owner)
    return parse_qs(urlsplit(url).query)["state"][0]


def connect(service):
    return asyncio.run(service.callback("alice", attempt(service), "test-code"))


def test_callback_uri_rejects_unowned_insecure_or_extra_routes():
    assert valid_redirect("http://localhost:8000/api/auth/google/callback")
    assert valid_redirect("https://app.example.test/api/auth/google/callback")
    assert not valid_redirect("http://10.0.0.2:8000/api/auth/google/callback")
    assert not valid_redirect("https://user:secret@app.example.test/api/auth/google/callback")
    assert not valid_redirect("https://app.example.test/api/auth/google/callback?next=evil")
    assert not valid_redirect("https://app.example.test/other")
    assert not valid_redirect("https://app.example.test:bad/api/auth/google/callback")


def test_start_uses_state_pkce_and_no_client_secret(connection):
    service, calls, _ = connection
    url = service.start("alice")
    query = parse_qs(urlsplit(url).query)
    assert query["code_challenge_method"] == ["S256"]
    assert query["access_type"] == ["offline"]
    assert query["scope"] == [" ".join(SCOPES)]
    assert "test-client-secret" not in url and "code_verifier" not in query
    assert not calls


def test_callback_verifies_account_encrypts_grants_and_consumes_state(connection):
    service, calls, _ = connection
    state = attempt(service)
    metadata = asyncio.run(service.callback("alice", state, "test-code"))
    assert metadata["status"] == "connected"
    assert metadata["account_label"] == "alice@example.test"
    assert "test-access" not in json.dumps(metadata)
    stored = service.store.db.execute("SELECT data FROM oauth_grants").fetchone()[0]
    assert b"test-refresh-secret" not in stored
    with pytest.raises(HTTPException) as error:
        asyncio.run(service.callback("alice", state, "test-code"))
    assert error.value.status_code == 400
    assert len([r for r in calls if str(r.url) == TOKEN_URL]) == 1


def test_wrong_session_and_expired_state_cannot_exchange_codes(connection):
    service, calls, _ = connection
    state = attempt(service)
    with pytest.raises(HTTPException):
        asyncio.run(service.callback("bob", state, "test-code"))
    service.store.db.execute("UPDATE oauth_attempts SET expires=0"); service.store.db.commit()
    with pytest.raises(HTTPException):
        asyncio.run(service.callback("alice", state, "test-code"))
    assert calls == []


def test_missing_scopes_never_create_a_connected_account(connection):
    service, _, mode = connection
    mode["scopes"] = "openid"
    with pytest.raises(HTTPException):
        connect(service)
    assert service.metadata("alice")["status"] == "disconnected"


def test_refresh_is_serialized_and_scope_bound(connection):
    service, calls, _ = connection
    connect(service)
    grant = service.grant("alice"); grant["expires"] = 0; service.save("alice", grant)
    async def both():
        return await asyncio.gather(service.access_token("alice", ["email"]), service.access_token("alice", ["profile"]))
    assert asyncio.run(both()) == ["refreshed-test-access"] * 2
    refresh_calls = [r for r in calls if r.url.path == "/token" and b"grant_type=refresh_token" in r.content]
    assert len(refresh_calls) == 1
    with pytest.raises(HTTPException) as error:
        asyncio.run(service.access_token("alice", ["calendar"]))
    assert error.value.status_code == 403
    assert service.metadata("bob")["status"] == "disconnected"


def test_revoked_refresh_grant_is_removed(connection):
    service, _, mode = connection
    connect(service)
    grant = service.grant("alice"); grant["expires"] = 0; service.save("alice", grant)
    mode["revoked"] = True
    with pytest.raises(HTTPException) as error:
        asyncio.run(service.access_token("alice", ["email"]))
    assert error.value.status_code == 401
    assert service.grant("alice") is None


def test_account_switch_does_not_reuse_old_refresh_token(connection):
    service, _, mode = connection
    connect(service)
    mode.update(subject="google-bob", refresh=False)
    connect(service)
    assert service.grant("alice")["subject"] == "google-bob"
    assert service.grant("alice")["refresh_token"] is None


def test_disconnect_revokes_and_deletes_grant(connection):
    service, calls, _ = connection
    connect(service)
    assert asyncio.run(service.disconnect("alice")) == {"disconnected": True}
    assert service.grant("alice") is None
    assert calls[-1].url.path == "/revoke"


def test_http_callback_only_exposes_refresh_signal(connection, monkeypatch):
    service, _, _ = connection
    monkeypatch.setattr(actions, "_engine", ActionEngine(service.store))
    monkeypatch.setattr(auth, "_google", service)
    monkeypatch.setattr(auth.settings, "google_oauth_client_id", "test-client")
    monkeypatch.setattr(auth.settings, "google_oauth_client_secret", "test-client-secret")
    monkeypatch.setattr(auth.settings, "google_oauth_redirect_uri", service.redirect_uri)
    app = FastAPI(); app.include_router(actions.router); app.include_router(auth.router)
    client = TestClient(app, base_url="http://localhost:8000")
    client.get('/api/session')
    start = client.get('/api/auth/google/start', follow_redirects=False)
    state = parse_qs(urlsplit(start.headers['location']).query)['state'][0]
    callback = client.get('/api/auth/google/callback', params={"state":state,"code":"test-code"})
    assert callback.status_code == 200 and 'auth.complete' in callback.text
    assert 'test-access' not in callback.text and 'test-refresh-secret' not in callback.text
    assert callback.headers['cache-control'] == 'no-store'
    assert client.get('/api/auth/connections').json()['providers'][0]['status'] == 'connected'
    assert client.post('/api/auth/google/disconnect', headers={"origin":"https://other.example.test"}).status_code == 403
