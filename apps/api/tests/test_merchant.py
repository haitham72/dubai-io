"""Fixed-price order loop: user approval -> sandbox merchant inbox -> merchant taps -> user state."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import actions, merchant
from app.actions import ActionEngine, ActionStore


@pytest.fixture
def clients(tmp_path, monkeypatch):
    store = ActionStore(tmp_path / "actions.sqlite3")
    monkeypatch.setattr(actions, "_engine", ActionEngine(store))
    monkeypatch.setattr(merchant, "_pin", "246810")
    app = FastAPI()
    app.include_router(actions.router)
    app.include_router(merchant.router)
    user, shop, rival = TestClient(app), TestClient(app), TestClient(app)
    user.get("/api/session")
    assert shop.post("/api/merchant/login", json={"provider_id": "marinaexpress", "pin": "246810"}).status_code == 200
    assert rival.post("/api/merchant/login", json={"provider_id": "foldpress", "pin": "246810"}).status_code == 200
    yield user, shop, rival
    store.db.close()


def order_body(price=6, deadline="Tomorrow 09:00"):
    # The widget's price is attacker-controlled; the host must ignore it.
    return {"capability_id": "order.request", "fields": {"area": {"value": "Dubai Marina"}, "deadline": {"value": deadline}},
            "order": {"provider_id": "marinaexpress", "items": [{"name": "Shirt wash + press", "qty": 2, "price": price}], "slot": "Today 21:00"}}


def send(user, body):
    draft = user.post("/api/actions/prepare", json=body).json()
    sent = user.post(f"/api/actions/{draft['id']}/approve", json={"snapshot_hash": draft["snapshot_hash"], "revision": draft["revision"]}, headers={"Idempotency-Key": "approve-1"})
    return draft, sent


def tap(shop, action_id, command, key, **body):
    return shop.post(f"/api/merchant/orders/{action_id}/{command}", json=body, headers={"Idempotency-Key": key})


def test_total_is_rebuilt_from_the_host_catalog(clients):
    user, _, _ = clients
    draft = user.post("/api/actions/prepare", json=order_body(price=0.01)).json()
    assert draft["status"] == "AWAITING_APPROVAL"
    assert draft["fixed_total_aed"] == "12" and draft["order"]["lines"][0]["price_aed"] == "6"
    assert draft["recipient"] == "Marina Express Laundry (sandbox merchant)"


def test_failed_merchant_command_receipt_rolls_back_the_source_status(clients,monkeypatch):
    user,shop,_ = clients
    _,sent=send(user,order_body())
    action=sent.json()
    store=actions.engine().store
    execute=store.db.execute
    def fail_receipt(sql,params=()):
        if sql.startswith("INSERT INTO merchant_commands"):
            raise RuntimeError("Simulated receipt write failure")
        return execute(sql,params)
    monkeypatch.setattr(store.db,"execute",fail_receipt)
    with pytest.raises(RuntimeError,match="receipt"):
        tap(shop,action["id"],"accept","atomic-accept",ready_at="Tomorrow 10:00")
    latest=user.get('/api/actions/'+action['id']).json()
    assert latest['status']=='SUBMITTED' and not latest.get('ready_at')


def test_unknown_item_slot_or_provider_is_rejected(clients):
    user, _, _ = clients
    for change in ({"items": [{"name": "Gold plating", "qty": 1}]}, {"slot": "Midnight"}, {"provider_id": "real-brand"}):
        body = order_body()
        body["order"] |= change
        assert user.post("/api/actions/prepare", json=body).status_code == 422


def test_full_deadline_loop_reaches_the_user_only_through_merchant_taps(clients):
    user, shop, rival = clients
    draft, sent = send(user, order_body())
    assert sent.json()["status"] == "SUBMITTED" and sent.json()["evidence"]["reference"].startswith("DIO-")
    action_id = draft["id"]

    assert rival.get("/api/merchant/orders").json() == {"orders": []}
    assert tap(rival, action_id, "accept", "rival-key-1", ready_at="Tomorrow 08:00").status_code == 404
    inbox = shop.get("/api/merchant/orders").json()["orders"]
    assert [o["id"] for o in inbox] == [action_id] and "owner" not in inbox[0]

    assert tap(shop, action_id, "accept", "accept-1", ready_at="Tomorrow 10:00").json()["status"] == "ACCEPTED"
    seen = user.get(f"/api/actions/{action_id}").json()
    assert seen["deadline_check"] == {"deadline": "Tomorrow 09:00", "ready_at": "Tomorrow 10:00", "meets": False}

    asked = user.post(f"/api/actions/{action_id}/request-earlier", json={"target": "Tomorrow 08:30"}).json()
    assert asked["earlier_request"]["target"] == "Tomorrow 08:30" and asked["fixed_total_aed"] == "12"
    assert shop.get("/api/merchant/orders").json()["orders"][0]["earlier_request"]["target"] == "Tomorrow 08:30"

    tap(shop, action_id, "confirm-time", "time-key-1", ready_at="Tomorrow 08:30")
    seen = user.get(f"/api/actions/{action_id}").json()
    assert seen["deadline_check"]["meets"] is True and seen["fixed_total_aed"] == "12" and seen["status"] == "ACCEPTED"
    assert user.post(f"/api/actions/{action_id}/request-earlier", json={"target": "Tomorrow 08:00"}).status_code == 409

    assert tap(shop, action_id, "ready", "ready-key-1").json()["status"] == "READY"
    assert tap(shop, action_id, "complete", "done-key-1").json()["status"] == "COMPLETED"
    moves = [(e["from"], e["to"], e["actor"]) for e in user.get(f"/api/actions/{action_id}").json()["events"] if e["kind"] == "status"]
    assert moves == [("SUBMITTED", "ACCEPTED", "merchant"), ("ACCEPTED", "READY", "merchant"), ("READY", "COMPLETED", "merchant")]


def test_double_approve_and_replayed_taps_are_single(clients):
    user, shop, _ = clients
    draft, sent = send(user, order_body())
    again = user.post(f"/api/actions/{draft['id']}/approve", json={"snapshot_hash": draft["snapshot_hash"], "revision": draft["revision"]}, headers={"Idempotency-Key": "approve-1"})
    assert again.json() == sent.json()
    first = tap(shop, draft["id"], "accept", "accept-1", ready_at="Tomorrow 10:00")
    assert tap(shop, draft["id"], "accept", "accept-1", ready_at="Tomorrow 10:00").json() == first.json()
    assert tap(shop, draft["id"], "accept", "accept-2", ready_at="Tomorrow 10:00").status_code == 409
    assert sum(e["kind"] == "status" for e in user.get(f"/api/actions/{draft['id']}").json()["events"]) == 1


def test_decline_and_illegal_moves(clients):
    user, shop, _ = clients
    draft, _ = send(user, order_body())
    assert tap(shop, draft["id"], "ready", "ready-key-1").status_code == 409
    assert tap(shop, draft["id"], "accept", "accept-1").status_code == 422  # a ready time is required
    declined = tap(shop, draft["id"], "decline", "no-key-1", reason="Fully booked").json()
    assert declined["status"] == "DECLINED"
    assert user.get(f"/api/actions/{draft['id']}").json()["status"] == "DECLINED"
    assert tap(shop, draft["id"], "quote", "quote-key-1").status_code == 404  # no quote path exists


def test_merchant_access_fails_closed(clients):
    user, _, _ = clients
    stranger = TestClient(user.app)
    assert stranger.get("/api/merchant/orders").status_code == 401
    assert stranger.post("/api/merchant/login", json={"provider_id": "marinaexpress", "pin": "000000"}).status_code == 403
