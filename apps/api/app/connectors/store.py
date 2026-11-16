"""Owner-scoped credential, cursor, record, and approval storage."""
from __future__ import annotations

import json
import uuid
from typing import Any

from .crypto import cipher_for, decrypt_json, encrypt_json
from .schema import ensure_connector_schema
from .types import RawItem


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def payload_hash(value: Any) -> str:
    import hashlib

    return hashlib.sha256(canonical(value).encode()).hexdigest()


class ConnectorStore:
    def __init__(self, db, *, key: bytes | str | None = None):
        self.db = db
        self.cipher = cipher_for(key)
        ensure_connector_schema(db)

    def _rows(self, sql: str, params=()) -> list[dict]:
        cur = self.db.execute(sql, params)
        names = [d[0] for d in cur.description]
        out = []
        for row in cur.fetchall():
            item = dict(zip(names, row))
            for field in ("cursor", "metadata", "payload", "shares"):
                if field in item and isinstance(item[field], str) and item[field]:
                    try:
                        item[field] = json.loads(item[field])
                    except json.JSONDecodeError:
                        pass
            out.append(item)
        return out

    def _one(self, sql: str, params=()) -> dict | None:
        rows = self._rows(sql, params)
        return rows[0] if rows else None

    def save_credentials(self, owner: str, connector_id: str, credentials: dict, at: str) -> None:
        blob = encrypt_json(self.cipher, credentials)
        self.db.execute(
            "INSERT INTO connector_credentials (owner, connector_id, ciphertext, updated_at) VALUES (?,?,?,?) "
            "ON CONFLICT(owner, connector_id) DO UPDATE SET ciphertext=excluded.ciphertext, updated_at=excluded.updated_at",
            (owner, connector_id, blob, at),
        )
        self.db.commit()

    def credentials(self, owner: str, connector_id: str) -> dict | None:
        row = self.db.execute(
            "SELECT ciphertext FROM connector_credentials WHERE owner=? AND connector_id=?",
            (owner, connector_id),
        ).fetchone()
        if not row:
            return None
        return decrypt_json(self.cipher, row[0])

    def delete_credentials(self, owner: str, connector_id: str) -> None:
        self.db.execute(
            "DELETE FROM connector_credentials WHERE owner=? AND connector_id=?",
            (owner, connector_id),
        )
        self.db.commit()

    def upsert_connection(self, owner: str, connector_id: str, **fields) -> None:
        current = self.connection(owner, connector_id)
        merged = {
            "status": "disconnected",
            "health": "unknown",
            "account_label": None,
            "cursor": None,
            "hook_id": None,
            "secret_hash": None,
            "last_sync_at": None,
            "last_error": None,
            "next_retry_at": None,
            "attempt": 0,
            "notice": None,
            "connected_at": None,
            "updated_at": fields.get("updated_at"),
        }
        if current:
            merged.update(current)
        merged.update(fields)
        cursor = merged.get("cursor")
        cursor_json = None if cursor is None else canonical(cursor)
        self.db.execute(
            "INSERT INTO connector_connections (owner, connector_id, status, health, account_label, cursor, hook_id, "
            "secret_hash, last_sync_at, last_error, next_retry_at, attempt, notice, connected_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(owner, connector_id) DO UPDATE SET status=excluded.status, health=excluded.health, "
            "account_label=excluded.account_label, cursor=excluded.cursor, hook_id=excluded.hook_id, "
            "secret_hash=excluded.secret_hash, last_sync_at=excluded.last_sync_at, last_error=excluded.last_error, "
            "next_retry_at=excluded.next_retry_at, attempt=excluded.attempt, notice=excluded.notice, "
            "connected_at=excluded.connected_at, updated_at=excluded.updated_at",
            (
                owner,
                connector_id,
                merged["status"],
                merged["health"],
                merged.get("account_label"),
                cursor_json,
                merged.get("hook_id"),
                merged.get("secret_hash"),
                merged.get("last_sync_at"),
                merged.get("last_error"),
                merged.get("next_retry_at"),
                int(merged.get("attempt") or 0),
                merged.get("notice"),
                merged.get("connected_at"),
                merged["updated_at"],
            ),
        )
        self.db.commit()

    def connection(self, owner: str, connector_id: str) -> dict | None:
        return self._one(
            "SELECT owner, connector_id, status, health, account_label, cursor, hook_id, secret_hash, last_sync_at, "
            "last_error, next_retry_at, attempt, notice, connected_at, updated_at "
            "FROM connector_connections WHERE owner=? AND connector_id=?",
            (owner, connector_id),
        )

    def connection_by_hook(self, hook_id: str) -> dict | None:
        if not hook_id:
            return None
        return self._one(
            "SELECT owner, connector_id, status, health, account_label, cursor, hook_id, secret_hash, last_sync_at, "
            "last_error, next_retry_at, attempt, notice, connected_at, updated_at "
            "FROM connector_connections WHERE hook_id=?",
            (hook_id,),
        )

    def public_connection(self, owner: str, connector_id: str) -> dict:
        row = self.connection(owner, connector_id)
        if not row:
            return {"status": "disconnected", "health": "unknown", "account_label": None, "attempt": 0}
        return {
            "status": row["status"],
            "health": row["health"],
            "account_label": row.get("account_label"),
            "last_sync_at": row.get("last_sync_at"),
            "last_error": row.get("last_error"),
            "next_retry_at": row.get("next_retry_at"),
            "attempt": row.get("attempt") or 0,
            "notice": row.get("notice"),
            "connected_at": row.get("connected_at"),
            "updated_at": row.get("updated_at"),
        }

    def log_sync(self, owner: str, connector_id: str, **fields) -> None:
        self.db.execute(
            "INSERT INTO connector_sync_log (id, owner, connector_id, started_at, finished_at, status, attempt, imported, duplicate, error) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                str(uuid.uuid4()),
                owner,
                connector_id,
                fields["started_at"],
                fields.get("finished_at"),
                fields["status"],
                int(fields.get("attempt") or 0),
                int(fields.get("imported") or 0),
                int(fields.get("duplicate") or 0),
                fields.get("error"),
            ),
        )
        self.db.commit()

    def upsert_records(
        self,
        owner: str,
        connector_id: str,
        items: list[RawItem],
        *,
        now: str,
        provenance: str,
    ) -> dict[str, int]:
        imported = duplicate = updated = skipped = 0
        for item in items:
            source_id = (item.source_id or "").strip()
            timestamp = item.source_timestamp if item.source_timestamp is not None else ""
            if not source_id or len(source_id) > 500 or len(timestamp) > 2000:
                skipped += 1
                continue
            meta = dict(item.metadata or {})
            text = item.text if item.text else (item.title or "")
            if len(text) > 8000:
                text = text[:8000]
                meta["truncated"] = True
            title = (item.title or "")[:300]
            dedupe = f"{connector_id}:{source_id}"
            digest = payload_hash(
                {"title": title, "text": text, "source_timestamp": timestamp, "metadata": meta, "kind": item.kind}
            )
            existing = self._one(
                "SELECT id, content_hash FROM connector_records WHERE owner=? AND dedupe_key=?",
                (owner, dedupe),
            )
            meta_json = canonical(meta)
            if existing and existing["content_hash"] == digest:
                duplicate += 1
                continue
            if existing:
                self.db.execute(
                    "UPDATE connector_records SET source_timestamp=?, ingested_at=?, title=?, text=?, provenance=?, "
                    "as_of=?, content_hash=?, metadata=?, kind=? WHERE id=? AND owner=?",
                    (timestamp, now, title, text, provenance, now, digest, meta_json, item.kind, existing["id"], owner),
                )
                updated += 1
                continue
            self.db.execute(
                "INSERT INTO connector_records (id, owner, connector_id, source_id, source_timestamp, ingested_at, "
                "dedupe_key, kind, title, text, provenance, as_of, content_hash, metadata) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    str(uuid.uuid4()),
                    owner,
                    connector_id,
                    source_id,
                    timestamp,
                    now,
                    dedupe,
                    item.kind,
                    title,
                    text,
                    provenance,
                    now,
                    digest,
                    meta_json,
                ),
            )
            imported += 1
        self.db.commit()
        return {"imported": imported, "duplicate": duplicate, "updated": updated, "skipped": skipped}

    def records(self, owner: str, connector_id: str, limit: int = 50) -> list[dict]:
        rows = self._rows(
            "SELECT id, owner, connector_id, source_id, source_timestamp, ingested_at, dedupe_key, kind, title, text, "
            "provenance, as_of, metadata FROM connector_records WHERE owner=? AND connector_id=? "
            "ORDER BY ingested_at DESC LIMIT ?",
            (owner, connector_id, limit),
        )
        for row in rows:
            row.pop("owner", None)
        return rows

    def record(self, owner: str, record_id: str) -> dict | None:
        return self._one(
            "SELECT id, connector_id, source_id, source_timestamp, text, title, provenance FROM connector_records "
            "WHERE owner=? AND id=?",
            (owner, record_id),
        )

    def create_grant(self, owner: str, connector_id: str, action: str, payload: dict, shares: list[str], at: str, expires_at: str) -> str:
        grant_id = str(uuid.uuid4())
        self.db.execute(
            "INSERT INTO connector_outbound_grants (id, owner, connector_id, action, payload_hash, payload, shares, status, created_at, expires_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                grant_id,
                owner,
                connector_id,
                action,
                payload_hash(payload),
                canonical(payload),
                canonical(shares),
                "pending",
                at,
                expires_at,
            ),
        )
        self.db.commit()
        return grant_id

    def grant(self, owner: str, grant_id: str) -> dict | None:
        return self._one(
            "SELECT id, owner, connector_id, action, payload_hash, payload, shares, status, created_at, expires_at, decided_at "
            "FROM connector_outbound_grants WHERE owner=? AND id=?",
            (owner, grant_id),
        )

    def set_grant(self, owner: str, grant_id: str, status: str, at: str, *, expected: str | None = None) -> bool:
        if expected:
            cur = self.db.execute(
                "UPDATE connector_outbound_grants SET status=?, decided_at=? WHERE owner=? AND id=? AND status=?",
                (status, at, owner, grant_id, expected),
            )
        else:
            cur = self.db.execute(
                "UPDATE connector_outbound_grants SET status=?, decided_at=? WHERE owner=? AND id=?",
                (status, at, owner, grant_id),
            )
        self.db.commit()
        return bool(cur.rowcount)

    def delete_user_data(self, owner: str, connector_id: str) -> dict[str, int]:
        counts = {}
        for table in (
            "connector_records",
            "connector_credentials",
            "connector_connections",
            "connector_sync_log",
            "connector_outbound_grants",
        ):
            cur = self.db.execute(
                f"DELETE FROM {table} WHERE owner=? AND connector_id=?",
                (owner, connector_id),
            )
            counts[table] = int(cur.rowcount or 0)
        self.db.commit()
        return counts
