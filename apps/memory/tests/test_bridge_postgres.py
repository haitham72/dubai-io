"""CR-TM routes on PostgresGraphStore, including Forget cache invalidation."""
from __future__ import annotations

import json
import os
import subprocess
import sys

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


def test_search_applies_source_prefix_before_limit(api):
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


def test_forget_drops_warm_context_and_is_durable(api):
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
    forgotten = client.post("/v1/owners/karim/forget", headers=headers, json={
        "record_ids": [],
        "fact_id": fact_id,
        "idempotency_key": "forget-nb",
    })
    assert forgotten.status_code == 200, forgotten.text
    assert forgotten.json()["facts_erased"] == 1
    cold = client.post("/v1/owners/karim/context", headers=headers, json={"text": text, "max_tokens": 1500})
    assert all(item["id"] != fact_id for item in cold.json()["facts"])
    again = client.post("/v1/owners/karim/forget", headers=headers, json={
        "record_ids": [],
        "fact_id": fact_id,
        "idempotency_key": "forget-nb",
    })
    assert again.json() == forgotten.json()

    env = os.environ.copy()
    env["TM_TEST_DATABASE_URL"] = api["db"].dsn
    env["TM_SCHEMA"] = api["schema"]
    env["PYTHONPATH"] = os.path.join(os.path.dirname(__file__), "..", "src")
    script = (
        "import json, os\n"
        "from temporal_memory.core.bridge_store import forget\n"
        "from temporal_memory.core.graph_store import PostgresGraphStore\n"
        "from temporal_memory.db.db import Database\n"
        "from temporal_memory.db import db as db_module\n"
        "db = Database(os.environ['TM_TEST_DATABASE_URL'], schema=os.environ['TM_SCHEMA'])\n"
        "db_module._DEFAULT_DB = db\n"
        "print(json.dumps(forget(PostgresGraphStore(db), 'karim', [], %r, 'forget-nb')))\n" % fact_id
    )
    with api["db"].connection() as conn:
        before = conn.execute(
            "SELECT facts_version, privacy_revision FROM owners WHERE id = 'karim'"
        ).fetchone()
    assert int(before["facts_version"]) >= 1
    assert int(before["privacy_revision"]) >= 1
    proc = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["facts_erased"] == 1
    with api["db"].connection() as conn:
        after = conn.execute(
            "SELECT facts_version, privacy_revision FROM owners WHERE id = 'karim'"
        ).fetchone()
    assert int(after["facts_version"]) == int(before["facts_version"])
    assert int(after["privacy_revision"]) == int(before["privacy_revision"])


def test_forget_blocks_reimport_and_cross_owner(api):
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
    assert blocked.status_code == 409
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
    assert missing.json()["facts"] == []


def test_leased_job_submit_is_generation_stale(api):
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
    forgotten = client.post("/v1/owners/karim/forget", headers=headers, json={"record_ids": ["live1"]})
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
    assert any("generation" in reason or "fence" in reason for reason in verdict.reasons)
