import base64
import json
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import actions
from app.actions import ActionEngine, ActionStore
from app.community.media import router as media_router
from app.community.routes import router as community_router
from tests.fixtures.community.bind import install

FIXTURE = Path(__file__).parent / "fixtures" / "community" / "media_fixture.json"


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


@pytest.fixture
def clients(tmp_path, monkeypatch):
    monkeypatch.setenv("CM_MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("CM_MEDIA_SECRET", "test-cm-media-secret")
    monkeypatch.delenv("CM_MEDIA_QUOTA_BYTES", raising=False)
    monkeypatch.delenv("CM_MEDIA_MAX_FILE_BYTES", raising=False)
    store = ActionStore(tmp_path / "community.sqlite3")
    monkeypatch.setattr(actions, "_engine", ActionEngine(store))
    app = FastAPI()
    app.include_router(actions.router)
    app.include_router(community_router)
    app.include_router(media_router)
    install(app, store, tmp_path)
    c = TestClient(app)
    c.get("/api/session")
    yield c, store, tmp_path, monkeypatch
    store.db.close()


def other(c):
    o = TestClient(c.app)
    o.get("/api/session")
    return o


def _upload(c, data=b"hello cm-b6", filename="hello.txt", content_type="text/plain", **kw):
    body = {"filename": filename, "content_type": content_type, "content": _b64(data)}
    body.update(kw)
    return c.post("/api/community/media", json=body)


def test_happy_upload_signed_content_roundtrip(clients):
    c, store, _, _ = clients
    fixture = json.loads(FIXTURE.read_text())
    r = c.post("/api/community/media", json={
        "filename": fixture["filename"], "content_type": fixture["content_type"],
        "content": fixture["content_base64"]})
    assert r.status_code == 200, r.text
    media = r.json()["media"]
    assert media["provenance"] == "user_supplied"
    assert media["size"] == len(b"hello cm-b6")
    assert media["filename"] == "hello.txt"
    mid = media["id"]
    # owner metadata
    assert c.get(f"/api/community/media/{mid}").json()["media"]["id"] == mid
    # signed -> content roundtrip
    signed = c.get(f"/api/community/media/{mid}/signed?expires=300")
    assert signed.status_code == 200, signed.text
    payload = signed.json()
    assert payload["exp"] > int(time.time())
    url = payload["url"]
    assert url.startswith(f"/api/community/media/{mid}/content?")
    got = c.get(url)
    assert got.status_code == 200 and got.content == b"hello cm-b6"
    # also via token/exp params explicitly
    qs = parse_qs(urlparse(url).query)
    got2 = c.get(f"/api/community/media/{mid}/content", params={"token": qs["token"][0], "exp": qs["exp"][0]})
    assert got2.status_code == 200 and got2.content == b"hello cm-b6"
    # row persisted in cm_media
    row = store.db.execute("SELECT owner,provenance,size FROM cm_media WHERE id=?", (mid,)).fetchone()
    assert row and row[1] == "user_supplied" and row[2] == media["size"]


def test_other_user_metadata_and_signed_404(clients):
    c, _, _, _ = clients
    mid = _upload(c).json()["media"]["id"]
    o = other(c)
    assert o.get(f"/api/community/media/{mid}").status_code == 404
    assert o.get(f"/api/community/media/{mid}/signed").status_code == 404
    # owner still ok
    assert c.get(f"/api/community/media/{mid}").status_code == 200


def test_tampered_and_expired_token_403(clients):
    c, _, _, _ = clients
    mid = _upload(c).json()["media"]["id"]
    signed = c.get(f"/api/community/media/{mid}/signed?expires=300").json()
    qs = parse_qs(urlparse(signed["url"]).query)
    token, exp = qs["token"][0], qs["exp"][0]
    assert c.get(f"/api/community/media/{mid}/content", params={"token": "deadbeef", "exp": exp}).status_code == 403
    assert c.get(f"/api/community/media/{mid}/content", params={"token": token, "exp": 1}).status_code == 403
    assert c.get(f"/api/community/media/{mid}/content").status_code == 403
    # valid still works
    assert c.get(f"/api/community/media/{mid}/content", params={"token": token, "exp": exp}).status_code == 200


def test_quota_exceeded_honest_error(clients):
    c, _, _, monkeypatch = clients
    monkeypatch.setenv("CM_MEDIA_QUOTA_BYTES", "20")
    monkeypatch.setenv("CM_MEDIA_MAX_FILE_BYTES", "1000")
    assert _upload(c, data=b"0123456789").status_code == 200
    r = _upload(c, data=b"0123456789ABCDEF")  # 10+16 > 20
    assert r.status_code == 429, r.text
    assert "quota" in r.json()["detail"].lower()


def test_oversize_file_413(clients):
    c, _, _, monkeypatch = clients
    monkeypatch.setenv("CM_MEDIA_MAX_FILE_BYTES", "8")
    r = _upload(c, data=b"way too large payload")
    assert r.status_code == 413, r.text


def test_invalid_base64_400(clients):
    c, _, _, _ = clients
    r = c.post("/api/community/media", json={"filename": "x.txt", "content": "!!!not-base64!!!"})
    assert r.status_code == 400


def test_server_app_loads_media_router(clients):
    c, _, _, _ = clients
    from app.community import server as community_server
    paths = TestClient(community_server.app).get("/openapi.json").json()["paths"]
    assert "/api/community/media" in paths
    assert "/api/community/media/{media_id}/signed" in paths
    assert "/api/community/media/{media_id}/content" in paths
