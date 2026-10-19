"""User profile document + bi-temporal facts."""
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import actions, profile
from app.actions import ActionEngine, ActionStore
from app.luna import graph
from app.user_profile import ProfileStore


@pytest.fixture
def store(tmp_path):
    s = ActionStore(tmp_path / "a.sqlite3")
    yield s
    s.db.close()


def test_document_grows_and_keeps_history(store):
    p = ProfileStore(lambda: store)
    p.add("u", "area", "JLT", "I live in JLT")
    p.add("u", "area", "Dubai Marina", "I moved")
    p.add("u", "pet", "dog", "I have a dog")
    p.add("u", "prefers_express", "yes", "told", facet="preference")
    doc = p.document("u")
    assert doc["core"]["home_area"] == "Dubai Marina"
    assert doc["attributes"] == {"context": {"area": "Dubai Marina"}, "identity": {"pet": "dog"}, "preference": {"prefers_express": "yes"}}
    old, new = p.history("u", "area")
    assert old["valid_to"] and "valid_to" not in new
    assert "context.area=Dubai Marina" in p.digest("u")


def test_repeat_statement_is_not_a_new_fact(store):
    p = ProfileStore(lambda: store)
    p.add("u", "area", "JLT", "a")
    p.add("u", "area", "JLT", "b")
    assert len(p.history("u", "area")) == 1


def test_forget_removes_history_and_projection(store):
    p = ProfileStore(lambda: store)
    p.add("u", "area", "JLT", "a")
    assert p.forget("u", "area") == 1
    assert p.current("u") == [] and p.document("u")["attributes"] == {}


def test_unknown_facet_is_rejected(store):
    with pytest.raises(ValueError):
        ProfileStore(lambda: store).add("u", "religion", "x", "x", facet="religion")


def test_legacy_json_is_imported_once(store, tmp_path):
    legacy = tmp_path / "memory.json"
    legacy.write_text(json.dumps({"u": [{"key": "area", "value": "JLT", "as_of": "2026-10-01T00:00:00+00:00", "source": "s"}]}))
    p = ProfileStore(lambda: store, legacy_json=legacy)
    assert [f["value"] for f in p.current("u")] == ["JLT"]
    assert not legacy.exists() and legacy.with_suffix(".json.migrated").exists()


def test_confirming_a_hypothesis_writes_a_preference_and_not_true_removes_it(store, monkeypatch):
    monkeypatch.setattr(actions, "_engine", ActionEngine(store))
    monkeypatch.setattr(graph, "facts", ProfileStore(lambda: store))
    app = FastAPI()
    app.include_router(actions.router)
    app.include_router(profile.router)
    c = TestClient(app)
    c.get("/api/session")
    c.put("/api/profile/overrides/prefers_closest", json={"status": "confirmed"})
    me = c.get("/api/profile/me").json()
    assert me["attributes"]["preference"]["prefers_closest"] == "You pick the closest provider"
    assert me["facts"][0]["status"] == "confirmed" and me["facts"][0]["provenance"] == "user_supplied"
    c.put("/api/profile/overrides/prefers_closest", json={"status": "rejected"})
    assert c.get("/api/profile/me").json()["attributes"] == {}
