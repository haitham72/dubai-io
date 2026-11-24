"""Default-off consent store and projection cache invalidation for memory_bridge."""
from __future__ import annotations

from datetime import datetime, timezone
import threading
from typing import Any

from app.identity.models import VerifiedPrincipal

from .models import (
    APP_IDS,
    CONSENT_SCOPE_KINDS,
    CONVERSATION_AI_MODES,
    SOURCE_KINDS,
    AppId,
    ConsentGrant,
    ConsentScopeKind,
    ConversationAIMode,
    MemoryBridgeError,
    MinorProtectionError,
    SourceKind,
)
from .schema import ensure_memory_bridge_schema


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_conversation_scope_id(conversation_id: str) -> str:
    """Return canonical `messenger:<conversation_id>` scope_id."""
    conv = (conversation_id or "").strip()
    if not conv:
        raise MemoryBridgeError("conversation_id is required", code="invalid_conversation_id", status_code=422)
    if conv.startswith("messenger:"):
        suffix = conv[len("messenger:") :].strip()
        if not suffix:
            raise MemoryBridgeError("conversation_id is required", code="invalid_conversation_id", status_code=422)
        return f"messenger:{suffix}"
    return f"messenger:{conv}"


def _require_verified_owner(principal: VerifiedPrincipal) -> str:
    if not isinstance(principal, VerifiedPrincipal) or not principal.is_verified or not (principal.user_id or "").strip():
        raise MemoryBridgeError("verified principal required", code="unauthorized", status_code=401)
    return principal.user_id


class ConsentStore:
    """Thread-safe portable SQLite/PostgreSQL consent store (default-off everywhere)."""

    def __init__(self, db: Any, *, lock: threading.RLock | None = None) -> None:
        self._db = db
        self._lock = lock if lock is not None else threading.RLock()
        ensure_memory_bridge_schema(self._db, lock=self._lock)

    def _row_to_grant(self, row: tuple[Any, ...]) -> ConsentGrant:
        return ConsentGrant(
            owner_id=str(row[0]),
            scope_kind=row[1],
            scope_id=str(row[2]),
            enabled=bool(row[3]),
            read_enabled=bool(row[4]),
            write_enabled=bool(row[5]),
            ai_mode=row[6],
            allow_interest_export=bool(row[7]),
            allow_cross_source_recall=bool(row[8]),
            generation=int(row[9]),
            updated_at=str(row[10] or ""),
        )

    def get_consent(
        self,
        owner_id: str,
        scope_kind: ConsentScopeKind,
        scope_id: str,
    ) -> ConsentGrant:
        """Return stored grant or default-off ConsentGrant (generation=1)."""
        if scope_kind not in CONSENT_SCOPE_KINDS:
            raise MemoryBridgeError(f"invalid scope_kind: {scope_kind!r}", code="invalid_scope_kind", status_code=422)
        if not owner_id or not scope_id:
            raise MemoryBridgeError("owner_id and scope_id are required", code="invalid_scope", status_code=422)

        with self._lock:
            row = self._db.execute(
                """
                SELECT owner_id, scope_kind, scope_id, enabled, read_enabled, write_enabled,
                       ai_mode, allow_interest_export, allow_cross_source_recall,
                       generation, updated_at
                FROM cs_consent_grants
                WHERE owner_id = ? AND scope_kind = ? AND scope_id = ?
                """,
                (owner_id, scope_kind, scope_id),
            ).fetchone()
        if row is None:
            return ConsentGrant(
                owner_id=owner_id,
                scope_kind=scope_kind,
                scope_id=scope_id,
                enabled=False,
                read_enabled=False,
                write_enabled=False,
                ai_mode="off",
                allow_interest_export=False,
                allow_cross_source_recall=False,
                generation=1,
                updated_at="",
            )
        return self._row_to_grant(row)

    def list_consents(
        self,
        owner_id: str,
        scope_kind: ConsentScopeKind | None = None,
    ) -> list[ConsentGrant]:
        """List persisted consent grants for an owner, optionally filtered by scope_kind."""
        if not owner_id:
            raise MemoryBridgeError("owner_id is required", code="invalid_owner", status_code=422)
        if scope_kind is not None and scope_kind not in CONSENT_SCOPE_KINDS:
            raise MemoryBridgeError(f"invalid scope_kind: {scope_kind!r}", code="invalid_scope_kind", status_code=422)

        with self._lock:
            if scope_kind is not None:
                rows = self._db.execute(
                    """
                    SELECT owner_id, scope_kind, scope_id, enabled, read_enabled, write_enabled,
                           ai_mode, allow_interest_export, allow_cross_source_recall,
                           generation, updated_at
                    FROM cs_consent_grants
                    WHERE owner_id = ? AND scope_kind = ?
                    ORDER BY scope_kind, scope_id
                    """,
                    (owner_id, scope_kind),
                ).fetchall()
            else:
                rows = self._db.execute(
                    """
                    SELECT owner_id, scope_kind, scope_id, enabled, read_enabled, write_enabled,
                           ai_mode, allow_interest_export, allow_cross_source_recall,
                           generation, updated_at
                    FROM cs_consent_grants
                    WHERE owner_id = ?
                    ORDER BY scope_kind, scope_id
                    """,
                    (owner_id,),
                ).fetchall()
        return [self._row_to_grant(r) for r in rows]

    def consent_generation_sig(self, owner_id: str) -> str:
        """Return deterministic signature of all grant generations for cache validation."""
        with self._lock:
            rows = self._db.execute(
                """
                SELECT scope_kind, scope_id, generation
                FROM cs_consent_grants
                WHERE owner_id = ?
                ORDER BY scope_kind, scope_id
                """,
                (owner_id,),
            ).fetchall()
        if not rows:
            return "default:1"
        return "|".join(f"{r[0]}:{r[1]}={int(r[2])}" for r in rows)

    def invalidate_projection_cache(self, owner_id: str) -> None:
        """Synchronously delete Community interest projection cache for owner_id."""
        with self._lock:
            self._db.execute(
                "DELETE FROM cs_interest_projection_cache WHERE owner_id = ?",
                (owner_id,),
            )
            self._db.commit()

    def _upsert_grant(
        self,
        *,
        owner_id: str,
        scope_kind: ConsentScopeKind,
        scope_id: str,
        enabled: bool,
        read_enabled: bool,
        write_enabled: bool,
        ai_mode: ConversationAIMode,
        allow_interest_export: bool,
        allow_cross_source_recall: bool,
        updated_by: str,
    ) -> ConsentGrant:
        now_iso = _now_iso()
        with self._lock:
            # First persisted toggle bumps default generation 1 -> 2; subsequent updates increment +1.
            self._db.execute(
                """
                INSERT INTO cs_consent_grants (
                    owner_id, scope_kind, scope_id, enabled, read_enabled, write_enabled,
                    ai_mode, allow_interest_export, allow_cross_source_recall, generation,
                    updated_at, updated_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 2, ?, ?)
                ON CONFLICT(owner_id, scope_kind, scope_id) DO UPDATE SET
                    enabled = excluded.enabled,
                    read_enabled = excluded.read_enabled,
                    write_enabled = excluded.write_enabled,
                    ai_mode = excluded.ai_mode,
                    allow_interest_export = excluded.allow_interest_export,
                    allow_cross_source_recall = excluded.allow_cross_source_recall,
                    generation = cs_consent_grants.generation + 1,
                    updated_at = excluded.updated_at,
                    updated_by = excluded.updated_by
                """,
                (
                    owner_id,
                    scope_kind,
                    scope_id,
                    int(bool(enabled)),
                    int(bool(read_enabled)),
                    int(bool(write_enabled)),
                    ai_mode,
                    int(bool(allow_interest_export)),
                    int(bool(allow_cross_source_recall)),
                    now_iso,
                    updated_by,
                ),
            )
            self._db.execute(
                "DELETE FROM cs_interest_projection_cache WHERE owner_id = ?",
                (owner_id,),
            )
            self._db.commit()
            return self.get_consent(owner_id, scope_kind, scope_id)

    def set_source_consent(
        self,
        principal: VerifiedPrincipal,
        source_kind: SourceKind,
        *,
        enabled: bool,
        allow_interest_export: bool = False,
    ) -> ConsentGrant:
        """Toggle consent for a data source; D11 blocks interest export for minor-protected accounts."""
        owner_id = _require_verified_owner(principal)
        if source_kind not in SOURCE_KINDS:
            raise MemoryBridgeError(f"invalid source_kind: {source_kind!r}", code="invalid_source_kind", status_code=422)
        if allow_interest_export and principal.is_minor_protected:
            raise MinorProtectionError(
                "minor-protected accounts cannot enable cross-app interest export"
            )
        return self._upsert_grant(
            owner_id=owner_id,
            scope_kind="source",
            scope_id=source_kind,
            enabled=bool(enabled),
            read_enabled=bool(enabled),
            write_enabled=bool(enabled),
            ai_mode="off",
            allow_interest_export=bool(allow_interest_export) if enabled else False,
            allow_cross_source_recall=False,
            updated_by=owner_id,
        )

    def set_app_consent(
        self,
        principal: VerifiedPrincipal,
        app_id: AppId,
        *,
        read_enabled: bool,
        write_enabled: bool,
        allow_interest_export_to_community: bool = False,
        allow_cross_source_recall: bool = False,
    ) -> ConsentGrant:
        """Toggle per-app consent; D11 blocks cross-app interest export for minor-protected accounts."""
        owner_id = _require_verified_owner(principal)
        if app_id not in APP_IDS:
            raise MemoryBridgeError(f"invalid app_id: {app_id!r}", code="invalid_app_id", status_code=422)
        if allow_interest_export_to_community and principal.is_minor_protected:
            raise MinorProtectionError(
                "minor-protected accounts cannot enable cross-app interest export to community"
            )
        return self._upsert_grant(
            owner_id=owner_id,
            scope_kind="app",
            scope_id=app_id,
            enabled=bool(read_enabled or write_enabled),
            read_enabled=bool(read_enabled),
            write_enabled=bool(write_enabled),
            ai_mode="off",
            allow_interest_export=bool(allow_interest_export_to_community),
            allow_cross_source_recall=bool(allow_cross_source_recall),
            updated_by=owner_id,
        )

    def set_conversation_consent(
        self,
        principal: VerifiedPrincipal,
        conversation_id: str,
        *,
        ai_mode: ConversationAIMode,
        allow_interest_export: bool = False,
    ) -> ConsentGrant:
        """Toggle per-conversation Messenger consent (`off` | `session` | `save`)."""
        owner_id = _require_verified_owner(principal)
        if ai_mode not in CONVERSATION_AI_MODES:
            raise MemoryBridgeError(f"invalid ai_mode: {ai_mode!r}", code="invalid_ai_mode", status_code=422)
        if allow_interest_export and principal.is_minor_protected:
            raise MinorProtectionError(
                "minor-protected accounts cannot enable cross-app interest export"
            )
        scope_id = canonical_conversation_scope_id(conversation_id)
        return self._upsert_grant(
            owner_id=owner_id,
            scope_kind="conversation",
            scope_id=scope_id,
            enabled=ai_mode in ("session", "save"),
            read_enabled=ai_mode in ("session", "save"),
            write_enabled=(ai_mode == "save"),
            ai_mode=ai_mode,
            allow_interest_export=bool(allow_interest_export) if ai_mode == "save" else False,
            allow_cross_source_recall=False,
            updated_by=owner_id,
        )
