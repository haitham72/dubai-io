"""One-off: copy the local SQLite store (data/actions.sqlite3) into Postgres (DATABASE_URL).

Run from apps/api:  .venv\\Scripts\\python -m app.migrate_sqlite
Creates the Postgres tables through the normal stores, then copies rows; existing rows win
(ON CONFLICT DO NOTHING), so running it twice is harmless. SQLite is left untouched.
"""
import sqlite3

from .actions import ActionStore
from .config import settings
from . import proactive, profile
from .user_profile import ProfileStore


def main():
    source = settings.data_dir / "actions.sqlite3"
    if not settings.database_url or not source.exists():
        raise SystemExit("Need DATABASE_URL and data/actions.sqlite3")
    target = ActionStore(settings.database_url)
    proactive.setup(target)
    profile.setup(target)
    ProfileStore(lambda: target).db  # creates user_profile / profile_facts
    src = sqlite3.connect(source)
    tables = [r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    for table in tables:
        cols = [r[1] for r in src.execute(f"PRAGMA table_info({table})")]
        rows = src.execute(f"SELECT {', '.join(cols)} FROM {table}").fetchall()
        try:
            for row in rows:
                target.db.execute(f"INSERT OR IGNORE INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", row)
            target.db.commit()
            print(f"{table}: {len(rows)} rows")
        except Exception as err:  # e.g. a table only the OAuth connector creates lazily
            print(f"{table}: skipped ({type(err).__name__})")
    src.close()


if __name__ == "__main__":
    main()
