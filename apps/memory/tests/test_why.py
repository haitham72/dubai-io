"""Postgres + HTTP integration tests for /why/{fact_id} (U5)."""
from __future__ import annotations

import hashlib

from fastapi.testclient import TestClient
import pytest

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
        drop_test_schema(db, schema)


def test_why_returns_evidence_spans_and_separate_reason_on_postgres(pg_db) -> None:
    app = create_app(db=pg_db, admin_token="u5-admin")
    client = TestClient(app)
    hdr = {"Authorization": "Bearer u5-admin"}

    long_raw = (
        ("Header banner noise filler. " * 25)
        + "Omar and Rana moved their wedding venue to Zabeel Hall because JBR Beach Hall double-booked December 18."
        + (" Footer trailing noise filler." * 25)
    )
    span_phrase = "Omar and Rana moved their wedding venue to Zabeel Hall"
    reason_phrase = "JBR Beach Hall double-booked December 18"
    span_start = long_raw.index(span_phrase)
    span_end = span_start + len(span_phrase)
    reason_start = long_raw.index(reason_phrase)
    reason_end = reason_start + len(reason_phrase)

    with pg_db.transaction() as conn:
        conn.execute("INSERT INTO owners (id, label, kind) VALUES ('karim', 'Karim', 'demo')")
        conn.execute(
            "INSERT INTO subjects (id, owner, path, label, kind, status) VALUES "
            "('s_ev', 'karim', 'events/wedding', 'Wedding', 'event', 'active'),"
            "('s_hl', 'karim', 'health/meds', 'Health', 'topic', 'active')"
        )
        conn.execute("UPDATE subjects SET sensitive_cat = 'health' WHERE owner = 'karim' AND id = 's_hl'")
        conn.execute(
            "INSERT INTO records (id, owner, source, at, author, text, content_hash) VALUES "
            "('r_long', 'karim', 'gmail', '2026-11-09T10:00:00Z', 'Omar', %s, %s)",
            (long_raw, hashlib.sha256(b"r_long").hexdigest()),
        )
        conn.execute(
            "INSERT INTO facts (id, owner, text, text_folded, subject_id, valid_from, status, provenance, content_hash, "
            "span_record_id, span_start, span_end, reason_text, reason_record_id, reason_start, reason_end) VALUES "
            "('f_reason', 'karim', 'Omar and Rana moved their wedding venue to Zabeel Hall', 'omar zabeel', 's_ev', '2026-11-09', 'active', 'inferred', 'h_r', "
            "'r_long', %s, %s, %s, 'r_long', %s, %s)",
            (span_start, span_end, reason_phrase, reason_start, reason_end),
        )
        conn.execute(
            "INSERT INTO facts (id, owner, text, text_folded, subject_id, valid_from, status, provenance, content_hash) VALUES "
            "('f_noreason', 'karim', 'Karim works at QamarTech on Atlas', 'karim qamartech', 's_ev', '2026-10-20', 'active', 'user_supplied', 'h_nr'),"
            "('f_sens', 'karim', 'Inferred private medical check', 'medical check', 's_hl', '2026-11-10', 'active', 'inferred', 'h_s')"
        )
        for fid in ("f_reason", "f_noreason", "f_sens"):
            conn.execute(
                "INSERT INTO fact_evidence (owner, fact_id, record_id, record_generation) VALUES ('karim', %s, 'r_long', 0)",
                (fid,),
            )

    # 1. Stored span + separate reason + provenance
    r1 = client.get("/v1/owners/karim/why/f_reason", headers=hdr)
    assert r1.status_code == 200
    b1 = r1.json()
    assert b1["provenance"] == "inferred"
    assert b1["reason"] == reason_phrase
    assert b1["reason_span"]["record_id"] == "r_long"
    assert len(b1["evidence"]) == 1
    assert b1["evidence"][0]["span"] == span_phrase
    assert len(b1["evidence"][0]["text"]) < 250  # compact span, never full raw record

    # 2. Absent reason returns literal "reason unknown" (never generated), separate from provenance
    r2 = client.get("/v1/owners/karim/why/f_noreason", headers=hdr)
    assert r2.status_code == 200
    b2 = r2.json()
    assert b2["provenance"] == "user_supplied"
    assert b2["reason"] == "reason unknown"
    assert b2["reason_span"] is None

    # 3. Unconfirmed sensitive fact returns 404
    r_sens = client.get("/v1/owners/karim/why/f_sens", headers=hdr)
    assert r_sens.status_code == 404

    # 4. Forgotten fact returns 404
    import temporal_memory.db as tm_db
    prev_db = tm_db.db._DEFAULT_DB
    tm_db.db._DEFAULT_DB = pg_db
    try:
        forget_mod.forget_fact("karim", "f_reason")
    finally:
        tm_db.db._DEFAULT_DB = prev_db
    assert client.get("/v1/owners/karim/why/f_reason", headers=hdr).status_code == 404
