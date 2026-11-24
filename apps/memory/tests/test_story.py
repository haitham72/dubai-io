"""Postgres + HTTP integration tests for GET /v1/owners/{owner}/story (U5)."""
from __future__ import annotations

import json
import time

from fastapi.testclient import TestClient
import pytest

from temporal_memory.api import story as story_api
from temporal_memory.api.app import create_app
from temporal_memory.db.db import create_test_schema, drop_test_schema, fold_text
from temporal_memory.privacy import forget as forget_mod

pytest.importorskip("psycopg")


@pytest.fixture()
def pg_db():
    try:
        db, schema = create_test_schema()
    except Exception as exc:
        pytest.skip(f"Postgres test DB unavailable: {exc}")
    try:
        yield db
    finally:
        story_api.set_narrator(None)
        story_api.set_screen_classifier(None)
        drop_test_schema(db, schema)


def _seed_story_owner(pg_db) -> None:
    with pg_db.transaction() as conn:
        conn.execute("INSERT INTO owners (id, label, kind) VALUES ('karim', 'Karim', 'simulated')")
        conn.execute(
            "INSERT INTO entities (id, owner, kind, name, status) VALUES "
            "('e_omar', 'karim', 'person', 'Omar Farouk', 'active'),"
            "('e_camry', 'karim', 'project', 'Camry Purchase', 'active')"
        )
        conn.execute(
            "INSERT INTO entity_aliases (owner, entity_id, alias, alias_folded) VALUES "
            "('karim', 'e_omar', 'Omar', 'omar')"
        )
        conn.execute(
            "INSERT INTO subjects (id, owner, path, label, kind, status) VALUES "
            "('s_ev', 'karim', 'events/wedding', 'Wedding', 'event', 'active'),"
            "('s_fam', 'karim', 'people-family/updates', 'Family Updates', 'topic', 'active'),"
            "('s_hlth', 'karim', 'health/meds', 'Health', 'topic', 'active')"
        )
        conn.execute("UPDATE subjects SET sensitive_cat = 'health' WHERE owner = 'karim' AND id = 's_hlth'")
        for rid, txt in [("r1", "Venue JBR"), ("r2", "Venue Zabeel"), ("r3", "Family check"), ("r4", "Clinic secret")]:
            conn.execute(
                "INSERT INTO records (id, owner, source, at, author, text, content_hash) VALUES (%s, 'karim', 'whatsapp:best', '2026-11-01', 'Karim', %s, %s)",
                (rid, txt, f"hc_{rid}"),
            )

        rows = [
            # Chronological superseded -> active change
            ("f_v1", "Omar and Rana booked JBR Beach Hall", "s_ev", "2026-10-20", "2026-11-09", "superseded", "user_supplied", None, "r1"),
            ("f_v2", "Omar and Rana moved their wedding venue to Zabeel Hall", "s_ev", "2026-11-09", None, "active", "user_supplied", "JBR double-booked Dec 18", "r2"),
            # Hypothesis must never enter story
            ("f_hyp", "I noticed Omar likes outdoor venues", "s_ev", "2026-11-10", None, "hypothesis", "inferred", None, "r2"),
            # Sensitive subject must NEVER be narrated even if user_supplied
            ("f_sens", "Doctor prescribed daily tablets", "s_hlth", "2026-11-11", None, "active", "user_supplied", None, "r4"),
            # Unconfirmed inferred people-family excluded; confirmed people-family included
            ("f_fam_inf", "Layla plans a surprise dinner", "s_fam", "2026-11-12", None, "active", "inferred", None, "r3"),
            ("f_fam_conf", "Mom arrives in Dubai on Dec 1", "s_fam", "2026-11-13", None, "active", "user_supplied", None, "r3"),
        ]
        for fid, txt, sid, vf, vt, st, prov, rsn, rid in rows:
            conn.execute(
                "INSERT INTO facts (id, owner, text, text_folded, subject_id, valid_from, valid_to, status, provenance, content_hash, reason_text) "
                "VALUES (%s, 'karim', %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (fid, txt, fold_text(txt), sid, vf, vt, st, prov, f"hf_{fid}", rsn),
            )
            conn.execute("INSERT INTO fact_evidence (owner, fact_id, record_id, record_generation) VALUES ('karim', %s, %s, 0)", (fid, rid))
            if fid in ("f_v1", "f_v2"):
                conn.execute("INSERT INTO fact_entities (owner, fact_id, entity_id) VALUES ('karim', %s, 'e_omar')", (fid,))


def test_story_template_citation_filters_and_forget_invalidation(pg_db) -> None:
    _seed_story_owner(pg_db)
    app = create_app(db=pg_db, admin_token="u5-admin")
    client = TestClient(app)
    hdr = {"Authorization": "Bearer u5-admin"}

    # 1. Deterministic template (uncached, then cached)
    r1 = client.get("/v1/owners/karim/story", headers=hdr)
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["mode"] == "template"
    assert d1["cached"] is False
    assert set(d1["fact_ids"]) == {"f_v1", "f_v2", "f_fam_conf"}
    assert "was active until 2026-11-09; superseded" in d1["story"]
    assert "JBR double-booked Dec 18" in d1["story"]
    assert "Doctor" not in d1["story"]
    assert "hypothesis" not in d1["story"]
    assert "Layla plans" not in d1["story"]
    for sent in d1["sentences"]:
        assert sent["fact_ids"]

    # Second hit comes from Postgres story_cache
    r2 = client.get("/v1/owners/karim/story", headers=hdr)
    assert r2.status_code == 200
    assert r2.json()["cached"] is True

    # 2. Forget invalidates story_cache atomically
    import temporal_memory.db as tm_db
    prev_db = tm_db.db._DEFAULT_DB
    tm_db.db._DEFAULT_DB = pg_db
    try:
        forget_mod.forget_fact("karim", "f_v2")
    finally:
        tm_db.db._DEFAULT_DB = prev_db

    r3 = client.get("/v1/owners/karim/story", headers=hdr)
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["cached"] is False
    assert "f_v2" not in d3["fact_ids"]
    assert "Zabeel" not in d3["story"]


def test_story_narrate_drops_uncited_invented_and_respects_budget_and_privacy(pg_db, monkeypatch) -> None:
    _seed_story_owner(pg_db)
    app = create_app(db=pg_db, admin_token="u5-admin")
    client = TestClient(app)
    hdr = {"Authorization": "Bearer u5-admin"}

    # Narrator emits: 1 valid cited sentence, 1 uncited sentence, 1 sentence citing invented/sensitive id, 1 Rule-9 sensitive text
    def fake_narrator(_prompt: str, fact_items: list[dict]):
        assert all(it["id"] != "f_sens" for it in fact_items)
        payload = {
            "sentences": [
                {"text": "Omar switched the wedding hall from JBR to Zabeel Hall [f_v1, f_v2].", "fact_ids": ["f_v1", "f_v2"]},
                {"text": "I completely invented a secret trip with zero citations.", "fact_ids": []},
                {"text": "He visited a hidden diabetes clinic [f_sens].", "fact_ids": ["f_sens"]},
                {"text": "Invented id reference [f_999].", "fact_ids": ["f_999"]},
                {"text": "Mom visits a hospital clinic too [f_v2].", "fact_ids": ["f_v2"]},
            ]
        }
        return json.dumps(payload), 0.0, "qwen/qwen3-4b-2507"

    story_api.set_narrator(fake_narrator)
    res = client.get("/v1/owners/karim/story", headers=hdr, params={"entity": "Omar", "narrate": "1"})
    assert res.status_code == 200
    data = res.json()
    assert data["mode"] == "narrated"
    assert data["dropped_sentences"] == 4
    assert len(data["sentences"]) == 1
    assert set(data["fact_ids"]) <= {"f_v1", "f_v2"}
    assert "invented" not in data["story"].lower()
    assert "clinic" not in data["story"].lower()

    # Over monthly budget -> deterministic template
    monkeypatch.setenv("TM_GOVERNOR_USD_PER_MONTH", "0.10")
    with pg_db.transaction() as conn:
        conn.execute(
            "INSERT INTO jobs (id, owner, kind, priority, pool, input_ref, input_version, idempotency_key) "
            "VALUES ('j_b', 'karim', 'extract.day', 1, 'internal', '{}', 0, 'idem_jb')"
        )
        conn.execute(
            "INSERT INTO job_attempts (id, job_id, owner, attempt_no, fence_token, worker_id, worker_kind, model, prompt_version, cost_usd, verdict) "
            "VALUES ('att_b', 'j_b', 'karim', 1, 'ft', 'w1', 'internal-cloud', 'haiku', 'p1', 0.25, 'applied')"
        )
    res_budget = client.get("/v1/owners/karim/story", headers=hdr, params={"narrate": "1"})
    assert res_budget.status_code == 200
    dbud = res_budget.json()
    assert dbud["mode"] == "template"
    assert dbud["fallback_reason"] == "over_budget"
    assert dbud["cost_usd"] == 0.0


def test_story_latency_gates_postgres(pg_db) -> None:
    _seed_story_owner(pg_db)
    app = create_app(db=pg_db, admin_token="u5-admin")
    client = TestClient(app)
    hdr = {"Authorization": "Bearer u5-admin"}

    # Warmup
    assert client.get("/v1/owners/karim/story", headers=hdr).status_code == 200

    # Measure cached (n=30)
    cached_lats: list[float] = []
    for _ in range(30):
        t0 = time.perf_counter()
        r = client.get("/v1/owners/karim/story", headers=hdr)
        assert r.status_code == 200 and r.json()["cached"] is True
        cached_lats.append((time.perf_counter() - t0) * 1000)

    # Measure uncached template (n=30, unique date_to per request to bypass cache)
    uncached_lats: list[float] = []
    for idx in range(30):
        to_day = f"2026-11-{14 + (idx % 16):02d}"
        with pg_db.transaction() as conn:
            conn.execute("DELETE FROM story_cache WHERE owner = 'karim'")
        t0 = time.perf_counter()
        r = client.get("/v1/owners/karim/story", headers=hdr, params={"to": to_day})
        assert r.status_code == 200 and r.json()["cached"] is False
        uncached_lats.append((time.perf_counter() - t0) * 1000)

    cached_lats.sort()
    uncached_lats.sort()
    cached_p95 = cached_lats[int(0.95 * (len(cached_lats) - 1))]
    uncached_p95 = uncached_lats[int(0.95 * (len(uncached_lats) - 1))]
    assert cached_p95 < 50.0, f"cached p95 {cached_p95:.2f}ms >= 50ms"
    assert uncached_p95 < 150.0, f"uncached p95 {uncached_p95:.2f}ms >= 150ms"
