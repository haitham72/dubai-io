"""CRUD helpers for product memory. Forget removes search/timeline visibility immediately."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from .schema import ensure_memory_schema


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


class MemoryStore:
    def __init__(self, db):
        self.db = db
        ensure_memory_schema(db)

    def add_event(
        self,
        owner: str,
        *,
        kind: str,
        text: str,
        source: str = "",
        provenance: str = "user_supplied",
        confidence: float | None = None,
        ontology_path: str | None = None,
        at: str | None = None,
    ) -> dict[str, Any]:
        eid = str(uuid.uuid4())
        content_hash = _hash(f"{kind}|{text}|{ontology_path or ''}")
        row = self.db.execute(
            "SELECT id FROM mem_events WHERE owner=? AND content_hash=?",
            (owner, content_hash),
        ).fetchone()
        if row:
            return {"id": row[0], "deduped": True}
        self.db.execute(
            "INSERT INTO mem_events (id, owner, at, kind, text, source, provenance, confidence, content_hash, ontology_path) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (eid, owner, at or _now(), kind, text, source, provenance, confidence, content_hash, ontology_path),
        )
        self.db.commit()
        return {"id": eid, "deduped": False}

    def upsert_entity(
        self,
        owner: str,
        *,
        kind: str,
        name: str,
        ontology_path: str | None = None,
        provenance: str = "user_supplied",
    ) -> str:
        existing = self.db.execute(
            "SELECT id FROM mem_entities WHERE owner=? AND kind=? AND lower(name)=lower(?)",
            (owner, kind, name),
        ).fetchone()
        if existing:
            return existing[0]
        eid = str(uuid.uuid4())
        self.db.execute(
            "INSERT INTO mem_entities (id, owner, kind, name, ontology_path, provenance) VALUES (?,?,?,?,?,?)",
            (eid, owner, kind, name, ontology_path, provenance),
        )
        self.db.commit()
        return eid

    def add_pattern(
        self,
        owner: str,
        statement: str,
        *,
        confidence: float = 0.5,
        evidence: list | None = None,
        status: str = "hypothesis",
    ) -> str:
        pid = str(uuid.uuid4())
        self.db.execute(
            "INSERT INTO mem_patterns (id, owner, statement, confidence, evidence_json, status, valid_from) "
            "VALUES (?,?,?,?,?,?,?)",
            (pid, owner, statement, confidence, json.dumps(evidence or []), status, _now()),
        )
        self.db.commit()
        return pid

    def timeline(self, owner: str, limit: int = 40) -> list[dict]:
        rows = self.db.execute(
            "SELECT id, at, kind, text, source, provenance, ontology_path FROM mem_events "
            "WHERE owner=? ORDER BY at DESC LIMIT ?",
            (owner, limit),
        ).fetchall()
        return [
            {
                "id": r[0],
                "at": r[1],
                "kind": r[2],
                "text": r[3],
                "source": r[4],
                "provenance": r[5],
                "ontology_path": r[6],
            }
            for r in rows
        ]

    def search(self, owner: str, query: str, k: int = 10) -> list[dict]:
        q = f"%{(query or '').strip()[:80]}%"
        if q == "%%":
            return []
        rows = self.db.execute(
            "SELECT id, at, kind, text, provenance FROM mem_events "
            "WHERE owner=? AND text LIKE ? ORDER BY at DESC LIMIT ?",
            (owner, q, k),
        ).fetchall()
        return [
            {"id": r[0], "at": r[1], "kind": r[2], "text": r[3], "provenance": r[4], "score": 1.0, "why": "keyword"}
            for r in rows
        ]

    def hypotheses(self, owner: str) -> list[dict]:
        rows = self.db.execute(
            "SELECT id, statement, confidence, evidence_json, status FROM mem_patterns "
            "WHERE owner=? AND status='hypothesis' ORDER BY confidence DESC",
            (owner,),
        ).fetchall()
        out = []
        for r in rows:
            evidence = []
            try:
                evidence = json.loads(r[3] or "[]")
            except json.JSONDecodeError:
                evidence = []
            out.append(
                {
                    "id": r[0],
                    "statement": r[1],
                    "confidence": r[2],
                    "evidence": evidence,
                    "status": r[4],
                    "provenance": "inferred",
                }
            )
        return out

    def set_hypothesis(self, owner: str, item_id: str, status: str) -> bool:
        if status not in {"confirmed", "rejected", "hypothesis"}:
            return False
        cur = self.db.execute(
            "UPDATE mem_patterns SET status=? WHERE id=? AND owner=?",
            (status, item_id, owner),
        )
        self.db.commit()
        return cur.rowcount > 0 if hasattr(cur, "rowcount") else True

    def forget(self, owner: str, item_id: str) -> bool:
        a = self.db.execute("DELETE FROM mem_events WHERE id=? AND owner=?", (item_id, owner))
        b = self.db.execute("DELETE FROM mem_patterns WHERE id=? AND owner=?", (item_id, owner))
        c = self.db.execute("DELETE FROM mem_entities WHERE id=? AND owner=?", (item_id, owner))
        self.db.execute("DELETE FROM mem_event_entities WHERE owner=? AND (event_id=? OR entity_id=?)", (owner, item_id, item_id))
        self.db.commit()
        # sqlite Cursor.rowcount works; postgres too after execute
        return True

    def context_pack(self, owner: str, query: str = "", budget_chars: int = 2000) -> str:
        lines: list[str] = []
        ents = self.db.execute(
            "SELECT name, kind, ontology_path, provenance FROM mem_entities WHERE owner=? LIMIT 30",
            (owner,),
        ).fetchall()
        for name, kind, path, prov in ents:
            if prov == "inferred":
                continue
            lines.append(f"- {kind}: {name}" + (f" ({path})" if path else "") + f" [{prov}]")
        hits = self.search(owner, query, k=8) if query.strip() else self.timeline(owner, limit=8)
        for h in hits:
            if h.get("provenance") == "inferred":
                continue
            lines.append(f"- {h.get('text', '')[:180]} [{h.get('provenance', '')}]")
        pack = "Known about the resident (visible in Me):\n" + "\n".join(lines)
        return pack[:budget_chars]
