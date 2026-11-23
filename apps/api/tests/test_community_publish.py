from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import actions
from app.actions import ActionEngine, ActionStore
from app.community.routes import router as community_router
from app.community.agents import router as agents_router, REGISTERED_CAPABILITIES

SRC = [{"title": "RTA", "url": "https://www.rta.ae/service", "publisher": "RTA", "as_of": "2026-11-23"}]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CM_SOURCE_ALLOWLIST", "example.com,gov.ae,rta.ae")
    store = ActionStore(tmp_path / "community.sqlite3")
    monkeypatch.setattr(actions, "_engine", ActionEngine(store))
    app = FastAPI()
    app.include_router(actions.router)
    app.include_router(community_router)
    app.include_router(agents_router)
    c = TestClient(app)
    c.get("/api/session")
    yield c, store
    store.db.close()


def profile(c, handle="alice_dxb"):
    r = c.put("/api/community/profiles/me", json={"handle": handle, "age_band": "18+", "interests": ["food"]})
    assert r.status_code == 200, r.text


def draft(c, text="Answer: use the RTA service.", **kw):
    body = {"question": "How?", "text": text, "sources": SRC}
    body.update(kw)
    r = c.post("/api/community/answers/draft", json=body)
    assert r.status_code == 200, r.text
    return r.json()["draft"]


def post_count(store):
    # exclude 2 demo seed posts
    return store.db.execute("SELECT COUNT(*) FROM cm_posts WHERE provenance!='demo_fixture'").fetchone()[0]


def test_registered_capability_present():
    assert "community.answer.publish" in REGISTERED_CAPABILITIES


def test_draft_no_approve_never_published(client):
    c, store = client; profile(c)
    d = draft(c)
    assert d["status"] == "draft" and d["revision"] == 1 and d["snapshot_hash"]
    assert post_count(store) == 0


def test_approve_publishes_exact_revision(client):
    c, store = client; profile(c)
    d = draft(c)
    r = c.post(f"/api/community/answers/{d['id']}/approve", json={"revision": d["revision"], "snapshot_hash": d["snapshot_hash"]})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "published" and r.json()["post_id"]
    assert post_count(store) == 1
    assert c.get(f"/api/community/posts/{r.json()['post_id']}").json()["post"]["text"] == d["text"]


def test_allowlist_reject_400(client):
    c, _ = client; profile(c)
    r = c.post("/api/community/answers/draft", json={"question": "Q", "text": "A",
               "sources": [{"title": "x", "url": "https://evil.example.net/x", "publisher": "x", "as_of": "2026"}]})
    assert r.status_code == 400
    r2 = c.post("/api/community/answers/draft", json={"question": "Q", "text": "A", "sources": []})
    assert r2.status_code == 400


def test_hash_drift_after_edit_409_and_zero_posts(client):
    c, store = client; profile(c)
    d = draft(c)
    edited = c.put(f"/api/community/answers/{d['id']}", json={"text": "Changed answer"})
    assert edited.status_code == 200 and edited.json()["draft"]["revision"] == 2
    assert edited.json()["draft"]["snapshot_hash"] != d["snapshot_hash"]
    r = c.post(f"/api/community/answers/{d['id']}/approve", json={"revision": d["revision"], "snapshot_hash": d["snapshot_hash"]})
    assert r.status_code == 409
    assert post_count(store) == 0
    # approving current revision works
    cur = edited.json()["draft"]
    ok = c.post(f"/api/community/answers/{d['id']}/approve", json={"revision": cur["revision"], "snapshot_hash": cur["snapshot_hash"]})
    assert ok.status_code == 200 and post_count(store) == 1


def test_replay_approve_dispatches_once_idempotent(client):
    c, store = client; profile(c)
    d = draft(c)
    body = {"revision": d["revision"], "snapshot_hash": d["snapshot_hash"]}
    r1 = c.post(f"/api/community/answers/{d['id']}/approve", json=body)
    r2 = c.post(f"/api/community/answers/{d['id']}/approve", json=body)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["post_id"] == r2.json()["post_id"] and r2.json()["idempotent"] is True
    assert post_count(store) == 1


def test_d15_two_drafts_need_two_approvals(client):
    c, store = client; profile(c)
    d1 = draft(c, text="First answer"); d2 = draft(c, text="Second answer")
    assert c.post(f"/api/community/answers/{d1['id']}/approve", json={"revision": 1, "snapshot_hash": d1["snapshot_hash"]}).status_code == 200
    assert post_count(store) == 1
    assert c.get(f"/api/community/answers/{d2['id']}").json()["draft"]["status"] == "draft"
    assert c.post(f"/api/community/answers/{d2['id']}/approve", json={"revision": 1, "snapshot_hash": d2["snapshot_hash"]}).status_code == 200
    assert post_count(store) == 2


def test_unregistered_capability_400_and_wrong_owner_404(client):
    c, _ = client; profile(c)
    r = c.post("/api/community/answers/draft", json={"question": "Q", "text": "A", "sources": SRC, "capability_id": "evil.publish"})
    assert r.status_code == 400
    d = draft(c)
    o = TestClient(c.app); o.get("/api/session")
    assert o.post(f"/api/community/answers/{d['id']}/approve", json={"revision": 1, "snapshot_hash": d["snapshot_hash"]}).status_code == 404


def test_group_destination_publish(client):
    c, store = client; profile(c)
    gid = c.post("/api/community/groups", json={"name": "Foodies B9", "handle": "foodies-b9", "visibility": "public"}).json()["group"]["id"]
    d = draft(c, group_id=gid)
    assert d["destination"] == f"group:{gid}"
    r = c.post(f"/api/community/answers/{d['id']}/approve", json={"revision": d["revision"], "snapshot_hash": d["snapshot_hash"]})
    assert r.status_code == 200, r.text
    assert r.json()["post"]["group_id"] == gid
