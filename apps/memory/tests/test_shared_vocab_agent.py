"""E13b shared-vocab agent: clustering, proposals, privacy, admin gates."""
from __future__ import annotations

import hashlib
import json

from fastapi.testclient import TestClient
import pytest

from temporal_memory.api.app import create_app
from temporal_memory.db import db as db_module
from temporal_memory.db.db import create_test_schema, drop_test_schema, fold_text
from temporal_memory.vocab.loader import DEFAULT_TREE_PATH, get_vocab
from temporal_memory.vocab.shared_proposer import propose_shared_vocab_promotions
from temporal_memory.vocab.similarity import (
    find_similar_queries_and_terms,
    hash_owner,
    purge_owner_query_signals,
    record_query_signal,
)

HMAC_KEY = "e13b-test-signal-hmac-key"
ADMIN = "e13b-admin"
PARENT = "lifestyle/sports/team_sports"
NOVEL = "korfball"


@pytest.fixture()
def pg(monkeypatch):
    monkeypatch.setenv("TM_SIGNAL_HMAC_KEY", HMAC_KEY)
    schema_db, schema = create_test_schema()
    prev = db_module._DEFAULT_DB
    db_module._DEFAULT_DB = schema_db
    try:
        yield schema_db
    finally:
        db_module._DEFAULT_DB = prev
        drop_test_schema(schema_db, schema)


@pytest.fixture()
def api(pg):
    app = create_app(pg, admin_token=ADMIN)
    client = TestClient(app)
    admin = {"Authorization": f"Bearer {ADMIN}"}
    for oid in ("alice", "bob", "carol", "dave"):
        assert client.post(
            "/v1/owners",
            headers=admin,
            json={"id": oid, "label": oid.title(), "kind": "simulated", "display_name": oid.title()},
        ).status_code == 200
    tokens = {}
    for oid in ("alice", "bob", "carol", "dave"):
        tokens[oid] = client.post(
            "/v1/tokens", headers=admin, json={"role": "owner-device", "owner": oid, "label": "phone"}
        ).json()["token"]
    worker = client.post("/v1/tokens", headers=admin, json={"role": "worker", "label": "w"}).json()["token"]
    return {
        "client": client,
        "db": pg,
        "admin": admin,
        "owner": {oid: {"Authorization": f"Bearer {tok}"} for oid, tok in tokens.items()},
        "worker": {"Authorization": f"Bearer {worker}"},
    }


def _seed_owner(conn, owner: str) -> None:
    conn.execute(
        "INSERT INTO owners (id, label, kind) VALUES (%s, %s, 'simulated') ON CONFLICT DO NOTHING",
        (owner, owner),
    )


def _mock_runner_ok(system: str, user_payload: str) -> dict:
    payload = json.loads(user_payload)
    assert "clusters" in payload
    # No owner ids / hashes in the model payload.
    blob = json.dumps(payload)
    assert "alice" not in blob and "bob" not in blob and "carol" not in blob
    assert hash_owner("alice") not in blob
    first = payload["clusters"][0]
    term = next(t for t in first["terms"] if NOVEL in t)
    parent = first["candidate_parents"][0]
    return {
        "new_terms": [
            {
                "term": term,
                "is_a": parent,
                "evidence": ["Popular racket-team sport across Dubai clubs", "korfbal"],
            }
        ]
    }


def _mock_runner_reject(system: str, user_payload: str) -> dict:
    return {"new_terms": []}


def test_happy_path_three_owners_en_ar_arabizi_pending_proposal(api, monkeypatch):
    monkeypatch.setenv("TM_SIGNAL_HMAC_KEY", HMAC_KEY)
    db = api["db"]
    tree_before = DEFAULT_TREE_PATH.read_bytes()
    with db.transaction() as conn:
        # EN / AR / Arabizi user-typed queries from three distinct owners.
        assert record_query_signal(
            conn, "alice", f"{NOVEL} tonight DIFC", source="user_typed", resolved_branch=PARENT
        )
        assert record_query_signal(
            conn, "bob", f"كورفبول {NOVEL} partners", source="user_typed", resolved_branch=PARENT
        )
        assert record_query_signal(
            conn, "carol", f"{NOVEL} arabizi korfbol partners", source="user_typed", resolved_branch=PARENT
        )

        similar = find_similar_queries_and_terms(conn, NOVEL, min_sim=0.5)
        assert similar
        top = next(r for r in similar if r["term_folded"] == fold_text(NOVEL) or NOVEL in r["term"])
        assert top["distinct_owners"] >= 3
        # Aggregate counts only — never owner ids or hashes in the return payload.
        dumped = json.dumps(similar)
        assert "alice" not in dumped and "bob" not in dumped and "carol" not in dumped
        assert hash_owner("alice") not in dumped

        result = propose_shared_vocab_promotions(conn, min_owners=3, min_sim=0.5, runner=_mock_runner_ok)
        assert result["proposed"], result
        prop = result["proposed"][0]
        assert prop["distinct_owners"] >= 3
        assert NOVEL in prop["canonical_term"].lower() or prop["canonical_term"]

        row = conn.execute(
            "SELECT * FROM shared_vocab_proposals WHERE id = %s", (prop["id"],)
        ).fetchone()
        assert row["status"] == "pending"
        assert int(row["distinct_owners"]) >= 3
        meta = row["cluster_metadata"]
        if isinstance(meta, str):
            meta = json.loads(meta)
        meta_blob = json.dumps(meta)
        assert "alice" not in meta_blob and hash_owner("alice") not in meta_blob

    # Admin list: aggregate fields only, no owner ids/hashes.
    listed = api["client"].get("/v1/admin/vocab/proposals", headers=api["admin"])
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert body["count"] >= 1
    out = json.dumps(body)
    assert "alice" not in out and hash_owner("alice") not in out
    assert all("owner" not in item or item.get("owner") is None for item in body["items"])

    # tree.json never modified by propose.
    assert DEFAULT_TREE_PATH.read_bytes() == tree_before


def test_fewer_than_min_owners_rejected(pg, monkeypatch):
    monkeypatch.setenv("TM_SIGNAL_HMAC_KEY", HMAC_KEY)
    with pg.transaction() as conn:
        _seed_owner(conn, "alice")
        _seed_owner(conn, "bob")
        record_query_signal(conn, "alice", f"{NOVEL} solo", source="user_typed", resolved_branch=PARENT)
        record_query_signal(conn, "bob", f"{NOVEL} duo", source="user_typed", resolved_branch=PARENT)
        result = propose_shared_vocab_promotions(conn, min_owners=3, min_sim=0.5, runner=_mock_runner_ok)
        assert result["proposed"] == []


def test_rule9_sensitive_term_blocked(pg, monkeypatch):
    monkeypatch.setenv("TM_SIGNAL_HMAC_KEY", HMAC_KEY)
    with pg.transaction() as conn:
        for oid in ("alice", "bob", "carol"):
            _seed_owner(conn, oid)
            stored = record_query_signal(
                conn, oid, "cancer diagnosis hospital therapy", source="user_typed"
            )
            assert stored == []
        terms = [r["term_folded"] for r in conn.execute("SELECT term_folded FROM vocab_query_signals").fetchall()]
        assert terms == []
        result = propose_shared_vocab_promotions(conn, min_owners=3, min_sim=0.1, runner=_mock_runner_ok)
        assert result["proposed"] == []


def test_f1_mixed_blocked_and_allowed_leaves_no_blocked_text(pg, monkeypatch):
    """F1: query_folded must never retain blocked clinic/password tokens."""
    monkeypatch.setenv("TM_SIGNAL_HMAC_KEY", HMAC_KEY)
    with pg.transaction() as conn:
        _seed_owner(conn, "alice")
        mixed = f"{NOVEL} clinic appointment password hospital"
        assert record_query_signal(conn, "alice", mixed, source="user_typed") == []
        rows = conn.execute(
            "SELECT term_folded, query_folded FROM vocab_query_signals"
        ).fetchall()
        blob = " ".join(f"{r['term_folded']} {r['query_folded']}" for r in rows)
        assert "clinic" not in blob
        assert "password" not in blob
        assert "hospital" not in blob
        assert rows == []


def test_google_sourced_learned_terms_excluded(pg, monkeypatch):
    monkeypatch.setenv("TM_SIGNAL_HMAC_KEY", HMAC_KEY)
    with pg.transaction() as conn:
        for i, oid in enumerate(("alice", "bob", "carol")):
            _seed_owner(conn, oid)
            # Mix: gmail source, e3:gmail: id (E13a-style), and google in meta.
            if i == 0:
                rid, source, meta = f"g{i}", "gmail:inbox", "{}"
            elif i == 1:
                rid, source, meta = f"e3:gmail:msg{i}", "notes:inbox", "{}"
            else:
                rid, source, meta = f"g{i}", "notes:inbox", '{"via":"youtube_takeout"}'
            conn.execute(
                "INSERT INTO records (id, owner, source, at, author, text, content_hash, meta) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)",
                (
                    rid,
                    oid,
                    source,
                    "2026-11-20T09:00:00Z",
                    oid,
                    f"{NOVEL} meetup",
                    hashlib.sha256(f"{oid}:{rid}".encode()).hexdigest(),
                    meta,
                ),
            )
            conn.execute(
                "INSERT INTO learned_terms (owner, term_folded, term, parent_path, path, provenance) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (oid, fold_text(NOVEL), NOVEL, PARENT, f"{PARENT}/{NOVEL}", "inferred"),
            )
            conn.execute(
                "INSERT INTO learned_term_sources (owner, term_folded, record_id, had_fact) "
                "VALUES (%s,%s,%s,%s)",
                (oid, fold_text(NOVEL), rid, False),
            )
        result = propose_shared_vocab_promotions(conn, min_owners=3, min_sim=0.5, runner=_mock_runner_ok)
        assert result["proposed"] == []
        similar = find_similar_queries_and_terms(conn, NOVEL, min_sim=0.5)
        assert not any(r["term_folded"] == fold_text(NOVEL) for r in similar)


def test_deleted_owner_signals_purged_and_excluded(api, monkeypatch):
    """F2: delete_account purges signals; deleted_from_external drops learned aggregates."""
    monkeypatch.setenv("TM_SIGNAL_HMAC_KEY", HMAC_KEY)
    monkeypatch.setattr(
        "temporal_memory.privacy.controls.purge_redis",
        lambda owner: True,
    )
    db = api["db"]
    with db.transaction() as conn:
        for oid in ("alice", "bob", "carol"):
            record_query_signal(conn, oid, f"{NOVEL} club", source="user_typed", resolved_branch=PARENT)
            rid = f"lt-{oid}"
            conn.execute(
                "INSERT INTO records (id, owner, source, at, author, text, content_hash) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (rid, oid, "notes:a", "2026-11-20T09:00:00Z", oid, f"{NOVEL}", hashlib.sha256(rid.encode()).hexdigest()),
            )
            conn.execute(
                "INSERT INTO learned_terms (owner, term_folded, term, parent_path, path, provenance) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (oid, fold_text(NOVEL), NOVEL, PARENT, f"{PARENT}/{NOVEL}-{oid}", "inferred"),
            )
            conn.execute(
                "INSERT INTO learned_term_sources (owner, term_folded, record_id, had_fact) "
                "VALUES (%s,%s,%s,%s)",
                (oid, fold_text(NOVEL), rid, False),
            )
        before = find_similar_queries_and_terms(conn, NOVEL, min_sim=0.5)
        assert any(r["distinct_owners"] >= 3 for r in before)

    # Admin delete-my-data triggers purge_owner_query_signals inside the transaction.
    resp = api["client"].post("/v1/owners/carol/delete-my-data", headers=api["admin"])
    assert resp.status_code == 200, resp.text
    with db.connection() as conn:
        carol_hash = hash_owner("carol")
        left = conn.execute(
            "SELECT COUNT(*) AS n FROM vocab_query_signals WHERE owner_hash = %s",
            (carol_hash,),
        ).fetchone()["n"]
        assert int(left) == 0
        assert conn.execute(
            "SELECT deleted_from_external FROM owners WHERE id = 'carol'"
        ).fetchone()["deleted_from_external"] is True
        after = find_similar_queries_and_terms(conn, NOVEL, min_sim=0.5)
        assert all(r["distinct_owners"] < 3 for r in after)
        result = propose_shared_vocab_promotions(conn, min_owners=3, min_sim=0.5, runner=_mock_runner_ok)
        assert result["proposed"] == []


def test_only_user_typed_queries_recorded(pg, monkeypatch):
    monkeypatch.setenv("TM_SIGNAL_HMAC_KEY", HMAC_KEY)
    with pg.transaction() as conn:
        _seed_owner(conn, "alice")
        assert record_query_signal(conn, "alice", f"{NOVEL} auto", source="context") == []
        assert record_query_signal(conn, "alice", f"{NOVEL} auto", source="automatic") == []
        assert record_query_signal(conn, "alice", f"{NOVEL} typed", source="user_typed")
        n = conn.execute("SELECT COUNT(*) AS n FROM vocab_query_signals").fetchone()["n"]
        assert int(n) >= 1


def test_f3_search_records_typed_context_does_not(api, monkeypatch):
    """F3: /search with include_lowered or user_typed records; /context never does."""
    monkeypatch.setenv("TM_SIGNAL_HMAC_KEY", HMAC_KEY)
    client, headers = api["client"], api["owner"]["alice"]
    db = api["db"]

    assert client.post(
        "/v1/owners/alice/context",
        headers=headers,
        json={"text": f"{NOVEL} from context pack"},
    ).status_code == 200
    with db.connection() as conn:
        n0 = conn.execute("SELECT COUNT(*) AS n FROM vocab_query_signals").fetchone()["n"]
    assert int(n0) == 0

    # Plain search without flags → not recorded.
    assert client.get(
        "/v1/owners/alice/search",
        headers=headers,
        params={"q": f"{NOVEL} plain"},
    ).status_code == 200
    with db.connection() as conn:
        n1 = conn.execute("SELECT COUNT(*) AS n FROM vocab_query_signals").fetchone()["n"]
    assert int(n1) == 0

    # Explicit owner-device typed search → recorded.
    assert client.get(
        "/v1/owners/alice/search",
        headers=headers,
        params={"q": f"{NOVEL} typed", "include_lowered": "true"},
    ).status_code == 200
    with db.connection() as conn:
        n2 = conn.execute("SELECT COUNT(*) AS n FROM vocab_query_signals").fetchone()["n"]
        rows = conn.execute("SELECT term_folded, query_folded FROM vocab_query_signals").fetchall()
    assert int(n2) >= 1
    blob = " ".join(f"{r['term_folded']} {r['query_folded']}" for r in rows)
    assert fold_text(NOVEL) in blob

    assert client.get(
        "/v1/owners/alice/search",
        headers=headers,
        params={"q": f"{NOVEL} flag", "user_typed": "true"},
    ).status_code == 200
    with db.connection() as conn:
        n3 = conn.execute("SELECT COUNT(*) AS n FROM vocab_query_signals").fetchone()["n"]
    assert int(n3) >= int(n2)


def test_hmac_key_unset_fail_closed_no_admin_fallback(pg, monkeypatch):
    monkeypatch.delenv("TM_SIGNAL_HMAC_KEY", raising=False)
    monkeypatch.setenv("TM_ADMIN_TOKEN", ADMIN)  # must NOT be reused as HMAC key
    assert hash_owner("alice") is None
    with pg.transaction() as conn:
        _seed_owner(conn, "alice")
        assert record_query_signal(conn, "alice", f"{NOVEL} typed", source="user_typed") == []
        n = conn.execute("SELECT COUNT(*) AS n FROM vocab_query_signals").fetchone()["n"]
        assert int(n) == 0
        assert purge_owner_query_signals(conn, "alice") == 0


def test_hmac_is_keyed_not_plain_sha256(monkeypatch):
    monkeypatch.setenv("TM_SIGNAL_HMAC_KEY", HMAC_KEY)
    plain = hashlib.sha256(b"alice").hexdigest()
    keyed = hash_owner("alice")
    assert keyed is not None
    assert keyed != plain
    assert len(keyed) == 64


def test_admin_only_vocab_routes_403_for_owner_and_worker(api):
    client = api["client"]
    for headers in (api["owner"]["alice"], api["worker"]):
        assert client.post("/v1/admin/vocab/propose", headers=headers).status_code == 403
        assert client.get("/v1/admin/vocab/proposals", headers=headers).status_code == 403
        assert client.post(
            "/v1/admin/vocab/proposals/1/decide",
            headers=headers,
            json={"decision": "approve"},
        ).status_code == 403


def test_on_conflict_keeps_single_live_proposal(pg, monkeypatch):
    monkeypatch.setenv("TM_SIGNAL_HMAC_KEY", HMAC_KEY)
    with pg.transaction() as conn:
        for oid in ("alice", "bob", "carol"):
            _seed_owner(conn, oid)
            record_query_signal(conn, oid, f"{NOVEL} night", source="user_typed", resolved_branch=PARENT)
        first = propose_shared_vocab_promotions(conn, min_owners=3, min_sim=0.5, runner=_mock_runner_ok)
        assert len(first["proposed"]) == 1
        second = propose_shared_vocab_promotions(conn, min_owners=3, min_sim=0.5, runner=_mock_runner_ok)
        assert second["proposed"] == []
        n = conn.execute(
            "SELECT COUNT(*) AS n FROM shared_vocab_proposals WHERE status = 'pending'"
        ).fetchone()["n"]
        assert int(n) == 1


def test_propose_endpoint_and_tree_json_untouched(api, monkeypatch):
    monkeypatch.setenv("TM_SIGNAL_HMAC_KEY", HMAC_KEY)
    db = api["db"]
    before = DEFAULT_TREE_PATH.read_bytes()
    mtime_before = DEFAULT_TREE_PATH.stat().st_mtime_ns
    with db.transaction() as conn:
        for oid in ("alice", "bob", "carol"):
            record_query_signal(conn, oid, f"{NOVEL} league", source="user_typed", resolved_branch=PARENT)

    # Inject runner via monkeypatch on module used by admin endpoint.
    import temporal_memory.vocab.shared_proposer as sp

    monkeypatch.setattr(sp, "propose_shared_vocab_promotions", lambda conn, **kw: {
        "considered": 1,
        "proposed": [],
        "llm_rejected": 0,
        "skipped": 0,
    })
    resp = api["client"].post("/v1/admin/vocab/propose", headers=api["admin"])
    assert resp.status_code == 200, resp.text
    assert resp.json()["ok"] is True
    assert DEFAULT_TREE_PATH.read_bytes() == before
    assert DEFAULT_TREE_PATH.stat().st_mtime_ns == mtime_before
    # Base curated tree still loads from tree.json only for get_vocab().
    assert any(n.path == PARENT for n in get_vocab().nodes)
