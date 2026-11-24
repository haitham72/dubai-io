"""CR-TM-1..4 acceptance tests from handoff-temporal-note.md §4."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from temporal_memory.api import bridge, vault
from temporal_memory.api.vault import AuthContext
from temporal_memory.live.context import context_pack
from temporal_memory.models import Fact, Job, Owner, Record
from tests.fixtures.fake_store import FakeGraphStore


def _client(store: FakeGraphStore) -> TestClient:
    tokens = {
        "admin-tok": AuthContext(role="admin", owner=None, token_id="t-admin"),
        "karim-tok": AuthContext(role="owner-device", owner="karim", token_id="t-karim"),
        "other-tok": AuthContext(role="owner-device", owner="layla", token_id="t-layla"),
        "worker-tok": AuthContext(role="worker", owner=None, token_id="t-worker"),
    }
    vault.configure(store=store, auth_verifier=lambda tok: tokens.get(tok or ""))
    app = FastAPI()
    app.include_router(vault.router)
    app.include_router(bridge.router)
    return TestClient(app)


def _owner(store: FakeGraphStore, owner: str = "karim") -> None:
    store.owners[owner] = Owner(id=owner, label=owner, kind="real", display_name=owner)


def test_vault_and_crtm_reject_worker_and_cross_owner():
    store = FakeGraphStore()
    _owner(store)
    _owner(store, "layla")
    client = _client(store)
    worker = {"Authorization": "Bearer worker-tok"}
    other = {"Authorization": "Bearer other-tok"}
    vault_paths = ["/v1/owners/karim/vault/subjects", "/v1/owners/karim/vault/people"]
    crtm = [
        ("post", "/v1/owners/karim/records", {"records": []}),
        ("post", "/v1/owners/karim/forget", {"record_ids": []}),
        ("post", "/v1/owners/karim/facts/f1/resolve", {"action": "confirm"}),
        ("post", "/v1/owners/karim/context", {"text": "hello", "max_tokens": 200}),
        ("get", "/v1/owners/karim/search?q=hello", None),
    ]
    for path in vault_paths:
        assert client.get(path, headers=worker).status_code == 403
        assert client.get(path, headers=other).status_code == 403
    for method, path, body in crtm:
        if method == "get":
            assert client.get(path, headers=worker).status_code == 403
            assert client.get(path, headers=other).status_code == 403
        else:
            assert client.post(path, headers=worker, json=body).status_code == 403
            assert client.post(path, headers=other, json=body).status_code == 403


def test_crtm1_records_upsert_and_direct_fact():
    store = FakeGraphStore()
    _owner(store)
    client = _client(store)
    hdr = {"Authorization": "Bearer karim-tok"}
    created = client.post("/v1/owners/karim/records", headers=hdr, json={
        "records": [{
            "id": "mgmsg:m-101", "source": "messenger:conv-42",
            "at": "2026-11-23T14:00:00+04:00", "author": "karim",
            "text": "The Raseef beta is ready for testers",
        }],
        "enqueue": "extract.live",
        "direct_fact": {
            "text": "The Raseef beta is ready for testers",
            "subject_id": "projects/dubai-io",
            "valid_from": "2026-11-23T14:00:00+04:00",
            "evidence": ["mgmsg:m-101"],
            "provenance": "user_supplied",
        },
    })
    assert created.status_code == 200
    body = created.json()
    assert body["ok"] is True and body["record_ids"] == ["mgmsg:m-101"]
    assert body["job_id"] and body["fact_ids"] and body["quarantined"] == 0
    fact = next(item for item in store.facts["karim"] if item.id == body["fact_ids"][0])
    assert fact.status == "active" and fact.provenance == "user_supplied"
    assert store.facts_version("karim") >= 1

    missing = client.post("/v1/owners/karim/records", headers=hdr, json={
        "records": [],
        "direct_fact": {
            "text": "No evidence", "subject_id": "projects/dubai-io",
            "valid_from": "2026-11-23T14:00:00+04:00", "evidence": [],
        },
    })
    assert missing.status_code == 422

    secret = client.post("/v1/owners/karim/records", headers=hdr, json={
        "records": [{
            "id": "mgmsg:secret", "source": "messenger:conv-42",
            "at": "2026-11-23T15:00:00+04:00", "author": "karim",
            "text": "my password is hunter2",
        }],
    })
    assert secret.status_code == 400
    assert "mgmsg:secret" not in store.records["karim"]


def test_crtm2_forget_erases_trims_and_requeues_live_jobs():
    store = FakeGraphStore()
    _owner(store)
    store.records["karim"]["r-only"] = Record(id="r-only", owner="karim", source="messenger:c1", at="2026-11-23T10:00:00+04:00", author="karim", text="only")
    store.records["karim"]["r-keep"] = Record(id="r-keep", owner="karim", source="gmail", at="2026-11-23T10:00:00+04:00", author="karim", text="keep")
    store.facts["karim"].extend([
        Fact(id="f-only", owner="karim", text="Only evidence fact", subject_id="s1", valid_from="2026-11-23", evidence=["r-only"], status="active", provenance="user_supplied"),
        Fact(id="f-shared", owner="karim", text="Shared evidence fact", subject_id="s1", valid_from="2026-11-23", evidence=["r-only", "r-keep"], status="active", provenance="user_supplied"),
    ])
    store.jobs.append(Job(
        id="live-1", owner="karim", kind="extract.live", priority=0, pool="internal",
        input_ref=["r-only", "r-keep"], input_version=0, context_hash="h", prompt_version="extract@3",
        day="2026-11-23", state="queued",
    ))
    client = _client(store)
    res = client.post("/v1/owners/karim/forget", headers={"Authorization": "Bearer karim-tok"}, json={
        "record_ids": ["r-only"], "fact_id": None, "idempotency_key": "forget-1",
    })
    assert res.status_code == 200
    body = res.json()
    assert body["facts_erased"] == 1 and body["facts_trimmed"] == 1
    visible = {fact.id for fact in store.visible_facts("karim", limit=20)}
    assert "f-only" not in visible and "f-shared" in visible
    job = next(item for item in store.jobs if item.id == "live-1")
    assert job.state == "queued" and job.input_ref == ["r-keep"]
    assert store.check_fence("karim", 0) == "fence_stale"


def test_crtm3_resolve_confirm_edit_reject():
    store = FakeGraphStore()
    _owner(store)
    store.records["karim"]["r1"] = Record(id="r1", owner="karim", source="gmail", at="2026-11-18T10:00:00+04:00", author="karim", text="note")
    store.facts["karim"].append(Fact(
        id="hyp-1", owner="karim", text="Karim might prefer shorebirds", subject_id="learning",
        valid_from="2026-11-18", evidence=["r1"], status="hypothesis", provenance="inferred",
    ))
    client = _client(store)
    hdr = {"Authorization": "Bearer karim-tok"}
    before = store.facts_version("karim")
    confirmed = client.post("/v1/owners/karim/facts/hyp-1/resolve", headers=hdr, json={"action": "confirm"}).json()
    assert confirmed["status"] == "active" and confirmed["facts_version"] == before + 1
    assert store.facts["karim"][0].provenance == "user_supplied"

    edited = client.post("/v1/owners/karim/facts/hyp-1/resolve", headers=hdr, json={
        "action": "edit", "new_text": "Karim prefers shorebird guides", "valid_from": "2026-11-20T00:00:00+04:00",
    }).json()
    assert edited["new_fact_id"] and edited["facts_version"] == before + 2
    assert edited["old_fact"] == {"id": "hyp-1", "status": "superseded"}
    assert edited["new_fact"] == {"id": edited["new_fact_id"], "status": "active"}
    old = next(fact for fact in store.facts["karim"] if fact.id == "hyp-1")
    assert old.status == "superseded" and old.superseded_by == edited["new_fact_id"] and old.valid_to

    rejected = client.post(f"/v1/owners/karim/facts/{edited['new_fact_id']}/resolve", headers=hdr, json={"action": "reject"}).json()
    assert rejected["status"] == "rejected" and rejected["facts_version"] == before + 3
    assert edited["new_fact_id"] not in {fact.id for fact in store.visible_facts("karim", limit=20)}


def test_crtm4_http_context_and_source_prefix_search():
    store = FakeGraphStore.from_karim_slice()
    store.records["karim"]["m1"] = Record(id="m1", owner="karim", source="messenger:c1", at="2026-11-23T10:00:00+04:00", author="karim", text="messenger one")
    store.records["karim"]["m2"] = Record(id="m2", owner="karim", source="messenger:c2", at="2026-11-23T10:00:00+04:00", author="karim", text="messenger two")
    store.records["karim"]["q1"] = Record(id="q1", owner="karim", source="quest:board", at="2026-11-23T10:00:00+04:00", author="karim", text="quest board")
    store.facts["karim"].extend([
        Fact(id="fm1", owner="karim", text="Shorebirds in conversation one", subject_id="th_career", valid_from="2026-11-23", evidence=["m1"], status="active", provenance="user_supplied"),
        Fact(id="fm2", owner="karim", text="Shorebirds in conversation two", subject_id="th_career", valid_from="2026-11-23", evidence=["m2"], status="active", provenance="user_supplied"),
        Fact(id="fq1", owner="karim", text="Shorebirds on the quest board", subject_id="th_career", valid_from="2026-11-23", evidence=["q1"], status="active", provenance="user_supplied"),
    ])
    client = _client(store)
    hdr = {"Authorization": "Bearer karim-tok"}
    http_pack = client.post("/v1/owners/karim/context", headers=hdr, json={"text": "Omar", "max_tokens": 1500}).json()
    direct = context_pack("karim", "Omar", max_tokens=1500, store=store)
    assert http_pack["owner"] == direct["owner"]
    assert [fact["id"] for fact in http_pack["facts"]] == [fact["id"] for fact in direct["facts"]]
    found = client.get("/v1/owners/karim/search", headers=hdr, params={"q": "Shorebirds", "source_prefix": "messenger:c1"}).json()
    ids = {fact["id"] for fact in found["facts"]}
    assert ids == {"fm1"}


def test_crtm2_forget_blocks_reimport():
    store = FakeGraphStore()
    _owner(store)
    client = _client(store)
    hdr = {"Authorization": "Bearer karim-tok"}
    payload = {
        "records": [{
            "id": "mgmsg:m-101", "source": "messenger:conv-42",
            "at": "2026-11-23T14:00:00+04:00", "author": "karim", "text": "beta note",
        }],
        "enqueue": "none",
    }
    assert client.post("/v1/owners/karim/records", headers=hdr, json=payload).status_code == 200
    forgotten = client.post("/v1/owners/karim/forget", headers=hdr, json={"record_ids": ["mgmsg:m-101"], "idempotency_key": "once"})
    assert forgotten.status_code == 200
    assert "mgmsg:m-101" in store.forget_rule_values["karim"]
    again = client.post("/v1/owners/karim/records", headers=hdr, json=payload)
    assert again.status_code == 409
