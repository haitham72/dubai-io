"""E11b: lazy embedding keeps going until done, never loads the model on the query path,
and caches a failed load for a backoff window."""
from __future__ import annotations

import pytest

from temporal_memory.core import embed
from temporal_memory.core.embed import EMBED_DIM, ensure_embeddings, embed_pending_facts
from temporal_memory.db.db import create_test_schema, drop_test_schema, fold_text

psycopg = pytest.importorskip("psycopg")


@pytest.fixture()
def pg_db():
    try:
        db, schema = create_test_schema()
    except Exception as exc:
        pytest.skip(f"Postgres test DB unavailable: {exc}")
    embed._BACKFILLED_AT.clear()
    embed._LAST_SWEEP_AT.clear()
    embed._PENDING.clear()
    try:
        yield db
    finally:
        embed._BACKFILLED_AT.clear()
        embed._LAST_SWEEP_AT.clear()
        embed._PENDING.clear()
        drop_test_schema(db, schema)


def _fake_passages(texts, **_kwargs):
    return [[0.001] * EMBED_DIM for _ in texts]


def _seed_facts(db, owner: str, n: int) -> None:
    with db.transaction() as conn:
        conn.execute("INSERT INTO owners (id, label, kind) VALUES (%s, %s, 'demo')", (owner, owner))
        conn.execute(
            "INSERT INTO subjects (id, owner, path, label, kind, status) VALUES "
            "('s_lazy', %s, 'life/hobbies', 'Hobbies', 'topic', 'active')",
            (owner,),
        )
        for i in range(n):
            fid = f"f_lazy_{i:03d}"
            txt = f"Karim note number {i} about a synthetic hobby fact"
            conn.execute(
                "INSERT INTO facts (id, owner, text, text_folded, subject_id, valid_from, status, provenance, content_hash) "
                "VALUES (%s, %s, %s, %s, 's_lazy', '2026-11-10', 'active', 'user_supplied', %s)",
                (fid, owner, txt, fold_text(txt), f"h_{fid}"),
            )


def _embedded_count(db, owner: str) -> int:
    with db.connection() as conn:
        return conn.execute(
            "SELECT count(*) AS c FROM facts WHERE owner = %s AND embedding IS NOT NULL", (owner,)
        ).fetchone()["c"]


def test_lazy_backfill_eventually_embeds_all_and_marks_done_only_at_end(pg_db, monkeypatch) -> None:
    _seed_facts(pg_db, "e11_lazy", 150)
    monkeypatch.setenv("TM_SEMANTIC", "1")
    monkeypatch.setenv("TM_SEMANTIC_LAZY_INTERVAL_S", "0")
    monkeypatch.setattr(embed, "is_loaded", lambda *a, **k: True)
    monkeypatch.setattr(embed, "embed_passages", _fake_passages)

    # time_budget_s=0 -> exactly one batch per call, so progress is deterministic.
    for call in range(10):
        assert ensure_embeddings(pg_db, "e11_lazy", batch_size=32, time_budget_s=0) is None
        done = embed._BACKFILLED_AT.get("e11_lazy") == 0
        if done:
            break
        # version is only marked done once nothing is left
        assert embed._BACKFILLED_AT.get("e11_lazy") is None
    assert done
    assert _embedded_count(pg_db, "e11_lazy") == 150

    # a further call is a no-op: version already marked done
    assert ensure_embeddings(pg_db, "e11_lazy", batch_size=32, time_budget_s=0) is None
    assert _embedded_count(pg_db, "e11_lazy") == 150


def test_ensure_embeddings_never_loads_model_on_query_path(pg_db, monkeypatch) -> None:
    _seed_facts(pg_db, "e11_cold", 3)
    monkeypatch.setenv("TM_SEMANTIC", "1")
    monkeypatch.setattr(embed, "is_loaded", lambda *a, **k: False)

    def _no_embed(*a, **k):
        raise AssertionError("embed_pending_facts must not run while the model is not loaded")

    monkeypatch.setattr(embed, "embed_pending_facts", _no_embed)
    assert ensure_embeddings(pg_db, "e11_cold") == "embedder_unavailable"
    assert embed._BACKFILLED_AT.get("e11_cold") is None
    assert _embedded_count(pg_db, "e11_cold") == 0

    # embed_query raises instead of loading/downloading inside a request
    monkeypatch.setattr(embed, "_SESSION", None)
    monkeypatch.setattr(embed, "_LOADED_MODEL_NAME", None)
    with pytest.raises(RuntimeError, match="not loaded"):
        embed.embed_query("surf school")


def test_failed_model_load_is_cached_for_backoff_window(monkeypatch) -> None:
    # The download path is what matters here, so stub the optional ONNX deps:
    # the load fails inside _download_asset before onnxruntime is ever used.
    import sys
    import types

    fake_ort = types.ModuleType("onnxruntime")
    fake_tok = types.ModuleType("tokenizers")
    fake_tok.Tokenizer = object  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "onnxruntime", fake_ort)
    monkeypatch.setitem(sys.modules, "tokenizers", fake_tok)

    monkeypatch.setenv("TM_SEMANTIC", "1")
    monkeypatch.setenv("TM_EMBED_LOAD_BACKOFF_S", "60")
    monkeypatch.setattr(embed, "_SESSION", None)
    monkeypatch.setattr(embed, "_LOADED_MODEL_NAME", None)
    monkeypatch.setattr(embed, "_LOAD_RETRY_AT", 0.0)

    attempts = []

    def _offline(repo_id, filename):
        attempts.append(filename)
        raise RuntimeError("offline")

    monkeypatch.setattr(embed, "_download_asset", _offline)

    assert embed.is_available() is False
    assert embed.is_available() is False
    # second call failed fast inside the backoff window: only one download attempt
    assert len(attempts) == 1

    # after the backoff window a new attempt is allowed
    monkeypatch.setattr(embed, "_LOAD_RETRY_AT", 0.0)
    assert embed.is_available() is False
    assert len(attempts) == 2


def test_embed_pending_facts_time_budget_reports_remaining(pg_db, monkeypatch) -> None:
    _seed_facts(pg_db, "e11_budget", 25)
    monkeypatch.setattr(embed, "embed_passages", _fake_passages)

    stats = embed_pending_facts(
        pg_db, owner="e11_budget", batch_size=10, limit=100, time_budget_s=0
    )
    assert stats["embedded"] == 10
    assert stats["fetched"] == 25
    assert stats["remaining"] == 15
    assert _embedded_count(pg_db, "e11_budget") == 10
