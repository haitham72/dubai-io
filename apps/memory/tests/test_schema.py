"""Tests for PostgreSQL 17 schema, views, and PostgresGraphStore helpers (WP-A)."""
from __future__ import annotations

import json
import pytest

from temporal_memory.core.graph_store import PostgresGraphStore
from temporal_memory.db.db import create_test_schema, drop_test_schema, fold_text
from temporal_memory.models import Owner, Record


@pytest.fixture(scope="module")
def db_and_store():
    db, schema = create_test_schema()
    store = PostgresGraphStore(db)
    yield db, store
    drop_test_schema(db, schema)


def test_schema_tables_and_views_exist(db_and_store):
    db, _ = db_and_store
    expected_tables = {
        "owners", "records", "entities", "entity_aliases", "subjects",
        "facts", "fact_entities", "fact_evidence", "links", "entity_subjects",
        "milestones", "quarantine", "forget_rules", "workers", "tokens",
        "jobs", "job_attempts", "outbox",
    }
    expected_views = {"visible_facts", "hypotheses"}
    with db.connection() as conn:
        rows = conn.execute(
            """
            SELECT table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = current_schema()
            """
        ).fetchall()
    tables = {r["table_name"] for r in rows if r["table_type"] == "BASE TABLE"}
    views = {r["table_name"] for r in rows if r["table_type"] == "VIEW"}
    assert expected_tables.issubset(tables)
    assert expected_views.issubset(views)


def test_owner_records_and_user_md_roundtrip(db_and_store):
    _, store = db_and_store
    owner = store.create_owner(
        Owner(
            id="karim_schema",
            label="Karim Haddad",
            kind="demo",
            display_name="Karim",
            self_aliases=["Kimo", "كريم"],
        )
    )
    assert owner.id == "karim_schema"
    fetched = store.get_owner("karim_schema")
    assert fetched is not None
    assert fetched.self_aliases == ["Kimo", "كريم"]

    store.set_user_md("karim_schema", "# Karim\nBased in Dubai.")
    assert "Based in Dubai" in store.get_user_md("karim_schema")

    recs = [
        Record(
            id="wa-1",
            owner="karim_schema",
            source="whatsapp:friends",
            at="2026-10-01T09:00:00Z",
            author="Karim",
            text="Meeting Nadia at DIFC Gate",
            generation=0,
        ),
        Record(
            id="g-1",
            owner="karim_schema",
            source="gmail",
            at="2026-10-01T10:00:00Z",
            author="hr@falcon.ae",
            text="Interview scheduled with Falcon Tech",
            generation=0,
        ),
    ]
    assert store.upsert_records("karim_schema", recs) == 2
    got = store.get_records("karim_schema", ["wa-1", "g-1"])
    assert [r.id for r in got] == ["wa-1", "g-1"]


def test_scoped_context_1hop_and_budget(db_and_store):
    db, store = db_and_store
    store.create_owner("karim_ctx", label="Karim", display_name="Karim")
    with db.transaction() as conn:
        conn.execute(
            "INSERT INTO entities (id, owner, kind, name, status, salience) VALUES "
            "('e1', 'karim_ctx', 'person', 'Nadia Mansour', 'active', 0.9),"
            "('e2', 'karim_ctx', 'org', 'Falcon Tech', 'active', 0.8),"
            "('e3', 'karim_ctx', 'place', 'Cairo', 'candidate', 0.1)"
        )
        conn.execute(
            "INSERT INTO entity_aliases (owner, entity_id, alias, alias_folded) VALUES "
            "('karim_ctx', 'e1', 'نادية', %s),"
            "('karim_ctx', 'e2', 'Falcon Tech', %s),"
            "('karim_ctx', 'e3', 'Cairo', %s)",
            (fold_text("نادية"), fold_text("Falcon Tech"), fold_text("Cairo")),
        )
        conn.execute(
            "INSERT INTO links (id, owner, src, rel, dst) VALUES "
            "('l1', 'karim_ctx', 'e1', 'WORKS_AT', 'e2')"
        )
        conn.execute(
            "INSERT INTO subjects (id, owner, path, label, kind, status, salience, fact_count) VALUES "
            "('s1', 'karim_ctx', 'career/network', 'network', 'topic', 'active', 0.9, 1)"
        )
        conn.execute(
            "INSERT INTO records (id, owner, source, at, author, text, content_hash) VALUES "
            "('wa-10', 'karim_ctx', 'whatsapp:dm', '2026-10-02T10:00:00Z', 'Karim', 'Spoke with نادية today', 'h10')"
        )
        conn.execute(
            "INSERT INTO facts (id, owner, text, text_folded, subject_id, valid_from, status, content_hash) VALUES "
            "('f1', 'karim_ctx', 'Nadia works at Falcon Tech in DIFC', 'nadia works at falcon tech in difc', 's1', '2026-10-01', 'active', 'fh1')"
        )
        conn.execute(
            "INSERT INTO fact_entities (owner, fact_id, entity_id, role) VALUES "
            "('karim_ctx', 'f1', 'e1', 'contact'), ('karim_ctx', 'f1', 'e2', 'employer')"
        )
        conn.execute(
            "INSERT INTO fact_evidence (owner, fact_id, record_id, record_generation) VALUES "
            "('karim_ctx', 'f1', 'wa-10', 0)"
        )

    rec = Record(
        id="wa-10",
        owner="karim_ctx",
        source="whatsapp:dm",
        at="2026-10-02T10:00:00Z",
        author="Karim",
        text="Coffee with نادية tomorrow",
    )
    ctx = store.scoped_context("karim_ctx", [rec], max_tokens=3000)
    ent_ids = [e["id"] for e in ctx["entities"]]
    assert "e1" in ent_ids
    assert "e2" in ent_ids  # pulled in via 1-hop link from e1
    assert any(f["id"] == "f1" for f in ctx["facts"])
    assert any(s["id"] == "s1" for s in ctx["subjects"])

    # Tight budget packing never exceeds char budget (max_tokens * 4)
    tight = store.scoped_context("karim_ctx", [rec], max_tokens=40)
    assert len(json.dumps(tight, ensure_ascii=False)) <= 40 * 4


def test_visible_facts_filters_history_generation_and_forget(db_and_store):
    db, store = db_and_store
    store.create_owner("karim_vis", label="Karim")
    store.upsert_records(
        "karim_vis",
        [
            Record(id="r1", owner="karim_vis", source="notes", at="2026-10-01T09:00:00Z", author="Karim", text="R1", generation=0),
            Record(id="r2", owner="karim_vis", source="notes", at="2026-10-01T10:00:00Z", author="Karim", text="R2", generation=1),
        ],
    )
    with db.transaction() as conn:
        conn.execute(
            "INSERT INTO subjects (id, owner, path, label) VALUES ('sv1', 'karim_vis', 'work/ops', 'ops')"
        )
        conn.execute(
            "INSERT INTO facts (id, owner, text, text_folded, subject_id, valid_from, status, content_hash) VALUES "
            "('fv_ok', 'karim_vis', 'Karim leads backend sprint', 'karim leads backend sprint', 'sv1', '2026-10-01', 'active', 'c1'),"
            "('fv_hist', 'karim_vis', 'Old sprint role', 'old sprint role', 'sv1', '2026-09-01', 'history', 'c2'),"
            "('fv_gen', 'karim_vis', 'Stale generation fact', 'stale generation fact', 'sv1', '2026-10-01', 'active', 'c3'),"
            "('fv_hyp', 'karim_vis', 'Karim might switch teams', 'karim might switch teams', 'sv1', '2026-10-02', 'hypothesis', 'c4'),"
            "('fv_fgt', 'karim_vis', 'Secret project codename', 'secret project codename', 'sv1', '2026-10-02', 'active', 'c5')"
        )
        conn.execute(
            "INSERT INTO fact_evidence (owner, fact_id, record_id, record_generation) VALUES "
            "('karim_vis', 'fv_ok', 'r1', 0),"
            "('karim_vis', 'fv_gen', 'r2', 0)"  # r2 already has generation=1 > 0
        )
        conn.execute(
            "INSERT INTO forget_rules (owner, kind, value) VALUES ('karim_vis', 'text', 'codename')"
        )

    vis = store.visible_facts("karim_vis")
    vis_ids = {f.id for f in vis}
    assert "fv_ok" in vis_ids
    assert "fv_hyp" in vis_ids
    assert "fv_hist" not in vis_ids
    assert "fv_gen" not in vis_ids
    assert "fv_fgt" not in vis_ids

    with db.connection() as conn:
        hyp_ids = {
            r["id"]
            for r in conn.execute("SELECT id FROM hypotheses WHERE owner = 'karim_vis'").fetchall()
        }
    assert hyp_ids == {"fv_hyp"}
    assert store.list_subjects("karim_vis")[0].id == "sv1"
    assert store.get_quarantine_counts("karim_vis") == {}
    assert store.list_jobs("karim_vis") == []
    assert store.list_workers() == []
    assert store.list_attempts(owner="karim_vis") == []
    assert store.get_attempt("missing") is None
