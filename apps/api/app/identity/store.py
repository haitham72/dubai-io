"""Portable SQLite/PostgreSQL identity store for all cs_* identity tables."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from threading import RLock
from typing import Any, Optional
import uuid

from .. import db as db_mod


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(dt: Optional[datetime] = None) -> str:
    value = dt or utcnow()
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _valid_uuid_str(value: str) -> Optional[str]:
    try:
        return str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError):
        return None


_DDL_STATEMENTS: tuple[str, ...] = (
    """CREATE TABLE IF NOT EXISTS cs_users (
        user_id TEXT PRIMARY KEY,
        display_name TEXT NOT NULL DEFAULT '',
        email TEXT,
        age_band TEXT NOT NULL DEFAULT 'unknown',
        age_declared_at TEXT,
        age_source TEXT NOT NULL DEFAULT 'self_declared',
        status TEXT NOT NULL DEFAULT 'active',
        session_version INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS cs_identity_links (
        issuer TEXT NOT NULL,
        subject TEXT NOT NULL,
        user_id TEXT NOT NULL,
        email_verified INTEGER NOT NULL DEFAULT 0,
        linked_at TEXT NOT NULL,
        link_proof TEXT NOT NULL,
        PRIMARY KEY (issuer, subject),
        FOREIGN KEY (user_id) REFERENCES cs_users(user_id)
    )""",
    "CREATE INDEX IF NOT EXISTS cs_identity_links_user ON cs_identity_links(user_id)",
    """CREATE TABLE IF NOT EXISTS cs_session_adoptions (
        session_owner TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        adopted_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES cs_users(user_id)
    )""",
    """CREATE TABLE IF NOT EXISTS cs_link_challenges (
        challenge_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        nonce_hash TEXT NOT NULL,
        target_issuer TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        consumed_at TEXT,
        FOREIGN KEY (user_id) REFERENCES cs_users(user_id)
    )""",
    """CREATE TABLE IF NOT EXISTS cs_app_sessions (
        session_id TEXT PRIMARY KEY,
        token_hash TEXT NOT NULL UNIQUE,
        user_id TEXT NOT NULL,
        app_id TEXT NOT NULL,
        capabilities JSON NOT NULL,
        session_version INTEGER NOT NULL,
        source_jti TEXT,
        device_label TEXT,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        revoked_at TEXT,
        revocation_reason TEXT,
        FOREIGN KEY (user_id) REFERENCES cs_users(user_id)
    )""",
    "CREATE INDEX IF NOT EXISTS cs_app_sessions_user_app ON cs_app_sessions(user_id, app_id, revoked_at)",
    """CREATE TABLE IF NOT EXISTS cs_oauth_attempts (
        state_hash TEXT PRIMARY KEY,
        client_kind TEXT NOT NULL,
        return_to TEXT NOT NULL,
        code_verifier_enc BLOB NOT NULL,
        expires_at TEXT NOT NULL,
        consumed_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS cs_oauth_auth_codes (
        code_hash TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        client_kind TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        consumed_at TEXT,
        FOREIGN KEY (user_id) REFERENCES cs_users(user_id)
    )""",
    """CREATE TABLE IF NOT EXISTS cs_pairing_codes (
        code_hash TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        created_by_session_id TEXT,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        consumed_at TEXT,
        consumed_by_session_id TEXT,
        FOREIGN KEY (user_id) REFERENCES cs_users(user_id)
    )""",
    """CREATE TABLE IF NOT EXISTS cs_revoked_jtis (
        jti TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        revoked_at TEXT NOT NULL,
        expires_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS cs_ws_tickets (
        ticket_hash TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        app_id TEXT NOT NULL,
        origin TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        consumed_at TEXT,
        FOREIGN KEY (session_id) REFERENCES cs_app_sessions(session_id)
    )""",
    """CREATE TABLE IF NOT EXISTS cs_memory_tokens (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        tm_owner_id TEXT NOT NULL,
        tm_token_id TEXT NOT NULL UNIQUE,
        kind TEXT NOT NULL,
        label TEXT NOT NULL DEFAULT '',
        encrypted_token BLOB,
        created_at TEXT NOT NULL,
        revoked_at TEXT,
        FOREIGN KEY (user_id) REFERENCES cs_users(user_id)
    )""",
    "CREATE INDEX IF NOT EXISTS cs_memory_tokens_user ON cs_memory_tokens(user_id, kind, revoked_at)",
    """CREATE TABLE IF NOT EXISTS cs_identity_audit (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        app_id TEXT,
        session_id TEXT,
        event_kind TEXT NOT NULL,
        at TEXT NOT NULL,
        detail JSON NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS cs_identity_audit_user_at ON cs_identity_audit(user_id, at)",
)


class IdentityStore:
    """Thread-safe store for canonical users, identity links, sessions, WS tickets, and audit events."""

    def __init__(self, target_or_db: str | Path | Any) -> None:
        if hasattr(target_or_db, "execute") and hasattr(target_or_db, "commit"):
            self.db = target_or_db
        else:
            self.db = db_mod.connect(target_or_db)
        self.lock = RLock()
        self._init_schema()

    def _init_schema(self) -> None:
        with self.lock:
            for stmt in _DDL_STATEMENTS:
                self.db.execute(stmt)
            self._migrate_schema()
            self.db.commit()

    def _migrate_schema(self) -> None:
        dialect = getattr(self.db, "dialect", "sqlite")
        if dialect == "postgres":
            self.db.execute("ALTER TABLE cs_users ADD COLUMN IF NOT EXISTS email TEXT")
            self.db.execute("ALTER TABLE cs_app_sessions ADD COLUMN IF NOT EXISTS device_label TEXT")
            return
        user_cols = {row[1] for row in self.db.execute("PRAGMA table_info(cs_users)").fetchall()}
        if "email" not in user_cols:
            self.db.execute("ALTER TABLE cs_users ADD COLUMN email TEXT")
        sess_cols = {row[1] for row in self.db.execute("PRAGMA table_info(cs_app_sessions)").fetchall()}
        if "device_label" not in sess_cols:
            self.db.execute("ALTER TABLE cs_app_sessions ADD COLUMN device_label TEXT")

    def close(self) -> None:
        with self.lock:
            self.db.close()

    def get_user(self, user_id: str) -> Optional[dict[str, Any]]:
        with self.lock:
            row = self.db.execute(
                """SELECT user_id, display_name, email, age_band, age_declared_at, age_source,
                          status, session_version, created_at, updated_at
                   FROM cs_users WHERE user_id = ?""",
                (user_id,),
            ).fetchone()
            if not row:
                return None
            return {
                "user_id": row[0],
                "display_name": row[1],
                "email": row[2],
                "age_band": row[3],
                "age_declared_at": row[4],
                "age_source": row[5],
                "status": row[6],
                "session_version": int(row[7]),
                "created_at": row[8],
                "updated_at": row[9],
            }

    def get_identity_link(self, issuer: str, subject: str) -> Optional[dict[str, Any]]:
        with self.lock:
            row = self.db.execute(
                """SELECT issuer, subject, user_id, email_verified, linked_at, link_proof
                   FROM cs_identity_links WHERE issuer = ? AND subject = ?""",
                (issuer, subject),
            ).fetchone()
            if not row:
                return None
            return {
                "issuer": row[0],
                "subject": row[1],
                "user_id": row[2],
                "email_verified": bool(row[3]),
                "linked_at": row[4],
                "link_proof": row[5],
            }

    def get_or_create_user_for_identity(
        self,
        *,
        issuer: str,
        subject: str,
        display_name: str = "",
        email: Optional[str] = None,
        email_verified: bool = False,
    ) -> tuple[dict[str, Any], bool]:
        """Resolve canonical user_id strictly by (issuer, subject); never auto-merge by display_name or email."""
        with self.lock:
            link = self.get_identity_link(issuer, subject)
            if link is not None:
                user = self.get_user(link["user_id"])
                if user is None:
                    raise RuntimeError("Orphaned identity link")
                clean_name = (display_name or "").strip()
                clean_email = (email or "").strip() or None
                if (clean_name and clean_name != user["display_name"]) or (clean_email and clean_email != user.get("email")):
                    now_str = iso_utc()
                    self.db.execute(
                        "UPDATE cs_users SET display_name = ?, email = ?, updated_at = ? WHERE user_id = ?",
                        (clean_name or user["display_name"], clean_email or user.get("email"), now_str, user["user_id"]),
                    )
                    self.db.commit()
                    user = self.get_user(user["user_id"])
                    assert user is not None
                return user, False

            now_str = iso_utc()
            uuid_candidate = _valid_uuid_str(subject)
            if uuid_candidate and self.get_user(uuid_candidate) is None:
                user_id = uuid_candidate
            else:
                user_id = f"usr_{uuid.uuid4()}"

            clean_email = (email or "").strip() or None
            self.db.execute(
                """INSERT INTO cs_users
                   (user_id, display_name, email, age_band, age_declared_at, age_source, status, session_version, created_at, updated_at)
                   VALUES (?, ?, ?, 'unknown', NULL, 'self_declared', 'active', 1, ?, ?)""",
                (user_id, display_name or "", clean_email, now_str, now_str),
            )
            self.db.execute(
                """INSERT INTO cs_identity_links
                   (issuer, subject, user_id, email_verified, linked_at, link_proof)
                   VALUES (?, ?, ?, ?, ?, 'primary_jwt')""",
                (issuer, subject, user_id, 1 if email_verified else 0, now_str),
            )
            self.db.commit()
            user = self.get_user(user_id)
            assert user is not None
            return user, True

    def update_age_band(self, user_id: str, *, age_band: str, declared_at: str) -> Optional[dict[str, Any]]:
        with self.lock:
            cur = self.db.execute(
                """UPDATE cs_users
                   SET age_band = ?, age_declared_at = ?, age_source = 'self_declared', updated_at = ?
                   WHERE user_id = ?""",
                (age_band, declared_at, declared_at, user_id),
            )
            self.db.commit()
            if cur.rowcount == 0:
                return None
            return self.get_user(user_id)

    def get_session_adoption(self, session_owner: str) -> Optional[dict[str, Any]]:
        with self.lock:
            row = self.db.execute(
                "SELECT session_owner, user_id, adopted_at FROM cs_session_adoptions WHERE session_owner = ?",
                (session_owner,),
            ).fetchone()
            if not row:
                return None
            return {"session_owner": row[0], "user_id": row[1], "adopted_at": row[2]}

    def create_session_adoption(self, *, session_owner: str, user_id: str, adopted_at: str) -> bool:
        """One-time adoption insert; returns False if session_owner was already adopted."""
        with self.lock:
            existing = self.get_session_adoption(session_owner)
            if existing is not None:
                return False
            self.db.execute(
                "INSERT INTO cs_session_adoptions (session_owner, user_id, adopted_at) VALUES (?, ?, ?)",
                (session_owner, user_id, adopted_at),
            )
            self.db.commit()
            return True

    def create_link_challenge(
        self,
        *,
        challenge_id: str,
        user_id: str,
        nonce_hash: str,
        target_issuer: str,
        expires_at: str,
    ) -> None:
        with self.lock:
            self.db.execute(
                """INSERT INTO cs_link_challenges
                   (challenge_id, user_id, nonce_hash, target_issuer, expires_at, consumed_at)
                   VALUES (?, ?, ?, ?, ?, NULL)""",
                (challenge_id, user_id, nonce_hash, target_issuer, expires_at),
            )
            self.db.commit()

    def get_link_challenge(self, challenge_id: str) -> Optional[dict[str, Any]]:
        with self.lock:
            row = self.db.execute(
                """SELECT challenge_id, user_id, nonce_hash, target_issuer, expires_at, consumed_at
                   FROM cs_link_challenges WHERE challenge_id = ?""",
                (challenge_id,),
            ).fetchone()
            if not row:
                return None
            return {
                "challenge_id": row[0],
                "user_id": row[1],
                "nonce_hash": row[2],
                "target_issuer": row[3],
                "expires_at": row[4],
                "consumed_at": row[5],
            }

    def consume_link_challenge(self, challenge_id: str, *, consumed_at: str) -> bool:
        with self.lock:
            cur = self.db.execute(
                "UPDATE cs_link_challenges SET consumed_at = ? WHERE challenge_id = ? AND consumed_at IS NULL",
                (consumed_at, challenge_id),
            )
            self.db.commit()
            return cur.rowcount == 1

    def add_identity_link(
        self,
        *,
        issuer: str,
        subject: str,
        user_id: str,
        email_verified: bool,
        linked_at: str,
        link_proof: str,
    ) -> None:
        with self.lock:
            self.db.execute(
                """INSERT INTO cs_identity_links
                   (issuer, subject, user_id, email_verified, linked_at, link_proof)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (issuer, subject, user_id, 1 if email_verified else 0, linked_at, link_proof),
            )
            self.db.commit()

    def create_app_session(
        self,
        *,
        session_id: str,
        token_hash: str,
        user_id: str,
        app_id: str,
        capabilities: list[str],
        session_version: int,
        source_jti: Optional[str],
        created_at: str,
        expires_at: str,
        device_label: Optional[str] = None,
    ) -> None:
        with self.lock:
            self.db.execute(
                """INSERT INTO cs_app_sessions
                   (session_id, token_hash, user_id, app_id, capabilities, session_version,
                    source_jti, device_label, created_at, expires_at, revoked_at, revocation_reason)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)""",
                (
                    session_id,
                    token_hash,
                    user_id,
                    app_id,
                    json.dumps(sorted(capabilities)),
                    session_version,
                    source_jti,
                    device_label,
                    created_at,
                    expires_at,
                ),
            )
            self.db.commit()

    def _row_to_session(self, row: Any) -> dict[str, Any]:
        return {
            "session_id": row[0],
            "token_hash": row[1],
            "user_id": row[2],
            "app_id": row[3],
            "capabilities": list(json.loads(row[4])),
            "session_version": int(row[5]),
            "source_jti": row[6],
            "device_label": row[7],
            "created_at": row[8],
            "expires_at": row[9],
            "revoked_at": row[10],
            "revocation_reason": row[11],
        }

    def get_app_session_by_token_hash(self, token_hash: str) -> Optional[dict[str, Any]]:
        with self.lock:
            row = self.db.execute(
                """SELECT session_id, token_hash, user_id, app_id, capabilities, session_version,
                          source_jti, device_label, created_at, expires_at, revoked_at, revocation_reason
                   FROM cs_app_sessions WHERE token_hash = ?""",
                (token_hash,),
            ).fetchone()
            return self._row_to_session(row) if row else None

    def get_app_session_by_id(self, session_id: str) -> Optional[dict[str, Any]]:
        with self.lock:
            row = self.db.execute(
                """SELECT session_id, token_hash, user_id, app_id, capabilities, session_version,
                          source_jti, device_label, created_at, expires_at, revoked_at, revocation_reason
                   FROM cs_app_sessions WHERE session_id = ?""",
                (session_id,),
            ).fetchone()
            return self._row_to_session(row) if row else None

    def list_active_user_sessions(self, user_id: str) -> list[dict[str, Any]]:
        with self.lock:
            user = self.get_user(user_id)
            if user is None or user["status"] != "active":
                return []
            rows = self.db.execute(
                """SELECT session_id, token_hash, user_id, app_id, capabilities, session_version,
                          source_jti, device_label, created_at, expires_at, revoked_at, revocation_reason
                   FROM cs_app_sessions
                   WHERE user_id = ? AND revoked_at IS NULL AND session_version = ?
                   ORDER BY created_at DESC""",
                (user_id, user["session_version"]),
            ).fetchall()
            now_dt = utcnow()
            out: list[dict[str, Any]] = []
            for row in rows:
                sess = self._row_to_session(row)
                if parse_iso(sess["expires_at"]) > now_dt:
                    out.append(sess)
            return out

    def revoke_app_session(self, session_id: str, *, revoked_at: str, reason: str) -> bool:
        with self.lock:
            cur = self.db.execute(
                """UPDATE cs_app_sessions
                   SET revoked_at = ?, revocation_reason = ?
                   WHERE session_id = ? AND revoked_at IS NULL""",
                (revoked_at, reason, session_id),
            )
            self.db.commit()
            return cur.rowcount == 1

    def revoke_all_user_sessions(
        self,
        user_id: str,
        *,
        app_id: Optional[str],
        revoked_at: str,
        reason: str,
        bump_session_version: bool,
    ) -> int:
        with self.lock:
            if app_id is None:
                cur = self.db.execute(
                    """UPDATE cs_app_sessions
                       SET revoked_at = ?, revocation_reason = ?
                       WHERE user_id = ? AND revoked_at IS NULL""",
                    (revoked_at, reason, user_id),
                )
            else:
                cur = self.db.execute(
                    """UPDATE cs_app_sessions
                       SET revoked_at = ?, revocation_reason = ?
                       WHERE user_id = ? AND app_id = ? AND revoked_at IS NULL""",
                    (revoked_at, reason, user_id, app_id),
                )
            if bump_session_version:
                self.db.execute(
                    "UPDATE cs_users SET session_version = session_version + 1, updated_at = ? WHERE user_id = ?",
                    (revoked_at, user_id),
                )
            self.db.commit()
            return int(cur.rowcount)

    def revoke_jti(self, *, jti: str, user_id: str, revoked_at: str, expires_at: str) -> None:
        with self.lock:
            self.db.execute(
                """INSERT INTO cs_revoked_jtis (jti, user_id, revoked_at, expires_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(jti) DO UPDATE SET
                       user_id = excluded.user_id,
                       revoked_at = excluded.revoked_at,
                       expires_at = excluded.expires_at""",
                (jti, user_id, revoked_at, expires_at),
            )
            self.db.commit()

    def is_jti_revoked(self, jti: str) -> bool:
        with self.lock:
            row = self.db.execute("SELECT 1 FROM cs_revoked_jtis WHERE jti = ?", (jti,)).fetchone()
            return row is not None

    def create_ws_ticket(
        self,
        *,
        ticket_hash: str,
        session_id: str,
        user_id: str,
        app_id: str,
        origin: str,
        expires_at: str,
    ) -> None:
        with self.lock:
            self.db.execute(
                """INSERT INTO cs_ws_tickets
                   (ticket_hash, session_id, user_id, app_id, origin, expires_at, consumed_at)
                   VALUES (?, ?, ?, ?, ?, ?, NULL)""",
                (ticket_hash, session_id, user_id, app_id, origin, expires_at),
            )
            self.db.commit()

    def get_ws_ticket(self, ticket_hash: str) -> Optional[dict[str, Any]]:
        with self.lock:
            row = self.db.execute(
                """SELECT ticket_hash, session_id, user_id, app_id, origin, expires_at, consumed_at
                   FROM cs_ws_tickets WHERE ticket_hash = ?""",
                (ticket_hash,),
            ).fetchone()
            if not row:
                return None
            return {
                "ticket_hash": row[0],
                "session_id": row[1],
                "user_id": row[2],
                "app_id": row[3],
                "origin": row[4],
                "expires_at": row[5],
                "consumed_at": row[6],
            }

    def consume_ws_ticket_atomic(self, ticket_hash: str, *, consumed_at: str) -> bool:
        with self.lock:
            cur = self.db.execute(
                "UPDATE cs_ws_tickets SET consumed_at = ? WHERE ticket_hash = ? AND consumed_at IS NULL",
                (consumed_at, ticket_hash),
            )
            self.db.commit()
            return cur.rowcount == 1

    # Helper methods on cs_memory_tokens for CS-B5
    def create_memory_token(
        self,
        *,
        record_id: str,
        user_id: str,
        tm_owner_id: str,
        tm_token_id: str,
        kind: str,
        label: str,
        encrypted_token: Optional[bytes],
        created_at: str,
    ) -> None:
        with self.lock:
            self.db.execute(
                """INSERT INTO cs_memory_tokens
                   (id, user_id, tm_owner_id, tm_token_id, kind, label, encrypted_token, created_at, revoked_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)""",
                (record_id, user_id, tm_owner_id, tm_token_id, kind, label, encrypted_token, created_at),
            )
            self.db.commit()

    def get_active_memory_token(self, user_id: str, *, kind: str) -> Optional[dict[str, Any]]:
        with self.lock:
            row = self.db.execute(
                """SELECT id, user_id, tm_owner_id, tm_token_id, kind, label, encrypted_token, created_at, revoked_at
                   FROM cs_memory_tokens
                   WHERE user_id = ? AND kind = ? AND revoked_at IS NULL
                   ORDER BY created_at DESC LIMIT 1""",
                (user_id, kind),
            ).fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "user_id": row[1],
                "tm_owner_id": row[2],
                "tm_token_id": row[3],
                "kind": row[4],
                "label": row[5],
                "encrypted_token": bytes(row[6]) if row[6] is not None else None,
                "created_at": row[7],
                "revoked_at": row[8],
            }

    def get_memory_token_by_tm_id(self, tm_token_id: str) -> Optional[dict[str, Any]]:
        with self.lock:
            row = self.db.execute(
                """SELECT id, user_id, tm_owner_id, tm_token_id, kind, label, encrypted_token, created_at, revoked_at
                   FROM cs_memory_tokens WHERE tm_token_id = ?""",
                (tm_token_id,),
            ).fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "user_id": row[1],
                "tm_owner_id": row[2],
                "tm_token_id": row[3],
                "kind": row[4],
                "label": row[5],
                "encrypted_token": bytes(row[6]) if row[6] is not None else None,
                "created_at": row[7],
                "revoked_at": row[8],
            }

    def revoke_memory_token(self, tm_token_id: str, *, revoked_at: str) -> bool:
        with self.lock:
            cur = self.db.execute(
                "UPDATE cs_memory_tokens SET revoked_at = ? WHERE tm_token_id = ? AND revoked_at IS NULL",
                (revoked_at, tm_token_id),
            )
            self.db.commit()
            return cur.rowcount == 1

    def record_audit(
        self,
        *,
        user_id: Optional[str],
        app_id: Optional[str],
        session_id: Optional[str],
        event_kind: str,
        detail: dict[str, Any],
        at: Optional[str] = None,
    ) -> str:
        event_id = f"aud_{uuid.uuid4().hex}"
        timestamp = at or iso_utc()
        with self.lock:
            self.db.execute(
                """INSERT INTO cs_identity_audit
                   (id, user_id, app_id, session_id, event_kind, at, detail)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (event_id, user_id, app_id, session_id, event_kind, timestamp, json.dumps(detail)),
            )
            self.db.commit()
        return event_id

    def list_audit_events(self, user_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.db.execute(
                """SELECT id, user_id, app_id, session_id, event_kind, at, detail
                   FROM cs_identity_audit WHERE user_id = ? ORDER BY at DESC LIMIT ?""",
                (user_id, limit),
            ).fetchall()
            return [
                {
                    "id": row[0],
                    "user_id": row[1],
                    "app_id": row[2],
                    "session_id": row[3],
                    "event_kind": row[4],
                    "at": row[5],
                    "detail": json.loads(row[6]),
                }
                for row in rows
            ]

    # Google OAuth PKCE attempts, single-use auth codes, and QR pairing codes (E2)
    def create_oauth_attempt(
        self,
        *,
        state_hash: str,
        client_kind: str,
        return_to: str,
        code_verifier_enc: bytes,
        expires_at: str,
    ) -> None:
        with self.lock:
            self.db.execute(
                """INSERT INTO cs_oauth_attempts
                   (state_hash, client_kind, return_to, code_verifier_enc, expires_at, consumed_at)
                   VALUES (?, ?, ?, ?, ?, NULL)""",
                (state_hash, client_kind, return_to, code_verifier_enc, expires_at),
            )
            self.db.commit()

    def get_oauth_attempt(self, state_hash: str) -> Optional[dict[str, Any]]:
        with self.lock:
            row = self.db.execute(
                """SELECT state_hash, client_kind, return_to, code_verifier_enc, expires_at, consumed_at
                   FROM cs_oauth_attempts WHERE state_hash = ?""",
                (state_hash,),
            ).fetchone()
            if not row:
                return None
            return {
                "state_hash": row[0],
                "client_kind": row[1],
                "return_to": row[2],
                "code_verifier_enc": bytes(row[3]),
                "expires_at": row[4],
                "consumed_at": row[5],
            }

    def consume_oauth_attempt_atomic(self, state_hash: str, *, consumed_at: str) -> bool:
        with self.lock:
            cur = self.db.execute(
                "UPDATE cs_oauth_attempts SET consumed_at = ? WHERE state_hash = ? AND consumed_at IS NULL",
                (consumed_at, state_hash),
            )
            self.db.commit()
            return cur.rowcount == 1

    def create_oauth_auth_code(
        self,
        *,
        code_hash: str,
        user_id: str,
        client_kind: str,
        expires_at: str,
    ) -> None:
        with self.lock:
            self.db.execute(
                """INSERT INTO cs_oauth_auth_codes
                   (code_hash, user_id, client_kind, expires_at, consumed_at)
                   VALUES (?, ?, ?, ?, NULL)""",
                (code_hash, user_id, client_kind, expires_at),
            )
            self.db.commit()

    def get_oauth_auth_code(self, code_hash: str) -> Optional[dict[str, Any]]:
        with self.lock:
            row = self.db.execute(
                """SELECT code_hash, user_id, client_kind, expires_at, consumed_at
                   FROM cs_oauth_auth_codes WHERE code_hash = ?""",
                (code_hash,),
            ).fetchone()
            if not row:
                return None
            return {
                "code_hash": row[0],
                "user_id": row[1],
                "client_kind": row[2],
                "expires_at": row[3],
                "consumed_at": row[4],
            }

    def consume_oauth_auth_code_atomic(self, code_hash: str, *, consumed_at: str) -> bool:
        with self.lock:
            cur = self.db.execute(
                "UPDATE cs_oauth_auth_codes SET consumed_at = ? WHERE code_hash = ? AND consumed_at IS NULL",
                (consumed_at, code_hash),
            )
            self.db.commit()
            return cur.rowcount == 1

    def create_pairing_code(
        self,
        *,
        code_hash: str,
        user_id: str,
        created_by_session_id: Optional[str],
        created_at: str,
        expires_at: str,
    ) -> None:
        with self.lock:
            self.db.execute(
                """INSERT INTO cs_pairing_codes
                   (code_hash, user_id, created_by_session_id, created_at, expires_at, consumed_at, consumed_by_session_id)
                   VALUES (?, ?, ?, ?, ?, NULL, NULL)""",
                (code_hash, user_id, created_by_session_id, created_at, expires_at),
            )
            self.db.commit()

    def get_pairing_code(self, code_hash: str) -> Optional[dict[str, Any]]:
        with self.lock:
            row = self.db.execute(
                """SELECT code_hash, user_id, created_by_session_id, created_at, expires_at, consumed_at, consumed_by_session_id
                   FROM cs_pairing_codes WHERE code_hash = ?""",
                (code_hash,),
            ).fetchone()
            if not row:
                return None
            return {
                "code_hash": row[0],
                "user_id": row[1],
                "created_by_session_id": row[2],
                "created_at": row[3],
                "expires_at": row[4],
                "consumed_at": row[5],
                "consumed_by_session_id": row[6],
            }

    def is_pairing_session(self, session_id: str) -> bool:
        """True when this session was minted by completing a pairing code (a paired phone)."""
        with self.lock:
            row = self.db.execute(
                "SELECT 1 FROM cs_pairing_codes WHERE consumed_by_session_id = ? LIMIT 1",
                (session_id,),
            ).fetchone()
            return row is not None

    def invalidate_pairing_code(self, code_hash: str, *, at: str) -> bool:
        with self.lock:
            cur = self.db.execute(
                "UPDATE cs_pairing_codes SET consumed_at = ? WHERE code_hash = ? AND consumed_at IS NULL",
                (at, code_hash),
            )
            self.db.commit()
            return cur.rowcount == 1

    def consume_pairing_code_atomic(
        self,
        code_hash: str,
        *,
        consumed_at: str,
        consumed_by_session_id: str,
    ) -> bool:
        with self.lock:
            cur = self.db.execute(
                """UPDATE cs_pairing_codes
                   SET consumed_at = ?, consumed_by_session_id = ?
                   WHERE code_hash = ? AND consumed_at IS NULL""",
                (consumed_at, consumed_by_session_id, code_hash),
            )
            self.db.commit()
            return cur.rowcount == 1
