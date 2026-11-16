"""Lab database: raw messages (connector_records), memory (mem_*), plus the lab's own layers.

One annotation table with a `facet` column is the whole trick: every extraction (topic, project,
person, fact, open loop, tone) is a row pointing at evidence message ids, so any new question is a
GROUP BY or a vector lookup over the same rows - no re-reading the chat.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from app.connectors.store import ConnectorStore
from app.connectors.types import RawItem
from app.db import connect
from app.memory.store import MemoryStore

DDL = [
    """CREATE TABLE IF NOT EXISTS lab_windows (
        id TEXT PRIMARY KEY,
        owner TEXT NOT NULL,
        chat TEXT NOT NULL,
        first_idx INTEGER NOT NULL,
        last_idx INTEGER NOT NULL,
        t_start TEXT NOT NULL,
        t_end TEXT NOT NULL,
        n_msgs INTEGER NOT NULL,
        summary TEXT NOT NULL,
        tone TEXT NOT NULL,
        text_hash TEXT NOT NULL,
        prompt_version TEXT NOT NULL,
        model TEXT NOT NULL,
        as_of TEXT NOT NULL,
        UNIQUE (owner, chat, first_idx, last_idx, text_hash, prompt_version)
    )""",
    """CREATE TABLE IF NOT EXISTS lab_annotations (
        id TEXT PRIMARY KEY,
        owner TEXT NOT NULL,
        window_id TEXT NOT NULL,
        chat TEXT NOT NULL,
        facet TEXT NOT NULL,
        label TEXT NOT NULL,
        norm TEXT NOT NULL,
        detail TEXT,
        evidence TEXT NOT NULL,
        confidence REAL,
        provenance TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'hypothesis',
        valid_from TEXT NOT NULL,
        as_of TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS lab_vectors (
        id TEXT PRIMARY KEY,
        owner TEXT NOT NULL,
        ref_kind TEXT NOT NULL,
        ref_id TEXT NOT NULL,
        model TEXT NOT NULL,
        dim INTEGER NOT NULL,
        vec TEXT NOT NULL,
        UNIQUE (owner, ref_kind, ref_id, model)
    )""",
    """CREATE TABLE IF NOT EXISTS lab_rows (
        id TEXT PRIMARY KEY,
        owner TEXT NOT NULL,
        chat TEXT NOT NULL,
        first_idx INTEGER NOT NULL,
        last_idx INTEGER NOT NULL,
        n_msgs INTEGER NOT NULL,
        t_start TEXT NOT NULL,
        t_end TEXT NOT NULL,
        t_avg TEXT NOT NULL,
        topics TEXT NOT NULL,
        names TEXT NOT NULL,
        user_text TEXT NOT NULL,
        memory TEXT NOT NULL,
        memory_original TEXT,
        multimodal TEXT NOT NULL,
        emotions TEXT NOT NULL,
        sentiment REAL,
        salience TEXT NOT NULL,
        recurring TEXT,
        sensitive INTEGER NOT NULL DEFAULT 0,
        kind TEXT NOT NULL DEFAULT 'chat',
        extra TEXT,
        followup INTEGER NOT NULL DEFAULT 0,
        scores_other TEXT,
        scorers TEXT,
        text_hash TEXT NOT NULL,
        prompt_version TEXT NOT NULL,
        model TEXT NOT NULL,
        as_of TEXT NOT NULL,
        UNIQUE (owner, chat, first_idx, last_idx, text_hash, prompt_version)
    )""",
    """CREATE TABLE IF NOT EXISTS lab_followups (
        id TEXT PRIMARY KEY,
        owner TEXT NOT NULL,
        row_id TEXT NOT NULL,
        question TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open',
        attempts INTEGER NOT NULL DEFAULT 0,
        resolution TEXT,
        evidence_rows TEXT,
        updated_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS lab_alias_suggestions (
        id TEXT PRIMARY KEY,
        owner TEXT NOT NULL,
        person TEXT NOT NULL,
        alias TEXT NOT NULL,
        canonical TEXT NOT NULL,
        count INTEGER NOT NULL DEFAULT 1,
        status TEXT NOT NULL DEFAULT 'hypothesis',
        UNIQUE (owner, person, alias)
    )""",
    "CREATE INDEX IF NOT EXISTS lab_rows_owner ON lab_rows(owner, chat, t_avg)",
    "CREATE INDEX IF NOT EXISTS lab_ann_facet ON lab_annotations(owner, facet, norm)",
    "CREATE INDEX IF NOT EXISTS lab_ann_window ON lab_annotations(window_id)",
]


class Lab:
    """Everything a lab step needs, opened on <data>/lab.sqlite."""

    def __init__(self, data_dir: str | Path, owner: str):
        self.dir = Path(data_dir)
        self.owner = owner
        self.db = connect(self.dir / "lab.sqlite")
        for stmt in DDL:
            self.db.execute(stmt)
        for col, kind in (("kind", "TEXT NOT NULL DEFAULT 'chat'"), ("extra", "TEXT"), ("followup", "INTEGER NOT NULL DEFAULT 0"),
                          ("scores_other", "TEXT"), ("scorers", "TEXT")):
            try:  # older lab databases: add the columns the skills design needs
                self.db.execute(f"ALTER TABLE lab_rows ADD COLUMN {col} {kind}")
            except Exception:
                pass
        self.db.commit()
        self.records = ConnectorStore(self.db)
        self.memory = MemoryStore(self.db)

    # -- raw messages ---------------------------------------------------------------------
    def ingest_messages(self, connector_id: str, chat: str, messages, now: str) -> dict:
        items = [
            RawItem(
                source_id=f"{chat}:{m.idx}",
                source_timestamp=m.ts,
                text=m.text,
                kind=m.kind,
                title=m.sender,
                metadata={**m.meta, "chat": chat, "idx": m.idx, "sender": m.sender},
            )
            for m in messages
        ]
        return self.records.upsert_records(self.owner, connector_id, items, now=now, provenance="user_supplied")

    def load_messages(self, connector_id: str, chat: str):
        from .parse import Message

        rows = self.db.execute(
            "SELECT metadata, source_timestamp, title, text, kind FROM connector_records "
            "WHERE owner=? AND connector_id=? AND source_id LIKE ?",
            (self.owner, connector_id, f"{chat}:%"),
        ).fetchall()
        out = []
        for meta, ts, sender, text, kind in rows:
            data = json.loads(meta)
            extra = {k: v for k, v in data.items() if k not in ("chat", "idx", "sender")}
            out.append(Message(idx=int(data["idx"]), ts=ts, sender=sender, text=text, kind=kind, meta=extra))
        return sorted(out, key=lambda m: m.idx)

    def sources(self) -> list[tuple[str, str]]:
        """Every (connector_id, source name) with imported records."""
        rows = self.db.execute("SELECT DISTINCT connector_id, metadata FROM connector_records WHERE owner=?", (self.owner,)).fetchall()
        return sorted({(r[0], json.loads(r[1])["chat"]) for r in rows})

    def chats(self, connector_id: str) -> list[str]:
        rows = self.db.execute(
            "SELECT DISTINCT metadata FROM connector_records WHERE owner=? AND connector_id=?",
            (self.owner, connector_id),
        ).fetchall()
        return sorted({json.loads(r[0])["chat"] for r in rows})

    # -- annotations ----------------------------------------------------------------------
    def window_done(self, chat: str, first: int, last: int, text_hash: str, version: str) -> bool:
        return bool(
            self.db.execute(
                "SELECT 1 FROM lab_windows WHERE owner=? AND chat=? AND first_idx>=? AND last_idx<=? AND text_hash=? AND prompt_version=?",
                (self.owner, chat, first, last, text_hash, version),
            ).fetchone()
        )

    def add_window(self, **w) -> str:
        wid = w.get("wid") or str(uuid.uuid4())
        self.db.execute(
            "INSERT INTO lab_windows (id, owner, chat, first_idx, last_idx, t_start, t_end, n_msgs, summary, tone, "
            "text_hash, prompt_version, model, as_of) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (wid, self.owner, w["chat"], w["first_idx"], w["last_idx"], w["t_start"], w["t_end"], w["n_msgs"],
             w["summary"], w["tone"], w["text_hash"], w["prompt_version"], w["model"], w["as_of"]),
        )
        return wid

    def add_annotation(self, window_id: str, chat: str, facet: str, label: str, norm: str, evidence: list[int],
                       *, detail: str = "", confidence: float | None = None, provenance: str = "inferred",
                       valid_from: str, as_of: str) -> str:
        aid = str(uuid.uuid4())
        self.db.execute(
            "INSERT INTO lab_annotations (id, owner, window_id, chat, facet, label, norm, detail, evidence, confidence, "
            "provenance, status, valid_from, as_of) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (aid, self.owner, window_id, chat, facet, label, norm, detail, json.dumps(evidence), confidence, provenance,
             "hypothesis", valid_from, as_of),
        )
        return aid

    def annotations(self, facet: str | None = None) -> list[dict]:
        sql = ("SELECT id, window_id, chat, facet, label, norm, detail, evidence, confidence, provenance, status, valid_from "
               "FROM lab_annotations WHERE owner=?")
        params: list = [self.owner]
        if facet:
            sql += " AND facet=?"
            params.append(facet)
        cols = ["id", "window_id", "chat", "facet", "label", "norm", "detail", "evidence", "confidence", "provenance",
                "status", "valid_from"]
        out = []
        for r in self.db.execute(sql + " ORDER BY valid_from", params).fetchall():
            row = dict(zip(cols, r))
            row["evidence"] = json.loads(row["evidence"])
            out.append(row)
        return out

    def windows(self) -> list[dict]:
        cols = ["id", "chat", "first_idx", "last_idx", "t_start", "t_end", "n_msgs", "summary", "tone"]
        rows = self.db.execute(
            "SELECT id, chat, first_idx, last_idx, t_start, t_end, n_msgs, summary, tone FROM lab_windows "
            "WHERE owner=? ORDER BY t_start",
            (self.owner,),
        ).fetchall()
        return [dict(zip(cols, r)) for r in rows]

    # -- vectors --------------------------------------------------------------------------
    def put_vector(self, ref_kind: str, ref_id: str, model: str, vec: list[float]) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO lab_vectors (id, owner, ref_kind, ref_id, model, dim, vec) VALUES (?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), self.owner, ref_kind, ref_id, model, len(vec), json.dumps(vec)),
        )

    def vectors(self, ref_kind: str) -> dict[str, list[float]]:
        rows = self.db.execute(
            "SELECT ref_id, vec FROM lab_vectors WHERE owner=? AND ref_kind=?", (self.owner, ref_kind)
        ).fetchall()
        return {r[0]: json.loads(r[1]) for r in rows}

    def purge_annotations(self, ids: list[str]) -> int:
        """Remove annotations everywhere they were copied: vectors and the mem_* row made from a fact."""
        n = 0
        for aid in ids:
            row = self.db.execute("SELECT facet, label FROM lab_annotations WHERE owner=? AND id=?", (self.owner, aid)).fetchone()
            if not row:
                continue
            if row[0] == "fact":
                self.db.execute("DELETE FROM mem_patterns WHERE owner=? AND statement=?", (self.owner, row[1]))
                self.db.execute("DELETE FROM mem_events WHERE owner=? AND text=?", (self.owner, row[1]))
            self.db.execute("DELETE FROM lab_vectors WHERE owner=? AND ref_kind='annotation' AND ref_id=?", (self.owner, aid))
            self.db.execute("DELETE FROM lab_annotations WHERE owner=? AND id=?", (self.owner, aid))
            n += 1
        self.db.commit()
        return n

    def blank_summary(self, window_id: str) -> None:
        self.db.execute("UPDATE lab_windows SET summary=? WHERE owner=? AND id=?",
                        ("[summary withheld: sensitive content in this slice]", self.owner, window_id))
        self.db.execute("DELETE FROM lab_vectors WHERE owner=? AND ref_kind='window' AND ref_id=?", (self.owner, window_id))
        self.db.execute("UPDATE lab_rows SET memory='', user_text='', sensitive=1 WHERE owner=? AND id=?", (self.owner, window_id))
        self.db.commit()

    def blank_row_user_text(self, row_id: str) -> None:
        self.db.execute("UPDATE lab_rows SET user_text='', sensitive=1 WHERE owner=? AND id=?", (self.owner, row_id))
        self.db.commit()

    # -- rows (v2: one memory row per 5-10 messages) ---------------------------------------
    JSON_COLS = ("topics", "names", "multimodal", "emotions", "salience", "recurring", "extra", "scores_other", "scorers")

    def row_done(self, chat: str, first: int, last: int, text_hash: str, version: str) -> bool:
        return bool(self.db.execute(
            "SELECT 1 FROM lab_rows WHERE owner=? AND chat=? AND first_idx=? AND last_idx=? AND text_hash=? AND prompt_version=?",
            (self.owner, chat, first, last, text_hash, version)).fetchone())

    def add_row(self, **r) -> str:
        """Store a row and project it into lab_windows (same id) so index / tree / search work unchanged."""
        rid = str(uuid.uuid4())
        sentiment = r.get("sentiment")
        tone = "neutral" if sentiment is None else ("positive" if sentiment > 0.2 else "negative" if sentiment < -0.2 else "neutral")
        dump = lambda v: json.dumps(v, ensure_ascii=False)  # noqa: E731
        self.db.execute(
            "INSERT INTO lab_rows (id, owner, chat, first_idx, last_idx, n_msgs, t_start, t_end, t_avg, topics, names, "
            "user_text, memory, memory_original, multimodal, emotions, sentiment, salience, recurring, sensitive, "
            "kind, extra, followup, scores_other, scorers, text_hash, prompt_version, model, as_of) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (rid, self.owner, r["chat"], r["first_idx"], r["last_idx"], r["n_msgs"], r["t_start"], r["t_end"], r["t_avg"],
             dump(r["topics"]), dump(r["names"]), r["user_text"], r["memory"], None, dump(r["multimodal"]),
             dump(r["emotions"]), sentiment, dump(r["salience"]), None, int(r.get("sensitive", 0)),
             r.get("kind", "chat"), dump(r.get("extra") or {}), int(r.get("followup", 0)),
             dump(r["scores_other"]) if r.get("scores_other") else None, dump(r["scorers"]) if r.get("scorers") else None,
             r["text_hash"], r["prompt_version"], r["model"], r["as_of"]),
        )
        self.add_window(wid=rid, chat=r["chat"], first_idx=r["first_idx"], last_idx=r["last_idx"], t_start=r["t_start"],
                        t_end=r["t_end"], n_msgs=r["n_msgs"], summary=r["memory"] or "[summary withheld: sensitive content in this slice]",
                        tone=tone, text_hash=r["text_hash"], prompt_version=r["prompt_version"], model=r["model"], as_of=r["as_of"])
        return rid

    def sync_followup_flag(self, row_id: str) -> None:
        """rows.followup = 1 while the row still has an open question."""
        n = self.db.execute("SELECT COUNT(*) FROM lab_followups WHERE owner=? AND row_id=? AND status='open'",
                            (self.owner, row_id)).fetchone()[0]
        self.db.execute("UPDATE lab_rows SET followup=? WHERE owner=? AND id=?", (1 if n else 0, self.owner, row_id))

    def rows(self, chat: str | None = None) -> list[dict]:
        sql = "SELECT * FROM lab_rows WHERE owner=?"
        params: list = [self.owner]
        if chat:
            sql += " AND chat=?"
            params.append(chat)
        cur = self.db.execute(sql + " ORDER BY t_avg", params)
        names = [d[0] for d in cur.description]
        out = []
        for raw in cur.fetchall():
            row = dict(zip(names, raw))
            for col in self.JSON_COLS:
                row[col] = json.loads(row[col]) if row[col] else None
            out.append(row)
        return out

    def update_row_memory(self, row_id: str, memory: str, original: str) -> None:
        self.db.execute("UPDATE lab_rows SET memory=?, memory_original=COALESCE(memory_original, ?) WHERE owner=? AND id=?",
                        (memory, original, self.owner, row_id))
        self.db.execute("UPDATE lab_windows SET summary=? WHERE owner=? AND id=?", (memory, self.owner, row_id))
        self.db.execute("DELETE FROM lab_vectors WHERE owner=? AND ref_kind='window' AND ref_id=?", (self.owner, row_id))
        self.db.commit()

    def set_recurring(self, row_id: str, recurring: dict) -> None:
        self.db.execute("UPDATE lab_rows SET recurring=? WHERE owner=? AND id=?",
                        (json.dumps(recurring, ensure_ascii=False), self.owner, row_id))

    def add_followup(self, row_id: str, question: str, now: str) -> str:
        fid = str(uuid.uuid4())
        self.db.execute("INSERT INTO lab_followups (id, owner, row_id, question, updated_at) VALUES (?,?,?,?,?)",
                        (fid, self.owner, row_id, question, now))
        return fid

    def followups(self, status: str | None = None) -> list[dict]:
        sql = "SELECT id, row_id, question, status, attempts, resolution, evidence_rows FROM lab_followups WHERE owner=?"
        params: list = [self.owner]
        if status:
            sql += " AND status=?"
            params.append(status)
        cols = ["id", "row_id", "question", "status", "attempts", "resolution", "evidence_rows"]
        out = []
        for r in self.db.execute(sql, params).fetchall():
            row = dict(zip(cols, r))
            row["evidence_rows"] = json.loads(row["evidence_rows"]) if row["evidence_rows"] else []
            out.append(row)
        return out

    def set_followup(self, fid: str, *, status: str, resolution: str | None, evidence_rows: list[str], now: str) -> None:
        self.db.execute(
            "UPDATE lab_followups SET status=?, attempts=attempts+1, resolution=?, evidence_rows=?, updated_at=? WHERE owner=? AND id=?",
            (status, resolution, json.dumps(evidence_rows), now, self.owner, fid))
        self.db.commit()

    def add_alias_suggestion(self, person: str, alias: str, canonical: str) -> None:
        self.db.execute(
            "INSERT INTO lab_alias_suggestions (id, owner, person, alias, canonical) VALUES (?,?,?,?,?) "
            "ON CONFLICT(owner, person, alias) DO UPDATE SET count=count+1",
            (str(uuid.uuid4()), self.owner, person, alias, canonical))

    def alias_suggestions(self) -> list[dict]:
        cur = self.db.execute("SELECT person, alias, canonical, count, status FROM lab_alias_suggestions WHERE owner=? "
                              "ORDER BY count DESC", (self.owner,))
        return [dict(zip(["person", "alias", "canonical", "count", "status"], r)) for r in cur.fetchall()]

    # -- forget ---------------------------------------------------------------------------
    def forget_chat(self, chat: str) -> dict:
        """'Forget everything from this chat': raw rows, windows, annotations and their vectors."""
        wins = [r[0] for r in self.db.execute("SELECT id FROM lab_windows WHERE owner=? AND chat=?", (self.owner, chat))]
        anns = [r[0] for r in self.db.execute("SELECT id FROM lab_annotations WHERE owner=? AND chat=?", (self.owner, chat))]
        for ref_kind, ids in (("window", wins), ("annotation", anns)):
            for i in ids:
                self.db.execute("DELETE FROM lab_vectors WHERE owner=? AND ref_kind=? AND ref_id=?", (self.owner, ref_kind, i))
        self.db.execute("DELETE FROM lab_followups WHERE owner=? AND row_id IN (SELECT id FROM lab_rows WHERE owner=? AND chat=?)",
                        (self.owner, self.owner, chat))
        self.db.execute("DELETE FROM lab_rows WHERE owner=? AND chat=?", (self.owner, chat))
        self.db.execute("DELETE FROM lab_alias_suggestions WHERE owner=? AND person=?", (self.owner, chat))
        self.db.execute("DELETE FROM lab_annotations WHERE owner=? AND chat=?", (self.owner, chat))
        self.db.execute("DELETE FROM lab_windows WHERE owner=? AND chat=?", (self.owner, chat))
        self.db.execute("DELETE FROM mem_patterns WHERE owner=? AND evidence_json LIKE ?", (self.owner, f'%"chat": "{chat}"%'))
        self.db.execute("DELETE FROM mem_events WHERE owner=? AND source=?", (self.owner, f"chat:{chat}"))
        self.db.execute("DELETE FROM connector_records WHERE owner=? AND source_id LIKE ?", (self.owner, f"{chat}:%"))
        self.db.commit()
        return {"windows": len(wins), "annotations": len(anns)}
