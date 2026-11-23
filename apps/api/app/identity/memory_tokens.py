"""Per-owner temporal_memory token binding, Fernet encryption at rest, and device token management."""
from __future__ import annotations

import os
from pathlib import Path
from threading import RLock
from typing import Any, Optional
import uuid

from cryptography.fernet import Fernet, InvalidToken

from ..config import settings
from ..memory_bridge.models import TemporalMemoryClient
from ..oauth import local_key
from .models import IdentityError, VerifiedPrincipal
from .store import IdentityStore, iso_utc

_FORBIDDEN_SPOOF_OWNER_KEYS: frozenset[str] = frozenset({"owner", "owner_id", "user_id", "tm_owner_id"})
_FORBIDDEN_OVERRIDE_KEYS: frozenset[str] = frozenset({"role", "scope", "provenance", "age_band", "kind"})


def _require_device_token_principal(principal: VerifiedPrincipal) -> str:
    if not isinstance(principal, VerifiedPrincipal) or not principal.is_verified or not (principal.user_id or "").strip():
        raise IdentityError("unverified_principal", "Verified principal is required", 401)
    if principal.app_id != "quest" or "memory:device_token" not in principal.capabilities:
        raise IdentityError(
            "missing_capability",
            "Quest session with memory:device_token capability is required",
            403,
        )
    return principal.user_id


class MemoryTokenService:
    """Manages Fernet-encrypted bridge_service tokens and metadata-only owner_device tokens."""

    def __init__(
        self,
        store: IdentityStore,
        client: TemporalMemoryClient,
        *,
        token_key: Optional[str | bytes] = None,
        key_path: Optional[Path] = None,
    ) -> None:
        self.store = store
        self.client = client
        self._lock = RLock()

        configured: str = ""
        if isinstance(token_key, bytes):
            raw_key = token_key
        else:
            configured = (token_key if token_key is not None else os.environ.get("IDENTITY_TOKEN_KEY", "")).strip()
            resolved_path = Path(key_path) if key_path is not None else (settings.data_dir / "identity_token.key")
            raw_key = local_key(resolved_path, configured)
        self._fernet = Fernet(raw_key)

    def ensure_bridge_token(self, user_id: str) -> str:
        """Ensure a temporal_memory owner and active encrypted bridge_service token exist for user_id."""
        clean_uid = (user_id or "").strip()
        if not clean_uid:
            raise IdentityError("invalid_user_id", "user_id is required", 400)

        with self._lock:
            self.client.ensure_owner(clean_uid, label=clean_uid, kind="real")
            existing = self.store.get_active_memory_token(clean_uid, kind="bridge_service")
            if existing is not None:
                encrypted_blob = existing.get("encrypted_token")
                if encrypted_blob is None:
                    raise IdentityError(
                        "missing_encrypted_token",
                        "Stored bridge_service token has no ciphertext",
                        500,
                    )
                try:
                    return self._fernet.decrypt(encrypted_blob).decode("utf-8")
                except InvalidToken as exc:
                    raise IdentityError(
                        "token_decryption_failed",
                        "Stored bridge_service token could not be decrypted",
                        500,
                    ) from exc

            minted = self.client.mint_owner_device_token(clean_uid, label="cs-bridge")
            tm_token_id = str(minted["id"])
            raw_token = str(minted["token"])
            encrypted = self._fernet.encrypt(raw_token.encode("utf-8"))
            now_str = iso_utc()

            self.store.create_memory_token(
                record_id=f"mt_{uuid.uuid4().hex}",
                user_id=clean_uid,
                tm_owner_id=clean_uid,
                tm_token_id=tm_token_id,
                kind="bridge_service",
                label=str(minted.get("label") or "cs-bridge"),
                encrypted_token=encrypted,
                created_at=now_str,
            )
            self.store.record_audit(
                user_id=clean_uid,
                app_id=None,
                session_id=None,
                event_kind="memory_bridge_token_provisioned",
                detail={"tm_token_id": tm_token_id, "kind": "bridge_service"},
                at=now_str,
            )
            return raw_token

    def owner_token_resolver(self, owner_id: str) -> str:
        """Resolver callback compatible with HttpTemporalMemoryClient(owner_token_resolver=...)."""
        return self.ensure_bridge_token(owner_id)

    def mint_device_token(
        self,
        principal: VerifiedPrincipal,
        *,
        label: str = "owner-device",
    ) -> dict[str, Any]:
        """Mint an owner-device token strictly bound to principal.user_id (metadata-only storage)."""
        owner_id = _require_device_token_principal(principal)
        clean_label = (label or "owner-device").strip()
        if not clean_label or len(clean_label) > 120:
            raise IdentityError("invalid_label", "label must be between 1 and 120 characters", 422)

        with self._lock:
            self.client.ensure_owner(owner_id, label=owner_id, kind="real")
            minted = self.client.mint_owner_device_token(owner_id, label=clean_label)
            tm_token_id = str(minted["id"])
            raw_token = str(minted["token"])
            now_str = iso_utc()

            self.store.create_memory_token(
                record_id=f"mt_{uuid.uuid4().hex}",
                user_id=owner_id,
                tm_owner_id=owner_id,
                tm_token_id=tm_token_id,
                kind="owner_device",
                label=clean_label,
                encrypted_token=None,
                created_at=now_str,
            )
            self.store.record_audit(
                user_id=owner_id,
                app_id=principal.app_id,
                session_id=principal.session_id,
                event_kind="memory_device_token_minted",
                detail={"tm_token_id": tm_token_id, "label": clean_label},
                at=now_str,
            )
            return {
                "tm_token_id": tm_token_id,
                "token": raw_token,
                "owner_id": owner_id,
                "label": clean_label,
                "created_at": now_str,
            }

    def revoke_device_token(self, principal: VerifiedPrincipal, tm_token_id: str) -> bool:
        """Verify ownership, revoke in temporal_memory, mark revoked_at, and audit."""
        owner_id = _require_device_token_principal(principal)
        clean_tid = (tm_token_id or "").strip()
        if not clean_tid:
            raise IdentityError("invalid_token_id", "tm_token_id is required", 422)

        with self._lock:
            row = self.store.get_memory_token_by_tm_id(clean_tid)
            if row is None:
                raise IdentityError("token_not_found", "Memory device token not found", 404)
            if row["user_id"] != owner_id:
                raise IdentityError("forbidden", "Cannot revoke another user's memory token", 403)
            if row["kind"] != "owner_device":
                raise IdentityError("forbidden", "Internal bridge token cannot be revoked as a device token", 403)
            if row["revoked_at"] is not None:
                return False

            self.client.revoke_token(clean_tid)
            now_str = iso_utc()
            updated = self.store.revoke_memory_token(clean_tid, revoked_at=now_str)
            self.store.record_audit(
                user_id=owner_id,
                app_id=principal.app_id,
                session_id=principal.session_id,
                event_kind="memory_device_token_revoked",
                detail={"tm_token_id": clean_tid, "label": row["label"]},
                at=now_str,
            )
            return updated

    def list_tokens(self, principal: VerifiedPrincipal) -> list[dict[str, Any]]:
        """List metadata-only token records for principal.user_id (never returns raw or encrypted tokens)."""
        owner_id = _require_device_token_principal(principal)
        with self.store.lock:
            rows = self.store.db.execute(
                """SELECT id, user_id, tm_owner_id, tm_token_id, kind, label, created_at, revoked_at
                   FROM cs_memory_tokens
                   WHERE user_id = ?
                   ORDER BY created_at DESC, id DESC""",
                (owner_id,),
            ).fetchall()
        return [
            {
                "id": row[0],
                "owner_id": row[1],
                "tm_owner_id": row[2],
                "tm_token_id": row[3],
                "kind": row[4],
                "label": row[5],
                "created_at": row[6],
                "revoked_at": row[7],
            }
            for row in rows
        ]

    # Router handler adapters for /api/identity/memory-device-token
    def mint(self, principal: VerifiedPrincipal, body: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        payload = body or {}
        if not isinstance(payload, dict):
            raise IdentityError("invalid_body", "JSON object body is required", 422)
        for key in _FORBIDDEN_SPOOF_OWNER_KEYS:
            if key in payload:
                raise IdentityError(
                    "owner_spoof_rejected",
                    f"Caller cannot supply '{key}'; owner is bound from verified principal",
                    403,
                )
        for key in _FORBIDDEN_OVERRIDE_KEYS:
            if key in payload:
                raise IdentityError(
                    "forbidden_override",
                    f"Caller cannot supply '{key}'",
                    422,
                )
        unknown = set(payload.keys()) - {"label"}
        if unknown:
            raise IdentityError(
                "invalid_fields",
                f"Unsupported fields: {', '.join(sorted(unknown))}",
                422,
            )
        raw_label = payload.get("label")
        if raw_label is None:
            label = "owner-device"
        elif isinstance(raw_label, str):
            label = raw_label
        else:
            raise IdentityError("invalid_label", "label must be a string", 422)
        return self.mint_device_token(principal, label=label)

    def revoke(self, principal: VerifiedPrincipal, tm_token_id: str) -> dict[str, Any]:
        revoked = self.revoke_device_token(principal, tm_token_id)
        return {"revoked": revoked, "tm_token_id": tm_token_id}

    def list(self, principal: VerifiedPrincipal) -> dict[str, Any]:
        return {"tokens": self.list_tokens(principal)}
