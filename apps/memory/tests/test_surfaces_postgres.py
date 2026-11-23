"""Parametrised FakeGraphStore vs PostgresGraphStore surface tests (contract v1.1)."""
from __future__ import annotations

import json
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from temporal_memory.api import export_md, ops, vault
from temporal_memory.api.app import create_app
from temporal_memory.api.vault import AuthContext
from temporal_memory.core.applier import apply
from temporal_memory.core.graph_store import PostgresGraphStore
from temporal_memory.db.db import create_test_schema, drop_test_schema
from temporal_memory.live.context import context_pack, invalidate_alias_cache
from temporal_memory.models import (
    Attempt,
    ExtractionOutput,
    FactEntity,
    GraphStoreFull,
    Job,
    OutEntity,
    OutFact,
    OutLink,
    Owner,
    Record,
)
from temporal_memory.reflect import reflect_week
from tests.fixtures.fake_store import FakeGraphStore


def _seed_postgres_karim(db, store: PostgresGraphStore) -> None:
    store.create_owner(
        Owner(id="karim", label="Karim Haddad", kind="real", display_name="Karim Haddad", self_aliases=["Karim", "Kimo"])
    )
    store.upsert_records(
        "karim",
        [
            Record(id="n001", owner="karim", source="notes", at="2026-10-20T09:00:00Z", author="Karim", text="31yo AI engineer at QamarTech, living in Al Barsha."),
            Record(id="g012", owner="karim", source="gmail", at="2026-10-20T12:00:00Z", author="DarProperty", text="Tenancy renewal AED 5,000/month in Al Barsha."),
            Record(id="g081", owner="karim", source="gmail", at="2026-11-01T10:00:00Z", author="DarProperty", text="Updated Al Barsha rent AED 5,400/month effective Nov 1."),
            Record(id="wab-0032", owner="karim", source="whatsapp:best", at="2026-10-23T18:10:00Z", author="3omar", text="Event with Rana set for Dec 18, 2026 at Zabeel Hall."),
            Record(id="wag-0014", owner="karim", source="whatsapp:work", at="2026-10-21T10:30:00Z", author="Salma Nasser", text="Omar El-Sayed joined Atlas squad at QamarTech billing."),
            Record(id="n011", owner="karim", source="notes", at="2026-11-04T08:00:00Z", author="Karim", text="كورس الوكلاء الذكية يبدأ ١٦ نوفمبر (LLM agents cohort)."),
        ],
    )
    out = ExtractionOutput(
        entities=[
            OutEntity(ref="new:Karim Haddad", kind="person", aliases=["Kimo"], relation_to_user="self"),
            OutEntity(ref="new:Omar Farouk", kind="person", aliases=["Omar", "عمر", "3omar"], relation_to_user="friend"),
            OutEntity(ref="new:Omar El-Sayed", kind="person", aliases=["Omar", "Omar El-Sayed"], relation_to_user="colleague"),
            OutEntity(ref="new:QamarTech", kind="org", aliases=[], relation_to_user=None),
            OutEntity(ref="new:Zabeel Hall", kind="place", aliases=[], relation_to_user=None),
        ],
        facts=[
            OutFact(text="Karim lives in Al Barsha and rents for AED 5,000", text_orig=None, subject_path="money/al-barsha-rent", entities=[FactEntity("new:Karim Haddad", "tenant")], op="new", target=None, valid_from="2026-10-20", evidence=["g012"], sensitive=None),
            OutFact(text="Omar Farouk booked Zabeel Hall on Dec 18", text_orig="فرح عمر اتنقل لقاعة زعبيل", subject_path="lifestyle/omar-event", entities=[FactEntity("new:Omar Farouk", "host"), FactEntity("new:Zabeel Hall", "venue")], op="new", target=None, valid_from="2026-10-23", evidence=["wab-0032"], sensitive=None),
            OutFact(text="Omar El-Sayed works on Atlas billing at QamarTech", text_orig=None, subject_path="career/atlas-work", entities=[FactEntity("new:Omar El-Sayed", "billing owner"), FactEntity("new:QamarTech", "employer")], op="new", target=None, valid_from="2026-10-21", evidence=["wag-0014"], sensitive=None),
            OutFact(text="LLM Agents course cohort starts Nov 16", text_orig="كورس الوكلاء الذكية يبدأ ١٦ نوفمبر", subject_path="learning/llm-agents", entities=[FactEntity("new:Karim Haddad", "student")], op="new", target=None, valid_from="2026-11-04", evidence=["n011"], sensitive=None),
        ],
        links=[OutLink(src="new:Omar El-Sayed", rel="WORKS_AT", dst="new:QamarTech", valid_from="2026-10-21", evidence=["wag-0014"])],
    )
    job = Job(id="j-seed", owner="karim", kind="extract.day", priority=1, pool="internal", input_ref=["n001", "g012", "wab-0032", "wag-0014", "n011"], input_version=0, context_hash="c", prompt_version="extract@3", state="leased", attempt_no=1, fence_token="tok-seed", worker_id="w-haiku")
    att = Attempt(job_id="j-seed", attempt_no=1, fence_token="tok-seed", worker_id="w-haiku", worker_kind="internal-cloud", model="claude-haiku-5-5", prompt_version="extract@3", output=out, tokens_in=4000, tokens_out=1200, cost_usd=0.01)
    with db.transaction() as conn:
        conn.execute(
            "INSERT INTO workers (id, kind, model, runner, owner, status, released) VALUES ('w-owner', 'owner-hook', 'claude-code-hook', 'mcp', 'karim', 'online', TRUE)"
        )
        conn.execute(
            "INSERT INTO jobs (id, owner, kind, priority, pool, input_ref, input_version, context_hash, prompt_version, day, state, attempt_no, fence_token, worker_id, idempotency_key) "
            "VALUES ('j-seed', 'karim', 'extract.day', 1, 'internal', %s, 0, 'c', 'extract@3', '2026-10-23', 'applied', 1, 'tok-seed', 'w-owner', %s)",
            (job.input_ref, uuid.uuid4().hex),
        )
        conn.execute(
            "INSERT INTO job_attempts (id, job_id, owner, attempt_no, fence_token, worker_id, worker_kind, model, prompt_version, tokens_in, tokens_out, cost_usd, verdict) "
            "VALUES ('j-seed:1', 'j-seed', 'karim', 1, 'tok-seed', 'w-owner', 'owner-hook', 'claude-code-hook', 'extract@3', 500000, 100000, 0.0, 'applied')"
        )
    v = apply("karim", job, att, db=db)
    assert v.ok is True


@pytest.fixture(params=["fake", "postgres"])
def dual_store(request):
    invalidate_alias_cache()
    if request.param == "fake":
        yield "fake", FakeGraphStore.from_karim_slice()
        return

    db, schema = create_test_schema()
    pg = PostgresGraphStore(db)
    _seed_postgres_karim(db, pg)
    yield "postgres", pg
    drop_test_schema(db, schema)


def test_postgres_store_satisfies_graphstorefull_protocol(dual_store):
    _, st = dual_store
    required = [
        "scoped_context", "visible_facts", "alias_version", "facts_version", "owner_generation",
        "get_owner", "list_entities", "list_subjects", "list_links", "list_milestones",
        "list_entity_subjects", "get_records", "get_attempt", "get_quarantine_counts",
        "get_user_md", "set_user_md", "add_alias", "add_hypothesis_fact", "add_hypothesis_milestone",
        "list_jobs", "job_created_at", "list_workers", "list_attempts",
    ]
    for meth in required:
        assert callable(getattr(st, meth, None)), f"Missing GraphStoreFull method: {meth}"
    assert st.get_owner("karim") is not None
    assert st.alias_version("karim") >= 0
    assert st.facts_version("karim") >= 0
    assert st.owner_generation("karim") >= 0


def test_surfaces_parametrised_fake_vs_postgres(dual_store, monkeypatch):
    kind, st = dual_store

    # 1. live context: Arabizi + colliding Omars + Arabic text_orig
    res_3omar = context_pack("karim", "What did 3omar book at Zabeel Hall?", store=st)
    assert "Omar Farouk" in [e["name"] for e in res_3omar["entities"]]

    res_ar = context_pack("karim", "متى يبدأ كورس الوكلاء الذكية؟", store=st)
    assert res_ar["facts"], f"{kind}: Arabic text_orig query must return hits"

    # 2. Vault + Ops API
    tokens = {
        "karim-tok": AuthContext(role="owner-device", owner="karim", token_id="t-k"),
        "admin-tok": AuthContext(role="admin", owner=None, token_id="t-a"),
    }
    vault.configure(store=st, auth_verifier=lambda t: tokens.get(t or ""))
    app = FastAPI()
    app.include_router(vault.router)
    app.include_router(export_md.router)
    app.include_router(ops.router)
    client = TestClient(app)

    assert client.get("/v1/owners/karim/vault/subjects", headers={"Authorization": "Bearer karim-tok"}).status_code == 200
    assert client.get("/v1/owners/karim/vault/people", headers={"Authorization": "Bearer karim-tok"}).status_code == 200
    ops_body = client.get("/v1/ops/memory", headers={"Authorization": "Bearer admin-tok"}).json()
    assert ops_body["demo_cost_saved_usd"] > 0

    # 3. Markdown export
    md = export_md.render("karim", store=st)
    assert "MEMORIES.md" in md and "people/omar-farouk.md" in md

    # 4. reflect_week with Layer-2 privacy.policy.screen mocked offline (never skips Layer 2!)
    screen_calls: list[list[str]] = []

    def _fake_screen(labels: list[str], **_kw):
        screen_calls.append(list(labels))
        return {lbl: "health" for lbl in labels if "thyroid" in lbl.lower()}

    monkeypatch.setattr("temporal_memory.privacy.policy.screen", _fake_screen)

    if kind == "fake":
        ev_ids = ["f001", "f015"]
    else:
        ev_ids = [f.id for f in st.visible_facts("karim", limit=10) if "Al Barsha" in f.text or "Atlas" in f.text][:2]

    canned = json.dumps({
        "user_md": "",
        "claims": [
            {"section": "Interests", "text": "Follows LLM agents coursework closely.", "evidence": ev_ids},
        ],
        "milestones": [
            {"title": "Complete LLM agents cohort", "subject_path": "quests/llm-cohort", "state": "in_progress", "evidence": ev_ids},
            {"title": "Review thyroid checkup results", "subject_path": "quests/health", "state": "in_progress", "evidence": ev_ids},
        ],
    })
    verdict = reflect_week("karim", "2026-10-20", store=st, runner_fn=lambda _b, _r, _m: canned)
    assert verdict.ok is True
    assert len(verdict.applied_fact_ids) == 1
    assert screen_calls, "reflect_week must route outputs through policy.gate_fact Layer-2 screen"


def test_app_wires_wpb_endpoints_and_db_auth():
    db, schema = create_test_schema()
    try:
        app = create_app(db, admin_token="adm-secret")
        client = TestClient(app)
        assert client.get("/health").status_code == 200

        r_own = client.post("/v1/owners", headers={"Authorization": "Bearer adm-secret"}, json={"id": "karim", "label": "Karim", "kind": "real"})
        assert r_own.status_code == 200
        tok = client.post("/v1/tokens", headers={"Authorization": "Bearer adm-secret"}, json={"role": "owner-device", "owner": "karim"}).json()["token"]

        assert client.get("/v1/owners/karim/vault/subjects", headers={"Authorization": f"Bearer {tok}"}).status_code == 200
        assert client.get("/v1/owners/other/vault/subjects", headers={"Authorization": f"Bearer {tok}"}).status_code == 403
        assert client.get("/v1/ops/memory", headers={"Authorization": f"Bearer {tok}"}).status_code == 403
        assert client.get("/v1/ops/memory", headers={"Authorization": "Bearer adm-secret"}).status_code == 200
    finally:
        drop_test_schema(db, schema)
