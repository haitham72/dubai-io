"""Profile store: allowlisted evidence only, idempotent ingestion, persisted overrides, Forget unlinks evidence."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import actions, profile
from app.actions import ActionEngine, ActionStore


@pytest.fixture
def user(tmp_path, monkeypatch):
    store = ActionStore(tmp_path / "actions.sqlite3")
    monkeypatch.setattr(actions, "_engine", ActionEngine(store))
    app = FastAPI()
    app.include_router(actions.router)
    app.include_router(profile.router)
    client = TestClient(app)
    client.get("/api/session")
    yield client
    store.db.close()


def episode(h="prefers_closest", w=2, key="order:abc", kind="choice"):
    return {"kind": kind, "text": "Chose the closest laundry", "ev": [{"h": h, "w": w}], "dedupe_key": key}


def test_ingestion_is_idempotent(user):
    assert user.post("/api/profile/episodes", json=episode()).json()["recorded"] is True
    assert user.post("/api/profile/episodes", json=episode()).json()["recorded"] is False
    assert len(user.get("/api/profile").json()["episodes"]) == 1


@pytest.mark.parametrize("h", ["religion", "nationality_egyptian", "health_condition", "gender"])
def test_sensitive_or_unknown_hypotheses_cannot_be_stored(user, h):
    assert user.post("/api/profile/episodes", json=episode(h=h)).status_code == 422


def test_weights_and_kinds_are_fixed(user):
    assert user.post("/api/profile/episodes", json=episode(w=50)).status_code == 422
    assert user.post("/api/profile/episodes", json=episode(kind="told")).status_code == 422


def test_overrides_persist_and_forget_unlinks_evidence(user):
    user.post("/api/profile/episodes", json=episode())
    user.put("/api/profile/overrides/prefers_closest", json={"status": "rejected"})
    assert user.get("/api/profile").json()["overrides"] == {"prefers_closest": "rejected"}
    user.put("/api/profile/overrides/prefers_closest", json={"status": "forgotten"})
    state = user.get("/api/profile").json()
    assert state["overrides"] == {"prefers_closest": "forgotten"} and state["episodes"] == []


def test_profile_is_private_to_its_session(user):
    user.post("/api/profile/episodes", json=episode())
    other = TestClient(user.app)
    assert other.get("/api/profile").status_code == 401
    other.get("/api/session")
    assert other.get("/api/profile").json() == {"episodes": [], "overrides": {}}
