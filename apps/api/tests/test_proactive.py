"""Gate 2: deterministic, deduplicated, consented proactive messages that respect quiet hours."""
from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import actions, merchant, proactive
from app.actions import ActionEngine, ActionStore
from tests.test_merchant import order_body, send, tap


@pytest.fixture
def world(tmp_path, monkeypatch):
    store = ActionStore(tmp_path / "actions.sqlite3")
    monkeypatch.setattr(actions, "_engine", ActionEngine(store))
    monkeypatch.setattr(merchant, "_pin", "246810")
    now = {"t": datetime(2026, 10, 19, 21, 0, tzinfo=proactive.DUBAI)}
    monkeypatch.setattr(proactive, "clock", lambda: now["t"])
    app = FastAPI()
    for module in (actions, merchant, proactive):
        app.include_router(module.router)
    user, shop = TestClient(app), TestClient(app)
    user.get("/api/session")
    shop.post("/api/merchant/login", json={"provider_id": "marinaexpress", "pin": "246810"})
    yield user, shop, now
    store.db.close()


def accepted_order(user, shop, ready="Tomorrow 08:30"):
    draft, _ = send(user, order_body())
    tap(shop, draft["id"], "accept", "accept-key-1", ready_at=ready)
    return draft["id"]


def test_reminder_needs_an_accepted_order(world):
    user, _, _ = world
    draft, _ = send(user, order_body())
    assert user.post("/api/reminders", json={"action_id": draft["id"]}).status_code == 409


def test_reminder_fires_once_and_persists(world):
    user, shop, now = world
    action_id = accepted_order(user, shop)
    first = user.post("/api/reminders", json={"action_id": action_id}).json()
    assert first["created"] is True and first["scheduled_for"].startswith("2026-10-20T08:15")
    assert user.post("/api/reminders", json={"action_id": action_id}).json()["created"] is False  # same dedupe_key
    assert user.get("/api/messages").json()["messages"] == []  # not due yet

    now["t"] = datetime(2026, 10, 20, 8, 16, tzinfo=proactive.DUBAI)
    delivered = user.get("/api/messages").json()["messages"]
    assert len(delivered) == 1 and delivered[0]["trigger_source"] == "user_reminder"
    assert "ready at Tomorrow 08:30" in delivered[0]["text"]
    assert user.get("/api/messages").json()["messages"] == delivered  # reload: same single message


def test_demo_trigger_twice_gives_one_message_and_is_labelled(world):
    user, shop, now = world
    user.post("/api/proactive/consent", json={"on": True})
    assert shop.post("/api/demo/triggers", json={"kind": "flight_landed"}).json()["affected"] == 1
    assert shop.post("/api/demo/triggers", json={"kind": "flight_landed"}).json()["affected"] == 0
    got = user.get("/api/messages").json()["messages"]
    assert len(got) == 1 and got[0]["trigger_source"] == "demo"


def test_fast_forward_makes_a_pending_reminder_due_and_labels_it(world):
    user, shop, _ = world
    user.post("/api/reminders", json={"action_id": accepted_order(user, shop)})
    shop.post("/api/demo/triggers", json={"kind": "fast_forward_reminders"})
    got = user.get("/api/messages").json()["messages"]
    assert len(got) == 1 and got[0]["trigger_source"] == "demo"


def test_quiet_hours_defer_delivery(world):
    user, shop, now = world
    user.post("/api/proactive/consent", json={"on": True})
    now["t"] = datetime(2026, 10, 19, 23, 30, tzinfo=proactive.DUBAI)
    shop.post("/api/demo/triggers", json={"kind": "flight_landed"})
    assert user.get("/api/messages").json()["messages"] == []
    now["t"] = datetime(2026, 10, 20, 7, 1, tzinfo=proactive.DUBAI)
    assert len(user.get("/api/messages").json()["messages"]) == 1


def test_no_consent_no_message_and_withdrawal_clears_pending(world):
    user, shop, _ = world
    shop.post("/api/demo/triggers", json={"kind": "flight_landed"})
    assert user.get("/api/messages").json()["messages"] == []
    user.post("/api/reminders", json={"action_id": accepted_order(user, shop)})
    user.post("/api/proactive/consent", json={"on": False})
    shop.post("/api/demo/triggers", json={"kind": "fast_forward_reminders"})
    assert user.get("/api/messages").json()["messages"] == []


def test_triggers_are_operator_only(world):
    user, _, _ = world
    assert user.post("/api/demo/triggers", json={"kind": "flight_landed"}).status_code == 401
