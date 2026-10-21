"""Explicit, backed-up review-data import. Old Postgres recovery is separate.

python -m app.migrate_supabase --source <sqlite file> [--apply]
Uses DATABASE_URL/DATABASE_SCHEMA. Defaults to a read-only inventory.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3

from .config import settings
from .db import connect

TABLES = {"actions","sessions","preparations","approvals","merchant_sessions","merchant_commands",
          "consent","outbox","episodes","profile_overrides","user_profile","profile_facts",
          "oauth_attempts","oauth_grants","recommendation_events","profile_interests","recommendation_runs"}


def identifier(value):
    if not re.fullmatch(r"[a-z_][a-z_0-9]*",value):
        raise ValueError("Unexpected source column")
    return '"' + value + '"'


def inventory(source):
    with sqlite3.connect(source.resolve().as_uri()+"?mode=ro",uri=True) as src:
        names = {r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        if names - TABLES:
            raise ValueError("Unmapped source tables; review before importing")
        return {name:src.execute("SELECT COUNT(*) FROM " + identifier(name)).fetchone()[0] for name in sorted(names)}


def import_snapshot(source, target_url, backup):
    """Snapshot WAL safely; verify inserts and fail on changed conflicts instead of hiding them."""
    inventory(source)
    backup.parent.mkdir(parents=True,exist_ok=True)
    if backup.exists():
        raise ValueError("Backup destination already exists")
    with sqlite3.connect(source.resolve().as_uri()+"?mode=ro",uri=True) as live:
        with sqlite3.connect(backup) as snapshot:
            live.backup(snapshot)
    counts = inventory(backup)
    target = connect(target_url)
    result = {}
    try:
        with sqlite3.connect(backup) as src:
            for table, count in counts.items():
                cols = [r[1] for r in src.execute("PRAGMA table_info(" + identifier(table) + ")")]
                quoted = ','.join(identifier(col) for col in cols)
                rows = src.execute("SELECT " + quoted + " FROM " + identifier(table)).fetchall()
                inserted = 0
                for row in rows:
                    cur = target.execute(f"INSERT OR IGNORE INTO {identifier(table)} ({quoted}) VALUES ({','.join('?' for _ in cols)})",row)
                    inserted += cur.rowcount
                    if not cur.rowcount:
                        # Existing primary keys may be kept only when the whole imported record matches.
                        matches = target.execute("SELECT " + quoted + " FROM " + identifier(table)).fetchall()
                        def normalized(values):
                            output=[]
                            for value in values:
                                if isinstance(value,memoryview): value=bytes(value)
                                if isinstance(value,str):
                                    try: value=json.loads(value)
                                    except (ValueError,TypeError): pass
                                output.append(value)
                            return output
                        if not any(normalized(existing)==normalized(row) for existing in matches):
                            raise ValueError("Conflicting record in " + table + "; destination kept unchanged")
                result[table] = {"source":count,"inserted":inserted,"already_identical":count-inserted}
        target.commit()
        return result
    except Exception:
        target.conn.rollback()
        raise
    finally:
        target.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--apply",action="store_true")
    args = parser.parse_args()
    if not args.source.is_file():
        raise SystemExit("Source file is missing")
    if not args.apply:
        print(json.dumps({"mode":"inventory_only","tables":inventory(args.source)}))
        return
    if not settings.database_url.startswith(("postgresql://","postgres://")):
        raise SystemExit("Set the target DATABASE_URL; apply the Supabase migrations first")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = settings.web_dir.parents[1] / "output" / "backups" / ("review-before-supabase-"+stamp+".sqlite3")
    result = import_snapshot(args.source,settings.database_url,backup)
    print(json.dumps({"backup":str(backup),"tables":result}))


if __name__ == "__main__":
    main()
