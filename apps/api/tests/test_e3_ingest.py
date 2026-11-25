"""Synthetic E3 HTTP integration against a temporary compose Postgres schema."""
from datetime import datetime, timezone
import io
import os
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4
from zipfile import ZipFile

from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
import psycopg
from psycopg.conninfo import make_conninfo
import pytest

from app import ingest_routes
from app.connectors import e3_google
from app.connectors.e3_oauth import GoogleAuth
from app.connectors.e3_store import Bridge, State
from app.identity.deps import get_identity_service
from app.identity.models import IdentityError, VerifiedPrincipal
from app.oauth import TOKEN_URL, USERINFO_URL


FIRST = {"X-App-Session": "owner-a"}
SECOND = {"X-App-Session": "owner-b"}
NOW = datetime(2026, 11, 24, 10, tzinfo=timezone.utc)


class Identity:
    def authenticate_session(self, token, **kwargs):
        if token not in {"owner-a", "owner-b"}:
            raise IdentityError("invalid", "Unknown test session", 401)
        return VerifiedPrincipal(token, "quest", frozenset({"memory:device_token"}),
                                 "verified_app_session", session_id=token)


@pytest.fixture
def e3(monkeypatch):
    monkeypatch.setenv("TM_SEMANTIC", "0")
    monkeypatch.setattr(ingest_routes, "utcnow", lambda: NOW)
    ingest_routes._memory_module("models")
    from temporal_memory.api.app import create_app
    from temporal_memory.core.graph_store import PostgresGraphStore
    from temporal_memory.db.db import Database, drop_test_schema, migrate
    from temporal_memory.models import Owner

    target = os.environ.get("TM_TEST_DATABASE_URL", "postgresql://tm:tm@localhost:5442/tm")
    schema = f"tm_test_e3_{uuid4().hex[:12]}"
    db = Database(target, schema=schema)
    try:
        migrate(db)
    except psycopg.OperationalError:
        db.close()
        pytest.skip("Temporal memory compose Postgres is unavailable")
    try:
        store = PostgresGraphStore(db)
        for owner in ("owner-a", "owner-b"):
            store.create_owner(Owner(owner, owner, kind="simulated"))
        tm_app = create_app(db, admin_token="synthetic-admin")
        with TestClient(tm_app) as tm:
            tokens = {
                owner: tm.post("/v1/tokens", headers={"Authorization": "Bearer synthetic-admin"},
                               json={"role": "owner-device", "owner": owner}).json()["token"]
                for owner in ("owner-a", "owner-b")
            }

            def proxy(request):
                response = tm.request(request.method, request.url.path, headers=dict(request.headers),
                                      content=request.content)
                return httpx.Response(response.status_code, content=response.content)

            calls = []

            def google(request):
                calls.append((request.method, request.url.path, dict(request.url.params)))
                if str(request.url) == TOKEN_URL:
                    form = parse_qs(request.content.decode())
                    assert form["code_verifier"][0]
                    return httpx.Response(200, json={
                        "access_token": "fake-access", "refresh_token": "fake-refresh", "expires_in": 3600,
                        "token_type": "Bearer", "scope": f"openid {e3_google.SCOPES['gmail']}",
                    })
                if str(request.url) == USERINFO_URL:
                    return httpx.Response(200, json={"sub": "verified-google-subject"})
                if request.url.path.endswith("/messages"):
                    assert "category:primary" in request.url.params["q"]
                    assert request.url.params["includeSpamTrash"] == "false"
                    return httpx.Response(200, json={"messages": [{"id": "memo"}, {"id": "advert"}]})
                if "/messages/" in request.url.path:
                    advert = request.url.path.endswith("advert")
                    return httpx.Response(200, json={
                        "labelIds": ["CATEGORY_PROMOTIONS"] if advert else ["CATEGORY_PERSONAL"],
                        "internalDate": str(int(NOW.timestamp() * 1000)),
                        "payload": {"headers": [{"name": "Subject", "value": "Coral architecture workshop"}]},
                        "snippet": "The coral architecture workshop moved to Studio Blue.",
                    })
                raise AssertionError(f"Unexpected Google test route {request.url.path}")

            scoped = make_conninfo(target, options=f"-csearch_path={schema},public")
            state = State(scoped, Fernet(Fernet.generate_key()))
            auth = GoogleAuth(state, "synthetic-client", "synthetic-secret",
                              "http://localhost:8000/api/ingest/google/callback", transport=httpx.MockTransport(google))
            service = ingest_routes.Ingest(
                state, Bridge("http://memory.test", tokens.__getitem__, transport=httpx.MockTransport(proxy)),
                auth, google_transport=httpx.MockTransport(google),
            )
            app = FastAPI()
            app.include_router(ingest_routes.router)
            app.state.e3_ingest = service
            app.dependency_overrides[get_identity_service] = Identity
            with TestClient(app) as client:
                yield client, tm, tokens, state, calls
    finally:
        drop_test_schema(db, schema)


def enable(client, source, headers=FIRST):
    response = client.put(f"/api/ingest/consent/{source}", headers=headers, json={"enabled": True})
    assert response.status_code == 200, response.text


def connect(client, headers=FIRST):
    response = client.post("/api/ingest/google/gmail/connect", headers=headers)
    assert response.status_code == 200, response.text
    params = parse_qs(urlsplit(response.json()["authorization_url"]).query)
    assert params["scope"] == [f"openid {e3_google.SCOPES['gmail']}"]
    assert params["include_granted_scopes"] == ["true"]
    assert params["code_challenge_method"] == ["S256"]
    return params["state"][0]


def finish(client, state, headers=FIRST):
    return client.get("/api/ingest/google/callback", headers=headers, params={"state": state, "code": "fake-code"})


def test_default_off_blocks_pull_upload_and_oauth_without_external_calls(e3):
    client, _, _, _, calls = e3
    assert client.post("/api/ingest/google/gmail/pull", headers=FIRST).status_code == 403
    assert client.post("/api/ingest/google/gmail/connect", headers=FIRST).status_code == 403
    assert client.post("/api/ingest/takeout", headers=FIRST, files={"file": ("data.zip", b"xyz")}).status_code == 403
    assert client.get("/api/ingest/status").status_code == 401
    assert calls == []


def test_gmail_is_incremental_encrypted_idempotent_and_owner_scoped(e3):
    client, _, _, state, calls = e3
    enable(client, "gmail")
    key = connect(client)
    assert finish(client, key, SECOND).status_code == 400
    assert finish(client, key).json() == {"source": "gmail", "connected": True}
    assert finish(client, key).status_code == 400
    with state.connection() as conn:
        blob = conn.execute("SELECT grant_cipher FROM e3_ingest_sources WHERE source='gmail'").fetchone()["grant_cipher"]
        assert b"fake-access" not in blob and b"fake-refresh" not in blob
    for expected in (1, 0):
        response = client.post("/api/ingest/google/gmail/pull", headers=FIRST)
        assert response.status_code == 200, response.text
        assert response.json()["records_added"]["value"] == expected
        assert response.json()["jobs_enqueued"]["value"] == expected
    status = client.get("/api/ingest/status", headers=FIRST).json()
    assert status["sources"]["gmail"]["records"]["value"] == 1
    assert status["sources"]["gmail"]["queued"]["value"] == 1
    assert status["onboarding_percent"]["value"] is not None
    assert client.get("/api/ingest/status", headers=SECOND).json()["sources"]["gmail"]["records"]["value"] == 0
    enable(client, "gmail", SECOND)
    assert finish(client, connect(client, SECOND), SECOND).status_code == 409
    assert client.post("/api/ingest/google/gmail/pull", headers=SECOND).status_code == 409
    client.put("/api/ingest/consent/gmail", headers=FIRST, json={"enabled": False}).raise_for_status()
    before = len(calls)
    assert client.post("/api/ingest/google/gmail/pull", headers=FIRST).status_code == 403
    assert len(calls) == before


def test_source_lower_preserves_fact_and_evidence_and_restores(e3):
    client, tm, tokens, state, _ = e3
    enable(client, "gmail")
    assert finish(client, connect(client)).status_code == 200
    assert client.post("/api/ingest/google/gmail/pull", headers=FIRST).status_code == 200
    owner = "owner-a"
    base = f"/v1/owners/{owner}"
    tm_headers = {"Authorization": f"Bearer {tokens[owner]}"}
    response = tm.post(f"{base}/records", headers=tm_headers, json={"enqueue": "none", "direct_fact": {
        "text": "Coral architecture workshop moved to Studio Blue", "valid_from": "2026-11-24",
        "subject_id": "learning/workshops", "evidence": ["e3:gmail:primary:memo"], "provenance": "inferred",
    }})
    assert response.status_code == 200, response.text
    fact_id, = response.json()["fact_ids"]
    assert tm.get(f"{base}/why/{fact_id}", headers=tm_headers).status_code == 200
    assert client.delete("/api/ingest/gmail/data", headers=SECOND).json()["records"]["value"] == 0
    assert tm.get(f"{base}/why/{fact_id}", headers=tm_headers).status_code == 200
    result = client.delete("/api/ingest/gmail/data", headers=FIRST)
    assert result.status_code == 200, result.text
    assert result.json()["records"]["value"] == 1
    assert tm.get(f"{base}/why/{fact_id}", headers=tm_headers).status_code == 200
    assert fact_id not in tm.post(f"{base}/context", headers=tm_headers,
                                 json={"text": "Coral architecture workshop"}).text
    with state.connection() as conn:
        assert state.record_ids(conn, owner, "gmail") == ["e3:gmail:primary:memo"]
    assert client.post("/api/ingest/gmail/restore", headers=FIRST).status_code == 200
    assert fact_id in tm.get(f"{base}/search", headers=tm_headers, params={"q": "workshop"}).text


def test_upload_rejects_bad_archive_and_imports_a_consented_whatsapp_file(e3):
    client, _, _, _, _ = e3
    enable(client, "takeout")
    endpoint = "/api/ingest/takeout"
    assert client.post(endpoint, headers=FIRST, files={"file": ("export.zip", b"not zip")}).status_code == 400
    evil = io.BytesIO()
    with ZipFile(evil, "w") as zip_file:
        zip_file.writestr("../bad", "unused")
    assert client.post(endpoint, headers=FIRST, files={"file": ("export.zip", evil.getvalue())}).status_code == 400
    enable(client, "whatsapp")
    whatsapp = {"file": ("Workshop.txt", b"11/24/2026, 09:35 - Karim: Confirm the Coral Architecture workshop.\n")}
    response = client.post("/api/ingest/whatsapp", headers=FIRST, files=whatsapp)
    assert response.status_code == 200, response.text
    assert response.json()["records_added"]["value"] == 1
    assert client.post("/api/ingest/whatsapp", headers=FIRST, files=whatsapp).json()["records_added"]["value"] == 0


def test_desktop_upload_requires_consent_and_same_owner_memory_token(e3):
    client, _, tokens, _, _ = e3
    endpoint = "/api/ingest/desktop/browser"
    body = {"records": [{"id": "visit", "at": NOW.isoformat(), "text": "Read the public Python tutorial"}]}
    other = {**FIRST, "X-Memory-Device-Token": tokens["owner-b"]}
    mine = {**FIRST, "X-Memory-Device-Token": tokens["owner-a"]}
    assert client.post(endpoint, headers=mine, json=body).status_code == 403
    enable(client, "browser")
    assert client.post(endpoint, headers=other, json=body).status_code == 403
    done = client.post(endpoint, headers=mine, json=body)
    assert done.status_code == 200, done.text
    assert done.json()["records_added"]["value"] == 1


def test_calendar_and_youtube_use_the_scoped_read_only_feeds():
    observed = []

    def provider(request):
        leaf = request.url.path.rsplit("/", 1)[-1]
        observed.append(leaf)
        assert request.headers["Authorization"] == "Bearer synthetic"
        if leaf == "events":
            assert request.url.params["singleEvents"] == "true"
            lower = datetime.fromisoformat(request.url.params["timeMin"])
            upper = datetime.fromisoformat(request.url.params["timeMax"])
            assert (NOW - lower).days == (upper - NOW).days == 90
            return httpx.Response(200, json={"items": [{
                "id": "event", "summary": "Coral workshop", "start": {"dateTime": NOW.isoformat()},
            }, {"id": "deleted", "status": "cancelled"}]})
        if leaf == "channels":
            return httpx.Response(200, json={"items": [{
                "contentDetails": {"relatedPlaylists": {"uploads": "uploads-id"}},
            }]})
        if leaf == "videos":
            assert request.url.params["myRating"] == "like"
        if leaf in {"subscriptions", "playlists"}:
            assert request.url.params["mine"] == "true"
        if leaf == "playlistItems":
            assert request.url.params["playlistId"] == "uploads-id"
        return httpx.Response(200, json={"items": [{
            "id": leaf, "snippet": {"title": f"Synthetic {leaf}", "publishedAt": "2026-11-01T12:00:00Z"},
        }]})

    transport = httpx.MockTransport(provider)
    calendar, = e3_google.pull("calendar", "synthetic", NOW, transport=transport)
    assert calendar["source"] == "calendar:primary"
    yt = e3_google.pull("youtube", "synthetic", NOW, transport=transport)
    assert {row["source"] for row in yt} == {f"youtube:api:{leaf}" for leaf in ("likes", "subscriptions", "playlists", "uploads")}
    liked = next(row for row in yt if row["source"].endswith(":likes"))
    assert liked["at"] == NOW.isoformat()
    assert observed == ["events", "videos", "subscriptions", "playlists", "channels", "playlistItems"]


def test_disable_during_google_fetch_fences_writes(e3, monkeypatch):
    client, _, _, state, _ = e3
    enable(client, "gmail")
    assert finish(client, connect(client)).status_code == 200

    def fetch(*args, **kwargs):
        with state.lock("owner-a", "gmail") as conn:
            state.set_consent(conn, "owner-a", "gmail", False)
        return [{"id": "late-provider-record", "source": "gmail:primary", "at": NOW.isoformat(),
                 "author": "external", "text": "Coral workshop note"}]

    monkeypatch.setattr(e3_google, "pull", fetch)
    assert client.post("/api/ingest/google/gmail/pull", headers=FIRST).status_code in {403, 409}
    with state.connection() as conn:
        assert state.record_ids(conn, "owner-a", "gmail") == []



def test_retry_recovers_a_record_saved_before_job_enqueue(e3):
    client, tm, tokens, _, _ = e3
    enable(client, "gmail")
    assert finish(client, connect(client)).status_code == 200
    hdr = {"Authorization": f"Bearer {tokens['owner-a']}"}
    response = tm.post("/v1/owners/owner-a/records", headers=hdr, json={
        "enqueue": "none", "records": [{
            "id": "e3:gmail:primary:memo", "source": "gmail:primary",
            "at": "2026-11-24T14:00:00+04:00", "author": "gmail",
            "text": "Coral architecture workshop" + chr(10) + "The coral architecture workshop moved to Studio Blue.",
        }],
    })
    assert response.status_code == 200, response.text
    receipt = client.post("/api/ingest/google/gmail/pull", headers=FIRST).json()
    assert receipt["records_added"]["value"] == 0
    assert receipt["records_already_seen"]["value"] == 1
    assert receipt["jobs_enqueued"]["value"] == 1
    retry = client.post("/api/ingest/google/gmail/pull", headers=FIRST).json()
    assert retry["jobs_enqueued"]["value"] == 0
