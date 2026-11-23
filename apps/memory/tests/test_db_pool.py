"""Regression: pooled connections must come back clean (found by the Docker e2e, 23 Nov).

Without a schema (the API's case), a plain read left an implicit transaction open on the pooled
connection; the next `transaction()` became a SAVEPOINT inside it and its INSERT never committed.
"""
from __future__ import annotations

import os
import uuid

import psycopg
import pytest

from temporal_memory.db.db import Database

DSN = os.environ.get("TM_TEST_DATABASE_URL", "postgresql://tm:tm@localhost:5442/tm")


@pytest.fixture()
def scratch():
    schema = f"tm_pool_{uuid.uuid4().hex[:10]}"
    try:
        with psycopg.connect(DSN, autocommit=True) as c:
            c.execute(f"CREATE SCHEMA {schema}")
            c.execute(f"CREATE TABLE {schema}.t (id text primary key)")
    except psycopg.OperationalError as exc:  # no compose Postgres running
        pytest.skip(f"Postgres not reachable: {exc}")
    yield schema
    with psycopg.connect(DSN, autocommit=True) as c:
        c.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")


def _visible_elsewhere(schema: str, row_id: str) -> bool:
    with psycopg.connect(DSN, autocommit=True) as other:
        return other.execute(f"SELECT 1 FROM {schema}.t WHERE id = %s", (row_id,)).fetchone() is not None


def test_write_after_read_on_pooled_connection_is_committed(scratch):
    db = Database(DSN)  # no schema: the API's configuration
    try:
        with db.connection() as conn:  # a plain read (like /health) opens an implicit transaction
            conn.execute("SELECT 1").fetchone()
        with db.transaction() as conn:
            conn.execute(f"INSERT INTO {scratch}.t (id) VALUES ('owner-1')")
        assert _visible_elsewhere(scratch, "owner-1")
    finally:
        db.close()


def test_failed_block_does_not_poison_the_pool(scratch):
    db = Database(DSN)
    try:
        with pytest.raises(psycopg.errors.UndefinedTable):
            with db.transaction() as conn:
                conn.execute(f"SELECT * FROM {scratch}.missing")
        with db.transaction() as conn:
            conn.execute(f"INSERT INTO {scratch}.t (id) VALUES ('after-error')")
        assert _visible_elsewhere(scratch, "after-error")
    finally:
        db.close()


def test_uncommitted_write_on_connection_rolls_back_and_does_not_leak(scratch):
    db = Database(DSN)
    try:
        with db.connection() as conn:
            conn.execute(f"INSERT INTO {scratch}.t (id) VALUES ('uncommitted-row')")
        assert not _visible_elsewhere(scratch, "uncommitted-row")
        with db.transaction() as conn:
            conn.execute(f"INSERT INTO {scratch}.t (id) VALUES ('clean-next')")
        assert _visible_elsewhere(scratch, "clean-next")
        assert not _visible_elsewhere(scratch, "uncommitted-row")
    finally:
        db.close()
