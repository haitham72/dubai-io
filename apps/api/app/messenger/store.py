"""SQLite mg_* chat store. Local until D12 applies the Supabase script."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ChatError(Exception):
    def __init__(self, code: str, status: int):
        super().__init__(code)
        self.code = code
        self.status = status


class ChatStore:
    def __init__(self, path):
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.lock = RLock()
        with self.lock:
            self.db.executescript(
                """
                CREATE TABLE IF NOT EXISTS mg_conversations (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS mg_memberships (
                    conversation_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    ai_mode TEXT NOT NULL DEFAULT 'off',
                    PRIMARY KEY (conversation_id, user_id)
                );
                CREATE TABLE IF NOT EXISTS mg_messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    sender_id TEXT NOT NULL,
                    client_msg_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    body TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    edited_at TEXT,
                    deleted_at TEXT,
                    UNIQUE (conversation_id, sender_id, client_msg_id)
                );
                CREATE TABLE IF NOT EXISTS mg_receipts (
                    message_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    at TEXT NOT NULL,
                    PRIMARY KEY (message_id, user_id, kind)
                );
                CREATE TABLE IF NOT EXISTS mg_user_link (
                    user_id TEXT PRIMARY KEY
                );
                CREATE TABLE IF NOT EXISTS mg_voice_drafts (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    body TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS mg_decisions (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    text TEXT NOT NULL,
                    evidence_ids TEXT NOT NULL
                );
                """
            )
            self.db.commit()

    def close(self) -> None:
        self.db.close()

    def link_user(self, user_id: str) -> None:
        with self.lock:
            self.db.execute("INSERT OR IGNORE INTO mg_user_link (user_id) VALUES (?)", (user_id,))
            self.db.commit()

    def create_conversation(self, owner: str, member_ids: list[str], *, kind: str, title: str = "") -> str:
        if kind not in ("direct", "group"):
            raise ChatError("bad_kind", 422)
        members = list(dict.fromkeys([owner, *member_ids]))
        if kind == "direct" and len(members) != 2:
            raise ChatError("direct_needs_two", 422)
        if len(members) < 2:
            raise ChatError("needs_members", 422)
        conv_id = uuid4().hex
        with self.lock:
            self.db.execute(
                "INSERT INTO mg_conversations (id, kind, title, created_at) VALUES (?,?,?,?)",
                (conv_id, kind, title, _now()),
            )
            self.db.executemany(
                "INSERT INTO mg_memberships (conversation_id, user_id) VALUES (?,?)",
                [(conv_id, user) for user in members],
            )
            self.db.commit()
        return conv_id

    def is_member(self, conversation_id: str, user_id: str) -> bool:
        with self.lock:
            row = self.db.execute(
                "SELECT 1 FROM mg_memberships WHERE conversation_id=? AND user_id=?",
                (conversation_id, user_id),
            ).fetchone()
        return row is not None

    def require_member(self, conversation_id: str, user_id: str) -> None:
        with self.lock:
            conv = self.db.execute("SELECT id FROM mg_conversations WHERE id=?", (conversation_id,)).fetchone()
        if conv is None or not self.is_member(conversation_id, user_id):
            raise ChatError("not_found", 404)

    def members_of(self, conversation_id: str) -> list[str]:
        """Return member user_ids for a conversation in membership order."""
        with self.lock:
            rows = self.db.execute(
                "SELECT user_id FROM mg_memberships WHERE conversation_id=? ORDER BY rowid",
                (conversation_id,),
            ).fetchall()
        return [row["user_id"] for row in rows]

    def list_conversations(self, user_id: str) -> list[dict]:
        """Return conversations where user_id is a member, ordered by latest activity descending."""
        with self.lock:
            conv_rows = self.db.execute(
                """
                SELECT c.id, c.kind, c.title, c.created_at
                FROM mg_conversations c
                INNER JOIN mg_memberships mem
                    ON mem.conversation_id = c.id AND mem.user_id = ?
                LEFT JOIN (
                    SELECT conversation_id, MAX(created_at) AS last_msg_created_at
                    FROM mg_messages
                    GROUP BY conversation_id
                ) act ON act.conversation_id = c.id
                ORDER BY COALESCE(act.last_msg_created_at, c.created_at) DESC, c.rowid DESC
                """,
                (user_id,),
            ).fetchall()
            if not conv_rows:
                return []

            member_rows = self.db.execute(
                """
                SELECT m.conversation_id, m.user_id
                FROM mg_memberships m
                INNER JOIN mg_memberships me
                    ON me.conversation_id = m.conversation_id AND me.user_id = ?
                ORDER BY m.rowid
                """,
                (user_id,),
            ).fetchall()
            members_map: dict[str, list[str]] = {row["id"]: [] for row in conv_rows}
            for mrow in member_rows:
                cid = mrow["conversation_id"]
                if cid in members_map:
                    members_map[cid].append(mrow["user_id"])

            last_msg_rows = self.db.execute(
                """
                SELECT msg.*
                FROM mg_messages msg
                INNER JOIN (
                    SELECT m.conversation_id, MAX(m.seq) AS max_seq
                    FROM mg_messages m
                    INNER JOIN mg_memberships me
                        ON me.conversation_id = m.conversation_id AND me.user_id = ?
                    GROUP BY m.conversation_id
                ) latest
                    ON latest.conversation_id = msg.conversation_id AND latest.max_seq = msg.seq
                """,
                (user_id,),
            ).fetchall()
            last_msg_map = {mrow["conversation_id"]: self._message(mrow) for mrow in last_msg_rows}

        conversations: list[dict] = []
        for row in conv_rows:
            cid = row["id"]
            last_msg = last_msg_map.get(cid)
            conversations.append(
                {
                    "id": cid,
                    "kind": row["kind"],
                    "title": row["title"],
                    "member_ids": members_map.get(cid, []),
                    "created_at": row["created_at"],
                    "last_seq": last_msg["seq"] if last_msg is not None else 0,
                    "last_message": last_msg,
                }
            )
        return conversations

    def ai_modes(self, conversation_id: str) -> dict[str, str]:
        with self.lock:
            rows = self.db.execute(
                "SELECT user_id, ai_mode FROM mg_memberships WHERE conversation_id=?",
                (conversation_id,),
            ).fetchall()
        return {row["user_id"]: row["ai_mode"] for row in rows}

    def set_ai_mode(self, conversation_id: str, user_id: str, mode: str) -> None:
        if mode not in ("off", "session", "save"):
            raise ChatError("bad_mode", 422)
        self.require_member(conversation_id, user_id)
        with self.lock:
            self.db.execute(
                "UPDATE mg_memberships SET ai_mode=? WHERE conversation_id=? AND user_id=?",
                (mode, conversation_id, user_id),
            )
            self.db.commit()

    def send(self, conversation_id: str, sender_id: str, client_msg_id: str, body: str) -> dict:
        self.require_member(conversation_id, sender_id)
        text = (body or "").strip()
        if not text or len(text) > 4000:
            raise ChatError("bad_body", 422)
        if not client_msg_id or len(client_msg_id) > 80:
            raise ChatError("bad_client_msg_id", 422)
        with self.lock:
            existing = self.db.execute(
                """SELECT * FROM mg_messages
                   WHERE conversation_id=? AND sender_id=? AND client_msg_id=?""",
                (conversation_id, sender_id, client_msg_id),
            ).fetchone()
            if existing:
                return self._message(existing)
            seq = self.db.execute(
                "SELECT COALESCE(MAX(seq), 0) + 1 FROM mg_messages WHERE conversation_id=?",
                (conversation_id,),
            ).fetchone()[0]
            message_id = uuid4().hex
            created = _now()
            self.db.execute(
                """INSERT INTO mg_messages
                   (id, conversation_id, sender_id, client_msg_id, seq, body, created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (message_id, conversation_id, sender_id, client_msg_id, seq, text, created),
            )
            self.db.commit()
            row = self.db.execute("SELECT * FROM mg_messages WHERE id=?", (message_id,)).fetchone()
        return self._message(row)

    def get_message(self, conversation_id: str, user_id: str, message_id: str) -> dict | None:
        self.require_member(conversation_id, user_id)
        with self.lock:
            row = self.db.execute(
                "SELECT * FROM mg_messages WHERE id=? AND conversation_id=?", (message_id, conversation_id)
            ).fetchone()
        return self._message(row) if row else None

    def since(self, conversation_id: str, user_id: str, last_seq: int) -> list[dict]:
        self.require_member(conversation_id, user_id)
        with self.lock:
            rows = self.db.execute(
                """SELECT * FROM mg_messages
                   WHERE conversation_id=? AND seq>? ORDER BY seq""",
                (conversation_id, last_seq),
            ).fetchall()
        return [self._message(row) for row in rows]

    def edit(self, conversation_id: str, user_id: str, message_id: str, body: str) -> dict:
        self.require_member(conversation_id, user_id)
        text = (body or "").strip()
        if not text:
            raise ChatError("bad_body", 422)
        with self.lock:
            row = self.db.execute("SELECT * FROM mg_messages WHERE id=? AND conversation_id=?", (message_id, conversation_id)).fetchone()
            if row is None or row["sender_id"] != user_id or row["deleted_at"]:
                raise ChatError("not_found", 404)
            self.db.execute("UPDATE mg_messages SET body=?, edited_at=? WHERE id=?", (text, _now(), message_id))
            self.db.commit()
            row = self.db.execute("SELECT * FROM mg_messages WHERE id=?", (message_id,)).fetchone()
        return self._message(row)

    def delete(self, conversation_id: str, user_id: str, message_id: str) -> dict:
        self.require_member(conversation_id, user_id)
        with self.lock:
            row = self.db.execute("SELECT * FROM mg_messages WHERE id=? AND conversation_id=?", (message_id, conversation_id)).fetchone()
            if row is None or row["sender_id"] != user_id:
                raise ChatError("not_found", 404)
            self.db.execute(
                "UPDATE mg_messages SET body='', deleted_at=? WHERE id=?",
                (row["deleted_at"] or _now(), message_id),
            )
            self.db.commit()
            row = self.db.execute("SELECT * FROM mg_messages WHERE id=?", (message_id,)).fetchone()
        return self._message(row)

    def receipt(self, conversation_id: str, user_id: str, message_id: str, kind: str) -> None:
        if kind not in ("delivered", "read"):
            raise ChatError("bad_receipt", 422)
        self.require_member(conversation_id, user_id)
        with self.lock:
            row = self.db.execute(
                "SELECT id FROM mg_messages WHERE id=? AND conversation_id=?",
                (message_id, conversation_id),
            ).fetchone()
            if row is None:
                raise ChatError("not_found", 404)
            self.db.execute(
                "INSERT OR IGNORE INTO mg_receipts (message_id, user_id, kind, at) VALUES (?,?,?,?)",
                (message_id, user_id, kind, _now()),
            )
            self.db.commit()

    def receipts_for(self, message_id: str) -> list[dict]:
        with self.lock:
            rows = self.db.execute(
                "SELECT user_id, kind, at FROM mg_receipts WHERE message_id=?",
                (message_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def count_messages(self, conversation_id: str) -> int:
        with self.lock:
            return self.db.execute(
                "SELECT COUNT(*) FROM mg_messages WHERE conversation_id=?",
                (conversation_id,),
            ).fetchone()[0]

    def stage_voice(self, conversation_id: str, user_id: str, body: str) -> str:
        self.require_member(conversation_id, user_id)
        draft_id = uuid4().hex
        with self.lock:
            self.db.execute(
                "INSERT INTO mg_voice_drafts (id, conversation_id, user_id, body, created_at) VALUES (?,?,?,?,?)",
                (draft_id, conversation_id, user_id, body.strip(), _now()),
            )
            self.db.commit()
        return draft_id

    def confirm_voice(self, conversation_id: str, user_id: str, draft_id: str, *, confirmed: bool, client_msg_id: str) -> dict | None:
        with self.lock:
            row = self.db.execute(
                "SELECT * FROM mg_voice_drafts WHERE id=? AND conversation_id=? AND user_id=?",
                (draft_id, conversation_id, user_id),
            ).fetchone()
        if row is None:
            raise ChatError("not_found", 404)
        if not confirmed:
            return None
        return self.send(conversation_id, user_id, client_msg_id, row["body"])

    def save_decision(self, conversation_id: str, user_id: str, text: str, evidence_ids: list[str], *, recorded: bool) -> dict:
        self.require_member(conversation_id, user_id)
        decision_id = uuid4().hex
        status = "recorded" if recorded else "candidate"
        with self.lock:
            self.db.execute(
                "INSERT INTO mg_decisions (id, conversation_id, status, text, evidence_ids) VALUES (?,?,?,?,?)",
                (decision_id, conversation_id, status, text, ",".join(evidence_ids)),
            )
            self.db.commit()
        return {"id": decision_id, "status": status, "text": text, "evidence_ids": evidence_ids}

    def decision(self, conversation_id: str, user_id: str, decision_id: str) -> dict:
        self.require_member(conversation_id, user_id)
        with self.lock:
            row = self.db.execute(
                "SELECT * FROM mg_decisions WHERE id=? AND conversation_id=?",
                (decision_id, conversation_id),
            ).fetchone()
        if row is None:
            raise ChatError("not_found", 404)
        return {
            "id": row["id"],
            "status": row["status"],
            "text": row["text"],
            "evidence_ids": [part for part in row["evidence_ids"].split(",") if part],
        }

    def record_decision(self, conversation_id: str, user_id: str, decision_id: str) -> dict:
        self.require_member(conversation_id, user_id)
        with self.lock:
            row = self.db.execute(
                "SELECT id FROM mg_decisions WHERE id=? AND conversation_id=? AND status='candidate'",
                (decision_id, conversation_id),
            ).fetchone()
            if row is None:
                raise ChatError("not_found", 404)
            self.db.execute("UPDATE mg_decisions SET status='recorded' WHERE id=?", (decision_id,))
            self.db.commit()
        return self.decision(conversation_id, user_id, decision_id)

    @staticmethod
    def _message(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "conversation_id": row["conversation_id"],
            "sender_id": row["sender_id"],
            "client_msg_id": row["client_msg_id"],
            "seq": row["seq"],
            "body": "" if row["deleted_at"] else row["body"],
            "created_at": row["created_at"],
            "edited_at": row["edited_at"],
            "deleted": bool(row["deleted_at"]),
        }
