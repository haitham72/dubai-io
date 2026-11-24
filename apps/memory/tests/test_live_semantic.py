"""E9b: the live context pack (chat) uses the hybrid channels, incl. semantic, and degrades honestly."""
from __future__ import annotations

import pytest

pytest.importorskip("psycopg")


@pytest.fixture()
def env(monkeypatch):
    from temporal_memory.core import embed
    from temporal_memory.core.graph_store import PostgresGraphStore
    from temporal_memory.db.db import create_test_schema, drop_test_schema, fold_text

    try:
        db, schema = create_test_schema()
    except Exception as exc:
        pytest.skip(f"Postgres test DB unavailable: {exc}")
    monkeypatch.setenv("TM_SEMANTIC", "1")
    embed._BACKFILLED_AT.clear()
    from temporal_memory.live import context as live_context

    live_context._PACK_CACHE.clear()
    embed.clear_query_cache()
    with db.transaction() as conn:
        conn.execute("INSERT INTO owners (id, label, kind, display_name) VALUES ('lv','lv','demo','Rui')")
        conn.execute("INSERT INTO subjects (id, owner, path, label, kind, status) VALUES "
                     "('s1','lv','life/hobbies','Hobbies','topic','active')")
        conn.execute("INSERT INTO records (id, owner, source, at, author, text, content_hash) VALUES "
                     "('r1','lv','note','2026-11-10','Rui','x','h1')")
        for fid, txt in [("f_surf", "Rui joined the Marmoset surf school in Cascais"),
                         ("f_tax", "The accountant filed the quarterly VAT return in October"),
                         ("f_rent", "The flat rent is AED 5,400 per month"),
                         ("f_pass", "Rui's passport expires in March 2027 and the renewal appointment is booked")]:
            conn.execute(
                "INSERT INTO facts (id, owner, text, text_folded, subject_id, valid_from, status, provenance, content_hash) "
                "VALUES (%s,'lv',%s,%s,'s1','2026-11-10','active','user_supplied',%s)", (fid, txt, fold_text(txt), f"h{fid}"))
            conn.execute("INSERT INTO fact_evidence (owner, fact_id, record_id, record_generation) VALUES ('lv',%s,'r1',0)", (fid,))
    try:
        yield db, PostgresGraphStore(db), embed
    finally:
        drop_test_schema(db, schema)


def _texts(pack):
    return [f["text"] for f in pack["facts"]]


def test_paraphrase_query_finds_surf_school_via_semantic_channel(env):
    from temporal_memory.live.context import context_pack

    db, store, embed = env
    if not embed.is_available():
        pytest.skip("local bge-m3 embedder not installed/cached")
    pack = context_pack("lv", "sport", store=store)
    assert any("surf school" in t for t in _texts(pack)), _texts(pack)
    assert pack["retrieval"]["semantic"] == "ok" and "semantic" in pack["retrieval"]["channels"]
    # zero shared words: only the semantic channel can bridge this paraphrase
    para = context_pack("lv", "Which international border booklet is about to lapse?", store=store)
    assert [t for t in _texts(para) if "passport" in t], _texts(para)
    # facts were embedded lazily (live-extracted facts have no vector at write time)
    with db.connection() as conn:
        assert conn.execute("SELECT count(*) AS c FROM facts WHERE embedding IS NOT NULL").fetchone()["c"] == 4


def test_unrelated_query_returns_nothing_not_recent_padding(env):
    from temporal_memory.live.context import context_pack

    db, store, embed = env
    if not embed.is_available():
        pytest.skip("local bge-m3 embedder not installed/cached")
    pack = context_pack("lv", "volcano eruption insurance", store=store)
    assert pack["facts"] == []


def test_embedder_unavailable_degrades_to_lexical_with_flag(env, monkeypatch):
    from temporal_memory.live.context import context_pack

    db, store, embed = env
    monkeypatch.setattr(embed, "_ensure_loaded", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no onnx")))
    monkeypatch.setattr(embed, "_SESSION", None)
    lexical = context_pack("lv", "surf school", store=store)
    assert any("surf school" in t for t in _texts(lexical))
    assert lexical["retrieval"]["semantic"] == "embedder_unavailable"
    assert "semantic" not in lexical["retrieval"]["channels"]
    para = context_pack("lv", "Which international border booklet is about to lapse?", store=store)
    assert para["facts"] == [] and para["retrieval"]["semantic"] == "embedder_unavailable"


def test_semantic_disabled_flag(env, monkeypatch):
    from temporal_memory.live.context import context_pack

    _, store, _ = env
    monkeypatch.setenv("TM_SEMANTIC", "0")
    assert context_pack("lv", "surf", store=store)["retrieval"]["semantic"] == "disabled"
