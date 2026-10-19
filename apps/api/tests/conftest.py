"""Run the whole suite on Postgres too: set TEST_DATABASE_URL (e.g. the docker-compose database).

Each test gets its own schema, dropped afterwards, so tests stay isolated exactly as with
their per-test SQLite files. Without TEST_DATABASE_URL the suite uses SQLite (default, fast).
"""
import os
from uuid import uuid4

import pytest

URL = os.getenv("TEST_DATABASE_URL", "")


@pytest.fixture(autouse=True)
def postgres_schema(monkeypatch):
    if not URL:
        yield
        return
    import psycopg
    from app import actions, db

    schema = "t_" + uuid4().hex[:12]
    with psycopg.connect(URL, autocommit=True) as admin:
        admin.execute(f"CREATE SCHEMA {schema}")
    sep = "&" if "?" in URL else "?"
    scoped = f"{URL}{sep}options=-csearch_path%3D{schema},public"
    monkeypatch.setattr(actions, "connect", lambda target: db.PostgresDB(scoped))
    yield
    with psycopg.connect(URL, autocommit=True) as admin:
        admin.execute(f"DROP SCHEMA {schema} CASCADE")
