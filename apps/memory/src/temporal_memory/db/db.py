"""Thread-safe psycopg3 connection pool, schema migration, and fold_text helper (WP-A)."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from queue import Empty, LifoQueue
import re
from typing import Iterator
import uuid

import psycopg
from psycopg.pq import TransactionStatus
from psycopg.rows import dict_row

from temporal_memory.config import settings

SCHEMA_SQL_PATH = Path(__file__).with_name("schema.sql")
_DIACRITICS = re.compile("[\u064b-\u065f\u0670\u0640]")
_LETTERS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه"})


class SchemaError(RuntimeError):
    """Raised on invalid schema identifier."""


def fold_text(text: str) -> str:
    """Fold Arabic/Latin text for simple-config FTS and alias matching."""
    cleaned = _DIACRITICS.sub("", (text or "").lower()).translate(_LETTERS)
    return re.sub(r"[\W_]+", " ", cleaned).strip()


def _validate_ident(name: str) -> str:
    if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]{0,62}", name):
        raise SchemaError(f"Invalid SQL identifier: {name!r}")
    return name


class Database:
    """Lightweight thread-safe psycopg3 connection pool with optional search_path isolation."""

    def __init__(self, dsn: str | None = None, *, schema: str | None = None, max_size: int = 8) -> None:
        self.dsn = dsn or settings.database_url
        self.schema = _validate_ident(schema) if schema else None
        self.max_size = max_size
        self._pool: LifoQueue[psycopg.Connection] = LifoQueue(maxsize=max_size)

    def _new_conn(self) -> psycopg.Connection:
        conn = psycopg.connect(self.dsn, row_factory=dict_row, autocommit=False)
        if self.schema:
            conn.execute(f"SET search_path TO {self.schema}, public")
            conn.commit()
        return conn

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection]:
        conn: psycopg.Connection | None = None
        try:
            conn = self._pool.get_nowait()
            if conn.closed:
                conn = self._new_conn()
        except Empty:
            conn = self._new_conn()

        try:
            if self.schema:
                conn.execute(f"SET search_path TO {self.schema}, public")
                conn.commit()
            yield conn
        except Exception:
            if not conn.closed:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise
        finally:
            if conn and not conn.closed:
                try:
                    # Never pool a connection that still has an implicit transaction open: the next
                    # `transaction()` would become a SAVEPOINT inside it and its writes would never commit.
                    if conn.info.transaction_status != TransactionStatus.IDLE:
                        conn.rollback()
                    self._pool.put_nowait(conn)
                except Exception:
                    conn.close()

    @contextmanager
    def transaction(self) -> Iterator[psycopg.Connection]:
        with self.connection() as conn:
            with conn.transaction():
                yield conn

    def close(self) -> None:
        while True:
            try:
                conn = self._pool.get_nowait()
                if not conn.closed:
                    conn.close()
            except Empty:
                break


def migrate(db: Database) -> None:
    """Apply idempotent DDL from schema.sql."""
    sql = SCHEMA_SQL_PATH.read_text(encoding="utf-8")
    with db.connection() as conn:
        if db.schema:
            conn.execute(f"CREATE SCHEMA IF NOT EXISTS {db.schema}")
            conn.execute(f"SET search_path TO {db.schema}, public")
        conn.execute(sql)
        conn.execute("ALTER TABLE job_attempts ADD COLUMN IF NOT EXISTS model_observed TEXT")
        conn.commit()


def create_test_schema(dsn: str | None = None) -> tuple[Database, str]:
    """Create a fresh schema tm_test_<uuid>, migrate it, and return (db, schema_name)."""
    schema = f"tm_test_{uuid.uuid4().hex[:12]}"
    db = Database(dsn or settings.test_database_url, schema=schema)
    migrate(db)
    return db, schema


def drop_test_schema(db: Database, schema: str) -> None:
    """Close pool and drop the isolated test schema."""
    ident = _validate_ident(schema)
    dsn = db.dsn
    db.close()
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(f"DROP SCHEMA IF EXISTS {ident} CASCADE")


_DEFAULT_DB: Database | None = None


def get_database(dsn: str | None = None) -> Database:
    global _DEFAULT_DB
    if _DEFAULT_DB is None or (dsn and _DEFAULT_DB.dsn != dsn):
        _DEFAULT_DB = Database(dsn or settings.database_url)
    return _DEFAULT_DB


def connect(dsn: str | None = None) -> psycopg.Connection:
    """Open a direct tuple-row psycopg3 connection (used by privacy.forget_source)."""
    url = dsn or (_DEFAULT_DB.dsn if _DEFAULT_DB is not None else settings.database_url)
    conn = psycopg.connect(url, autocommit=False)
    if _DEFAULT_DB is not None and _DEFAULT_DB.schema:
        conn.execute(f"SET search_path TO {_DEFAULT_DB.schema}, public")
        conn.commit()
    return conn
