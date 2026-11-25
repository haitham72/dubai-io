"""Tests for CS-B2 config, schema, HttpTemporalMemoryClient, and FakeTemporalMemoryClient."""
from __future__ import annotations

import io
import json
import zipfile

import httpx
import pytest

from app.memory_bridge import (
    ConsentDeniedError,
    FakeTemporalMemoryClient,
    HttpTemporalMemoryClient,
    MemoryBridgeError,
    MemoryBridgeUnavailable,
    SensitiveContentError,
    TemporalMemoryClient,
    build_temporal_memory_client,
    ensure_memory_bridge_schema,
)
from tests.fixtures.contest_shared.db_fixtures import cs_postgres_isolation  # noqa: F401
from tests.fixtures.contest_shared.memory_bridge_fixtures import (  # noqa: F401
    fake_only,
    memory_bridge_env,
)
from tests.fixtures.contest_shared.memory_fixtures import (
    SYNTH_OWNER_A,
    SYNTH_OWNER_B,
    make_seeded_fake_client,
    make_sqlite_db,
)


# ---------------------------------------------------------------------- config
def test_config_defaults_to_fake_when_base_url_unset(monkeypatch):
    monkeypatch.delenv("MEMORY_BRIDGE_BACKEND", raising=False)
    monkeypatch.delenv("TM_BASE_URL", raising=False)
    monkeypatch.delenv("TM_SERVICE_TOKEN", raising=False)

    client = build_temporal_memory_client()
    assert isinstance(client, FakeTemporalMemoryClient)
    assert isinstance(client, TemporalMemoryClient)


def test_config_http_fails_closed_when_missing_env(monkeypatch):
    monkeypatch.setenv("MEMORY_BRIDGE_BACKEND", "http")
    monkeypatch.delenv("TM_BASE_URL", raising=False)
    monkeypatch.delenv("TM_SERVICE_TOKEN", raising=False)

    with pytest.raises(MemoryBridgeUnavailable):
        build_temporal_memory_client()

    monkeypatch.setenv("TM_BASE_URL", "https://tm.example.test")
    with pytest.raises(MemoryBridgeUnavailable):
        build_temporal_memory_client()


def test_config_rejects_invalid_backend_and_timeout(monkeypatch):
    monkeypatch.setenv("MEMORY_BRIDGE_BACKEND", "invalid_engine")
    with pytest.raises(MemoryBridgeUnavailable):
        build_temporal_memory_client()

    monkeypatch.setenv("MEMORY_BRIDGE_BACKEND", "fake")
    monkeypatch.setenv("TM_TIMEOUT_SECONDS", "-1")
    with pytest.raises(MemoryBridgeUnavailable):
        build_temporal_memory_client()


def test_config_builds_http_client_with_mock_transport(monkeypatch):
    monkeypatch.setenv("MEMORY_BRIDGE_BACKEND", "http")
    monkeypatch.setenv("TM_BASE_URL", "https://tm.example.test")
    monkeypatch.setenv("TM_SERVICE_TOKEN", "svc-tok")
    monkeypatch.setenv("TM_ADMIN_TOKEN", "adm-tok")
    monkeypatch.setenv("TM_TIMEOUT_SECONDS", "5.0")

    transport = httpx.MockTransport(lambda req: httpx.Response(200, json={"ok": True}))
    client = build_temporal_memory_client(transport=transport)
    assert isinstance(client, HttpTemporalMemoryClient)
    assert isinstance(client, TemporalMemoryClient)
    client.close()


# ---------------------------------------------------------------------- schema
def test_schema_creates_all_cs_tables_idempotently(tmp_path):
    db = make_sqlite_db(tmp_path)
    ensure_memory_bridge_schema(db)  # idempotent second call

    if getattr(db, "dialect", "sqlite") == "postgres":
        tables = {
            row[0]
            for row in db.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema()"
            ).fetchall()
        }
        indexes = {
            row[0]
            for row in db.execute(
                "SELECT indexname FROM pg_indexes WHERE schemaname = current_schema()"
            ).fetchall()
        }
    else:
        tables = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        indexes = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
        }
    assert {
        "cs_consent_grants",
        "cs_memory_record_refs",
        "cs_two_visit_signals",
        "cs_interest_projection_cache",
        "cs_memory_audit",
    } <= tables
    assert "cs_memory_audit_owner_at" in indexes

    # Verify PostgresDB.translate converts JSON -> JSONB cleanly for every DDL statement
    from app.db import PostgresDB
    from app.memory_bridge.schema import _DDL_STATEMENTS

    for stmt in _DDL_STATEMENTS:
        assert ";" not in stmt
        translated = PostgresDB.translate(stmt)
        if "JSON" in stmt:
            assert "JSONB" in translated
    db.close()


# --------------------------------------------------------- HttpTemporalMemoryClient
def test_http_client_endpoints_and_token_isolation():
    recorded: list[tuple[str, str, str, dict | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        auth = request.headers.get("authorization", "")
        body = json.loads(request.content.decode("utf-8")) if request.content else None
        recorded.append((request.method, request.url.path, auth, body))

        path = request.url.path
        if path == "/v1/owners":
            return httpx.Response(200, json={"id": body["id"], "label": body["label"]})
        if path == "/v1/tokens":
            return httpx.Response(200, json={"id": "tok_1", "token": "raw-dev-tok", "role": "owner-device", "owner": body["owner"]})
        if path == "/v1/tokens/tok_1":
            return httpx.Response(200, json={"ok": True, "id": "tok_1"})
        if path.endswith("/records"):
            return httpx.Response(200, json={"ok": True, "record_ids": ["r1"], "job_id": "j1", "fact_ids": ["f1"], "quarantined": 0})
        if path.endswith("/lower"):
            return httpx.Response(200, json={"ok": True, "generation": 2, "records": 1, "facts_erased": 0, "facts_trimmed": 0, "entity_subjects_recomputed": 0, "jobs_requeued": 0, "jobs_enqueued": 0})
        if path.endswith("/resolve"):
            return httpx.Response(200, json={"ok": True, "fact_id": "f1", "new_fact_id": None, "status": "active", "facts_version": 2})
        if path.endswith("/vault/subjects"):
            return httpx.Response(200, json={"owner": SYNTH_OWNER_A, "themes": [], "total_facts": 0})
        if path.endswith("/vault/people"):
            return httpx.Response(200, json={"owner": SYNTH_OWNER_A, "people": [], "places": [], "orgs": [], "links": []})
        if path.endswith("/hypotheses"):
            return httpx.Response(200, json={"owner": SYNTH_OWNER_A, "hypotheses": []})
        if path.endswith("/timeline"):
            return httpx.Response(200, json={"owner": SYNTH_OWNER_A, "items": []})
        if path.endswith("/why/f1"):
            return httpx.Response(200, json={"owner": SYNTH_OWNER_A, "fact_id": "f1", "evidence": []})
        if path.endswith("/export/md.zip"):
            return httpx.Response(200, content=b"PK\x03\x04fakezip")
        if path.endswith("/context"):
            return httpx.Response(200, json={"owner": SYNTH_OWNER_A, "facts": [{"id": "f1"}]})
        if path.endswith("/search"):
            assert request.url.params.get("source_prefix") == "messenger:conv-a"
            return httpx.Response(200, json={"facts": [{"id": "f1", "sources": ["messenger:conv-a"]}]})
        return httpx.Response(404, json={"detail": "unknown"})

    client = HttpTemporalMemoryClient(
        base_url="https://tm.example.test",
        service_token="svc-fallback",
        admin_token="adm-secret",
        transport=httpx.MockTransport(handler),
        owner_token_resolver=lambda owner_id: f"dev-tok-{owner_id}",
    )

    assert client.ensure_owner(SYNTH_OWNER_A, label="Alpha")["id"] == SYNTH_OWNER_A
    tok = client.mint_owner_device_token(SYNTH_OWNER_A, label="cs-bridge")
    assert tok["id"] == "tok_1"
    assert client.revoke_token("tok_1")["ok"] is True

    up = client.upsert_record_and_enqueue(
        SYNTH_OWNER_A,
        record_id="r1",
        source="messenger:conv-a",
        at="2026-11-23T10:00:00Z",
        author=SYNTH_OWNER_A,
        text="Sprint complete.",
        direct_fact={"text": "Sprint complete.", "evidence": ["r1"]},
    )
    assert up["fact_ids"] == ["f1"]
    assert client.context_pack(SYNTH_OWNER_A, "sprint")["facts"][0]["id"] == "f1"
    assert client.search_facts(SYNTH_OWNER_A, "sprint", source_prefix="messenger:conv-a")[0]["id"] == "f1"
    assert client.get_vault_subjects(SYNTH_OWNER_A)["owner"] == SYNTH_OWNER_A
    assert client.get_vault_people(SYNTH_OWNER_A)["owner"] == SYNTH_OWNER_A
    assert client.get_hypotheses(SYNTH_OWNER_A)["hypotheses"] == []
    assert client.get_timeline(SYNTH_OWNER_A, date_from="2026-11-01")["items"] == []
    assert client.get_why_fact(SYNTH_OWNER_A, "f1")["fact_id"] == "f1"
    assert client.resolve_fact(SYNTH_OWNER_A, "f1", action="confirm")["status"] == "active"
    assert client.forget_source(SYNTH_OWNER_A, ["r1"])["facts_erased"] == 0
    assert client.forget_fact(SYNTH_OWNER_A, "f1")["ok"] is True
    assert client.export_markdown_zip(SYNTH_OWNER_A).startswith(b"PK")

    # Admin token used ONLY for /v1/owners and /v1/tokens*; per-user token for owner routes.
    for _, path, auth, _ in recorded:
        if path.startswith("/v1/owners/" + SYNTH_OWNER_A):
            assert auth == f"Bearer dev-tok-{SYNTH_OWNER_A}"
        else:
            assert auth == "Bearer adm-secret"
    client.close()


def test_http_client_mcp_fallback_on_404():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/context") or request.url.path.endswith("/search"):
            return httpx.Response(404, json={"detail": "not yet deployed"})
        if request.url.path == "/mcp":
            payload = json.loads(request.content.decode("utf-8"))
            tool = payload["params"]["name"]
            if tool == "memory_context":
                return httpx.Response(
                    200,
                    json={"jsonrpc": "2.0", "id": payload["id"], "result": {"structuredContent": {"owner": SYNTH_OWNER_A, "facts": [{"id": "f-ctx"}]}}},
                )
            if tool == "memory_search":
                return httpx.Response(
                    200,
                    json={
                        "jsonrpc": "2.0",
                        "id": payload["id"],
                        "result": {
                            "structuredContent": {
                                "facts": [
                                    {"id": "f-a", "sources": ["messenger:conv-a"]},
                                    {"id": "f-b", "sources": ["messenger:conv-b"]},
                                ]
                            }
                        },
                    },
                )
        return httpx.Response(500)

    client = HttpTemporalMemoryClient(
        base_url="https://tm.example.test",
        service_token="svc-tok",
        transport=httpx.MockTransport(handler),
    )
    ctx = client.context_pack(SYNTH_OWNER_A, "hello")
    assert ctx["facts"][0]["id"] == "f-ctx"

    hits = client.search_facts(SYNTH_OWNER_A, "hello", source_prefix="messenger:conv-a")
    assert [h["id"] for h in hits] == ["f-a"]
    client.close()


def test_http_client_failure_paths():
    # Missing admin token fails closed on provisioning
    no_adm = HttpTemporalMemoryClient(
        base_url="https://tm.example.test",
        service_token="svc-tok",
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json={})),
    )
    with pytest.raises(MemoryBridgeUnavailable):
        no_adm.ensure_owner(SYNTH_OWNER_A, label="A")
    no_adm.close()

    # Network error -> MemoryBridgeUnavailable
    def net_boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    c_net = HttpTemporalMemoryClient(
        base_url="https://tm.example.test",
        service_token="svc-tok",
        transport=httpx.MockTransport(net_boom),
    )
    with pytest.raises(MemoryBridgeUnavailable):
        c_net.get_timeline(SYNTH_OWNER_A)
    c_net.close()

    # 5xx -> MemoryBridgeUnavailable; 403 -> ConsentDeniedError; 400 credential -> SensitiveContentError
    def status_handler(request: httpx.Request) -> httpx.Response:
        if "503" in request.url.path:
            return httpx.Response(503, json={"detail": "down"})
        if "403" in request.url.path:
            return httpx.Response(403, json={"detail": "cross-owner forbidden"})
        return httpx.Response(400, json={"detail": "blocked credential", "category": "credential"})

    c_err = HttpTemporalMemoryClient(
        base_url="https://tm.example.test",
        service_token="svc-tok",
        transport=httpx.MockTransport(status_handler),
    )
    with pytest.raises(MemoryBridgeUnavailable):
        c_err.get_vault_subjects("owner-503")
    with pytest.raises(ConsentDeniedError):
        c_err.get_vault_subjects("owner-403")
    with pytest.raises(SensitiveContentError):
        c_err.upsert_record_and_enqueue(
            SYNTH_OWNER_A,
            record_id="r1",
            source="quest:t1",
            at="2026-11-23T00:00:00Z",
            author=SYNTH_OWNER_A,
            text="clean",
        )
    c_err.close()


# ------------------------------------------------------- FakeTemporalMemoryClient
@fake_only
def test_fake_client_token_roles_and_owner_isolation():
    fake = make_seeded_fake_client()
    adm_tok = fake.register_token("admin", label="adm")["token"]
    worker_tok = fake.register_token("worker", label="wrk")["token"]
    a_tok_info = fake.as_scoped(adm_tok).mint_owner_device_token(SYNTH_OWNER_A)
    a_client = fake.as_scoped(a_tok_info["token"])

    # Owner A reads own facts, never sees Owner B's facts
    a_hits = a_client.search_facts(SYNTH_OWNER_A, "")
    assert all(h["owner"] == SYNTH_OWNER_A for h in a_hits)
    assert not any("Al Qudra" in h["text"] for h in a_hits)

    # Cross-owner owner-device token -> 403 ConsentDeniedError
    with pytest.raises(ConsentDeniedError) as exc_cross:
        a_client.get_vault_subjects(SYNTH_OWNER_B)
    assert exc_cross.value.status_code == 403

    # Worker token -> 403 ConsentDeniedError on vault/owner endpoints
    w_client = fake.as_scoped(worker_tok)
    with pytest.raises(ConsentDeniedError) as exc_wrk:
        w_client.get_vault_people(SYNTH_OWNER_A)
    assert exc_wrk.value.status_code == 403

    # Revoked token immediately fails 401
    fake.as_scoped(adm_tok).revoke_token(a_tok_info["id"])
    with pytest.raises(ConsentDeniedError) as exc_rev:
        a_client.get_timeline(SYNTH_OWNER_A)
    assert exc_rev.value.status_code == 401


@fake_only
def test_fake_client_source_prefix_isolation():
    fake = make_seeded_fake_client()
    conv_a = fake.search_facts(SYNTH_OWNER_A, "", source_prefix="messenger:conv-a")
    assert [f["id"] for f in conv_a] == ["fact-mg-a1"]
    conv_b = fake.search_facts(SYNTH_OWNER_A, "", source_prefix="messenger:conv-b")
    assert [f["id"] for f in conv_b] == ["fact-mg-b1"]


@fake_only
def test_fake_client_forget_erase_trim_fence_and_reimport():
    fake = make_seeded_fake_client()

    # Upsert two records + a shared multi-source fact + an extract.live job
    r1 = fake.upsert_record_and_enqueue(
        SYNTH_OWNER_A,
        record_id="rec-live-1",
        source="messenger:conv-x",
        at="2026-11-23T10:00:00Z",
        author=SYNTH_OWNER_A,
        text="Alpha enjoys padel.",
        enqueue="extract.live",
    )
    assert r1["job_id"] is not None

    # Create a multi-source fact supported by BOTH rec-live-1 and qmsg:q-1
    fake.upsert_record_and_enqueue(
        SYNTH_OWNER_A,
        record_id="rec-keep-2",
        source="quest:thread-2",
        at="2026-11-23T10:05:00Z",
        author=SYNTH_OWNER_A,
        text="Alpha plays padel weekly.",
        enqueue="none",
        direct_fact={
            "id": "fact-shared",
            "text": "Alpha plays padel every week.",
            "subject_path": "lifestyle/padel",
            "valid_from": "2026-11-23T10:05:00Z",
            "evidence": ["rec-live-1", "rec-keep-2"],
        },
    )
    # Also create an only-evidence fact for rec-live-1
    fake.upsert_record_and_enqueue(
        SYNTH_OWNER_A,
        record_id="rec-only-3",
        source="messenger:conv-x",
        at="2026-11-23T10:10:00Z",
        author=SYNTH_OWNER_A,
        text="Only-evidence temporary note.",
        enqueue="none",
        direct_fact={
            "id": "fact-only",
            "text": "Only-evidence temporary note.",
            "subject_path": "projects/temp",
            "valid_from": "2026-11-23T10:10:00Z",
            "evidence": ["rec-only-3"],
        },
    )

    # Capture old generation before forget
    stale_version = fake.records[SYNTH_OWNER_A]["rec-live-1"].generation

    res = fake.forget_source(SYNTH_OWNER_A, ["rec-live-1", "rec-only-3"])
    assert res["records"] == 2
    assert res["facts_erased"] == 1
    assert res["facts_trimmed"] == 1
    assert res["generation"] >= 2

    # Only-evidence fact erased; multi-source fact trimmed & still visible!
    visible_ids = {f["id"] for f in fake.search_facts(SYNTH_OWNER_A, "")}
    assert "fact-only" not in visible_ids
    assert "fact-shared" in visible_ids
    shared = next(f for f in fake.search_facts(SYNTH_OWNER_A, "padel") if f["id"] == "fact-shared")
    assert shared["evidence"] == ["rec-keep-2"]

    # Stale worker submission rejected by generation fence (zero resurrection)
    verdict = fake.simulate_worker_submit(
        SYNTH_OWNER_A,
        "rec-live-1",
        stale_version,
        "Resurrected fact",
    )
    assert verdict == {"ok": False, "verdict": "fence_stale", "reason": "generation_stale"}

    # Re-importing forgotten record_id is blocked by forget_rules
    with pytest.raises(ConsentDeniedError):
        fake.upsert_record_and_enqueue(
            SYNTH_OWNER_A,
            record_id="rec-live-1",
            source="messenger:conv-x",
            at="2026-11-23T11:00:00Z",
            author=SYNTH_OWNER_A,
            text="Re-import attempt",
        )


@fake_only
def test_fake_client_direct_fact_validation_resolve_and_export():
    fake = make_seeded_fake_client()

    # direct_fact missing evidence fails closed
    with pytest.raises(MemoryBridgeError):
        fake.upsert_record_and_enqueue(
            SYNTH_OWNER_A,
            record_id="rec-no-ev",
            source="quest:t",
            at="2026-11-23T10:00:00Z",
            author=SYNTH_OWNER_A,
            text="Text",
            direct_fact={"text": "No evidence", "evidence": []},
        )

    # Credential in direct_fact fails closed & records category-only quarantine
    with pytest.raises(SensitiveContentError) as exc_cred:
        fake.upsert_record_and_enqueue(
            SYNTH_OWNER_A,
            record_id="rec-cred",
            source="quest:t",
            at="2026-11-23T10:00:00Z",
            author=SYNTH_OWNER_A,
            text="clean",
            direct_fact={"text": "My OTP 482910", "evidence": ["rec-cred"]},
        )
    assert exc_cred.value.category == "credential"
    assert "482910" not in str(exc_cred.value)

    # Hypothesis -> confirm / edit / reject lifecycle + worker submit happy path
    fake.upsert_record_and_enqueue(
        SYNTH_OWNER_A,
        record_id="rec-ok-w",
        source="quest:t2",
        at="2026-11-23T12:00:00Z",
        author=SYNTH_OWNER_A,
        text="Alpha reads architecture books.",
        enqueue="extract.live",
    )
    ver = fake.records[SYNTH_OWNER_A]["rec-ok-w"].generation
    applied = fake.simulate_worker_submit(
        SYNTH_OWNER_A,
        "rec-ok-w",
        ver,
        "Alpha reads distributed systems books.",
        subject_path="learning/systems",
    )
    assert applied["ok"] is True
    hyp_id = applied["fact_id"]
    assert any(h["id"] == hyp_id for h in fake.get_hypotheses(SYNTH_OWNER_A)["hypotheses"])

    conf = fake.resolve_fact(SYNTH_OWNER_A, hyp_id, action="confirm")
    assert conf["status"] == "active"

    sup = fake.resolve_fact(
        SYNTH_OWNER_A,
        hyp_id,
        action="supersede",
        new_text="Alpha studies consensus protocols.",
    )
    assert sup["status"] == "superseded"
    new_fid = sup["new_fact_id"]
    assert fake.get_why_fact(SYNTH_OWNER_A, new_fid)["fact_id"] == new_fid

    # Markdown ZIP export keeps held-back category counts only (never secret text)
    raw_zip = fake.export_markdown_zip(SYNTH_OWNER_A)
    with zipfile.ZipFile(io.BytesIO(raw_zip), "r") as zf:
        names = set(zf.namelist())
        assert {"memory/MEMORIES.md", "memory/noticed.md", "memory/held-back.md"} <= names
        held = zf.read("memory/held-back.md").decode("utf-8")
        assert "credential" in held
        assert "482910" not in held

    # Additional happy/failure paths: edit, reject, forget_fact, context_pack, timeline filters, token errors
    with pytest.raises(MemoryBridgeError):
        fake.resolve_fact(SYNTH_OWNER_A, new_fid, action="edit", new_text="  ")
    edited = fake.resolve_fact(SYNTH_OWNER_A, new_fid, action="edit", new_text="Alpha studies Raft consensus.")
    edited_id = edited["new_fact_id"]
    ctx = fake.context_pack(SYNTH_OWNER_A, "Raft consensus")
    assert any(f["id"] == edited_id for f in ctx["facts"])

    tl = fake.get_timeline(SYNTH_OWNER_A, date_from="2026-11-20", date_to="2026-11-21")
    assert all("2026-11-20" <= item["valid_from"][:10] <= "2026-11-21" for item in tl["items"])

    fake.resolve_fact(SYNTH_OWNER_A, edited_id, action="reject")
    assert any(f["id"] == edited_id and f["weight"] == 0.5 for f in fake.search_facts(SYNTH_OWNER_A, "Raft"))

    ff = fake.forget_fact(SYNTH_OWNER_A, "fact-q-1")
    assert ff["facts_erased"] == 1
    with pytest.raises(MemoryBridgeError):
        fake.get_why_fact(SYNTH_OWNER_A, "fact-q-1")

    with pytest.raises(MemoryBridgeError):
        fake.register_token("owner-device", owner=None)
    with pytest.raises(MemoryBridgeError):
        fake.revoke_token("tok_does_not_exist")


def test_tm_client_contract_roundtrip(memory_bridge_env):
    """TemporalMemoryClient contract works identically across fake and live HTTP backends."""
    client = memory_bridge_env.client
    owner_a = memory_bridge_env.owner_id("contract_a")
    owner_b = memory_bridge_env.owner_id("contract_b")
    client.ensure_owner(owner_a, label=owner_a, display_name="Contract Alpha", kind="demo")
    client.ensure_owner(owner_b, label=owner_b, display_name="Contract Beta", kind="demo")

    up_a = client.upsert_record_and_enqueue(
        owner_a,
        record_id="mgmsg:c-a1",
        source="messenger:conv-a",
        at="2026-11-23T10:00:00Z",
        author=owner_a,
        text="Alpha studies consensus protocols.",
        enqueue="none",
        direct_fact={
            "text": "Alpha studies consensus protocols.",
            "subject_path": "learning/consensus",
            "valid_from": "2026-11-23T10:00:00Z",
            "evidence": ["mgmsg:c-a1"],
            "provenance": "user_supplied",
        },
    )
    memory_bridge_env.track_record(owner_a, "mgmsg:c-a1")
    fid_a = up_a["fact_ids"][0]

    up_b = client.upsert_record_and_enqueue(
        owner_b,
        record_id="mgmsg:c-b1",
        source="messenger:conv-b",
        at="2026-11-23T10:05:00Z",
        author=owner_b,
        text="Beta cycles in Al Qudra.",
        enqueue="none",
        direct_fact={
            "text": "Beta cycles in Al Qudra.",
            "subject_path": "lifestyle/cycling",
            "valid_from": "2026-11-23T10:05:00Z",
            "evidence": ["mgmsg:c-b1"],
            "provenance": "user_supplied",
        },
    )
    memory_bridge_env.track_record(owner_b, "mgmsg:c-b1")
    assert up_b["ok"] is True

    hits_a = client.search_facts(owner_a, "consensus", source_prefix="messenger:conv-a")
    assert [h["id"] for h in hits_a] == [fid_a]
    assert client.search_facts(owner_a, "Al Qudra") == []
    assert client.search_facts(owner_a, "consensus", source_prefix="messenger:conv-b") == []

    ctx = client.context_pack(owner_a, "consensus")
    assert any(f["id"] == fid_a for f in ctx["facts"])
    assert client.get_vault_subjects(owner_a)["owner"] == owner_a
    assert client.get_vault_people(owner_a)["owner"] == owner_a
    assert client.get_hypotheses(owner_a)["owner"] == owner_a
    assert any(i["id"] == fid_a for i in client.get_timeline(owner_a)["items"])
    assert client.get_why_fact(owner_a, fid_a)["fact_id"] == fid_a

    edited = client.resolve_fact(owner_a, fid_a, action="edit", new_text="Alpha studies Raft consensus.")
    new_fid = edited["new_fact_id"]
    assert new_fid is not None
    assert client.get_why_fact(owner_a, new_fid)["fact_id"] == new_fid

    raw_zip = client.export_markdown_zip(owner_a)
    with zipfile.ZipFile(io.BytesIO(raw_zip), "r") as zf:
        assert "memory/MEMORIES.md" in set(zf.namelist())

    fg = client.forget_source(owner_a, ["mgmsg:c-a1"])
    assert fg["ok"] is True
    assert client.search_facts(owner_a, "Raft") == []
