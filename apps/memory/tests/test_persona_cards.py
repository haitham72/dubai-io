"""Postgres cards and §9 leaves: privacy, supersession, forget, tiers, splits, 20k p95."""
from __future__ import annotations

import statistics
import time

from fastapi.testclient import TestClient
import pytest

from temporal_memory.api.app import create_app
from temporal_memory.api.export_md import render
from temporal_memory.core.persona import person_card
from temporal_memory.db.db import create_test_schema, drop_test_schema, fold_text

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


def _owner(conn, owner="karim"):
    conn.execute(
        "INSERT INTO owners (id, label, display_name, evidence_limits) VALUES (%s, %s, %s, %s)",
        (owner, "Karim", "Karim Haddad", "voice notes not read; history before import start not seen"),
    )


def _subject(conn, sid, path, label, *, sensitive=None):
    conn.execute(
        """
        INSERT INTO subjects (id, owner, path, label, kind, status, sensitive_cat)
        VALUES (%s, 'karim', %s, %s, 'topic', 'active', %s)
        """,
        (sid, path, label, sensitive),
    )


def _fact(conn, fid, sid, text, *, status="active", provenance="user_supplied", valid_from="2026-11-01", valid_to=None):
    conn.execute(
        """
        INSERT INTO facts (id, owner, text, text_folded, subject_id, valid_from, valid_to, status, provenance, content_hash)
        VALUES (%s, 'karim', %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (fid, text, fold_text(text), sid, valid_from, valid_to, status, provenance, "h-" + fid),
    )


def test_leaves_hide_sensitive_and_inferred_stated_and_show_supersession(pg_db):
    with pg_db.transaction() as conn:
        _owner(conn)
        _subject(conn, "s-rent", "home-money/rent", "Rent")
        _subject(conn, "s-health", "health/clinic", "Clinic", sensitive="health")
        _fact(conn, "f-old", "s-rent", "Karim paid AED 5000", status="superseded", valid_to="2026-11-02", valid_from="2026-10-01")
        _fact(conn, "f-new", "s-rent", "Karim pays AED 5400", valid_from="2026-11-02")
        _fact(conn, "f-guess", "s-rent", "Karim wants a different project", provenance="inferred")
        _fact(conn, "f-secret", "s-health", "thyroid panel was abnormal")
        conn.execute(
            "INSERT INTO quarantine (owner, category, record_ids) VALUES ('karim', 'credential', '[]'::jsonb)"
        )
    tree = render("karim", db=pg_db)
    blob = "\n".join(tree.values())
    assert "was Karim paid AED 5000 until 2026-11-02" in tree["05-home-and-money/rent.md"]
    assert "thyroid panel was abnormal" not in blob
    assert "health/" not in " ".join(tree)
    guess = next(line for line in tree["05-home-and-money/rent.md"].splitlines() if "different project" in line)
    assert "You told me" not in guess
    assert "inferred" in guess
    told = next(line for line in tree["05-home-and-money/rent.md"].splitlines() if "AED 5400" in line)
    assert "You told me" in told
    assert "credential" in tree["SOURCES.md"]
    assert "BarshaL0bby" not in blob


def test_forgotten_fact_leaves_the_tree_and_the_card(pg_db):
    with pg_db.transaction() as conn:
        _owner(conn)
        _subject(conn, "s-rent", "home-money/rent", "Rent")
        _fact(conn, "f-keep", "s-rent", "Karim pays AED 5400")
        _fact(conn, "f-gone", "s-rent", "Lobby code is 4412")
        conn.execute(
            """
            INSERT INTO entities (id, owner, kind, name, status, relation_to_user, closeness_tier, provenance, tier_confirmed_at)
            VALUES ('omar', 'karim', 'person', 'Omar Farouk', 'active', 'friend', 'T1', 'user_supplied', now())
            """
        )
        conn.execute(
            "INSERT INTO fact_entities (owner, fact_id, entity_id, role) VALUES ('karim', 'f-gone', 'omar', 'told')"
        )
    before = render("karim", db=pg_db)
    assert "4412" in "\n".join(before.values())
    with pg_db.transaction() as conn:
        conn.execute("UPDATE facts SET erased_at = now() WHERE id = 'f-gone'")
        conn.execute("UPDATE owners SET privacy_revision = privacy_revision + 1 WHERE id = 'karim'")
    after = render("karim", db=pg_db)
    assert "4412" not in "\n".join(after.values())
    card = person_card(pg_db, "karim", "omar")
    assert card is not None
    assert "4412" not in str(card)
    assert card["tier"] == "T1"


def test_confirmed_tier_card_differs_from_a_suggestion(pg_db):
    app = create_app(db=pg_db, admin_token="u6")
    client = TestClient(app)
    hdr = {"Authorization": "Bearer u6"}
    with pg_db.transaction() as conn:
        _owner(conn)
        _subject(conn, "s-people", "people-family/friends", "Friends")
        _fact(conn, "f-said", "s-people", "Omar is a close friend")
        conn.execute(
            """
            INSERT INTO entities (id, owner, kind, name, status, relation_to_user, closeness_tier, provenance, tier_confirmed_at)
            VALUES ('omar', 'karim', 'person', 'Omar Farouk', 'active', 'friend', 'T1', 'user_supplied', now())
            """
        )
        conn.execute(
            """
            INSERT INTO entities (id, owner, kind, name, status, closeness_suggested, provenance)
            VALUES ('layla', 'karim', 'person', 'Layla Haddad', 'active', 'T1', 'inferred')
            """
        )
        conn.execute(
            "INSERT INTO fact_entities (owner, fact_id, entity_id, role) VALUES ('karim', 'f-said', 'omar', 'friend')"
        )
    omar = client.get("/v1/owners/karim/people/omar/card", headers=hdr)
    layla = client.get("/v1/owners/karim/people/layla/card", headers=hdr)
    assert omar.status_code == 200
    assert layla.status_code == 200
    assert omar.json()["tier"] == "T1"
    assert omar.json()["relation"] == "friend"
    assert any(item["text"] == "Omar is a close friend" for item in omar.json()["snapshot"])
    assert layla.json()["tier"] is None
    assert any(item["text"].startswith("I noticed") for item in layla.json()["noticed"])
    assert "You told me" not in str(layla.json()["noticed"])
    other = client.get(
        "/v1/owners/karim/people/omar/card",
        headers={"Authorization": "Bearer nope"},
    )
    assert other.status_code == 401
    missing = client.get("/v1/owners/karim/people/nobody/card", headers=hdr)
    assert missing.status_code == 404


def test_split_proposal_fires_at_12_and_does_not_apply(pg_db):
    with pg_db.transaction() as conn:
        _owner(conn)
        _subject(conn, "s-rent", "home-money/rent", "Rent")
        for i in range(12):
            _fact(conn, f"f{i}", "s-rent", f"Rent note {i}", valid_from=f"2026-10-{i+1:02d}")
    tree = render("karim", db=pg_db)
    proposal = tree["_staging/proposed-tree-splits.md"]
    assert "05-home-and-money/rent.md" in proposal
    assert "Not applied" in proposal
    assert "05-home-and-money/rent/" not in " ".join(tree)
    assert not any("/rent/" in path for path in tree)


def test_cards_cluster_and_cross_owner_403(pg_db):
    app = create_app(db=pg_db, admin_token="u6")
    client = TestClient(app)
    tok = client.post(
        "/v1/tokens",
        headers={"Authorization": "Bearer u6"},
        json={"role": "owner-device", "owner": "other", "label": "phone"},
    ).json()["token"]
    with pg_db.transaction() as conn:
        _owner(conn)
        _subject(conn, "s-rent", "money/al-barsha-rent", "Rent")
        _fact(conn, "f-new", "s-rent", "Karim pays AED 5400")
    ok = client.get("/v1/owners/karim/cards", headers={"Authorization": "Bearer u6"}, params={"cluster": "home-money"})
    assert ok.status_code == 200
    assert ok.json()["cards"]
    assert ok.json()["cards"][0]["cluster"] == "home-money"
    blocked = client.get("/v1/owners/karim/cards", headers={"Authorization": f"Bearer {tok}"})
    assert blocked.status_code == 403
    bad = client.get("/v1/owners/karim/cards", headers={"Authorization": "Bearer u6"}, params={"cluster": "gaming"})
    assert bad.status_code == 400


def test_person_card_p95_under_150ms_at_20k(pg_db):
    n = 20_000
    with pg_db.transaction() as conn:
        _owner(conn, "karim")
        cur = conn.cursor()
        with cur.copy("COPY subjects (id, owner, path, label, kind, status) FROM STDIN") as cp:
            for j, path in enumerate(("career/atlas", "home-money/rent", "events/dining", "projects/raseef", "learning/ai", "travel/trips")):
                cp.write_row((f"s{j}", "karim", path, path, "topic", "active"))
        with cur.copy("COPY entities (id, owner, kind, name, status, closeness_tier, provenance) FROM STDIN") as cp:
            cp.write_row(("omar", "karim", "person", "Omar Farouk", "active", "T1", "user_supplied"))
        with cur.copy("COPY facts (id, owner, text, text_folded, subject_id, valid_from, status, provenance, content_hash) FROM STDIN") as cp:
            for k in range(n):
                text = f"Note {k} about rent and work"
                cp.write_row((f"f{k}", "karim", text, fold_text(text), f"s{k % 6}", "2026-11-01", "active", "user_supplied", f"h{k}"))
        with cur.copy("COPY fact_entities (owner, fact_id, entity_id) FROM STDIN") as cp:
            for k in range(n):
                cp.write_row(("karim", f"f{k}", "omar"))
        conn.execute("UPDATE entities SET tier_confirmed_at = now() WHERE id = 'omar'")
    with pg_db.connection() as conn:
        conn.commit()
        old = conn.autocommit
        conn.autocommit = True
        try:
            conn.execute("ANALYZE facts")
            conn.execute("ANALYZE fact_entities")
        finally:
            conn.autocommit = old
    samples = []
    for _ in range(30):
        t0 = time.perf_counter()
        body = person_card(pg_db, "karim", "omar")
        samples.append((time.perf_counter() - t0) * 1000.0)
        assert body is not None and body["tier"] == "T1"
        assert len(body["snapshot"]) <= 4
    p95 = statistics.quantiles(samples, n=20)[18]
    assert p95 < 150.0, f"person card p95 {p95:.2f}ms >= 150ms"
    app = create_app(db=pg_db, admin_token="u6")
    client = TestClient(app)
    res = client.get("/v1/owners/karim/people/omar/card", headers={"Authorization": "Bearer u6"})
    assert res.status_code == 200 and res.json()["tier"] == "T1"
