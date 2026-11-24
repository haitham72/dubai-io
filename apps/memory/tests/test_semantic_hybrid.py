"""Postgres integration tests for U4 local semantic embeddings & hybrid search."""
from __future__ import annotations

import hashlib
import json

from types import SimpleNamespace

import pytest

from temporal_memory.core.bridge_store import resolve_fact, search_facts
from temporal_memory.core.embed import (
    EMBED_DIM,
    EMBED_MODEL,
    clear_query_cache,
    embed_pending_facts,
)
from temporal_memory.core.graph_store import PostgresGraphStore
from temporal_memory.core.retrieval import search_candidates
from temporal_memory.db.db import create_test_schema, drop_test_schema, fold_text
from temporal_memory.privacy import forget as forget_mod

psycopg = pytest.importorskip("psycopg")


@pytest.fixture()
def pg_db():
    try:
        db, schema = create_test_schema()
    except Exception as exc:
        pytest.skip(f"Postgres test DB unavailable: {exc}")
    try:
        yield db
    finally:
        drop_test_schema(db, schema)


def test_migration_adds_vector_column_and_hnsw_index(pg_db) -> None:
    with pg_db.connection() as conn:
        cols = {
            r["attname"]: r["typ"]
            for r in conn.execute(
                """
                SELECT a.attname, format_type(a.atttypid, a.atttypmod) AS typ
                FROM pg_attribute a
                WHERE a.attrelid = 'facts'::regclass AND a.attnum > 0 AND NOT a.attisdropped
                """
            ).fetchall()
        }
        idx = conn.execute(
            "SELECT indexname FROM pg_indexes WHERE tablename = 'facts' AND indexname = 'idx_facts_embedding_hnsw'"
        ).fetchone()
    assert cols["embedding"] == f"public.vector({EMBED_DIM})" or cols["embedding"] == f"vector({EMBED_DIM})"
    assert cols["embedding_model"] == "text"
    assert cols["embedded_at"].startswith("timestamp")
    assert idx is not None


def test_backfill_skips_quarantine_sensitive_history_and_forget_rules(pg_db) -> None:
    with pg_db.transaction() as conn:
        conn.execute("INSERT INTO owners (id, label, kind) VALUES ('u4o', 'u4o', 'demo')")
        conn.execute(
            "INSERT INTO subjects (id, owner, path, label, kind, status) VALUES "
            "('s_gen', 'u4o', 'projects/raseef', 'Raseef', 'project', 'active'),"
            "('s_hlth', 'u4o', 'health/meds', 'Health', 'topic', 'active')"
        )
        conn.execute(
            "UPDATE subjects SET sensitive_cat = 'health' WHERE owner = 'u4o' AND id = 's_hlth'"
        )
        for rid, txt in [("r_ok", "Raseef receipt scanner"), ("r_quar", "Secret medical report"), ("r_erased", "Old note")]:
            conn.execute(
                "INSERT INTO records (id, owner, source, at, author, text, content_hash, erased_at) "
                "VALUES (%s, 'u4o', 'whatsapp:work', '2026-11-10', 'Karim', %s, %s, %s)",
                (rid, txt, hashlib.sha256(rid.encode()).hexdigest(), "2026-11-11" if rid == "r_erased" else None),
            )
        conn.execute(
            "INSERT INTO quarantine (owner, category, record_ids, status) VALUES ('u4o', 'health', %s::jsonb, 'held')",
            (json.dumps(["r_quar"]),),
        )
        conn.execute(
            "INSERT INTO forget_rules (owner, kind, value) VALUES ('u4o', 'text', 'secret phrase')"
        )

        rows = [
            ("f_elig", "Karim travels with his Egyptian passport expiring March 2027", "جواز السفر ينتهي مارس 2027", "s_gen", "active", "inferred", "r_ok"),
            ("f_hist", "Old superseded passport note", None, "s_gen", "history", "inferred", "r_ok"),
            ("f_sens_inf", "Inferred health dosage note", None, "s_hlth", "active", "inferred", "r_ok"),
            ("f_sens_usr", "User stated blood type O positive", None, "s_hlth", "active", "user_supplied", "r_ok"),
            ("f_quar", "Fact tied to held quarantine record", None, "s_gen", "active", "inferred", "r_quar"),
            ("f_fr", "Contains secret phrase blocked by rule", None, "s_gen", "active", "inferred", "r_ok"),
        ]
        for fid, txt, orig, sid, st, prov, rid in rows:
            conn.execute(
                "INSERT INTO facts (id, owner, text, text_orig, text_folded, subject_id, valid_from, status, provenance, content_hash) "
                "VALUES (%s, 'u4o', %s, %s, %s, %s, '2026-11-10', %s, %s, %s)",
                (fid, txt, orig, fold_text(txt), sid, st, prov, f"h_{fid}"),
            )
            conn.execute("INSERT INTO fact_evidence (owner, fact_id, record_id, record_generation) VALUES ('u4o', %s, %s, 0)", (fid, rid))

    stats = embed_pending_facts(pg_db, owner="u4o", batch_size=16)
    assert stats["embedded"] == 2

    with pg_db.connection() as conn:
        emb_ids = {
            r["id"]
            for r in conn.execute(
                "SELECT id FROM facts WHERE owner = 'u4o' AND embedding IS NOT NULL"
            ).fetchall()
        }
    assert emb_ids == {"f_elig", "f_sens_usr"}


def test_forget_and_reject_clear_embedding_same_transaction(pg_db) -> None:
    with pg_db.transaction() as conn:
        conn.execute("INSERT INTO owners (id, label, kind) VALUES ('u4f', 'u4f', 'demo')")
        conn.execute("INSERT INTO subjects (id, owner, path, label, kind, status) VALUES ('s1', 'u4f', 'travel/docs', 'Docs', 'topic', 'active')")
        for rid in ("r1", "r2", "r3"):
            conn.execute(
                "INSERT INTO records (id, owner, source, at, author, text, content_hash) VALUES (%s, 'u4f', 'notes', '2026-11-10', 'Karim', %s, %s)",
                (rid, f"note {rid}", f"hr_{rid}"),
            )
        for fid, rid in [("f_one", "r1"), ("f_src", "r2"), ("f_rej", "r3")]:
            conn.execute(
                "INSERT INTO facts (id, owner, text, text_folded, subject_id, valid_from, status, provenance, content_hash) "
                "VALUES (%s, 'u4f', %s, %s, 's1', '2026-11-10', 'active', 'user_supplied', %s)",
                (fid, f"Travel document detail {fid}", f"travel document detail {fid}", f"hf_{fid}"),
            )
            conn.execute("INSERT INTO fact_evidence (owner, fact_id, record_id, record_generation) VALUES ('u4f', %s, %s, 0)", (fid, rid))

    embed_pending_facts(pg_db, owner="u4f")
    store = PostgresGraphStore(pg_db)

    import temporal_memory.db as tm_db
    prev_db = tm_db.db._DEFAULT_DB
    tm_db.db._DEFAULT_DB = pg_db
    try:
        forget_mod.forget_fact("u4f", "f_one")
        forget_mod.forget_source("u4f", ["r2"])
        resolve_fact(store, "u4f", "f_rej", SimpleNamespace(action="reject"))
    finally:
        tm_db.db._DEFAULT_DB = prev_db

    with pg_db.connection() as conn:
        rows = conn.execute(
            "SELECT id, erased_at IS NOT NULL AS erased, embedding IS NULL AS emb_cleared, embedding_model, embedded_at "
            "FROM facts WHERE owner = 'u4f' ORDER BY id"
        ).fetchall()
    assert len(rows) == 3
    for r in rows:
        assert r["erased"] is True
        assert r["emb_cleared"] is True
        assert r["embedding_model"] is None
        assert r["embedded_at"] is None


def test_hybrid_paraphrase_retrieval_noise_and_privacy(pg_db, monkeypatch) -> None:
    with pg_db.transaction() as conn:
        conn.execute("INSERT INTO owners (id, label, kind) VALUES ('u4h', 'u4h', 'demo')")
        conn.execute(
            "INSERT INTO subjects (id, owner, path, label, kind, status) VALUES "
            "('s_tr', 'u4h', 'travel/docs', 'Docs', 'topic', 'active'),"
            "('s_sp', 'u4h', 'events/running', 'Running', 'topic', 'active'),"
            "('s_hl', 'u4h', 'health/clinic', 'Clinic', 'topic', 'active')"
        )
        conn.execute("UPDATE subjects SET sensitive_cat = 'health' WHERE owner = 'u4h' AND id = 's_hl'")
        conn.execute("INSERT INTO records (id, owner, source, at, author, text, content_hash) VALUES ('r1', 'u4h', 'notes', '2026-11-10', 'Karim', 'Passport & shoes', 'h1')")
        facts = [
            ("f_pass", "Karim's Egyptian passport expires March 2027; renewal appointment booked Dec 2.", None, "s_tr", "inferred"),
            ("f_shoe", "Karim bought Pegasus 41 running shoes; old pair retired at 700km.", None, "s_sp", "inferred"),
            ("f_sens", "Tarek takes daily insulin for diabetes.", None, "s_hl", "inferred"),
        ]
        for fid, txt, orig, sid, prov in facts:
            conn.execute(
                "INSERT INTO facts (id, owner, text, text_orig, text_folded, subject_id, valid_from, status, provenance, content_hash) "
                "VALUES (%s, 'u4h', %s, %s, %s, %s, '2026-11-10', 'active', %s, %s)",
                (fid, txt, orig, fold_text(txt), sid, prov, f"hh_{fid}"),
            )
            conn.execute("INSERT INTO fact_evidence (owner, fact_id, record_id, record_generation) VALUES ('u4h', %s, 'r1', 0)", (fid,))

    embed_pending_facts(pg_db, owner="u4h")
    clear_query_cache()
    store = PostgresGraphStore(pg_db)

    # Zero-keyword EN + Arabic paraphrase queries (no shared subject/synonym/keyword tokens)
    q_en = "Which international border booklet is about to lapse?"
    q_ar = "متى ينتهي جواز سفري وموعد التجديد؟"

    monkeypatch.setenv("TM_SEMANTIC", "0")
    assert [c.fact_id for c in search_candidates(pg_db, "u4h", q_en, limit=8)] == []
    assert [c.fact_id for c in search_candidates(pg_db, "u4h", q_ar, limit=8)] == []

    monkeypatch.setenv("TM_SEMANTIC", "1")
    hits_en = search_candidates(pg_db, "u4h", q_en, limit=8)
    hits_ar = search_candidates(pg_db, "u4h", q_ar, limit=8)
    assert hits_en and hits_en[0].fact_id == "f_pass"
    assert hits_ar and hits_ar[0].fact_id == "f_pass"

    # Bridge /search endpoint hydrates semantic matches too (not wiped out by ILIKE)
    res = search_facts(store, "u4h", q_en, limit=8, source_prefix=None)
    assert [f["id"] for f in res["facts"]][:1] == ["f_pass"]

    # Noise queries stay empty and unconfirmed sensitive never leaks
    assert search_candidates(pg_db, "u4h", "ok 👍", limit=8) == []
    assert search_candidates(pg_db, "u4h", "lol 😂😂", limit=8) == []
    sens_hits = search_candidates(pg_db, "u4h", "What diabetes medication does Tarek take?", limit=8)
    assert all(c.fact_id != "f_sens" for c in sens_hits)
