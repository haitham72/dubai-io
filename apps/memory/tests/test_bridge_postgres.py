"""CR-TM routes on PostgresGraphStore, including Forget cache invalidation."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api():
    from temporal_memory.api.app import create_app
    from temporal_memory.db import db as db_module
    from temporal_memory.db.db import create_test_schema, drop_test_schema

    db, schema = create_test_schema()
    previous = db_module._DEFAULT_DB
    db_module._DEFAULT_DB = db
    app = create_app(db, admin_token="adm")
    client = TestClient(app)
    admin = {"Authorization": "Bearer adm"}
    assert client.post("/v1/owners", headers=admin, json={
        "id": "karim", "label": "Karim", "kind": "simulated", "display_name": "Karim",
    }).status_code == 200
    assert client.post("/v1/owners", headers=admin, json={
        "id": "layla", "label": "Layla", "kind": "simulated", "display_name": "Layla",
    }).status_code == 200
    karim = client.post("/v1/tokens", headers=admin, json={
        "role": "owner-device", "owner": "karim", "label": "phone",
    }).json()["token"]
    layla = client.post("/v1/tokens", headers=admin, json={
        "role": "owner-device", "owner": "layla", "label": "phone",
    }).json()["token"]
    try:
        yield {
            "client": client,
            "db": db,
            "schema": schema,
            "karim": {"Authorization": f"Bearer {karim}"},
            "layla": {"Authorization": f"Bearer {layla}"},
        }
    finally:
        db_module._DEFAULT_DB = previous
        drop_test_schema(db, schema)


def _record(record_id: str, source: str, text: str, at: str) -> dict:
    return {"id": record_id, "source": source, "at": at, "author": "karim", "text": text}


def test_records_dedupe_enqueue_and_reject_bad_evidence(api):
    client, headers = api["client"], api["karim"]
    first = client.post("/v1/owners/karim/records", headers=headers, json={
        "records": [_record("n1", "notes:a", "harbour plan", "2026-11-01T09:00:00+04:00")],
        "enqueue": "extract.live",
    })
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["record_ids"] == ["n1"]
    assert body["job_id"]
    again = client.post("/v1/owners/karim/records", headers=headers, json={
        "records": [_record("n1-copy", "notes:a", "harbour plan", "2026-11-01T09:00:00+04:00")],
        "enqueue": "none",
    })
    assert again.status_code == 200
    assert again.json()["record_ids"] == ["n1"]
    missing = client.post("/v1/owners/karim/records", headers=headers, json={
        "records": [_record("n2", "notes:b", "other harbour", "2026-11-02T09:00:00+04:00")],
        "enqueue": "none",
        "direct_fact": {
            "text": "harbour plan stands",
            "subject_id": "notes",
            "valid_from": "2026-11-02",
            "evidence": ["does-not-exist"],
            "provenance": "user_supplied",
        },
    })
    assert missing.status_code == 422
    secret = client.post("/v1/owners/karim/records", headers=headers, json={
        "records": [_record("sec", "notes:c", "my password is swordfish", "2026-11-03T09:00:00+04:00")],
        "enqueue": "none",
    })
    assert secret.status_code == 400


def test_search_applies_source_prefix_before_limit(api, monkeypatch):
    monkeypatch.setenv("TM_SEMANTIC", "0")  # asserts lexical ordering; the semantic channel would reorder the equal-lexical hits
    client, headers = api["client"], api["karim"]
    records = [
        _record("m1", "messenger:c1", "harbour west", "2026-11-20T09:00:00+04:00"),
        _record("m2", "messenger:c2", "harbour east", "2026-11-21T09:00:00+04:00"),
        _record("n1", "notes:a", "harbour west", "2026-11-01T09:00:00+04:00"),
        _record("n2", "notes:b", "harbour east", "2026-11-02T09:00:00+04:00"),
    ]
    for record in records:
        created = client.post("/v1/owners/karim/records", headers=headers, json={
            "records": [record],
            "enqueue": "none",
            "direct_fact": {
                "text": record["text"] + " " + record["source"],
                "subject_path": "notes",
                "valid_from": record["at"][:10],
                "evidence": [record["id"]],
                "provenance": "user_supplied",
                "status": "active",
            },
        })
        assert created.status_code == 200, created.text
        assert created.json()["fact_ids"]
    unscoped = client.get("/v1/owners/karim/search", headers=headers, params={"q": "harbour", "limit": 2})
    assert unscoped.status_code == 200
    assert len(unscoped.json()["facts"]) == 2
    assert all(src.startswith("messenger:") for fact in unscoped.json()["facts"] for src in fact["sources"])
    prefixed = client.get("/v1/owners/karim/search", headers=headers, params={
        "q": "harbour", "limit": 2, "source_prefix": "notes:",
    })
    assert prefixed.status_code == 200
    facts = prefixed.json()["facts"]
    assert len(facts) == 2
    assert all(src.startswith("notes:") for fact in facts for src in fact["sources"])


def test_lower_hides_from_warm_context_and_restores(api):
    client, headers = api["client"], api["karim"]
    text = "Karim keeps a blue notebook in the drawer"
    created = client.post("/v1/owners/karim/records", headers=headers, json={
        "records": [_record("nb", "notes:drawer", text, "2026-11-04T09:00:00+04:00")],
        "enqueue": "none",
        "direct_fact": {
            "text": text,
            "subject_id": "notes",
            "valid_from": "2026-11-04",
            "evidence": ["nb"],
            "provenance": "user_supplied",
        },
    })
    assert created.status_code == 200, created.text
    fact_id = created.json()["fact_ids"][0]
    warm = client.post("/v1/owners/karim/context", headers=headers, json={"text": text, "max_tokens": 1500})
    assert warm.status_code == 200
    assert any(item["id"] == fact_id for item in warm.json()["facts"])
    lowered = client.post("/v1/owners/karim/lower", headers=headers, json={"fact_id": fact_id})
    assert lowered.json()["weight"] == 0.01
    assert lowered.json()["facts_erased"] == 0
    cold = client.post("/v1/owners/karim/context", headers=headers, json={"text": text})
    assert fact_id not in cold.text
    assert fact_id not in client.get("/v1/owners/karim/search", headers=headers, params={"q": "notebook"}).text
    vault = client.get("/v1/owners/karim/timeline", headers=headers, params={"lowered": True}).json()["items"]
    assert any(f["id"] == fact_id and f["lowered"] and f["weight"] == 0.01 for f in vault)
    with api["db"].connection() as conn:
        assert conn.execute("SELECT erased_at, text FROM facts WHERE id = %s", (fact_id,)).fetchone() == {
            "erased_at": None, "text": text,
        }
    assert client.post("/v1/owners/karim/restore", headers=headers, json={"fact_id": fact_id}).json()["lowered"] is False
    assert fact_id in client.post("/v1/owners/karim/context", headers=headers, json={"text": text}).text


def test_legacy_forget_alias_preserves_source_and_checks_owner(api):
    client = api["client"]
    created = client.post("/v1/owners/karim/records", headers=api["karim"], json={
        "records": [_record("gone", "messenger:c1", "harbour goodbye", "2026-11-05T09:00:00+04:00")],
        "enqueue": "extract.day",
    })
    assert created.status_code == 200, created.text
    forgotten = client.post("/v1/owners/karim/forget", headers=api["karim"], json={
        "record_ids": ["gone"], "idempotency_key": "gone-1",
    })
    assert forgotten.status_code == 200
    assert forgotten.json()["records"] == 1
    blocked = client.post("/v1/owners/karim/records", headers=api["karim"], json={
        "records": [_record("gone", "messenger:c1", "harbour goodbye", "2026-11-05T09:00:00+04:00")],
        "enqueue": "none",
    })
    assert blocked.status_code == 200
    with api["db"].connection() as conn:
        assert conn.execute("SELECT erased_at, text FROM records WHERE id = 'gone'").fetchone() == {
            "erased_at": None, "text": "harbour goodbye",
        }
    cross = client.post("/v1/owners/karim/forget", headers=api["layla"], json={"record_ids": ["gone"]})
    assert cross.status_code == 403


def test_resolve_confirm_edit_reject(api):
    client, headers = api["client"], api["karim"]
    created = client.post("/v1/owners/karim/records", headers=headers, json={
        "records": [_record("r1", "notes:a", "Karim likes the marina walk", "2026-11-06T09:00:00+04:00")],
        "enqueue": "none",
        "direct_fact": {
            "text": "Karim likes the marina walk",
            "subject_id": "notes",
            "valid_from": "2026-11-06",
            "evidence": ["r1"],
            "provenance": "inferred",
            "status": "hypothesis",
        },
    })
    fact_id = created.json()["fact_ids"][0]
    confirmed = client.post(f"/v1/owners/karim/facts/{fact_id}/resolve", headers=headers, json={"action": "confirm"})
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "active"
    edited = client.post(f"/v1/owners/karim/facts/{fact_id}/resolve", headers=headers, json={
        "action": "edit", "new_text": "Karim likes the marina walk at dusk", "valid_from": "2026-11-07",
    })
    assert edited.status_code == 200, edited.text
    assert edited.json()["new_fact_id"]
    body = edited.json()
    assert body["old_fact"] == {"id": fact_id, "status": "superseded"}
    assert body["new_fact"] == {"id": body["new_fact_id"], "status": "active"}
    assert body["status"] == "active"  # legacy field kept
    assert confirmed.json()["old_fact"] == {"id": fact_id, "status": "active"} and confirmed.json()["new_fact"] is None
    rejected = client.post(
        f"/v1/owners/karim/facts/{edited.json()['new_fact_id']}/resolve",
        headers=headers,
        json={"action": "reject"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    missing = client.get("/v1/owners/karim/search", headers=headers, params={"q": "dusk", "limit": 5})
    assert any(f["id"] == edited.json()["new_fact_id"] for f in missing.json()["facts"])
    with api["db"].connection() as conn:
        row = conn.execute("SELECT weight, lowered FROM memory_fact_weights WHERE id = %s",
                           (edited.json()["new_fact_id"],)).fetchone()
    assert row == {"weight": 0.5, "lowered": False}


def test_account_deletion_fences_leased_job(api, monkeypatch):
    monkeypatch.setenv("TM_REDIS_URL", "")
    from temporal_memory.models import Attempt, ExtractionOutput, OutFact, Worker
    from temporal_memory.queue.jobs import PostgresJobs

    client, headers = api["client"], api["karim"]
    created = client.post("/v1/owners/karim/records", headers=headers, json={
        "records": [_record("live1", "notes:a", "harbour lease", "2026-11-08T09:00:00+04:00")],
        "enqueue": "extract.day",
        "direct_fact": {
            "text": "harbour lease note",
            "subject_id": "notes",
            "valid_from": "2026-11-08",
            "evidence": ["live1"],
            "provenance": "user_supplied",
        },
    })
    assert created.status_code == 200, created.text
    jobs = PostgresJobs(api["db"], store=None)
    worker = Worker(id="w1", kind="internal-cloud", model="m", runner="anthropic", released=True)
    bundles = jobs.claim(worker, ["internal"], owner="karim", limit=1)
    assert bundles and bundles[0].job.fence_token
    leased = bundles[0].job
    forgotten = client.post("/v1/owners/karim/delete-my-data", headers={"Authorization": "Bearer adm"})
    assert forgotten.status_code == 200
    verdict = jobs.submit(Attempt(
        job_id=leased.id, attempt_no=leased.attempt_no, fence_token=leased.fence_token,
        worker_id="w1", worker_kind="internal-cloud", model="m", prompt_version=leased.prompt_version,
        output=ExtractionOutput(
            entities=[],
            facts=[OutFact(
                text="harbour lease", text_orig=None, subject_path="notes", entities=[],
                op="new", target=None, valid_from="2026-11-08", evidence=["live1"], sensitive=None,
            )],
            links=[],
        ),
    ))
    assert verdict.ok is False
    assert any("generation" in reason or "fence" in reason or "job_not_leased" in reason for reason in verdict.reasons)


def test_admin_warmup_is_admin_only_and_honest_when_semantic_off(api, monkeypatch):
    client = api["client"]
    assert client.post("/v1/admin/warmup", headers=api["karim"]).status_code == 403
    monkeypatch.setenv("TM_SEMANTIC", "0")
    body = client.post("/v1/admin/warmup", headers={"Authorization": "Bearer adm"}).json()
    assert body["ok"] is False and body["reason"] == "semantic_disabled"


@pytest.mark.parametrize("age, steps, confidence, provenance, lowered, expected", [
    (30, 0, 1.0, "inferred", False, 1.0),
    (60, 0, 1.0, "inferred", False, 0.5),
    (60, 2, 0.8, "inferred", False, 0.1),
    (600, 0, 1.0, "inferred", False, 0.05),
    (600, 8, 1.0, "inferred", False, 0.01),
    (600, 1, 1.0, "user_supplied", False, 0.5),
    (600, 0, 1.0, "provider_confirmed", False, 1.0),
    (0, 0, 1.0, "user_supplied", True, 0.01),
])
def test_memory_weight(api, age, steps, confidence, provenance, lowered, expected):
    with api["db"].connection() as conn:
        result = conn.execute("SELECT memory_weight(1.0,%s,%s,%s,%s,%s) AS w",
                              (confidence, age, steps, provenance, lowered)).fetchone()
    assert result["w"] == pytest.approx(expected)


def _seed_direct(api, headers, owner, record, source, subject, text, *, provenance="user_supplied"):
    created = api["client"].post(f"/v1/owners/{owner}/records", headers=headers, json={
        "records": [_record(record, source, text, "2026-11-25T09:00:00+04:00")],
        "enqueue": "none",
        "direct_fact": {"text": text, "subject_path": subject, "valid_from": "2026-11-25",
                        "evidence": [record], "provenance": provenance},
    })
    assert created.status_code == 200, created.text
    return created.json()["fact_ids"][0]


def test_source_lower_covers_future_import_and_restore(api):
    client, headers = api["client"], api["karim"]
    base = "/v1/owners/karim"
    client.post(f"{base}/lower", headers=headers, json={"source": "browser"}).raise_for_status()
    fact = _seed_direct(api, headers, "karim", "browser-1", "browser:history", "learning/research", "Blue notebook research")
    assert fact not in client.get(f"{base}/search", headers=headers, params={"q": "notebook"}).text
    assert fact not in client.post(f"{base}/context", headers=headers, json={"text": "notebook"}).text
    assert fact in client.get(f"{base}/timeline", headers=headers).text
    client.post(f"{base}/restore", headers=headers, json={"source": "browser"}).raise_for_status()
    assert fact in client.get(f"{base}/search", headers=headers, params={"q": "notebook"}).text


def test_account_deletion_purges_local_redis_and_excludes_owner(api, monkeypatch):
    import uuid
    import redis
    from temporal_memory.core import embed, retrieval
    from temporal_memory.live import context

    url = "redis://127.0.0.1:6390/0"
    monkeypatch.setenv("TM_REDIS_URL", url)
    monkeypatch.setenv("TM_SEMANTIC", "0")
    client, admin = api["client"], {"Authorization": "Bearer adm"}
    owner = "d19-" + uuid.uuid4().hex
    base = f"/v1/owners/{owner}"
    client.post("/v1/owners", headers=admin, json={"id": owner, "label": "Fixture Owner"}).raise_for_status()
    raw_token = client.post("/v1/tokens", headers=admin, json={"role": "owner-device", "owner": owner}).json()["token"]
    headers = {"Authorization": f"Bearer {raw_token}"}
    note = _seed_direct(api, headers, owner, "note", "notes", "learning/research", "Fixture note")
    _seed_direct(api, headers, owner, "gmail", "gmail:inbox", "career/work", "Fixture email")
    _seed_direct(api, headers, owner, "video", "takeout_youtube", "travel/air", "Fixture video")
    _seed_direct(api, headers, owner, "meeting", "calendar", "events/meeting", "Fixture calendar")
    assert note in client.post(f"{base}/context", headers=headers, json={"text": "Fixture note"}).text
    embed._PENDING[owner] = {"rows": []}
    embed._LAST_SWEEP_AT[owner] = 1.0
    key, unrelated = f"tm:owner:{owner}:context", f"tm:owner:{owner}b:context"
    with redis.Redis.from_url(url) as cache:
        cache.set(key, "owned", ex=120)
        cache.set(unrelated, "other", ex=120)
        try:
            assert client.post(f"{base}/delete-my-data", headers=headers).status_code == 403
            result = client.post(f"{base}/delete-my-data", headers=admin)
            assert result.status_code == 200, result.text
            assert result.json()["redis_purged"] is True and not cache.exists(key)
            assert cache.exists(unrelated)
            assert owner not in embed._PENDING and owner not in embed._LAST_SWEEP_AT
            assert owner not in context._PACK_CACHE and owner not in context._ALIAS_CACHE
            assert all(key[1] != owner for key in retrieval._LEARNED_CACHE)
            assert client.get(f"{base}/search", headers=headers).status_code == 401
            for path in ("search", "timeline", "vault/subjects", "vault/graph", "vocab/learned"):
                assert client.get(f"{base}/{path}", headers=admin).status_code == 403
            assert client.post(f"{base}/context", headers=admin, json={"text": "Fixture"}).status_code == 403
            assert client.post("/v1/tokens", headers=admin, json={"role": "owner-device", "owner": owner}).status_code == 403
            assert client.post(f"{base}/delete-my-data", headers=admin).json()["deleted_at"] == result.json()["deleted_at"]
            with api["db"].connection() as conn:
                rows = conn.execute("SELECT surrogate_id, signal_rows FROM training_backups").fetchall()
                assert len(rows) == 1 and str(rows[0]["surrogate_id"]) != owner
                assert rows[0]["signal_rows"] == [{"cluster": "learning", "count": 1}]
                assert conn.execute("SELECT count(*) AS n FROM visible_facts WHERE owner = %s", (owner,)).fetchone()["n"] == 0
                assert conn.execute("SELECT deletion_generation FROM owners WHERE id = %s", (owner,)).fetchone()["deletion_generation"] >= 1
        finally:
            cache.delete(key, unrelated)
