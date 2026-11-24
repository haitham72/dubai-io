"""Drop leaked T-1 schemas (t2b_tn_* and smoke_*) after verifying they belong to T-1."""
from __future__ import annotations

import json
import re
import sys

import psycopg

DSN = "postgresql://tm:tm@localhost:5442/tm"
T1_SCHEMA_RE = re.compile(r"^(?:t2b_tn_|smoke_)[0-9a-f]+$")
T1_DEMO_OWNERS = {"karim_smoke", "karim_t2b"}


def cleanup_t1_schemas(dsn: str = DSN) -> dict:
    dropped: list[str] = []
    skipped: list[dict] = []
    with psycopg.connect(dsn, autocommit=True) as conn:
        rows = conn.execute(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name NOT LIKE 'pg_%' AND schema_name != 'information_schema' "
            "ORDER BY schema_name"
        ).fetchall()
        candidates = [r[0] for r in rows if T1_SCHEMA_RE.match(r[0])]
        for sc in candidates:
            has_owners = bool(
                conn.execute(
                    "SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = 'owners'",
                    (sc,),
                ).fetchone()
            )
            if not has_owners:
                skipped.append({"schema": sc, "reason": "no owners table"})
                continue
            owners = conn.execute(f'SELECT id, kind FROM "{sc}".owners').fetchall()
            # T-1 smoke_2ab0c116 crashed/left 0 owners, smoke_9895751a had karim_smoke (demo), t2b_tn_baaedc05 had karim_t2b (demo)
            ok_t1 = len(owners) == 0 or all((oid in T1_DEMO_OWNERS and kind == "demo") for oid, kind in owners)
            if not ok_t1:
                skipped.append({"schema": sc, "reason": f"unexpected owners={owners}"})
                continue
            conn.execute(f'DROP SCHEMA IF EXISTS "{sc}" CASCADE')
            gone = conn.execute("SELECT to_regnamespace(%s)", (sc,)).fetchone()[0] is None
            if not gone:
                raise RuntimeError(f"Failed to drop T-1 schema {sc}")
            dropped.append(sc)
    return {"dropped": dropped, "skipped": skipped}


if __name__ == "__main__":
    res = cleanup_t1_schemas()
    print(json.dumps(res, indent=2))
    sys.exit(0)
