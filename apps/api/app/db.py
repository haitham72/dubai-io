"""One database handle for the API: PostgreSQL 16 (+pgvector) when DATABASE_URL is set, SQLite otherwise.

Modules write portable SQL with `?` placeholders. For Postgres this layer translates the few
dialect differences (placeholders, INSERT OR IGNORE, JSON column type) and keeps the
sqlite3-style surface the code already uses: execute() -> cursor, commit(), close().
JSON columns are declared with the `JSON` token in DDL (JSONB on Postgres, TEXT on SQLite)
and always read back as text, so callers keep using json.loads.
"""
import re
import sqlite3
from pathlib import Path


class PostgresDB:
    dialect = "postgres"

    def __init__(self, url: str):
        import psycopg
        from psycopg.types.string import TextLoader
        self.conn = psycopg.connect(url, autocommit=False)
        for name in ("json", "jsonb"):  # hand JSON back as text, like SQLite
            self.conn.adapters.register_loader(name, TextLoader)
        self.conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        self.conn.commit()

    @staticmethod
    def translate(sql: str) -> str:
        if sql.lstrip().upper().startswith("INSERT OR IGNORE"):
            sql = re.sub(r"(?i)^\s*INSERT OR IGNORE", "INSERT", sql) + " ON CONFLICT DO NOTHING"
        sql = sql.replace("%", "%%").replace("?", "%s")
        if sql.lstrip().upper().startswith(("CREATE", "ALTER")):
            sql = re.sub(r"\bBLOB\b", "BYTEA", re.sub(r"\bJSON\b", "JSONB", sql))
        return sql

    def execute(self, sql: str, params=()):
        try:
            return self.conn.execute(self.translate(sql), params)
        except Exception:
            self.conn.rollback()  # a failed statement must not poison the shared connection
            raise

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()


class SQLiteDB:
    dialect = "sqlite"

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")

    def execute(self, sql: str, params=()):
        if sql.lstrip().upper().startswith(("CREATE", "ALTER")):
            sql = re.sub(r"\bJSON\b", "TEXT", sql)
        return self.conn.execute(sql, params)

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()


def connect(target) -> "PostgresDB | SQLiteDB":
    """A postgresql:// URL selects Postgres; a path selects SQLite."""
    if isinstance(target, str) and target.startswith(("postgresql://", "postgres://")):
        return PostgresDB(target)
    return SQLiteDB(Path(target))
