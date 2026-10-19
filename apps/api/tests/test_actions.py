from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import actions
from app.actions import ActionEngine, ActionStore, ApprovalIn, Capability, InputValue, PrepareIn


@pytest.fixture
def store(tmp_path):
    value = ActionStore(tmp_path / "actions.sqlite3")
    yield value
    value.db.close()


def body(**kw):
    return PrepareIn(capability_id="cleaning.request", fields={"request": InputValue(value="2 hours cleaning"), "area": InputValue(value="Marina")}, **kw)


def approval(action):
    return ApprovalIn(snapshot_hash=action["snapshot_hash"], revision=action["revision"])


def configured(store, callback):
    cap = Capability("cleaning.request", "Cleaning", ("request", "area"), ("request", "area"), "Test merchant", "Unavailable", callback, fixed_total_aed="80.00")
    return ActionEngine(store, {cap.id: cap})


def test_unconnected_request_is_saved_but_not_submitted(store):
    engine = ActionEngine(store)
    action = engine.prepare("alice", body())
    assert action["status"] == "BLOCKED" and action["evidence"] is None
    with pytest.raises(HTTPException) as err:
        engine.approve("alice", action["id"], approval(action), "approval1")
    assert err.value.status_code == 409
    assert engine.get("alice", action["id"])["status"] == "BLOCKED"


def test_missing_fields_remain_missing(store):
    action = ActionEngine(store).prepare("alice", PrepareIn(capability_id="recovery.rta", fields={"description": InputValue(value="Brown wallet")}))
    assert action["status"] == "DRAFT"
    assert action["missing"] == ["when", "from", "to"]
    assert "plate" not in action["fields"]


def test_inferred_and_unregistered_fields_are_rejected(store):
    with pytest.raises(ValidationError):
        InputValue(value="Marina", provenance="inferred")
    engine = ActionEngine(store)
    with pytest.raises(HTTPException):
        engine.prepare("alice", PrepareIn(capability_id="unregistered", fields={}))
    with pytest.raises(HTTPException):
        engine.prepare("alice", PrepareIn(capability_id="cleaning.request", fields={"price": InputValue(value="1")}))


def test_drafts_are_private_and_survive_a_new_engine(store):
    action = ActionEngine(store).prepare("alice", body())
    assert ActionEngine(store).get("alice", action["id"]) == action
    with pytest.raises(HTTPException) as err:
        ActionEngine(store).get("bob", action["id"])
    assert err.value.status_code == 404


def test_changed_draft_invalidates_approval(store):
    engine = configured(store, lambda *_: {"reference": "test-ref", "provenance": "provider_confirmed"})
    first = engine.prepare("alice", body())
    changed = body(draft_id=first["id"])
    changed.fields["area"] = InputValue(value="Business Bay")
    latest = engine.prepare("alice", changed)
    assert latest["revision"] == 2
    with pytest.raises(HTTPException) as err:
        engine.approve("alice", first["id"], approval(first), "approval1")
    assert err.value.status_code == 409


def test_price_change_requires_a_new_review(store):
    engine = configured(store, lambda *_: {"reference": "test-ref", "provenance": "provider_confirmed"})
    action = engine.prepare("alice", body())
    engine.registry["cleaning.request"] = replace(engine.registry["cleaning.request"], fixed_total_aed="100.00")
    with pytest.raises(HTTPException) as err:
        engine.approve("alice", action["id"], approval(action), "approval1")
    assert err.value.status_code == 409


def test_repeated_approval_never_dispatches_twice(store):
    calls = []
    engine = configured(store, lambda *args: calls.append(args) or {"reference": "test-ref", "provenance": "provider_confirmed"})
    action = engine.prepare("alice", body())
    result = engine.approve("alice", action["id"], approval(action), "approval1")
    assert result["status"] == "SUBMITTED"
    assert engine.approve("alice", action["id"], approval(action), "approval1") == result
    assert engine.approve("alice", action["id"], approval(action), "another-key") == result
    assert len(calls) == 1
    with pytest.raises(HTTPException):
        engine.prepare("alice", body(draft_id=action["id"]))


@pytest.mark.parametrize("result", [None, {"reference": "guessed", "provenance": "inferred"}, {"reference": "", "provenance": "provider_confirmed"}])
def test_unverified_outcome_is_unknown_and_cannot_be_resent(store, result):
    calls = []
    engine = configured(store, lambda *_: calls.append(1) or result)
    action = engine.prepare("alice", body())
    assert engine.approve("alice", action["id"], approval(action), "approval1")["status"] == "UNKNOWN_STATUS"
    assert engine.approve("alice", action["id"], approval(action), "another-key")["status"] == "UNKNOWN_STATUS"
    assert len(calls) == 1


def test_timeout_does_not_create_success_or_retry(store):
    def adapter(*_):
        raise TimeoutError()
    engine = configured(store, adapter)
    action = engine.prepare("alice", body())
    assert engine.approve("alice", action["id"], approval(action), "approval1")["status"] == "UNKNOWN_STATUS"
    assert ActionEngine(store, engine.registry).get("alice", action["id"])["evidence"] is None


def test_concurrent_approval_has_one_dispatch(store):
    entered, release = Event(), Event()
    calls = []
    def adapter(*_):
        calls.append(1); entered.set(); release.wait(2)
        return {"reference": "test-ref", "provenance": "provider_confirmed"}
    engine = configured(store, adapter)
    action = engine.prepare("alice", body())
    with ThreadPoolExecutor() as pool:
        first = pool.submit(engine.approve, "alice", action["id"], approval(action), "approval1")
        assert entered.wait(2)
        assert engine.approve("alice", action["id"], approval(action), "another-key")["status"] == "DISPATCHING"
        release.set()
        assert first.result()["status"] == "SUBMITTED"
    assert len(calls) == 1


def test_interrupted_dispatch_is_unknown_after_restart(store):
    engine = configured(store, lambda *_: {})
    action = engine.prepare("alice", body()); action["status"] = "DISPATCHING"
    store.put("alice", action)
    assert ActionEngine(store, engine.registry).get("alice", action["id"])["status"] == "UNKNOWN_STATUS"


def test_http_sessions_isolate_actions_and_fail_closed(store, monkeypatch):
    monkeypatch.setattr(actions, "_engine", ActionEngine(store))
    app = FastAPI(); app.include_router(actions.router)
    a, b = TestClient(app), TestClient(app)
    assert a.post("/api/actions/prepare", json=body().model_dump()).status_code == 401
    sa, sb = a.get("/api/session"), b.get("/api/session")
    assert sa.json()["user_id"] != sb.json()["user_id"]
    assert "HttpOnly" in sa.headers["set-cookie"]
    action = a.post("/api/actions/prepare", json=body().model_dump()).json()
    assert b.get('/api/actions/' + action['id']).status_code == 404
    assert b.get('/api/actions').json() == {"actions": []}
    assert a.post('/api/actions/' + action['id'] + '/approve', json=approval(action).model_dump(), headers={"Idempotency-Key": "approval1"}).status_code == 409
    assert {c['id'] for c in a.get('/api/actions/capabilities').json()['capabilities'] if c['execution_available']} == {'order.request'}


def test_preparation_retry_is_idempotent_and_payload_bound(store):
    engine = ActionEngine(store)
    request = body()
    first = engine.prepare("alice", request)
    assert engine.prepare("alice", request) == first
    assert store.db.execute("SELECT COUNT(*) FROM actions").fetchone()[0] == 1
    request.fields["area"] = InputValue(value="JLT")
    with pytest.raises(HTTPException) as err:
        engine.prepare("alice", request)
    assert err.value.status_code == 409


def test_draft_survives_a_closed_database(tmp_path):
    path=tmp_path/"durable.sqlite3"
    first=ActionStore(path)
    action=ActionEngine(first).prepare("alice",body())
    first.db.close()
    second=ActionStore(path)
    try:
        assert ActionEngine(second).get("alice",action["id"])["fields"]["area"]["value"]=="Marina"
    finally:
        second.db.close()


def test_discard_is_local_idempotent_and_cannot_cancel_dispatch(store):
    engine=configured(store,lambda *_:{"reference":"test-ref","provenance":"provider_confirmed"})
    draft=engine.prepare("alice",body())
    cancelled=engine.cancel("alice",draft["id"])
    assert cancelled["status"]=="CANCELLED" and cancelled["evidence"] is None
    assert engine.cancel("alice",draft["id"])==cancelled
    with pytest.raises(HTTPException):
        engine.approve("alice",draft["id"],approval(draft),"approval1")
    sent=engine.prepare("alice",body())
    engine.approve("alice",sent["id"],approval(sent),"approval2")
    with pytest.raises(HTTPException):
        engine.cancel("alice",sent["id"])
