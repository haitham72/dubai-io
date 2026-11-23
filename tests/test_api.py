"""Tests for WP-A HTTP API (src/temporal_memory/api/app.py)."""
from __future__ import annotations

import hashlib
import sys
import types
import uuid
from typing import Iterator

from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb
import pytest

from temporal_memory.api.app import create_app
from temporal_memory.db.db import Database, create_test_schema, drop_test_schema
from temporal_memory.models import (
    Attempt,
    Job,
    JobBundle,
    Pool,
    Record,
    Verdict,
    Worker,
)

ADMIN_TOKEN = "test-admin-secret-token"


@pytest.fixture()
def isolated_db() -> Iterator[Database]:
    db, schema = create_test_schema()
    try:
        yield db
    finally:
        drop_test_schema(db, schema)


@pytest.fixture()
def client(isolated_db: Database) -> TestClient:
    app = create_app(isolated_db, admin_token=ADMIN_TOKEN)
    return TestClient(app)


def _admin_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}


def _issue_token(client: TestClient, role: str, owner: str | None = None, label: str = "") -> dict:
    resp = client.post(
        "/v1/tokens",
        headers=_admin_headers(),
        json={"role": role, "owner": owner, "label": label},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


class _SeededPostgresJobs:
    """Minimal Postgres-backed Jobs implementation for API roundtrip unit isolation."""

    def __init__(self, db: Database, store: object | None = None) -> None:
        self.db = db
        self.store = store
        self.submitted_attempts: list[Attempt] = []

    def claim(
        self,
        worker: Worker,
        pools: list[Pool],
        owner: str | None = None,
        day_from: str | None = None,
        day_to: str | None = None,
        limit: int = 1,
    ) -> list[JobBundle]:
        if not pools:
            return []
        clauses = ["state = 'queued'", "pool = ANY(%s)"]
        params: list[object] = [pools]
        if owner is not None:
            clauses.append("owner = %s")
            params.append(owner)
        if day_from is not None:
            clauses.append("day >= %s")
            params.append(day_from)
        if day_to is not None:
            clauses.append("day <= %s")
            params.append(day_to)
        params.append(limit)

        with self.db.transaction() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM jobs
                WHERE {' AND '.join(clauses)}
                ORDER BY priority ASC, created_at ASC
                LIMIT %s
                FOR UPDATE SKIP LOCKED
                """,
                params,
            ).fetchall()

            bundles: list[JobBundle] = []
            for row in rows:
                fence = f"fence_{uuid.uuid4().hex[:8]}"
                attempt_no = int(row["attempt_no"]) + 1
                conn.execute(
                    """
                    UPDATE jobs
                    SET state = 'leased', attempt_no = %s, fence_token = %s,
                        worker_id = %s, lease_expires_at = now() + interval '300 seconds'
                    WHERE id = %s
                    """,
                    (attempt_no, fence, worker.id, row["id"]),
                )
                rec_ids = list(row["input_ref"])
                rec_rows = conn.execute(
                    "SELECT id, owner, source, at, author, text, generation FROM records WHERE owner = %s AND id = ANY(%s)",
                    (row["owner"], rec_ids),
                ).fetchall()
                records = [
                    Record(
                        id=r["id"],
                        owner=r["owner"],
                        source=r["source"],
                        at=r["at"],
                        author=r["author"],
                        text=r["text"],
                        generation=r["generation"],
                    )
                    for r in rec_rows
                ]
                job = Job(
                    id=row["id"],
                    owner=row["owner"],
                    kind=row["kind"],
                    priority=row["priority"],
                    pool=row["pool"],
                    input_ref=rec_ids,
                    input_version=row["input_version"],
                    context_hash=row["context_hash"],
                    prompt_version=row["prompt_version"],
                    day=row["day"],
                    state="leased",
                    attempt_no=attempt_no,
                    fence_token=fence,
                    worker_id=worker.id,
                )
                bundles.append(
                    JobBundle(
                        job=job,
                        records=records,
                        context={"entities": [], "facts": [], "subjects": []},
                        system_prompt="Extract entities and facts.",
                        output_schema={"type": "object"},
                    )
                )
            return bundles

    def heartbeat(self, job_id: str, fence_token: str) -> bool:
        with self.db.transaction() as conn:
            row = conn.execute(
                """
                UPDATE jobs
                SET lease_expires_at = now() + interval '300 seconds', updated_at = now()
                WHERE id = %s AND state = 'leased' AND fence_token = %s
                RETURNING id
                """,
                (job_id, fence_token),
            ).fetchone()
        return row is not None

    def submit(self, attempt: Attempt) -> Verdict:
        self.submitted_attempts.append(attempt)
        with self.db.transaction() as conn:
            row = conn.execute(
                "SELECT owner, fence_token, state FROM jobs WHERE id = %s FOR UPDATE",
                (attempt.job_id,),
            ).fetchone()
            if row is None or row["state"] != "leased" or row["fence_token"] != attempt.fence_token:
                return Verdict(ok=False, reasons=["fence_stale"])

            conn.execute(
                """
                INSERT INTO job_attempts (
                    id, job_id, owner, attempt_no, fence_token, worker_id, worker_kind,
                    model, prompt_version, tokens_in, tokens_out, cost_usd, verdict
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ok')
                """,
                (
                    f"att_{uuid.uuid4().hex[:10]}",
                    attempt.job_id,
                    row["owner"],
                    attempt.attempt_no,
                    attempt.fence_token,
                    attempt.worker_id,
                    attempt.worker_kind,
                    attempt.model,
                    attempt.prompt_version,
                    attempt.tokens_in,
                    attempt.tokens_out,
                    attempt.cost_usd,
                ),
            )
            conn.execute("UPDATE jobs SET state = 'applied', updated_at = now() WHERE id = %s", (attempt.job_id,))

        fact_count = len(attempt.output.facts) if attempt.output else 0
        applied_ids = [f"f_{i + 1}" for i in range(fact_count)]
        return Verdict(ok=True, reasons=[], applied_fact_ids=applied_ids, quarantined={})


def test_health_unauthenticated(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "db": "ok"}


def test_auth_failures_401(client: TestClient) -> None:
    # Missing Authorization header
    assert client.post("/v1/owners", json={"id": "k1", "label": "Karim"}).status_code == 401
    # Wrong scheme
    assert client.post("/v1/owners", headers={"Authorization": "Basic abc"}, json={"id": "k1", "label": "Karim"}).status_code == 401
    # Unknown bearer token
    assert client.post("/v1/owners", headers={"Authorization": "Bearer unknown-tok"}, json={"id": "k1", "label": "Karim"}).status_code == 401

    # Revoked token -> 401
    issued = _issue_token(client, role="worker", label="w1")
    tok_headers = {"Authorization": f"Bearer {issued['token']}"}
    assert client.post(
        "/v1/workers/online",
        headers=tok_headers,
        json={"id": "w1", "kind": "agent-cli", "model": "claude-cli", "runner": "claude-cli"},
    ).status_code == 200

    del_resp = client.delete(f"/v1/tokens/{issued['id']}", headers=_admin_headers())
    assert del_resp.status_code == 200
    assert del_resp.json() == {"ok": True, "id": issued["id"]}

    assert client.post(
        "/v1/workers/online",
        headers=tok_headers,
        json={"id": "w1", "kind": "agent-cli", "model": "claude-cli", "runner": "claude-cli"},
    ).status_code == 401


def test_owners_and_tokens_admin_only(client: TestClient, isolated_db: Database) -> None:
    resp = client.post(
        "/v1/owners",
        headers=_admin_headers(),
        json={
            "id": "karim",
            "label": "Karim Haddad",
            "kind": "simulated",
            "display_name": "Karim",
            "self_aliases": ["Kimo", "كريم"],
            "timezone": "Asia/Dubai",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "karim"
    assert data["self_aliases"] == ["Kimo", "كريم"]

    with isolated_db.connection() as conn:
        row = conn.execute("SELECT id, label, kind, display_name, self_aliases, timezone FROM owners WHERE id = 'karim'").fetchone()
    assert row is not None
    assert row["label"] == "Karim Haddad"

    worker_tok = _issue_token(client, role="worker", label="ci-worker")
    owner_tok = _issue_token(client, role="owner-device", owner="karim", label="karim-mac")

    # Tokens stored as sha256 only
    with isolated_db.connection() as conn:
        db_tok = conn.execute("SELECT token_hash, role, owner FROM tokens WHERE id = %s", (owner_tok["id"],)).fetchone()
    assert db_tok is not None
    assert db_tok["token_hash"] == hashlib.sha256(owner_tok["token"].encode()).hexdigest()
    assert db_tok["role"] == "owner-device"
    assert db_tok["owner"] == "karim"

    # Non-admin -> 403 on owners & tokens
    for tok in (worker_tok["token"], owner_tok["token"]):
        hdr = {"Authorization": f"Bearer {tok}"}
        assert client.post("/v1/owners", headers=hdr, json={"id": "x", "label": "X"}).status_code == 403
        assert client.post("/v1/tokens", headers=hdr, json={"role": "worker"}).status_code == 403
        assert client.delete(f"/v1/tokens/{worker_tok['id']}", headers=hdr).status_code == 403


def test_workers_online_and_owner_device_restrictions(client: TestClient, isolated_db: Database) -> None:
    worker_tok = _issue_token(client, role="worker")
    owner_tok = _issue_token(client, role="owner-device", owner="karim")

    # Worker registers internal-cloud
    r1 = client.post(
        "/v1/workers/online",
        headers={"Authorization": f"Bearer {worker_tok['token']}"},
        json={
            "id": "w_cloud",
            "kind": "internal-cloud",
            "model": "claude-haiku-4-5-20251001",
            "model_version": "2025-10",
            "runner": "anthropic",
            "prompt_versions": ["extract@3"],
            "released": True,
        },
    )
    assert r1.status_code == 200
    assert r1.json()["status"] == "online"

    # owner-device cannot register non-owner-hook kind -> 403
    r2 = client.post(
        "/v1/workers/online",
        headers={"Authorization": f"Bearer {owner_tok['token']}"},
        json={"id": "w_bad", "kind": "internal-cloud", "model": "haiku", "runner": "anthropic"},
    )
    assert r2.status_code == 403

    # owner-device cannot register for another owner -> 403
    r3 = client.post(
        "/v1/workers/online",
        headers={"Authorization": f"Bearer {owner_tok['token']}"},
        json={"id": "w_bad2", "kind": "owner-hook", "model": "claude-sonnet", "runner": "mcp", "owner": "someone_else"},
    )
    assert r3.status_code == 403

    # owner-device registers owner-hook for self (owner inferred from token)
    r4 = client.post(
        "/v1/workers/online",
        headers={"Authorization": f"Bearer {owner_tok['token']}"},
        json={"id": "w_karim_hook", "kind": "owner-hook", "model": "claude-sonnet", "runner": "mcp"},
    )
    assert r4.status_code == 200
    assert r4.json()["owner"] == "karim"
    assert r4.json()["kind"] == "owner-hook"

    with isolated_db.connection() as conn:
        row = conn.execute("SELECT owner, status FROM workers WHERE id = 'w_karim_hook'").fetchone()
    assert row == {"owner": "karim", "status": "online"}


def test_claim_security_boundaries(client: TestClient, isolated_db: Database, monkeypatch: pytest.MonkeyPatch) -> None:
    worker_tok = _issue_token(client, role="worker")
    owner_tok = _issue_token(client, role="owner-device", owner="karim")

    captured_calls: list[dict] = []

    class _StubJobs:
        def __init__(self, db: Database, store: object | None = None) -> None:
            pass

        def claim(self, worker: Worker, pools: list[Pool], owner: str | None = None, **kwargs: object) -> list[JobBundle]:
            captured_calls.append({"worker": worker, "pools": pools, "owner": owner})
            return []

    fake_mod = types.ModuleType("temporal_memory.queue.jobs")
    fake_mod.PostgresJobs = _StubJobs  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "temporal_memory.queue.jobs", fake_mod)

    # Worker token claiming owner-device pool -> 403
    bad_worker = client.post(
        "/v1/jobs/claim",
        headers={"Authorization": f"Bearer {worker_tok['token']}"},
        json={
            "worker": {"id": "w1", "kind": "agent-cli", "model": "claude-cli", "runner": "claude-cli"},
            "pools": ["internal", "owner-device"],
        },
    )
    assert bad_worker.status_code == 403
    assert "owner-device" in bad_worker.json()["detail"]

    # owner-device token claiming another owner's jobs -> 403
    bad_owner = client.post(
        "/v1/jobs/claim",
        headers={"Authorization": f"Bearer {owner_tok['token']}"},
        json={
            "worker": {"id": "wh1", "kind": "owner-hook", "model": "claude", "runner": "mcp"},
            "pools": ["owner-device"],
            "owner": "other_user",
        },
    )
    assert bad_owner.status_code == 403

    # owner-device token sending internal pool -> forced to ["owner-device"] and owner="karim"
    ok_owner = client.post(
        "/v1/jobs/claim",
        headers={"Authorization": f"Bearer {owner_tok['token']}"},
        json={
            "worker": {"id": "wh1", "kind": "owner-hook", "model": "claude", "runner": "mcp"},
            "pools": ["internal"],
        },
    )
    assert ok_owner.status_code == 200
    assert ok_owner.json() == []
    assert len(captured_calls) == 1
    assert captured_calls[0]["pools"] == ["owner-device"]
    assert captured_calls[0]["owner"] == "karim"


def test_job_claim_heartbeat_result_roundtrip(
    client: TestClient, isolated_db: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Seed owners, records, and jobs directly in Postgres
    client.post("/v1/owners", headers=_admin_headers(), json={"id": "karim", "label": "Karim"})
    client.post("/v1/owners", headers=_admin_headers(), json={"id": "nora", "label": "Nora"})

    with isolated_db.transaction() as conn:
        conn.execute(
            """
            INSERT INTO records (id, owner, source, at, author, text, content_hash)
            VALUES
                ('r1', 'karim', 'whatsapp:work', '2026-04-01T10:00:00Z', 'Karim', 'Started new role at Careem', 'h1'),
                ('r2', 'nora', 'notes', '2026-04-01T11:00:00Z', 'Nora', 'Moved to Dubai', 'h2')
            """
        )
        conn.execute(
            """
            INSERT INTO jobs (id, owner, kind, priority, pool, input_ref, input_version, context_hash, prompt_version, day, idempotency_key)
            VALUES
                ('j_karim_od', 'karim', 'extract.day', 1, 'owner-device', %s, 0, 'ctx1', 'extract@3', '2026-04-01', 'ik_1'),
                ('j_nora_od', 'nora', 'extract.day', 1, 'owner-device', %s, 0, 'ctx2', 'extract@3', '2026-04-01', 'ik_2')
            """,
            (["r1"], ["r2"]),
        )

    jobs_impl = _SeededPostgresJobs(isolated_db)
    fake_mod = types.ModuleType("temporal_memory.queue.jobs")
    fake_mod.PostgresJobs = lambda db, store=None: jobs_impl  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "temporal_memory.queue.jobs", fake_mod)

    karim_tok = _issue_token(client, role="owner-device", owner="karim")
    karim_hdr = {"Authorization": f"Bearer {karim_tok['token']}"}

    # 1. Claim -> only karim's owner-device job is returned
    claim_resp = client.post(
        "/v1/jobs/claim",
        headers=karim_hdr,
        json={
            "worker": {"id": "wh_karim", "kind": "owner-hook", "model": "claude-sonnet", "runner": "mcp"},
            "pools": ["owner-device"],
            "limit": 5,
        },
    )
    assert claim_resp.status_code == 200
    bundles = claim_resp.json()
    assert len(bundles) == 1
    bundle = bundles[0]
    assert bundle["job"]["id"] == "j_karim_od"
    assert bundle["job"]["owner"] == "karim"
    assert len(bundle["records"]) == 1
    assert bundle["records"][0]["text"] == "Started new role at Careem"
    fence_token = bundle["job"]["fence_token"]
    assert fence_token

    # 2. Heartbeat -> ok=True with valid fence, ok=False with wrong fence
    hb_ok = client.post("/v1/jobs/j_karim_od/heartbeat", headers=karim_hdr, json={"fence_token": fence_token})
    assert hb_ok.status_code == 200
    assert hb_ok.json() == {"ok": True}

    hb_bad = client.post("/v1/jobs/j_karim_od/heartbeat", headers=karim_hdr, json={"fence_token": "wrong"})
    assert hb_bad.status_code == 200
    assert hb_bad.json() == {"ok": False}

    # Cross-owner heartbeat/submit blocked -> 403
    assert client.post("/v1/jobs/j_nora_od/heartbeat", headers=karim_hdr, json={"fence_token": "x"}).status_code == 403

    # owner-device must report worker_kind='owner-hook' -> 403
    bad_kind = client.post(
        "/v1/jobs/j_karim_od/result",
        headers=karim_hdr,
        json={
            "attempt_no": 1,
            "fence_token": fence_token,
            "worker_id": "wh_karim",
            "worker_kind": "internal-cloud",
            "model": "claude-sonnet",
            "prompt_version": "extract@3",
            "output": None,
        },
    )
    assert bad_kind.status_code == 403

    # 3. Result -> deserializes ExtractionOutput & forces cost_usd=0.0 for owner-hook
    res_resp = client.post(
        "/v1/jobs/j_karim_od/result",
        headers=karim_hdr,
        json={
            "attempt_no": 1,
            "fence_token": fence_token,
            "worker_id": "wh_karim",
            "worker_kind": "owner-hook",
            "model": "claude-sonnet",
            "prompt_version": "extract@3",
            "tokens_in": 120,
            "tokens_out": 45,
            "cost_usd": 1.25,
            "output": {
                "entities": [
                    {"ref": "new:Careem", "kind": "org", "aliases": ["Careem"], "relation_to_user": None},
                ],
                "facts": [
                    {
                        "text": "Karim started a new role at Careem",
                        "text_orig": None,
                        "subject_path": "career/job-search",
                        "entities": [{"entity_id": "new:Careem", "role": "employer"}],
                        "op": "new",
                        "target": None,
                        "valid_from": "2026-04-01",
                        "evidence": ["r1"],
                        "sensitive": None,
                    }
                ],
                "links": [
                    {
                        "src": "self",
                        "rel": "WORKS_AT",
                        "dst": "new:Careem",
                        "valid_from": "2026-04-01",
                        "evidence": ["r1"],
                    }
                ],
            },
        },
    )
    assert res_resp.status_code == 200
    verdict = res_resp.json()
    assert verdict == {"ok": True, "reasons": [], "applied_fact_ids": ["f_1"], "quarantined": {}}

    assert len(jobs_impl.submitted_attempts) == 1
    submitted = jobs_impl.submitted_attempts[0]
    assert isinstance(submitted, Attempt)
    assert submitted.cost_usd == 0.0
    assert submitted.output is not None
    assert submitted.output.entities[0].ref == "new:Careem"
    assert submitted.output.facts[0].entities[0].role == "employer"
    assert submitted.output.links[0].rel == "WORKS_AT"
