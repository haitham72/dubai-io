"""Synchronous 4-step forget/revoke cascade and generation-fenced propagation."""
from __future__ import annotations

from datetime import datetime, timezone
import threading
from typing import Any, Literal
import uuid

from app.identity.models import VerifiedPrincipal

from .audit import AuditStore
from .models import (
    APP_IDS,
    CONSENT_SCOPE_KINDS,
    SOURCE_KINDS,
    AppId,
    ConsentDeniedError,
    ConsentScopeKind,
    ForgetReceipt,
    MemoryBridgeError,
    MemoryBridgeUnavailable,
    MinorProtectionError,
    SourceKind,
    TemporalMemoryClient,
)
from .schema import ensure_memory_bridge_schema


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _require_verified_principal(principal: VerifiedPrincipal) -> str:
    if not isinstance(principal, VerifiedPrincipal) or principal.is_verified is not True:
        raise ConsentDeniedError(
            "verified principal required",
            code="unverified_principal",
            status_code=401,
        )
    owner_id = (principal.user_id or "").strip()
    if not owner_id:
        raise ConsentDeniedError(
            "verified principal missing user_id",
            code="unverified_principal",
            status_code=401,
        )
    return owner_id


def _validate_host_app(host_app: str) -> None:
    if host_app not in APP_IDS:
        raise MemoryBridgeError(f"invalid host_app: {host_app}", code="invalid_host_app", status_code=400)


def _validate_idempotency_key(idempotency_key: str | None) -> str:
    if not isinstance(idempotency_key, str) or not idempotency_key.strip():
        raise MemoryBridgeError(
            "idempotency_key is required",
            code="missing_idempotency_key",
            status_code=400,
        )
    return idempotency_key.strip()


def _normalize_conversation_scope_id(conversation_id: str) -> str:
    cid = (conversation_id or "").strip()
    if not cid:
        raise MemoryBridgeError(
            "conversation_id is required",
            code="missing_conversation_id",
            status_code=400,
        )
    return cid if cid.startswith("messenger:") else f"messenger:{cid}"


def _receipt_from_audit_event(event: dict[str, Any]) -> ForgetReceipt:
    raw = event.get("receipt") or {}
    required = {"idempotency_key", "owner_id", "scope_kind", "scope_id", "consent_generation", "status"}
    if not required.issubset(raw.keys()):
        raise MemoryBridgeError(
            "idempotency_key already used by a non-forget audit event",
            code="idempotency_conflict",
            status_code=409,
        )
    temporal_gen = raw.get("temporal_generation")
    return ForgetReceipt(
        idempotency_key=str(raw["idempotency_key"]),
        owner_id=str(raw["owner_id"]),
        scope_kind=raw["scope_kind"],
        scope_id=str(raw["scope_id"]),
        consent_generation=int(raw["consent_generation"]),
        temporal_generation=int(temporal_gen) if temporal_gen is not None else None,
        records_forgotten=int(raw.get("records_forgotten", 0)),
        facts_erased=int(raw.get("facts_erased", 0)),
        facts_trimmed=int(raw.get("facts_trimmed", 0)),
        jobs_requeued=int(raw.get("jobs_requeued", 0)),
        projections_invalidated=bool(raw.get("projections_invalidated", True)),
        status=raw["status"],
        recorded_at=str(raw.get("recorded_at") or event.get("created_at") or ""),
    )


class ForgetCoordinator:
    """Coordinates immediate consent closure, local derived wipe, temporal_memory forget, and audit."""

    def __init__(
        self,
        db: Any,
        client: TemporalMemoryClient,
        audit: AuditStore,
        *,
        lock: threading.RLock | None = None,
    ) -> None:
        self._db = db
        self._client = client
        self._audit = audit
        self._lock = lock or getattr(audit, "_lock", None) or threading.RLock()
        ensure_memory_bridge_schema(db, lock=self._lock)

    # ------------------------------------------------------------------ helpers
    def _close_consent_grant(
        self,
        *,
        owner_id: str,
        scope_kind: ConsentScopeKind,
        scope_id: str,
        actor_id: str,
        now_iso: str,
    ) -> int:
        """Atomically bump generation and close all consent flags for (owner_id, scope_kind, scope_id)."""
        with self._lock:
            self._db.execute(
                """
                INSERT INTO cs_consent_grants (
                    owner_id, scope_kind, scope_id,
                    enabled, read_enabled, write_enabled, ai_mode,
                    allow_interest_export, allow_cross_source_recall,
                    generation, updated_at, updated_by
                ) VALUES (?, ?, ?, 0, 0, 0, 'off', 0, 0, 2, ?, ?)
                ON CONFLICT(owner_id, scope_kind, scope_id) DO UPDATE SET
                    enabled = 0,
                    read_enabled = 0,
                    write_enabled = 0,
                    ai_mode = 'off',
                    allow_interest_export = 0,
                    allow_cross_source_recall = 0,
                    generation = cs_consent_grants.generation + 1,
                    updated_at = excluded.updated_at,
                    updated_by = excluded.updated_by
                """.strip(),
                (owner_id, scope_kind, scope_id, now_iso, actor_id),
            )
            row = self._db.execute(
                "SELECT generation FROM cs_consent_grants "
                "WHERE owner_id = ? AND scope_kind = ? AND scope_id = ?",
                (owner_id, scope_kind, scope_id),
            ).fetchone()
            return int(row[0]) if row is not None else 2

    def _current_owner_generation(
        self,
        owner_id: str,
        *,
        scope_kind: ConsentScopeKind | None = None,
        scope_id: str | None = None,
    ) -> int:
        with self._lock:
            if scope_kind is not None and scope_id is not None:
                row = self._db.execute(
                    "SELECT generation FROM cs_consent_grants "
                    "WHERE owner_id = ? AND scope_kind = ? AND scope_id = ?",
                    (owner_id, scope_kind, scope_id),
                ).fetchone()
                if row is not None:
                    return int(row[0])
            row = self._db.execute(
                "SELECT MAX(generation) FROM cs_consent_grants WHERE owner_id = ?",
                (owner_id,),
            ).fetchone()
            if row is not None and row[0] is not None:
                return int(row[0])
            return 1

    def _wipe_projection_cache(self, owner_id: str) -> None:
        with self._lock:
            self._db.execute(
                "DELETE FROM cs_interest_projection_cache WHERE owner_id = ?",
                (owner_id,),
            )

    def _mark_records_erased(self, owner_id: str, record_ids: list[str], now_iso: str) -> None:
        if not record_ids:
            return
        placeholders = ", ".join("?" for _ in record_ids)
        with self._lock:
            self._db.execute(
                f"UPDATE cs_memory_record_refs SET erased_at = ? "
                f"WHERE owner_id = ? AND erased_at IS NULL AND record_id IN ({placeholders})",
                (now_iso, owner_id, *record_ids),
            )
            self._db.execute(
                f"UPDATE cs_two_visit_signals SET erased_at = ? "
                f"WHERE owner_id = ? AND erased_at IS NULL AND id IN ({placeholders})",
                (now_iso, owner_id, *record_ids),
            )

    def _resolve_and_wipe_local(
        self,
        *,
        owner_id: str,
        actor_id: str,
        now_iso: str,
        close_scope: tuple[ConsentScopeKind, str] | None,
        ref_filter_col: Literal["source_id", "source_kind", "host_app"] | None = None,
        ref_filter_val: str | None = None,
        explicit_record_ids: list[str] | None = None,
        fact_id: str | None = None,
    ) -> tuple[int, list[str]]:
        """Execute Steps 1 & 2 atomically in local DB and commit before remote call."""
        with self._lock:
            if close_scope is not None:
                consent_gen = self._close_consent_grant(
                    owner_id=owner_id,
                    scope_kind=close_scope[0],
                    scope_id=close_scope[1],
                    actor_id=actor_id,
                    now_iso=now_iso,
                )
            else:
                consent_gen = self._current_owner_generation(owner_id)

            self._wipe_projection_cache(owner_id)

            resolved_rids: list[str]
            if explicit_record_ids is not None:
                resolved_rids = sorted({str(r).strip() for r in explicit_record_ids if str(r).strip()})
            elif ref_filter_col is not None and ref_filter_val is not None:
                rows = self._db.execute(
                    f"SELECT record_id FROM cs_memory_record_refs "
                    f"WHERE owner_id = ? AND {ref_filter_col} = ? AND erased_at IS NULL",
                    (owner_id, ref_filter_val),
                ).fetchall()
                resolved_rids = sorted({str(row[0]) for row in rows})
            else:
                resolved_rids = []

            self._db.commit()
            return consent_gen, resolved_rids

    def _run_cascade(
        self,
        *,
        principal: VerifiedPrincipal,
        host_app: AppId,
        action: str,
        scope_kind: ConsentScopeKind | Literal["record", "fact"],
        scope_id: str,
        idempotency_key: str,
        close_scope: tuple[ConsentScopeKind, str] | None = None,
        ref_filter_col: Literal["source_id", "source_kind", "host_app"] | None = None,
        ref_filter_val: str | None = None,
        explicit_record_ids: list[str] | None = None,
        fact_id: str | None = None,
    ) -> ForgetReceipt:
        owner_id = _require_verified_principal(principal)
        _validate_host_app(host_app)
        eff_key = _validate_idempotency_key(idempotency_key)

        prior = self._audit.check_idempotency_key(owner_id, eff_key)
        if prior is not None:
            prior_receipt = _receipt_from_audit_event(prior)
            if prior_receipt.status == "completed":
                return prior_receipt
            # Prior attempt ended in pending_reconciliation: keep local wipe clean and reuse
            # the original target_ids + consent_generation for temporal_memory reconciliation.
            now_iso = _now_iso()
            with self._lock:
                self._wipe_projection_cache(owner_id)
                self._db.commit()
            consent_gen = int(prior_receipt.consent_generation)
            target_ids = list(prior.get("target_ids") or [])
            is_retry = True
        else:
            now_iso = _now_iso()
            consent_gen, resolved_rids = self._resolve_and_wipe_local(
                owner_id=owner_id,
                actor_id=owner_id,
                now_iso=now_iso,
                close_scope=close_scope,
                ref_filter_col=ref_filter_col,
                ref_filter_val=ref_filter_val,
                explicit_record_ids=explicit_record_ids,
                fact_id=fact_id,
            )
            target_ids = [fact_id] if fact_id is not None else resolved_rids
            is_retry = False

        # Compatibility receipts retain the legacy keys with zero destructive effects.
        try:
            res = {"records": 0}
            if fact_id is not None:
                res = self._client.set_memory_lowered(owner_id, fact_id=fact_id)
            elif target_ids:
                for start in range(0, len(target_ids), 500):
                    self._client.set_memory_lowered(owner_id, record_ids=target_ids[start:start + 500])
            records_forgotten = facts_erased = facts_trimmed = jobs_requeued = 0
            temporal_gen = res.get("facts_version")
        except (ConsentDeniedError, MinorProtectionError):
            raise
        except (MemoryBridgeUnavailable, Exception):
            pending_receipt = ForgetReceipt(
                idempotency_key=eff_key,
                owner_id=owner_id,
                scope_kind=scope_kind,
                scope_id=scope_id,
                consent_generation=consent_gen,
                temporal_generation=None,
                records_forgotten=0,
                facts_erased=0,
                facts_trimmed=0,
                jobs_requeued=0,
                projections_invalidated=True,
                status="pending_reconciliation",
                recorded_at=now_iso,
            )
            if not is_retry:
                self._audit.record_event(
                    owner_id=owner_id,
                    actor_id=owner_id,
                    host_app=host_app,
                    action=action,
                    scope_kind=scope_kind,
                    scope_id=scope_id,
                    target_ids=target_ids,
                    consent_generation=consent_gen,
                    outcome="partial",
                    reason_code="pending_reconciliation",
                    receipt=pending_receipt,
                    idempotency_key=eff_key,
                )
            return pending_receipt

        # Step 4: Emit / reconcile immutable ForgetReceipt in cs_memory_audit.
        completed_receipt = ForgetReceipt(
            idempotency_key=eff_key,
            owner_id=owner_id,
            scope_kind=scope_kind,
            scope_id=scope_id,
            consent_generation=consent_gen,
            temporal_generation=temporal_gen,
            records_forgotten=records_forgotten,
            facts_erased=facts_erased,
            facts_trimmed=facts_trimmed,
            jobs_requeued=jobs_requeued,
            projections_invalidated=True,
            status="completed",
            recorded_at=now_iso,
        )
        if is_retry:
            self._audit.record_reconciliation(
                owner_id=owner_id,
                actor_id=owner_id,
                host_app=host_app,
                action=action,
                scope_kind=scope_kind,
                scope_id=scope_id,
                target_ids=target_ids,
                consent_generation=consent_gen,
                reason_code="reconciled",
                receipt=completed_receipt,
                idempotency_key=eff_key,
            )
        else:
            self._audit.record_event(
                owner_id=owner_id,
                actor_id=owner_id,
                host_app=host_app,
                action=action,
                scope_kind=scope_kind,
                scope_id=scope_id,
                target_ids=target_ids,
                consent_generation=consent_gen,
                outcome="ok",
                reason_code="completed",
                receipt=completed_receipt,
                idempotency_key=eff_key,
            )
        return completed_receipt

    # ------------------------------------------------------------------ public API
    def forget_records(
        self,
        principal: VerifiedPrincipal,
        record_ids: list[str],
        *,
        host_app: AppId,
        idempotency_key: str,
    ) -> ForgetReceipt:
        """Forget explicit record_ids for verified owner, wipe projection cache, and emit audit receipt."""
        clean_rids = sorted({str(r).strip() for r in (record_ids or []) if str(r).strip()})
        scope_id = clean_rids[0] if len(clean_rids) == 1 else f"{host_app}:{len(clean_rids)}_records"
        return self._run_cascade(
            principal=principal,
            host_app=host_app,
            action="memory.forget_records",
            scope_kind="record",
            scope_id=scope_id,
            idempotency_key=idempotency_key,
            explicit_record_ids=clean_rids,
        )

    def forget_conversation(
        self,
        principal: VerifiedPrincipal,
        conversation_id: str,
        *,
        idempotency_key: str,
    ) -> ForgetReceipt:
        """Forget derived memories for messenger:<conversation_id> while leaving Messenger messages intact."""
        conv_scope_id = _normalize_conversation_scope_id(conversation_id)
        return self._run_cascade(
            principal=principal,
            host_app="messenger",
            action="memory.forget_conversation",
            scope_kind="conversation",
            scope_id=conv_scope_id,
            idempotency_key=idempotency_key,
            close_scope=("conversation", conv_scope_id),
            ref_filter_col="source_id",
            ref_filter_val=conv_scope_id,
        )

    def forget_source(
        self,
        principal: VerifiedPrincipal,
        source_kind: SourceKind,
        *,
        host_app: AppId,
        idempotency_key: str,
    ) -> ForgetReceipt:
        """Forget all derived memories for source_kind while leaving Community/entry source content intact."""
        if source_kind not in SOURCE_KINDS:
            raise MemoryBridgeError(
                f"invalid source_kind: {source_kind}",
                code="invalid_source_kind",
                status_code=400,
            )
        return self._run_cascade(
            principal=principal,
            host_app=host_app,
            action="memory.forget_source",
            scope_kind="source",
            scope_id=source_kind,
            idempotency_key=idempotency_key,
            close_scope=("source", source_kind),
            ref_filter_col="source_kind",
            ref_filter_val=source_kind,
        )

    def forget_fact(
        self,
        principal: VerifiedPrincipal,
        fact_id: str,
        *,
        host_app: AppId,
        idempotency_key: str,
    ) -> ForgetReceipt:
        """Forget a specific fact_id in temporal_memory, wipe local projection cache, and emit audit receipt."""
        clean_fid = (fact_id or "").strip()
        if not clean_fid:
            raise MemoryBridgeError("fact_id is required", code="missing_fact_id", status_code=400)
        return self._run_cascade(
            principal=principal,
            host_app=host_app,
            action="memory.forget_fact",
            scope_kind="fact",
            scope_id=clean_fid,
            idempotency_key=idempotency_key,
            fact_id=clean_fid,
        )

    def revoke_consent_and_forget(
        self,
        principal: VerifiedPrincipal,
        *,
        scope_kind: ConsentScopeKind,
        scope_id: str,
        host_app: AppId,
        forget_derived: bool = True,
        idempotency_key: str | None = None,
    ) -> ForgetReceipt | None:
        """Atomically revoke consent and optionally cascade-forget all derived memories for that scope."""
        owner_id = _require_verified_principal(principal)
        _validate_host_app(host_app)
        if scope_kind not in CONSENT_SCOPE_KINDS:
            raise MemoryBridgeError(
                f"invalid scope_kind: {scope_kind}",
                code="invalid_scope_kind",
                status_code=400,
            )
        clean_scope_id = (scope_id or "").strip()
        if not clean_scope_id:
            raise MemoryBridgeError("scope_id is required", code="missing_scope_id", status_code=400)
        if scope_kind == "conversation":
            clean_scope_id = _normalize_conversation_scope_id(clean_scope_id)
        elif scope_kind == "source" and clean_scope_id not in SOURCE_KINDS:
            raise MemoryBridgeError(
                f"invalid source scope_id: {clean_scope_id}",
                code="invalid_source_kind",
                status_code=400,
            )
        elif scope_kind == "app" and clean_scope_id not in APP_IDS:
            raise MemoryBridgeError(
                f"invalid app scope_id: {clean_scope_id}",
                code="invalid_app_id",
                status_code=400,
            )

        if not forget_derived:
            if idempotency_key is not None and idempotency_key.strip():
                prior = self._audit.check_idempotency_key(owner_id, idempotency_key)
                if prior is not None:
                    return None
            now_iso = _now_iso()
            with self._lock:
                new_gen = self._close_consent_grant(
                    owner_id=owner_id,
                    scope_kind=scope_kind,
                    scope_id=clean_scope_id,
                    actor_id=owner_id,
                    now_iso=now_iso,
                )
                self._wipe_projection_cache(owner_id)
                self._db.commit()
            self._audit.record_event(
                owner_id=owner_id,
                actor_id=owner_id,
                host_app=host_app,
                action="consent.revoke",
                scope_kind=scope_kind,
                scope_id=clean_scope_id,
                target_ids=(),
                consent_generation=new_gen,
                outcome="ok",
                reason_code="revoked_without_forget",
                receipt={
                    "scope_kind": scope_kind,
                    "scope_id": clean_scope_id,
                    "consent_generation": new_gen,
                    "projections_invalidated": True,
                    "forget_derived": False,
                    "recorded_at": now_iso,
                },
                idempotency_key=idempotency_key,
            )
            return None

        eff_key = (
            idempotency_key.strip()
            if isinstance(idempotency_key, str) and idempotency_key.strip()
            else f"revoke:{owner_id}:{scope_kind}:{clean_scope_id}:{uuid.uuid4().hex}"
        )
        col_map: dict[ConsentScopeKind, Literal["source_kind", "source_id", "host_app"]] = {
            "source": "source_kind",
            "conversation": "source_id",
            "app": "host_app",
        }
        return self._run_cascade(
            principal=principal,
            host_app=host_app,
            action="consent.revoke_and_forget",
            scope_kind=scope_kind,
            scope_id=clean_scope_id,
            idempotency_key=eff_key,
            close_scope=(scope_kind, clean_scope_id),
            ref_filter_col=col_map[scope_kind],
            ref_filter_val=clean_scope_id,
        )
