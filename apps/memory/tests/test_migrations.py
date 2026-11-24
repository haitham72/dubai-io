"""Postgres migration compatibility and shared U1 contract checks."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import psycopg
import pytest

from temporal_memory.config import settings
from temporal_memory.db import db as db_module
from temporal_memory.models import Candidate, Fact, FactEntity, GraphStoreFull, Owner, Record
from tests.fixtures.fake_store import FakeGraphStore


@pytest.fixture
def db():
    schema = f"tm_test_u0a_{uuid4().hex[:12]}"
    database = db_module.Database(settings.test_database_url, schema=schema)
    try:
        yield database
    finally:
        db_module.drop_test_schema(database, schema)


def test_upgrade_bootstraps_existing_schema_without_changing_data(db):
    with db.transaction() as conn:
        conn.execute(f"CREATE SCHEMA {db.schema}")
        conn.execute(f"SET LOCAL search_path TO {db.schema}, public")
        conn.execute(db_module.SCHEMA_SQL_PATH.read_text(encoding="utf-8"))
        conn.execute("INSERT INTO owners (id, label) VALUES ('legacy', 'Legacy test owner')")
        conn.execute("INSERT INTO entities (id, owner, kind, name, status, closeness_tier) "
                     "VALUES ('e', 'legacy', 'person', 'Synthetic contact', 'active', 'T1')")
        conn.execute("INSERT INTO subjects (id, owner, path, label, status) "
                     "VALUES ('s', 'legacy', 'events', 'Events', 'active')")
        conn.execute("INSERT INTO facts (id, owner, text, subject_id, content_hash) "
                     "VALUES ('f', 'legacy', 'Synthetic fact', 's', 'hash')")
        conn.execute("INSERT INTO links (id, owner, src, rel, dst, evidence_fact_id) "
                     "VALUES ('l', 'legacy', 'e', 'RELATED_TO', 'e2', 'f')")

    db_module.migrate(db)

    with db.connection() as conn:
        entity = conn.execute(
            "SELECT name, status, closeness_tier, provenance, user_confirmed_at, closeness_suggested, "
            "closeness_suggested_evidence, tier_confirmed_at, salience_updated_at FROM entities"
        ).fetchone()
        assert entity == {
            "name": "Synthetic contact", "status": "active", "closeness_tier": "T1",
            "provenance": "inferred", "user_confirmed_at": None, "closeness_suggested": None,
            "closeness_suggested_evidence": None, "tier_confirmed_at": None, "salience_updated_at": None,
        }
        assert conn.execute("SELECT path, status, provenance, user_confirmed_at FROM subjects").fetchone() == {
            "path": "events", "status": "active", "provenance": "inferred", "user_confirmed_at": None,
        }
        assert conn.execute("SELECT id, label, privacy_revision FROM owners").fetchone() == {
            "id": "legacy", "label": "Legacy test owner", "privacy_revision": 0,
        }
        assert conn.execute("SELECT id, text FROM visible_facts").fetchone() == {"id": "f", "text": "Synthetic fact"}
        assert conn.execute("SELECT evidence_fact_id FROM links").fetchone() == {"evidence_fact_id": "f"}
        assert conn.execute("SELECT COUNT(*) AS n FROM link_evidence").fetchone()["n"] == 0
        stamp = conn.execute("SELECT applied_at FROM schema_migrations WHERE version = 1").fetchone()

    db_module.migrate(db)
    with db.connection() as conn:
        assert conn.execute("SELECT applied_at FROM schema_migrations WHERE version = 1").fetchone() == stamp


def test_pending_migrations_are_ordered_atomic_and_safe_to_retry(db, monkeypatch, tmp_path):
    db_module.migrate(db)
    for path in db_module.MIGRATIONS_PATH.glob("*.sql"):
        (tmp_path / path.name).write_bytes(path.read_bytes())
    monkeypatch.setattr(db_module, "MIGRATIONS_PATH", tmp_path)
    pending = tmp_path / "0003_insert_marker.sql"
    pending.write_text("INSERT INTO migration_probe VALUES (7); SELECT 1 / 0;", encoding="utf-8")
    (tmp_path / "0002_create_probe.sql").write_text("CREATE TABLE migration_probe (n INTEGER);", encoding="utf-8")

    with pytest.raises(psycopg.errors.DivisionByZero):
        db_module.migrate(db)
    with db.connection() as conn:
        assert list(conn.execute("SELECT version FROM schema_migrations ORDER BY version")) == [{"version": 1}]
        assert conn.execute("SELECT to_regclass('migration_probe') AS name").fetchone()["name"] is None

    pending.write_text("INSERT INTO migration_probe VALUES (7);", encoding="utf-8")
    db_module.migrate(db)
    db_module.migrate(db)
    with db.connection() as conn:
        assert list(conn.execute("SELECT version FROM schema_migrations ORDER BY version")) == [
            {"version": 1}, {"version": 2}, {"version": 3},
        ]
        assert list(conn.execute("SELECT n FROM migration_probe")) == [{"n": 7}]


def test_concurrent_fresh_installs_share_one_migration_ledger(db):
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(db_module.migrate, db)
        second = pool.submit(db_module.migrate, db)
        first.result(timeout=15)
        second.result(timeout=15)
    with db.connection() as conn:
        assert list(conn.execute("SELECT version FROM schema_migrations")) == [{"version": 1}]
        assert conn.execute("SELECT to_regclass('forget_requests') AS name").fetchone()["name"] == "forget_requests"


def test_link_evidence_and_forget_receipts_are_owner_scoped(db):
    db_module.migrate(db)
    with db.transaction() as conn:
        conn.execute("INSERT INTO owners (id, label) VALUES ('a', 'A'), ('b', 'B')")
        conn.execute("INSERT INTO facts (owner, id, text, subject_id, content_hash) "
                     "VALUES ('a', 'fa', 'A', 's', 'ha'), ('b', 'fb', 'B', 's', 'hb')")
        conn.execute("INSERT INTO links (owner, id, src, rel, dst) VALUES ('a', 'l', 's', 'RELATED_TO', 'd')")
        conn.execute("INSERT INTO link_evidence (owner, link_id, fact_id) VALUES ('a', 'l', 'fa')")
        conn.execute("INSERT INTO forget_requests (owner, idempotency_key, request, result) "
                     "VALUES ('a', 'same', '{}', '{}'), ('b', 'same', '{}', '{}')")
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        with db.transaction() as conn:
            conn.execute("INSERT INTO link_evidence (owner, link_id, fact_id) VALUES ('a', 'l', 'fb')")
    with pytest.raises(psycopg.errors.UniqueViolation):
        with db.transaction() as conn:
            conn.execute("INSERT INTO forget_requests (owner, idempotency_key, request, result) "
                         "VALUES ('a', 'same', '{}', '{}')")
    with db.transaction() as conn:
        conn.execute("DELETE FROM facts WHERE owner = 'a' AND id = 'fa'")
        assert not list(conn.execute("SELECT fact_id FROM link_evidence"))
        conn.execute("INSERT INTO facts (owner, id, text, subject_id, content_hash) VALUES ('a', 'fa', 'A', 's', 'ha')")
        conn.execute("INSERT INTO link_evidence (owner, link_id, fact_id) VALUES ('a', 'l', 'fa')")
        conn.execute("DELETE FROM links WHERE owner = 'a' AND id = 'l'")
        assert not list(conn.execute("SELECT fact_id FROM link_evidence"))
        conn.execute("DELETE FROM owners WHERE id = 'a'")
        assert list(conn.execute("SELECT owner FROM forget_requests")) == [{"owner": "b"}]


def test_fake_store_implements_new_contract():
    fake = FakeGraphStore()
    store: GraphStoreFull = fake
    fake.owners.update(a=Owner("a", "A"), b=Owner("b", "B"))
    fake.records["a"]["shared"] = Record("shared", "a", "messenger:c1", "2026-11-24", "Karim", "Coffee")
    fake.records["a"]["other"] = Record("other", "a", "community:abc", "2026-11-24", "Karim", "Coffee")
    fake.facts["a"] = [
        Fact("valid", "a", "Coffee", "s", "2026-11-24T09:00", ["shared"], [FactEntity("e")]),
        Fact("mixed", "a", "Coffee cafe", "s", "2026-11-24T08:00", ["shared", "other"]),
        Fact("forgotten", "a", "Coffee", "s", "2026-11-23", ["shared"]),
        Fact("history", "a", "Coffee", "s", "2026-11-22", ["shared"], status="history"),
    ]
    fake.forgotten_fact_ids["a"].add("forgotten")
    assert store.search_candidates("a", "coffee cafe", source_prefix="messenger:c1", limit=1) == [
        Candidate("valid", 1.0, "fts")
    ]
    assert store.search_candidates("a", "", entity_ids=["e"]) == [Candidate("valid", 1.0, "entity")]
    assert [fact.id for fact in store.get_facts("a", ["history", "mixed", "forgotten", "mixed", "valid"])] == [
        "mixed", "valid",
    ]
    assert store.get_facts("b", ["valid"]) == []
    assert store.fact_counts_by_subject("a") == {"s": 2}
    assert [fact.id for fact in store.iter_visible_facts(
        "a", date_from="2026-11-24", date_to="2026-11-24", after=("2026-11-24T09:00", "valid"), page_size=1,
    )] == ["mixed"]
    assert store.bump_privacy_revision("a") == 1
    assert fake.owners["a"].privacy_revision == 1
    assert fake.owners["b"].privacy_revision == 0
