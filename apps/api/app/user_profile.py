"""User profile: one growing document per user, backed by bi-temporal facts.

Industry pattern (LangGraph Store / LangMem, Mem0, Zep-Graphiti): a profile document for
fast reads, plus facts with provenance and validity windows as the source of truth.

  user_profile   one row per user: typed core fields + `attributes` JSON that grows with
                 the app (maps 1:1 to Postgres JSONB later). A projection; never edited by hand.
  profile_facts  append-only facts. A newer statement closes the old row (valid_to) instead of
                 overwriting it. Facets: identity · context · situation · preference · like · dislike · routine.

Rule 9: facts here are `user_supplied` (told, or a hypothesis the user confirmed). Unconfirmed
inferences stay in profile.py episodes and are never written here. Forget deletes the key's history.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

FACETS = {"identity", "context", "situation", "preference", "like", "dislike", "routine"}
# Luna's stated-fact keys -> facet; anything new defaults to context.
KEY_FACET = {"area": "context", "hotel": "situation", "terminal": "situation", "taxi_plate": "situation", "taxi_roof": "situation",
             "deadline": "situation", "pet": "identity", "language": "identity", "other": "context"}
CORE = {"area": "home_area", "language": "language"}  # typed columns kept in sync from current facts


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ProfileStore:
    """SQLite implementation; keeps the old FactStore interface (add / current / forget) for Luna."""

    def __init__(self, store_provider, legacy_json: Path | None = None):
        """store_provider returns the ActionStore, so profile writes share its connection and lock."""
        self._store, self.legacy, self._ready = store_provider, legacy_json, None

    @property
    def lock(self):
        return self._store().lock

    @property
    def db(self):
        db = self._store().db
        if self._ready is not db:
            db.execute("""CREATE TABLE IF NOT EXISTS user_profile (owner TEXT PRIMARY KEY, display_name TEXT, home_area TEXT, language TEXT,
                mode TEXT, attributes JSON NOT NULL DEFAULT '{}', version INTEGER NOT NULL DEFAULT 0, created_at TEXT, updated_at TEXT)""")
            db.execute("""CREATE TABLE IF NOT EXISTS profile_facts (id TEXT PRIMARY KEY, owner TEXT NOT NULL, facet TEXT NOT NULL, key TEXT NOT NULL,
                value JSON NOT NULL, provenance TEXT NOT NULL, status TEXT NOT NULL, confidence REAL, source TEXT, evidence JSON,
                valid_from TEXT NOT NULL, valid_to TEXT, recorded_at TEXT NOT NULL, superseded_by TEXT)""")
            db.execute("CREATE INDEX IF NOT EXISTS profile_facts_current ON profile_facts(owner, key, valid_to)")
            if db.dialect == "postgres":  # semantic recall later: one embedding per fact (pgvector)
                db.execute("ALTER TABLE profile_facts ADD COLUMN IF NOT EXISTS embedding vector(1536)")
                db.execute("CREATE INDEX IF NOT EXISTS profile_facts_attributes ON user_profile USING gin (attributes)")
            db.commit()
            self._ready = db
            self._import_legacy(db)
        return db

    def _import_legacy(self, db):
        """One-time import of the old memory.json told facts (history kept)."""
        if not self.legacy or not self.legacy.exists():
            return
        data = json.loads(self.legacy.read_text("utf-8"))
        for owner, facts in data.items():
            for f in facts:
                db.execute("INSERT INTO profile_facts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)",
                           (uuid4().hex, owner, KEY_FACET.get(f["key"], "context"), f["key"], json.dumps(f["value"]), "user_supplied",
                            "told", 1.0, f.get("source", "")[:140], "[]", f["as_of"], f.get("valid_to"), f["as_of"]))
            self._project(db, owner)
        db.commit()
        self.legacy.rename(self.legacy.with_suffix(".json.migrated"))

    # ------------------------------------------------------------ writes
    def add(self, owner: str, key: str, value: str, source: str, facet: str | None = None, status: str = "told", evidence=None, *, commit: bool = True) -> dict:
        """Save a stated fact; initialized callers can share a transaction with commit=False."""
        facet = facet or KEY_FACET.get(key, "context")
        if facet not in FACETS:
            raise ValueError("Unknown facet")
        at = now()
        with self.lock:
            db = self.db
            current = db.execute("SELECT id, value FROM profile_facts WHERE owner=? AND key=? AND valid_to IS NULL", (owner, key)).fetchall()
            if any(json.loads(v) == value for _, v in current):
                return self._as_fact(db.execute("SELECT * FROM profile_facts WHERE owner=? AND key=? AND valid_to IS NULL", (owner, key)).fetchone())
            new_id = uuid4().hex
            for old_id, _ in current:  # supersede, keep history
                db.execute("UPDATE profile_facts SET valid_to=?, superseded_by=? WHERE id=?", (at, new_id, old_id))
            db.execute("INSERT INTO profile_facts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)",
                       (new_id, owner, facet, key, json.dumps(value), "user_supplied", status, 1.0, source[:140], json.dumps(evidence or []), at, None, at))
            self._project(db, owner)
            if commit:
                db.commit()
            return self._as_fact(db.execute("SELECT * FROM profile_facts WHERE id=?", (new_id,)).fetchone())

    def forget(self, owner: str, key: str, *, commit: bool = True) -> int:
        """Remove a key's history, optionally inside the caller's transaction."""
        with self.lock:
            db = self.db
            n = db.execute("DELETE FROM profile_facts WHERE owner=? AND key=?", (owner, key)).rowcount
            self._project(db, owner)
            if commit:
                db.commit()
            return n

    def _project(self, db, owner):
        """Rebuild the profile document from current facts (deterministic, idempotent)."""
        rows = db.execute("SELECT facet, key, value FROM profile_facts WHERE owner=? AND valid_to IS NULL ORDER BY recorded_at", (owner,)).fetchall()
        attributes: dict = {}
        for facet, key, value in rows:
            attributes.setdefault(facet, {})[key] = json.loads(value)
        flat = {key: json.loads(value) for _, key, value in rows}
        at = now()
        db.execute("""INSERT INTO user_profile (owner, home_area, language, attributes, version, created_at, updated_at) VALUES (?,?,?,?,1,?,?)
            ON CONFLICT(owner) DO UPDATE SET home_area=excluded.home_area, language=excluded.language, attributes=excluded.attributes,
            version=user_profile.version+1, updated_at=excluded.updated_at""",
                   (owner, flat.get("area"), flat.get("language"), json.dumps(attributes, ensure_ascii=False), at, at))

    # ------------------------------------------------------------ reads
    @staticmethod
    def _as_fact(row):
        return {"key": row[3], "value": json.loads(row[4]), "facet": row[2], "provenance": row[5], "status": row[6],
                "as_of": row[10], "source": row[8] or "", **({"valid_to": row[11]} if row[11] else {})}

    def current(self, owner: str) -> list[dict]:
        with self.lock:
            return [self._as_fact(r) for r in self.db.execute("SELECT * FROM profile_facts WHERE owner=? AND valid_to IS NULL ORDER BY recorded_at", (owner,))]

    def history(self, owner: str, key: str | None = None) -> list[dict]:
        with self.lock:
            q, args = ("SELECT * FROM profile_facts WHERE owner=? AND key=? ORDER BY valid_to IS NULL, recorded_at", (owner, key)) if key else ("SELECT * FROM profile_facts WHERE owner=? ORDER BY valid_to IS NULL, recorded_at", (owner,))
            return [self._as_fact(r) for r in self.db.execute(q, args)]

    def document(self, owner: str) -> dict:
        with self.lock:
            row = self.db.execute("SELECT owner, display_name, home_area, language, mode, attributes, version, created_at, updated_at FROM user_profile WHERE owner=?", (owner,)).fetchone()
        if not row:
            return {"core": {}, "attributes": {}, "version": 0}
        return {"core": {"display_name": row[1], "home_area": row[2], "language": row[3], "mode": row[4]},
                "attributes": json.loads(row[5]), "version": row[6], "created_at": row[7], "updated_at": row[8]}

    def digest(self, owner: str) -> str:
        """Compact text for the model prompt: current told/confirmed facts only."""
        return "; ".join(f"{f['facet']}.{f['key']}={f['value']}" for f in self.current(owner))
