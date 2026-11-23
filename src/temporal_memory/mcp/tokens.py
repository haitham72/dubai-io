"""Token issuance, verification, revocation, and device-presence helpers (WP-D)."""
from __future__ import annotations

import hashlib
import secrets
from typing import Any, Literal
import uuid

from temporal_memory.api.app import AuthInfo
from temporal_memory.config import get_settings
from temporal_memory.db.db import Database

TokenRole = Literal["admin", "worker", "owner-device"]
_VALID_ROLES: tuple[str, ...] = ("admin", "worker", "owner-device")


def hash_token(raw_token: str) -> str:
    """Return the SHA-256 hex digest used in the tokens.token_hash column."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_token(
    db: Database,
    *,
    role: TokenRole,
    owner: str | None = None,
    label: str = "",
) -> dict[str, Any]:
    """Create a bearer token, persist its SHA-256 hash, and return the raw secret once."""
    if role not in _VALID_ROLES:
        raise ValueError(f"invalid token role: {role!r}")
    if role == "owner-device" and not owner:
        raise ValueError("owner-device token requires owner")

    token_id = f"tok_{uuid.uuid4().hex[:12]}"
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_token(raw_token)

    with db.transaction() as conn:
        conn.execute(
            "INSERT INTO tokens (id, token_hash, role, owner, label) VALUES (%s, %s, %s, %s, %s)",
            (token_id, token_hash, role, owner, label),
        )

    return {
        "id": token_id,
        "token": raw_token,
        "role": role,
        "owner": owner,
        "label": label,
    }


def verify_token(
    db: Database,
    raw_token: str,
    *,
    admin_token: str | None = None,
) -> AuthInfo | None:
    """Verify a raw bearer token (or header value) against admin secret and active DB tokens."""
    if not raw_token:
        return None
    raw = raw_token.strip()
    if raw.lower().startswith("bearer "):
        raw = raw[7:].strip()
    if not raw:
        return None

    expected_admin = admin_token if admin_token is not None else get_settings().admin_token
    if expected_admin and secrets.compare_digest(raw, expected_admin):
        return AuthInfo(id="admin", role="admin", owner=None)

    token_hash = hash_token(raw)
    with db.connection() as conn:
        row = conn.execute(
            "SELECT id, role, owner, revoked_at FROM tokens WHERE token_hash = %s",
            (token_hash,),
        ).fetchone()

    if row is None or row["revoked_at"] is not None:
        return None
    if row["role"] not in _VALID_ROLES:
        return None
    return AuthInfo(id=row["id"], role=row["role"], owner=row["owner"])


def revoke_token(db: Database, token_id: str) -> bool:
    """Revoke a token by id. Returns True if a matching token row existed."""
    with db.transaction() as conn:
        row = conn.execute(
            """
            UPDATE tokens
            SET revoked_at = COALESCE(revoked_at, now())
            WHERE id = %s
            RETURNING id
            """,
            (token_id,),
        ).fetchone()
    return row is not None


def owner_has_active_device(db: Database, owner: str) -> bool:
    """Return True if the owner has at least one non-revoked owner-device token."""
    with db.connection() as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM tokens
            WHERE owner = %s AND role = 'owner-device' AND revoked_at IS NULL
            LIMIT 1
            """,
            (owner,),
        ).fetchone()
    return row is not None
