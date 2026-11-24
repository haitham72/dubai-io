"""User-triggered Forget erases text everywhere (Rule 9). Real schema, synthetic owner, tombstones only."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

TOKEN = "zebraquark"


@pytest.fixture()
def tm():
    from temporal_memory.core.graph_store import PostgresGraphStore
    from temporal_memory.db import db as db_module
    from temporal_memory.db.db import create_test_schema, drop_test_schema

    db, schema = create_test_schema()
    previous = db_module._DEFAULT_DB
    db_module._DEFAULT_DB = db

    def write(sql, params=()):
        with db.transaction() as conn:
            conn.execute(sql, params)

    def read(sql, params=()):
        with db.connection() as conn:
            return conn.execute(sql, params).fetchall()

    write("INSERT INTO owners (id, label, kind, display_name) VALUES ('o1','O','simulated','Omar')")
    write("INSERT INTO subjects (id, owner, path, label, kind) VALUES ('s1','o1','life/cafes','Cafes','topic')")
    write(
        "INSERT INTO records (id, owner, source, at, author, text, content_hash, generation, meta) VALUES "
        "('r1','o1','note','2026-10-26T10:00:00+04:00','me',%s,'h1',1,%s::jsonb),"
        "('r2','o1','note','2026-10-26T11:00:00+04:00','me','Omar plays padel on Fridays','h2',1,'{}')",
        (f"I love the {TOKEN} cafe", json.dumps({"quote": TOKEN})),
    )
    write(
        "INSERT INTO entities (id, owner, kind, name, status, relation_to_user) VALUES ('e1','o1','place',%s,'active','favourite')",
        (f"{TOKEN} cafe",),
    )
    write(
        "INSERT INTO entity_aliases (owner, entity_id, alias, alias_folded) VALUES ('o1','e1',%s,%s)",
        (TOKEN, TOKEN),
    )
    write(
        "INSERT INTO facts (id, owner, text, text_orig, text_folded, subject_id, valid_from, status, content_hash,"
        " object_text, reason_text, span_record_id, span_start, span_end, attempt_id) VALUES "
        "('fa','o1',%s,%s,%s,'s1','2026-10-26','active','hfa',%s,%s,'r1',0,5,'att1'),"
        "('fb','o1','Omar plays padel','','omar plays padel','s1','2026-10-26','active','hfb',NULL,NULL,'r2',0,4,'att1')",
        (f"Omar loves the {TOKEN} cafe", f"{TOKEN} orig", TOKEN, f"{TOKEN} cafe", f"said {TOKEN}"),
    )
    write("INSERT INTO fact_evidence (owner, fact_id, record_id, record_generation) VALUES ('o1','fa','r1',1),('o1','fb','r2',1)")
    write("INSERT INTO fact_entities (owner, fact_id, entity_id) VALUES ('o1','fa','e1')")
    write(
        "INSERT INTO jobs (id, owner, kind, input_ref, input_version, state, idempotency_key, day) VALUES "
        "('j1','o1','extract.day','{r1,r2}',1,'applied','idem1','2026-10-26')"
    )
    write(
        "INSERT INTO job_attempts (id, job_id, owner, attempt_no, fence_token, worker_id, worker_kind, model,"
        " prompt_version, output_json, verdict) VALUES ('att1','j1','o1',1,'t','w','agent-cli','m','p',%s::jsonb,'applied')",
        (json.dumps({"facts": [{"text": TOKEN}]}),),
    )
    write(
        "INSERT INTO story_cache (owner, record_generation, facts_version, privacy_revision, query_hash, version_key,"
        " payload_json) VALUES ('o1',1,0,0,'q','v',%s::jsonb)",
        (json.dumps({"story": TOKEN}),),
    )
    write(
        "INSERT INTO milestones (id, owner, subject_id, title, evidence_fact_ids) VALUES ('ms1','o1','s1','Visit the cafe','[\"fa\"]')"
    )
    ns = SimpleNamespace(db=db, schema=schema, write=write, read=read, store=PostgresGraphStore(db))
    try:
        yield ns
    finally:
        db_module._DEFAULT_DB = previous
        drop_test_schema(db, schema)


def _scan(tm, token=TOKEN):
    """Raw scan of every table in the test schema for the token; returns {table: matching_rows}."""
    hits = {}
    for t in tm.read("SELECT tablename FROM pg_tables WHERE schemaname = %s", (tm.schema,)):
        name = t["tablename"]
        n = tm.read(f'SELECT count(*)::int AS c FROM "{name}" x WHERE x::text ILIKE %s', (f"%{token}%",))[0]["c"]
        if n:
            hits[name] = n
    return hits


def test_scan_finds_token_before_forget(tm):
    assert {"records", "facts", "entities", "entity_aliases", "job_attempts", "story_cache"} <= set(_scan(tm))


def test_forget_source_scrubs_every_copy(tm):
    from temporal_memory.privacy.forget import forget_source

    out = forget_source("o1", ["r1"])
    assert out["records"] == 1 and out["facts_erased"] == 1
    assert _scan(tm) == {}, _scan(tm)
    rec = tm.read("SELECT generation, erased_at, content_hash, text, author FROM records WHERE id='r1'")[0]
    assert rec["generation"] == 2 and rec["erased_at"] is not None and rec["content_hash"] == "h1"
    assert rec["text"] == "" and rec["author"] == ""
    fa = tm.read("SELECT erased_at, content_hash, text FROM facts WHERE id='fa'")[0]
    assert fa["erased_at"] is not None and fa["content_hash"] == "hfa" and fa["text"] == ""
    assert tm.read("SELECT count(*)::int c FROM milestones WHERE id='ms1'")[0]["c"] == 0
    v = tm.read("SELECT facts_version, privacy_revision FROM owners WHERE id='o1'")[0]
    assert int(v["facts_version"]) == 1 and int(v["privacy_revision"]) == 1
    assert tm.read("SELECT text FROM facts WHERE id='fb'")[0]["text"] == "Omar plays padel"
    assert tm.read("SELECT text FROM records WHERE id='r2'")[0]["text"].startswith("Omar plays")


def test_retrieval_does_not_return_it(tm):
    from temporal_memory.privacy.forget import forget_source

    forget_source("o1", ["r1"])
    visible = tm.store.visible_facts("o1", limit=100)
    assert [f.id for f in visible] == ["fb"]
    assert TOKEN not in repr(visible).lower()
    rows = tm.read("SELECT id FROM facts WHERE owner='o1' AND tsv @@ plainto_tsquery('simple', %s)", (TOKEN,))
    assert rows == []


def test_forget_fact_then_source_and_second_forget_idempotent(tm):
    from temporal_memory.privacy.forget import forget_fact, forget_source

    assert forget_fact("o1", "fa")["facts_erased"] == 1
    forget_source("o1", ["r1"])
    assert _scan(tm) == {}
    again = forget_source("o1", ["r1"])
    assert again["records"] == 1
    assert _scan(tm) == {}
    assert forget_fact("o1", "fa")["facts_erased"] == 0
    assert tm.read("SELECT text FROM facts WHERE id='fb'")[0]["text"] == "Omar plays padel"


def test_forget_fact_alone_scrubs_fact_text(tm):
    from temporal_memory.privacy.forget import forget_fact

    forget_fact("o1", "fa")
    hits = _scan(tm)
    assert "facts" not in hits and "entities" not in hits and "story_cache" not in hits
    assert "job_attempts" not in hits


def test_forget_twice_across_two_jobs_scrubs_every_attempt(tm):
    """E9b FAIL 4: attempts of earlier forgotten jobs/retries must not keep output_json."""
    from temporal_memory.privacy.forget import forget_source

    t2 = "quokkaflux"
    tm.write(
        "INSERT INTO records (id, owner, source, at, author, text, content_hash, generation, meta) VALUES "
        "('r3','o1','note','2026-10-27T10:00:00+04:00','me',%s,'h3',1,'{}')", (f"I adore {t2} tea",))
    tm.write(
        "INSERT INTO jobs (id, owner, kind, input_ref, input_version, state, idempotency_key, day) VALUES "
        "('j2','o1','extract.day','{r3}',1,'applied','idem2','2026-10-27')")
    tm.write(
        "INSERT INTO facts (id, owner, text, text_orig, text_folded, subject_id, valid_from, status, content_hash, attempt_id)"
        " VALUES ('fc','o1',%s,'',%s,'s1','2026-10-27','active','hfc','att2b')",
        (f"Omar adores {t2} tea", f"omar adores {t2} tea"))
    tm.write("INSERT INTO fact_evidence (owner, fact_id, record_id, record_generation) VALUES ('o1','fc','r3',1)")
    for aid, no, verdict in (("att2a", 1, "rejected"), ("att2b", 2, "applied")):
        tm.write(
            "INSERT INTO job_attempts (id, job_id, owner, attempt_no, fence_token, worker_id, worker_kind, model,"
            " prompt_version, output_json, verdict) VALUES (%s,'j2','o1',%s,'t','w','agent-cli','m','p',%s::jsonb,%s)",
            (aid, no, json.dumps({"facts": [{"text": f"{t2} tea"}]}), verdict))
    # Legacy state: an earlier forget only soft-erased r1 (no scrub, fact lost its attempt link) and left its attempt behind.
    tm.write("UPDATE records SET erased_at = now() WHERE id = 'r1'")
    tm.write("UPDATE facts SET erased_at = now(), attempt_id = NULL WHERE id = 'fa'")
    forget_source("o1", ["r3"])
    assert _scan(tm, t2) == {}, _scan(tm, t2)
    assert _scan(tm, TOKEN).get("job_attempts") is None, _scan(tm, TOKEN)
    assert tm.read("SELECT count(*)::int c FROM job_attempts WHERE output_json IS NOT NULL")[0]["c"] == 0
