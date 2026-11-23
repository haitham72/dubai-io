"""CM-B5: owners come from a verified community session. Adults only."""

from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import actions
from app.actions import ActionEngine, ActionStore
from app.community.routes import router as community_router
from app.identity import IdentityConfig, IdentityService, IdentityStore, JWTVerifier
from app.identity.router import create_identity_router
from tests.fixtures.contest_shared.identity_fixtures import (
    TEST_AUDIENCE,
    TEST_HS256_SECRET,
    TEST_ISSUER,
    default_claims,
    sign_hs256_jwt,
)


def _app(tmp_path, monkeypatch):
    store = ActionStore(tmp_path / "community.sqlite3")
    monkeypatch.setattr(actions, "_engine", ActionEngine(store))
    verifier = JWTVerifier(issuer=TEST_ISSUER, audience=TEST_AUDIENCE, hs256_secret=TEST_HS256_SECRET)
    service = IdentityService(
        IdentityStore(tmp_path / "identity.sqlite3"),
        verifier,
        config=IdentityConfig(jwt_issuer=TEST_ISSUER, jwt_audience=TEST_AUDIENCE, jwt_hs256_secret=TEST_HS256_SECRET),
        legacy_session_resolver=store.owner,
    )
    app = FastAPI()
    app.state.identity_service = service
    app.include_router(actions.router)
    app.include_router(create_identity_router())
    app.include_router(community_router)
    return TestClient(app), service, store


def _adult_session(client, service, sub):
    jwt_token = sign_hs256_jwt(default_claims(sub=sub))
    opened = client.post("/api/identity/sessions", headers={"Authorization": f"Bearer {jwt_token}"}, json={"app_id": "community"})
    assert opened.status_code == 200, opened.text
    body = opened.json()
    principal = service.authenticate_session(body["session_token"], expected_app="community")
    service.set_age_band(principal, age_band="adult_18_plus")
    return body["session_token"], body["user_id"], body["session_id"]


def test_community_two_users_isolated(tmp_path, monkeypatch):
    client, service, _store = _app(tmp_path, monkeypatch)
    token_a, user_a, _ = _adult_session(client, service, "adult-a")
    token_b, user_b, _ = _adult_session(client, service, "adult-b")
    assert user_a != user_b
    headers_a = {"X-App-Session": token_a}
    headers_b = {"X-App-Session": token_b}
    assert client.put("/api/community/profiles/me", headers=headers_a, json={"handle": "alice_id", "age_band": "18+", "privacy": "private"}).status_code == 200
    assert client.put("/api/community/profiles/me", headers=headers_b, json={"handle": "bob_id", "age_band": "18+", "privacy": "public"}).status_code == 200
    post = client.post("/api/community/posts", headers=headers_a, json={"text": "Alice private note"})
    assert post.status_code == 200, post.text
    pid = post.json()["post"]["id"]
    saved = client.post(f"/api/community/posts/{pid}/bookmarks", headers=headers_a)
    assert saved.status_code == 200, saved.text
    bob_marks = client.get("/api/community/bookmarks", headers=headers_b).json()["posts"]
    assert pid not in [item["id"] for item in bob_marks]
    alice = client.get("/api/community/profiles/me", headers=headers_a).json()["profile"]
    assert alice["owner"] == user_a
    assert client.get("/api/community/profiles/alice_id", headers=headers_b).status_code in (404, 403)


def test_community_spoofed_header_rejected(tmp_path, monkeypatch):
    client, service, _store = _app(tmp_path, monkeypatch)
    token, _user, _sid = _adult_session(client, service, "adult-spoof")
    denied = client.get("/api/community/profiles/me", headers={"X-App-Session": token, "X-User-Id": "usr_someone_else"})
    assert denied.status_code == 400
    assert denied.json()["detail"]["code"] == "spoofed_identity_header"


def test_community_expired_or_revoked_token_rejected(tmp_path, monkeypatch):
    client, service, _store = _app(tmp_path, monkeypatch)
    token, user_id, session_id = _adult_session(client, service, "adult-expire")
    past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    with service.store.lock:
        service.store.db.execute("UPDATE cs_app_sessions SET expires_at=? WHERE session_id=?", (past, session_id))
        service.store.db.commit()
    expired = client.get("/api/community/profiles/me", headers={"X-App-Session": token})
    assert expired.status_code == 401
    fresh, _user, fresh_id = _adult_session(client, service, "adult-revoke")
    holder = service.authenticate_session(fresh, expected_app="community")
    assert service.revoke_session(holder.user_id, fresh_id)
    revoked = client.get("/api/community/profiles/me", headers={"X-App-Session": fresh})
    assert revoked.status_code == 401


def test_community_minor_session_fails_closed(tmp_path, monkeypatch):
    client, service, _store = _app(tmp_path, monkeypatch)
    jwt_token = sign_hs256_jwt(default_claims(sub="unknown-age"))
    opened = client.post("/api/identity/sessions", headers={"Authorization": f"Bearer {jwt_token}"}, json={"app_id": "community"})
    assert opened.status_code == 200, opened.text
    denied = client.put(
        "/api/community/profiles/me",
        headers={"X-App-Session": opened.json()["session_token"]},
        json={"handle": "kid_id", "age_band": "18+"},
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "adults_only"


def test_community_adopt_session_owner(tmp_path, monkeypatch):
    client, service, store = _app(tmp_path, monkeypatch)
    client.get("/api/session")
    lab_owner = store.owner(client.cookies.get("dubaiio_lab_session"))
    token, user_id, _sid = _adult_session(client, service, "adult-adopt")
    adopted = client.post("/api/identity/adopt-session", headers={"X-App-Session": token})
    assert adopted.status_code == 200, adopted.text
    assert adopted.json()["session_owner"] == lab_owner
    assert adopted.json()["user_id"] == user_id
    profile = client.put(
        "/api/community/profiles/me",
        headers={"X-App-Session": token},
        json={"handle": "adopted_id", "age_band": "18+"},
    )
    assert profile.json()["profile"]["owner"] == user_id
    assert profile.json()["profile"]["owner"] != lab_owner
