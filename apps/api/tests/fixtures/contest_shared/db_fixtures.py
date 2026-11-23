"""Postgres isolation fixture for B0 contest_shared tests when TEST_DATABASE_URL is set."""
from __future__ import annotations

import os
from uuid import uuid4

import pytest

from app import actions, db as db_mod


@pytest.fixture(autouse=True)
def cs_postgres_isolation(monkeypatch):
    """Mirror apps/api/tests/conftest.py schema isolation for app.db.connect & ActionStore."""
    url = os.getenv("TEST_DATABASE_URL", "").strip()
    if not url:
        yield
        return

    import psycopg

    schema = "t_cs_" + uuid4().hex[:12]
    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute(f"CREATE SCHEMA {schema}")

    sep = "&" if "?" in url else "?"
    scoped = f"{url}{sep}options=-csearch_path%3D{schema},extensions,public"

    opened_handles: list[db_mod.PostgresDB] = []
    orig_connect = db_mod.connect

    def _pg_connect(_target):
        handle = db_mod.PostgresDB(scoped)
        opened_handles.append(handle)
        return handle

    monkeypatch.setattr(db_mod, "connect", _pg_connect)
    monkeypatch.setattr(actions, "connect", _pg_connect)
    # Keep direct imports via identity.store / actions cleanly routed too.
    from app.identity import store as id_store_mod

    monkeypatch.setattr(id_store_mod.db_mod, "connect", _pg_connect)

    try:
        yield schema
    finally:
        for handle in opened_handles:
            try:
                handle.close()
            except Exception:
                pass
        monkeypatch.setattr(db_mod, "connect", orig_connect)
        with psycopg.connect(url, autocommit=True) as admin:
            admin.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
