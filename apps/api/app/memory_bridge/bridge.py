"""MemoryBridge: D11 minor fence, consent gates, Rule 9 writes, two-visit signals, and per-app reads."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import re
import threading
from typing import Any, Callable, Literal
import uuid

from app.identity.models import VerifiedPrincipal

from .audit import AuditStore
from .consent import ConsentStore, canonical_conversation_scope_id
from .forget import ForgetCoordinator
from .models import (
    APP_IDS,
    FACT_RESOLUTION_ACTIONS,
    HOST_APPS,
    MEMORY_SCOPES,
    SOURCE_KINDS,
    AppId,
    ConsentDeniedError,
    ConsentGrant,
    ConsentScopeKind,
    ConversationAIMode,
    FactResolutionAction,
    FactStatus,
    ForgetReceipt,
    GroupConsentSnapshot,
    InterestFeature,
    MemoryBridgeError,
    MemoryBridgeUnavailable,
    MemoryFactView,
    MemoryRecordInput,
    MinorProtectionError,
    Provenance,
    SensitiveContentError,
    SourceKind,
    TemporalMemoryClient,
    TrustTier,
    WriteReceipt,
)
from .schema import ensure_memory_bridge_schema
from .sensitive import gate_record, pre_write

_SLUG_CLEAN_RE = re.compile(r"[^a-z0-9_-]+")
_DECAY_FLOOR = 0.15
_DECAY_LAMBDA = 0.005


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: str) -> datetime:
    raw = (value or "").strip()
    if not raw:
        raise MemoryBridgeError("timestamp is required", code="invalid_timestamp", status_code=422)
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise MemoryBridgeError(f"invalid ISO timestamp: {value!r}", code="invalid_timestamp", status_code=422) from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _require_verified_principal(principal: VerifiedPrincipal) -> str:
    if not isinstance(principal, VerifiedPrincipal) or not principal.is_verified or not (principal.user_id or "").strip():
        raise ConsentDeniedError("verified principal required", code="unauthorized", status_code=401)
    return principal.user_id


def _require_app_principal(principal: VerifiedPrincipal, expected_app: AppId) -> str:
    owner_id = _require_verified_principal(principal)
    if expected_app not in APP_IDS:
        raise MemoryBridgeError(f"invalid app_id: {expected_app!r}", code="invalid_app_id", status_code=422)
    if principal.app_id is not None and principal.app_id != expected_app:
        raise ConsentDeniedError(
            f"app session {principal.app_id!r} cannot call {expected_app!r} bridge method",
            code="app_scope_mismatch",
            status_code=403,
        )
    return owner_id


def _validate_source_id(source_kind: SourceKind, source_id: str) -> None:
    if source_kind not in SOURCE_KINDS:
        raise MemoryBridgeError(f"invalid source_kind: {source_kind!r}", code="invalid_source_kind", status_code=422)
    expected_prefix = f"{source_kind}:"
    if not isinstance(source_id, str) or not source_id.startswith(expected_prefix):
        raise MemoryBridgeError(
            f"source_id must start with {expected_prefix!r}",
            code="invalid_source_id",
            status_code=422,
        )
    suffix = source_id[len(expected_prefix) :].strip()
    if not suffix:
        raise MemoryBridgeError(
            f"source_id {source_id!r} requires a non-empty identifier",
            code="invalid_source_id",
            status_code=422,
        )


def _source_kind_from_source_id(source_id: str) -> str:
    head, sep, _ = (source_id or "").partition(":")
    return head if sep and head in SOURCE_KINDS else ""


def _trust_and_prefix(
    provenance: str,
    status: str,
    demo_data: bool,
) -> tuple[TrustTier, Literal["You told me", "I noticed", "Confirmed source", "Demo data"]]:
    if demo_data or provenance == "demo_fixture":
        return ("T3_demo_fixture", "Demo data")
    if provenance == "provider_confirmed":
        return ("T1_provider_confirmed", "Confirmed source")
    if provenance == "inferred" or status == "hypothesis":
        return ("T2_inferred_qualified", "I noticed")
    return ("T0_user_confirmed", "You told me")


def _safe_topic_slug(subject_path: str) -> str:
    raw_tail = (subject_path or "general").strip("/").split("/")[-1].lower()
    cleaned = _SLUG_CLEAN_RE.sub("-", raw_tail).strip("-_")
    return cleaned or "general"


def _source_app_for_kind(
    source_kind: str,
) -> Literal["quest", "community", "messenger", "youtube"]:
    if source_kind in ("quest", "community", "messenger", "youtube"):
        return source_kind  # type: ignore[return-value]
    return "quest"


class MemoryBridge:
    """Server-enforced, consent-gated, Rule-9 & D11-fenced bridge over temporal_memory."""

    def __init__(
        self,
        db: Any,
        client: TemporalMemoryClient,
        *,
        screen_fn: Callable[[list[str]], dict[str, str]] | None = None,
        audit_store: Any | None = None,
        forget_coordinator: Any | None = None,
        consent_store: ConsentStore | None = None,
    ) -> None:
        self._db = db
        self.client = client
        self.screen_fn = screen_fn
        self._lock = threading.RLock()
        ensure_memory_bridge_schema(self._db, lock=self._lock)
        self.consent_store = consent_store or ConsentStore(self._db, lock=self._lock)
        self.audit_store = audit_store if audit_store is not None else AuditStore(self._db, lock=self._lock)
        self._audit_store = self.audit_store
        self.forget_coordinator = (
            forget_coordinator
            if forget_coordinator is not None
            else ForgetCoordinator(self._db, self.client, self.audit_store, lock=self._lock)
        )
        self._forget_coordinator = self.forget_coordinator

    # ------------------------------------------------------------------ audit
    def _record_audit(
        self,
        *,
        owner_id: str,
        actor_id: str,
        host_app: str,
        action: str,
        scope_kind: str | None,
        scope_id: str | None,
        target_ids: list[str],
        consent_generation: int,
        outcome: Literal["ok", "denied", "quarantined", "partial", "error"],
        reason_code: str | None = None,
        receipt: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> None:
        """Write a content-free audit row (IDs and category codes only; never raw text)."""
        payload_receipt = dict(receipt or {})
        if self._audit_store is not None:
            for meth_name in ("record_event", "record", "log_event"):
                fn = getattr(self._audit_store, meth_name, None)
                if callable(fn):
                    fn(
                        owner_id=owner_id,
                        actor_id=actor_id,
                        host_app=host_app,
                        action=action,
                        scope_kind=scope_kind,
                        scope_id=scope_id,
                        target_ids=target_ids,
                        consent_generation=consent_generation,
                        outcome=outcome,
                        reason_code=reason_code,
                        receipt=payload_receipt,
                        idempotency_key=idempotency_key,
                    )
                    return

        now_iso = _now_iso()
        audit_id = f"aud_{uuid.uuid4().hex[:16]}"
        with self._lock:
            self._db.execute(
                """
                INSERT INTO cs_memory_audit (
                    id, owner_id, actor_id, host_app, action, scope_kind, scope_id,
                    target_ids_json, consent_generation, outcome, reason_code,
                    receipt_json, idempotency_key, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_id,
                    owner_id,
                    actor_id,
                    host_app,
                    action,
                    scope_kind,
                    scope_id,
                    json.dumps(list(target_ids)),
                    int(consent_generation),
                    outcome,
                    reason_code,
                    json.dumps(payload_receipt),
                    idempotency_key,
                    now_iso,
                ),
            )
            self._db.commit()

    def list_audit_events(
        self,
        principal: VerifiedPrincipal,
        *,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return content-free audit events belonging strictly to principal.user_id."""
        owner_id = _require_verified_principal(principal)
        if self._audit_store is not None and callable(getattr(self._audit_store, "list_events", None)):
            return list(self._audit_store.list_events(owner_id, limit=limit))

        lim = max(1, min(int(limit), 500))
        with self._lock:
            rows = self._db.execute(
                """
                SELECT id, owner_id, actor_id, host_app, action, scope_kind, scope_id,
                       target_ids_json, consent_generation, outcome, reason_code,
                       receipt_json, idempotency_key, created_at
                FROM cs_memory_audit
                WHERE owner_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (owner_id, lim),
            ).fetchall()
        events: list[dict[str, Any]] = []
        for row in rows:
            events.append(
                {
                    "id": row[0],
                    "owner_id": row[1],
                    "actor_id": row[2],
                    "host_app": row[3],
                    "action": row[4],
                    "scope_kind": row[5],
                    "scope_id": row[6],
                    "target_ids": json.loads(row[7]) if isinstance(row[7], str) else (row[7] or []),
                    "consent_generation": int(row[8]),
                    "outcome": row[9],
                    "reason_code": row[10],
                    "receipt": json.loads(row[11]) if isinstance(row[11], str) else (row[11] or {}),
                    "idempotency_key": row[12],
                    "created_at": row[13],
                }
            )
        return events

    # --------------------------------------------------------------- consent
    def get_consent(
        self,
        principal: VerifiedPrincipal,
        scope_kind: ConsentScopeKind,
        scope_id: str,
    ) -> ConsentGrant:
        owner_id = _require_verified_principal(principal)
        return self.consent_store.get_consent(owner_id, scope_kind, scope_id)

    def list_consents(
        self,
        principal: VerifiedPrincipal,
        scope_kind: ConsentScopeKind | None = None,
    ) -> list[ConsentGrant]:
        owner_id = _require_verified_principal(principal)
        return self.consent_store.list_consents(owner_id, scope_kind=scope_kind)

    def set_source_consent(
        self,
        principal: VerifiedPrincipal,
        source_kind: SourceKind,
        *,
        enabled: bool,
        allow_interest_export: bool = False,
        forget_on_revoke: bool = True,
        idempotency_key: str | None = None,
    ) -> tuple[ConsentGrant, ForgetReceipt | None]:
        owner_id = _require_verified_principal(principal)
        grant = self.consent_store.set_source_consent(
            principal,
            source_kind,
            enabled=enabled,
            allow_interest_export=allow_interest_export,
        )
        host_app: AppId = principal.app_id or "quest"
        self._record_audit(
            owner_id=owner_id,
            actor_id=owner_id,
            host_app=host_app,
            action="consent.source",
            scope_kind="source",
            scope_id=source_kind,
            target_ids=[source_kind],
            consent_generation=grant.generation,
            outcome="ok",
            receipt={"enabled": grant.enabled, "allow_interest_export": grant.allow_interest_export},
        )
        receipt: ForgetReceipt | None = None
        if not enabled and forget_on_revoke and self._forget_coordinator is not None:
            idem = idempotency_key or f"revoke-source:{owner_id}:{source_kind}:{grant.generation}"
            receipt = self._forget_coordinator.forget_source(
                principal,
                source_kind,
                host_app=host_app,
                idempotency_key=idem,
            )
            grant = self.consent_store.get_consent(owner_id, "source", source_kind)
        return (grant, receipt)

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
        owner_id = _require_verified_principal(principal)
        grant = self.consent_store.set_app_consent(
            principal,
            app_id,
            read_enabled=read_enabled,
            write_enabled=write_enabled,
            allow_interest_export_to_community=allow_interest_export_to_community,
            allow_cross_source_recall=allow_cross_source_recall,
        )
        self._record_audit(
            owner_id=owner_id,
            actor_id=owner_id,
            host_app=principal.app_id or app_id,
            action="consent.app",
            scope_kind="app",
            scope_id=app_id,
            target_ids=[app_id],
            consent_generation=grant.generation,
            outcome="ok",
            receipt={
                "read_enabled": grant.read_enabled,
                "write_enabled": grant.write_enabled,
                "allow_interest_export": grant.allow_interest_export,
                "allow_cross_source_recall": grant.allow_cross_source_recall,
            },
        )
        return grant

    def set_conversation_consent(
        self,
        principal: VerifiedPrincipal,
        conversation_id: str,
        *,
        ai_mode: ConversationAIMode,
        allow_interest_export: bool = False,
        forget_on_withdraw: bool = False,
        idempotency_key: str | None = None,
    ) -> tuple[ConsentGrant, ForgetReceipt | None]:
        owner_id = _require_verified_principal(principal)
        grant = self.consent_store.set_conversation_consent(
            principal,
            conversation_id,
            ai_mode=ai_mode,
            allow_interest_export=allow_interest_export,
        )
        self._record_audit(
            owner_id=owner_id,
            actor_id=owner_id,
            host_app=principal.app_id or "messenger",
            action="consent.conversation",
            scope_kind="conversation",
            scope_id=grant.scope_id,
            target_ids=[grant.scope_id],
            consent_generation=grant.generation,
            outcome="ok",
            receipt={"ai_mode": grant.ai_mode, "allow_interest_export": grant.allow_interest_export},
        )
        receipt: ForgetReceipt | None = None
        if ai_mode == "off" and forget_on_withdraw and self._forget_coordinator is not None:
            conv_id = grant.scope_id[len("messenger:") :]
            idem = idempotency_key or f"withdraw-conv:{owner_id}:{conv_id}:{grant.generation}"
            receipt = self._forget_coordinator.forget_conversation(
                principal,
                conv_id,
                idempotency_key=idem,
            )
            grant = self.consent_store.get_consent(owner_id, "conversation", grant.scope_id)
        return (grant, receipt)

    # ---------------------------------------------------------------- writes
    def _effective_write_app(self, principal: VerifiedPrincipal, item: MemoryRecordInput) -> AppId:
        if item.host_app not in HOST_APPS:
            raise MemoryBridgeError(f"invalid host_app: {item.host_app!r}", code="invalid_host_app", status_code=422)
        if principal.app_id == "community" and (item.host_app != "community" or item.source_kind != "community"):
            raise ConsentDeniedError(
                "community session can only write community-scoped records",
                code="app_scope_mismatch",
                status_code=403,
            )
        if principal.app_id == "messenger" and (item.host_app != "messenger" or item.source_kind != "messenger"):
            raise ConsentDeniedError(
                "messenger session can only write messenger-scoped records",
                code="app_scope_mismatch",
                status_code=403,
            )
        if principal.app_id == "quest" and item.host_app not in ("quest", "connector"):
            raise ConsentDeniedError(
                "quest session cannot spoof community or messenger host_app",
                code="app_scope_mismatch",
                status_code=403,
            )
        if item.host_app == "connector":
            return principal.app_id or "quest"
        return item.host_app  # type: ignore[return-value]

    def _upsert_record_ref(
        self,
        *,
        owner_id: str,
        record_id: str,
        source_kind: str,
        source_id: str,
        host_app: str,
        author_is_owner: bool,
        consent_generation: int,
        created_at: str,
    ) -> None:
        with self._lock:
            self._db.execute(
                """
                INSERT INTO cs_memory_record_refs (
                    owner_id, record_id, source_kind, source_id, host_app,
                    author_is_owner, consent_generation, created_at, erased_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)
                ON CONFLICT(owner_id, record_id) DO UPDATE SET
                    source_kind = excluded.source_kind,
                    source_id = excluded.source_id,
                    host_app = excluded.host_app,
                    author_is_owner = excluded.author_is_owner,
                    consent_generation = excluded.consent_generation,
                    erased_at = NULL
                """,
                (
                    owner_id,
                    record_id,
                    source_kind,
                    source_id,
                    host_app,
                    int(bool(author_is_owner)),
                    int(consent_generation),
                    created_at,
                ),
            )
            self._db.execute(
                "DELETE FROM cs_interest_projection_cache WHERE owner_id = ?",
                (owner_id,),
            )
            self._db.commit()

    def write_consented(
        self,
        principal: VerifiedPrincipal,
        item: MemoryRecordInput,
        *,
        group_consent: GroupConsentSnapshot | None = None,
        expected_consent_generation: int | None = None,
    ) -> WriteReceipt:
        """Write a consented memory record after D11, spoof, consent, and Rule 9 checks."""
        owner_id = _require_verified_principal(principal)

        # D11 hard fence (first gate): minor-protected accounts never write memory.
        if principal.is_minor_protected:
            raise MinorProtectionError(
                "minor-protected account cannot write memory records"
            )

        # Reject caller attempting to spoof owner or provenance on the input payload.
        for attr in ("owner", "owner_id"):
            spoofed_owner = getattr(item, attr, None)
            if spoofed_owner is not None and spoofed_owner != owner_id:
                raise ConsentDeniedError(
                    "caller cannot supply or override owner_id",
                    code="owner_spoof_rejected",
                    status_code=403,
                )
        if getattr(item, "provenance", None) is not None:
            raise ConsentDeniedError(
                "caller cannot supply provenance",
                code="provenance_spoof_rejected",
                status_code=403,
            )

        if not isinstance(item, MemoryRecordInput):
            raise MemoryBridgeError("item must be MemoryRecordInput", code="invalid_input", status_code=422)
        if not (item.record_id or "").strip():
            raise MemoryBridgeError("record_id is required", code="invalid_record_id", status_code=422)
        if not (item.author_id or "").strip():
            raise MemoryBridgeError("author_id is required", code="invalid_author_id", status_code=422)
        if not (item.text or "").strip():
            raise MemoryBridgeError("text is required", code="invalid_text", status_code=422)
        if item.scope not in MEMORY_SCOPES:
            raise MemoryBridgeError(f"invalid scope: {item.scope!r}", code="invalid_scope", status_code=422)
        _parse_iso(item.valid_time)
        _validate_source_id(item.source_kind, item.source_id)
        effective_app = self._effective_write_app(principal, item)

        # Third-party content can NEVER forge owner confirmation or user_supplied provenance.
        if item.author_id != owner_id and item.explicit_user_confirm:
            raise ConsentDeniedError(
                "cannot mark third-party content as explicit_user_confirm",
                code="provenance_spoof_rejected",
                status_code=403,
            )
        if (
            item.source_kind == "community"
            and item.record_id.startswith("cmpost:")
            and item.author_id != owner_id
        ):
            raise ConsentDeniedError(
                "community authored post record must be authored by owner",
                code="third_party_post_rejected",
                status_code=403,
            )

        # Fail-closed consent checks.
        source_grant = self.consent_store.get_consent(owner_id, "source", item.source_kind)
        app_grant = self.consent_store.get_consent(owner_id, "app", effective_app)
        consent_gen = max(source_grant.generation, app_grant.generation)

        if not source_grant.enabled or not app_grant.write_enabled:
            self._record_audit(
                owner_id=owner_id,
                actor_id=owner_id,
                host_app=item.host_app,
                action="write_consented",
                scope_kind="source",
                scope_id=item.source_kind,
                target_ids=[item.record_id],
                consent_generation=consent_gen,
                outcome="denied",
                reason_code="consent_required",
            )
            raise ConsentDeniedError("source and app write consent required")

        if item.source_kind == "messenger":
            conv_id = item.source_id[len("messenger:") :]
            conv_grant = self.consent_store.get_consent(owner_id, "conversation", item.source_id)
            consent_gen = max(consent_gen, conv_grant.generation)
            if conv_grant.ai_mode != "save":
                self._record_audit(
                    owner_id=owner_id,
                    actor_id=owner_id,
                    host_app=item.host_app,
                    action="write_consented",
                    scope_kind="conversation",
                    scope_id=item.source_id,
                    target_ids=[item.record_id],
                    consent_generation=consent_gen,
                    outcome="denied",
                    reason_code=f"conversation_ai_mode_{conv_grant.ai_mode}",
                )
                raise ConsentDeniedError("messenger conversation ai_mode must be 'save' for writes")
            if (
                group_consent is None
                or group_consent.conversation_id != conv_id
                or not group_consent.caller_is_member
                or not group_consent.all_active_members_ai_enabled
                or not group_consent.cited_authors_save_enabled
            ):
                self._record_audit(
                    owner_id=owner_id,
                    actor_id=owner_id,
                    host_app=item.host_app,
                    action="write_consented",
                    scope_kind="conversation",
                    scope_id=item.source_id,
                    target_ids=[item.record_id],
                    consent_generation=consent_gen,
                    outcome="denied",
                    reason_code="group_consent_denied",
                )
                raise ConsentDeniedError("messenger group consent snapshot rejected write")

        if expected_consent_generation is not None and expected_consent_generation != consent_gen:
            self._record_audit(
                owner_id=owner_id,
                actor_id=owner_id,
                host_app=item.host_app,
                action="write_consented",
                scope_kind="source",
                scope_id=item.source_kind,
                target_ids=[item.record_id],
                consent_generation=consent_gen,
                outcome="denied",
                reason_code="consent_generation_stale",
            )
            raise ConsentDeniedError(
                "consent generation changed before write committed",
                code="consent_generation_stale",
                status_code=409,
            )

        # Rule 9 fail-closed sensitive gate (Layer 1 + optional Layer 2).
        gate = gate_record(item, owner_id=owner_id, screen_fn=self.screen_fn)
        now_iso = _now_iso()
        if not gate.allowed:
            self._record_audit(
                owner_id=owner_id,
                actor_id=owner_id,
                host_app=item.host_app,
                action="write_consented",
                scope_kind="source",
                scope_id=item.source_kind,
                target_ids=[item.record_id],
                consent_generation=consent_gen,
                outcome="quarantined",
                reason_code=gate.reason_code or gate.category or "sensitive_blocked",
                receipt={"category": gate.category},
            )
            return WriteReceipt(
                ok=False,
                record_id=item.record_id,
                owner_id=owner_id,
                consent_generation=consent_gen,
                trust_tier="T3_demo_fixture" if item.demo_data else "T0_user_confirmed",
                provenance="demo_fixture" if item.demo_data else "user_supplied",
                status="quarantined",
                fact_ids=[],
                quarantine_category=gate.category,
                recorded_at=now_iso,
            )

        self.client.ensure_owner(
            owner_id,
            label=owner_id,
            kind="demo" if item.demo_data else "real",
        )

        # Third-party message rule: store Record evidence only, never a confirmed fact about owner_id.
        if item.author_id != owner_id:
            try:
                self.client.upsert_record_and_enqueue(
                    owner_id,
                    record_id=item.record_id,
                    source=item.source_id,
                    at=item.valid_time,
                    author=item.author_id,
                    text=item.text,
                    enqueue="none",
                    direct_fact=None,
                )
            except SensitiveContentError as exc:
                self._record_audit(
                    owner_id=owner_id,
                    actor_id=owner_id,
                    host_app=item.host_app,
                    action="write_consented",
                    scope_kind="source",
                    scope_id=item.source_kind,
                    target_ids=[item.record_id],
                    consent_generation=consent_gen,
                    outcome="quarantined",
                    reason_code=exc.code,
                    receipt={"category": exc.category},
                )
                return WriteReceipt(
                    ok=False,
                    record_id=item.record_id,
                    owner_id=owner_id,
                    consent_generation=consent_gen,
                    trust_tier="T3_demo_fixture" if item.demo_data else "T2_inferred_qualified",
                    provenance="demo_fixture" if item.demo_data else "inferred",
                    status="quarantined",
                    fact_ids=[],
                    quarantine_category=exc.category,
                    recorded_at=now_iso,
                )

            self._upsert_record_ref(
                owner_id=owner_id,
                record_id=item.record_id,
                source_kind=item.source_kind,
                source_id=item.source_id,
                host_app=item.host_app,
                author_is_owner=False,
                consent_generation=consent_gen,
                created_at=now_iso,
            )
            self._record_audit(
                owner_id=owner_id,
                actor_id=owner_id,
                host_app=item.host_app,
                action="write_consented",
                scope_kind="source",
                scope_id=item.source_kind,
                target_ids=[item.record_id],
                consent_generation=consent_gen,
                outcome="ok",
                receipt={"evidence_only": True, "fact_ids": []},
            )
            return WriteReceipt(
                ok=True,
                record_id=item.record_id,
                owner_id=owner_id,
                consent_generation=consent_gen,
                trust_tier="T3_demo_fixture" if item.demo_data else "T2_inferred_qualified",
                provenance="demo_fixture" if item.demo_data else "inferred",
                status="applied",
                fact_ids=[],
                recorded_at=now_iso,
            )

        # Owner-authored record.
        provenance: Provenance = "demo_fixture" if item.demo_data else (
            "user_supplied" if item.explicit_user_confirm else "inferred"
        )
        trust_tier: TrustTier = "T3_demo_fixture" if item.demo_data else (
            "T0_user_confirmed" if item.explicit_user_confirm else "T2_inferred_qualified"
        )
        direct_fact: dict[str, Any] | None = None
        enqueue_mode: Literal["extract.live", "extract.day", "none"] = "none"
        if item.explicit_user_confirm:
            direct_fact = {
                "text": item.text,
                "text_orig": item.text_orig,
                "subject_path": item.subject_path or "general/interests",
                "valid_from": item.valid_time,
                "provenance": provenance,
                "status": "active",
                "evidence": [item.record_id],
                "sensitive_cat": gate.sensitive_cat,
                "demo_data": bool(item.demo_data),
            }
        elif not (item.source_kind == "community" and item.record_id.startswith("cmsave:")):
            enqueue_mode = "extract.live"

        try:
            res = self.client.upsert_record_and_enqueue(
                owner_id,
                record_id=item.record_id,
                source=item.source_id,
                at=item.valid_time,
                author=owner_id,
                text=item.text,
                enqueue=enqueue_mode,
                direct_fact=direct_fact,
            )
        except SensitiveContentError as exc:
            self._record_audit(
                owner_id=owner_id,
                actor_id=owner_id,
                host_app=item.host_app,
                action="write_consented",
                scope_kind="source",
                scope_id=item.source_kind,
                target_ids=[item.record_id],
                consent_generation=consent_gen,
                outcome="quarantined",
                reason_code=exc.code,
                receipt={"category": exc.category},
            )
            return WriteReceipt(
                ok=False,
                record_id=item.record_id,
                owner_id=owner_id,
                consent_generation=consent_gen,
                trust_tier=trust_tier,
                provenance=provenance,
                status="quarantined",
                fact_ids=[],
                quarantine_category=exc.category,
                recorded_at=now_iso,
            )

        if res.get("quarantined"):
            q_cat = str(res.get("quarantine_category") or "sensitive")
            self._record_audit(
                owner_id=owner_id,
                actor_id=owner_id,
                host_app=item.host_app,
                action="write_consented",
                scope_kind="source",
                scope_id=item.source_kind,
                target_ids=[item.record_id],
                consent_generation=consent_gen,
                outcome="quarantined",
                reason_code=f"sensitive_{q_cat}",
                receipt={"category": q_cat},
            )
            return WriteReceipt(
                ok=False,
                record_id=item.record_id,
                owner_id=owner_id,
                consent_generation=consent_gen,
                trust_tier=trust_tier,
                provenance=provenance,
                status="quarantined",
                fact_ids=[],
                quarantine_category=q_cat,
                recorded_at=now_iso,
            )

        self._upsert_record_ref(
            owner_id=owner_id,
            record_id=item.record_id,
            source_kind=item.source_kind,
            source_id=item.source_id,
            host_app=item.host_app,
            author_is_owner=True,
            consent_generation=consent_gen,
            created_at=now_iso,
        )
        fact_ids = [str(fid) for fid in (res.get("fact_ids") or [])]
        job_id = res.get("job_id")
        receipt_status: Literal["applied", "queued"] = "queued" if (job_id and not fact_ids) else "applied"
        self._record_audit(
            owner_id=owner_id,
            actor_id=owner_id,
            host_app=item.host_app,
            action="write_consented",
            scope_kind="source",
            scope_id=item.source_kind,
            target_ids=[item.record_id, *fact_ids],
            consent_generation=consent_gen,
            outcome="ok",
            receipt={"fact_ids": fact_ids, "status": receipt_status},
        )
        return WriteReceipt(
            ok=True,
            record_id=item.record_id,
            owner_id=owner_id,
            consent_generation=consent_gen,
            trust_tier=trust_tier,
            provenance=provenance,
            status=receipt_status,
            fact_ids=fact_ids,
            job_id=job_id,
            recorded_at=now_iso,
        )

    def record_behavioral_signal(
        self,
        principal: VerifiedPrincipal,
        *,
        source_kind: SourceKind,
        source_id: str,
        topic_slug: str,
        option_key: str,
        at: str,
        weight: float = 1.0,
    ) -> dict[str, Any]:
        """Record a weak behavioral signal and promote to hypothesis only on >=2 separated visits."""
        owner_id = _require_verified_principal(principal)

        # D11 hard fence (first gate).
        if principal.is_minor_protected:
            raise MinorProtectionError(
                "minor-protected account cannot record behavioral signals"
            )

        _validate_source_id(source_kind, source_id)
        clean_slug = _safe_topic_slug(topic_slug)
        if not (topic_slug or "").strip() or not (option_key or "").strip():
            raise MemoryBridgeError("topic_slug and option_key are required", code="invalid_signal", status_code=422)
        _parse_iso(at)
        sig_weight = max(0.05, min(float(weight), 1.0))

        effective_app: AppId = principal.app_id or (
            "community" if source_kind == "community" else ("messenger" if source_kind == "messenger" else "quest")
        )
        if principal.app_id == "community" and source_kind != "community":
            raise ConsentDeniedError("community session cannot record non-community signal", status_code=403)
        if principal.app_id == "messenger" and source_kind != "messenger":
            raise ConsentDeniedError("messenger session cannot record non-messenger signal", status_code=403)

        source_grant = self.consent_store.get_consent(owner_id, "source", source_kind)
        app_grant = self.consent_store.get_consent(owner_id, "app", effective_app)
        consent_gen = max(source_grant.generation, app_grant.generation)
        if not source_grant.enabled or not app_grant.write_enabled:
            self._record_audit(
                owner_id=owner_id,
                actor_id=owner_id,
                host_app=effective_app,
                action="record_behavioral_signal",
                scope_kind="source",
                scope_id=source_kind,
                target_ids=[clean_slug],
                consent_generation=consent_gen,
                outcome="denied",
                reason_code="consent_required",
            )
            raise ConsentDeniedError("source and app write consent required for behavioral signal")
        if source_kind == "messenger":
            conv_grant = self.consent_store.get_consent(owner_id, "conversation", source_id)
            if conv_grant.ai_mode != "save":
                raise ConsentDeniedError("messenger conversation ai_mode must be 'save'")

        if pre_write(f"{topic_slug} {option_key}") is not None:
            self._record_audit(
                owner_id=owner_id,
                actor_id=owner_id,
                host_app=effective_app,
                action="record_behavioral_signal",
                scope_kind="source",
                scope_id=source_kind,
                target_ids=[clean_slug],
                consent_generation=consent_gen,
                outcome="quarantined",
                reason_code="sensitive_signal_blocked",
            )
            return {"qualified": False, "promoted_fact_id": None, "quarantined": True}

        sig_id = f"sig_{uuid.uuid4().hex[:12]}"
        with self._lock:
            self._db.execute(
                """
                INSERT INTO cs_two_visit_signals (
                    id, owner_id, source_kind, source_id, topic_slug, option_key,
                    visit_at, weight, promoted_fact_id, erased_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
                """,
                (sig_id, owner_id, source_kind, source_id, clean_slug, option_key, at, sig_weight),
            )
            self._db.commit()

            rows = self._db.execute(
                """
                SELECT id, visit_at, option_key, promoted_fact_id
                FROM cs_two_visit_signals
                WHERE owner_id = ? AND topic_slug = ? AND erased_at IS NULL
                ORDER BY visit_at ASC
                """,
                (owner_id, clean_slug),
            ).fetchall()

        visit_dts = [_parse_iso(str(r[1])) for r in rows]
        distinct_days = len({dt.date() for dt in visit_dts})
        span = (max(visit_dts) - min(visit_dts)) if len(visit_dts) >= 2 else timedelta(0)
        qualified = len(rows) >= 2 and (span >= timedelta(hours=6) or distinct_days >= 2)
        if not qualified:
            return {"qualified": False, "promoted_fact_id": None, "visit_count": len(rows)}

        existing_fid = next((str(r[3]) for r in rows if r[3]), None)
        if existing_fid:
            with self._lock:
                self._db.execute(
                    "UPDATE cs_two_visit_signals SET promoted_fact_id = ? WHERE id = ?",
                    (existing_fid, sig_id),
                )
                self._db.execute(
                    "DELETE FROM cs_interest_projection_cache WHERE owner_id = ?",
                    (owner_id,),
                )
                self._db.commit()
            return {"qualified": True, "promoted_fact_id": existing_fid, "visit_count": len(rows)}

        # Promote to hypothesis in temporal_memory with synthetic signal record evidence.
        self.client.ensure_owner(owner_id, label=owner_id, kind="real")
        signal_record_id = f"cmsig:{sig_id}"
        topic_label = clean_slug.replace("-", " ").replace("_", " ").strip()
        fact_text = f"I noticed recurring interest in {topic_label}"
        res = self.client.upsert_record_and_enqueue(
            owner_id,
            record_id=signal_record_id,
            source=source_id,
            at=at,
            author=owner_id,
            text=f"Repeated interest signal in {topic_label}",
            enqueue="none",
            direct_fact={
                "text": fact_text,
                "subject_path": f"interests/{clean_slug}",
                "valid_from": at,
                "provenance": "inferred",
                "status": "hypothesis",
                "evidence": [signal_record_id],
            },
        )
        promoted_fids = [str(fid) for fid in (res.get("fact_ids") or [])]
        promoted_fact_id = promoted_fids[0] if promoted_fids else None
        now_iso = _now_iso()
        if promoted_fact_id:
            self._upsert_record_ref(
                owner_id=owner_id,
                record_id=signal_record_id,
                source_kind=source_kind,
                source_id=source_id,
                host_app=effective_app,
                author_is_owner=True,
                consent_generation=consent_gen,
                created_at=now_iso,
            )
            with self._lock:
                self._db.execute(
                    """
                    UPDATE cs_two_visit_signals
                    SET promoted_fact_id = ?
                    WHERE owner_id = ? AND topic_slug = ? AND erased_at IS NULL
                    """,
                    (promoted_fact_id, owner_id, clean_slug),
                )
                self._db.execute(
                    "DELETE FROM cs_interest_projection_cache WHERE owner_id = ?",
                    (owner_id,),
                )
                self._db.commit()

        self._record_audit(
            owner_id=owner_id,
            actor_id=owner_id,
            host_app=effective_app,
            action="promote_two_visit_hypothesis",
            scope_kind="source",
            scope_id=source_kind,
            target_ids=[clean_slug, *(promoted_fids)],
            consent_generation=consent_gen,
            outcome="ok",
            receipt={"qualified": True, "promoted_fact_id": promoted_fact_id, "visit_count": len(rows)},
        )
        return {
            "qualified": True,
            "promoted_fact_id": promoted_fact_id,
            "record_id": signal_record_id,
            "visit_count": len(rows),
        }

    def resolve_fact(
        self,
        principal: VerifiedPrincipal,
        fact_id: str,
        *,
        action: FactResolutionAction,
        host_app: AppId,
        new_text: str | None = None,
        valid_from: str | None = None,
    ) -> dict[str, Any]:
        """Confirm, edit, supersede, or reject a fact and synchronously wipe derived projection cache."""
        owner_id = _require_app_principal(principal, host_app)
        if action not in FACT_RESOLUTION_ACTIONS:
            raise MemoryBridgeError(f"invalid resolution action: {action!r}", code="invalid_action", status_code=422)
        if action in ("confirm", "edit", "supersede") and principal.is_minor_protected:
            raise MinorProtectionError("minor-protected account cannot confirm or edit memory facts")

        if action in ("edit", "supersede") and new_text is not None:
            hit = pre_write(new_text)
            if hit is not None:
                self._record_audit(
                    owner_id=owner_id,
                    actor_id=owner_id,
                    host_app=host_app,
                    action=f"resolve_fact.{action}",
                    scope_kind="app",
                    scope_id=host_app,
                    target_ids=[fact_id],
                    consent_generation=self.consent_store.get_consent(owner_id, "app", host_app).generation,
                    outcome="quarantined",
                    reason_code=f"sensitive_{hit}",
                    receipt={"category": hit},
                )
                raise SensitiveContentError(hit)

        res = dict(self.client.resolve_fact(
            owner_id,
            fact_id,
            action=action,
            new_text=new_text,
            valid_from=valid_from,
        ))
        old_fact = res.get("old_fact")
        if isinstance(old_fact, dict) and old_fact.get("status"):
            # Newer engines return the resolved fact's own status explicitly (old_fact / new_fact).
            res["status"] = old_fact["status"]
        elif action in ("edit", "supersede") and res.get("new_fact_id"):
            # Older engines report the NEW fact's status ("active") next to the OLD fact_id; the contract (and the
            # fake) report the status of the fact_id that was resolved: superseded.
            res["status"] = "superseded"
        now_iso = _now_iso()
        with self._lock:
            if action == "reject":
                self._db.execute(
                    """
                    UPDATE cs_two_visit_signals
                    SET erased_at = ?
                    WHERE owner_id = ? AND promoted_fact_id = ? AND erased_at IS NULL
                    """,
                    (now_iso, owner_id, fact_id),
                )
            self._db.execute(
                "DELETE FROM cs_interest_projection_cache WHERE owner_id = ?",
                (owner_id,),
            )
            self._db.commit()

        app_grant = self.consent_store.get_consent(owner_id, "app", host_app)
        self._record_audit(
            owner_id=owner_id,
            actor_id=owner_id,
            host_app=host_app,
            action=f"resolve_fact.{action}",
            scope_kind="app",
            scope_id=host_app,
            target_ids=[fact_id, *([res["new_fact_id"]] if res.get("new_fact_id") else [])],
            consent_generation=app_grant.generation,
            outcome="ok",
            receipt={"action": action, "status": res.get("status"), "new_fact_id": res.get("new_fact_id")},
        )
        return res

    # ------------------------------------------------------------ read helpers
    def _record_ref_map(self, owner_id: str) -> dict[str, tuple[str, str]]:
        with self._lock:
            rows = self._db.execute(
                """
                SELECT record_id, source_kind, source_id
                FROM cs_memory_record_refs
                WHERE owner_id = ? AND erased_at IS NULL
                """,
                (owner_id,),
            ).fetchall()
        return {str(r[0]): (str(r[1]), str(r[2])) for r in rows}

    def _source_consented_for_quest(
        self,
        owner_id: str,
        source_id: str,
        source_cache: dict[str, ConsentGrant],
        conv_cache: dict[str, ConsentGrant],
    ) -> bool:
        src_kind = _source_kind_from_source_id(source_id)
        if not src_kind:
            return False
        s_grant = source_cache.get(src_kind)
        if s_grant is None:
            s_grant = self.consent_store.get_consent(owner_id, "source", src_kind)
            source_cache[src_kind] = s_grant
        if not s_grant.enabled:
            return False
        if src_kind == "messenger":
            c_grant = conv_cache.get(source_id)
            if c_grant is None:
                c_grant = self.consent_store.get_consent(owner_id, "conversation", source_id)
                conv_cache[source_id] = c_grant
            return c_grant.ai_mode == "save"
        return True

    def _fact_source_index(self, owner_id: str) -> dict[str, dict[str, Any]]:
        """Map fact_id -> search_facts metadata (sources, evidence, status, etc.)."""
        all_facts = self.client.search_facts(owner_id, "", limit=500)
        return {str(f.get("id")): f for f in all_facts if f.get("id")}

    def _resolve_fact_sources(
        self,
        fact_dict: dict[str, Any],
        ref_map: dict[str, tuple[str, str]],
        fact_index: dict[str, dict[str, Any]],
    ) -> tuple[list[str], list[str]]:
        fid = str(fact_dict.get("id") or fact_dict.get("fact_id") or "")
        indexed = fact_index.get(fid, {})
        evidence_ids = [
            str(rid)
            for rid in (fact_dict.get("evidence") or indexed.get("evidence") or [])
            if rid
        ]
        source_ids: list[str] = []
        for s in (fact_dict.get("sources") or indexed.get("sources") or []):
            s_str = str(s)
            if s_str and s_str not in source_ids:
                source_ids.append(s_str)
        for rid in evidence_ids:
            ref = ref_map.get(rid)
            if ref is not None and ref[1] not in source_ids:
                source_ids.append(ref[1])
        if not source_ids and fid:
            try:
                why = self.client.get_why_fact(owner_id, fid)
            except MemoryBridgeError:
                why = {}
            for ev in why.get("evidence") or []:
                ev_id = str(ev.get("id") or "")
                if ev_id and ev_id not in evidence_ids:
                    evidence_ids.append(ev_id)
                ev_src = str(ev.get("source") or "")
                if ev_src and ev_src not in source_ids:
                    source_ids.append(ev_src)
        return (evidence_ids, source_ids)

    def _to_fact_view(
        self,
        fact_dict: dict[str, Any],
        *,
        evidence_ids: list[str],
        source_ids: list[str],
    ) -> MemoryFactView:
        fid = str(fact_dict.get("id") or fact_dict.get("fact_id") or "")
        provenance_raw = str(fact_dict.get("provenance") or "user_supplied")
        status_raw = str(fact_dict.get("status") or "active")
        demo_data = bool(fact_dict.get("demo_data"))
        trust_tier, prefix = _trust_and_prefix(provenance_raw, status_raw, demo_data)
        actions = list(fact_dict.get("actions") or (
            ["Confirm", "Edit", "Not true", "Forget"] if status_raw == "hypothesis" else ["Edit", "Forget"]
        ))
        return MemoryFactView(
            fact_id=fid,
            text=str(fact_dict.get("text") or ""),
            text_orig=fact_dict.get("text_orig"),
            subject_id=str(fact_dict.get("subject_id") or ""),
            subject_path=str(fact_dict.get("subject_path") or fact_dict.get("subject_id") or "general"),
            valid_from=str(fact_dict.get("valid_from") or ""),
            valid_to=fact_dict.get("valid_to"),
            status=status_raw,  # type: ignore[arg-type]
            superseded_by=fact_dict.get("superseded_by"),
            provenance=provenance_raw,  # type: ignore[arg-type]
            trust_tier=trust_tier,
            display_prefix=prefix,
            evidence_record_ids=evidence_ids,
            source_ids=source_ids,
            as_of=str(fact_dict.get("as_of") or fact_dict.get("valid_from") or _now_iso()),
            demo_data=demo_data,
            actions=actions,
        )

    # ----------------------------------------------------------- Quest reads
    def _require_quest_read_grant(self, principal: VerifiedPrincipal) -> tuple[str, ConsentGrant]:
        owner_id = _require_app_principal(principal, "quest")
        app_grant = self.consent_store.get_consent(owner_id, "app", "quest")
        if not app_grant.read_enabled:
            self._record_audit(
                owner_id=owner_id,
                actor_id=owner_id,
                host_app="quest",
                action="read_quest",
                scope_kind="app",
                scope_id="quest",
                target_ids=[],
                consent_generation=app_grant.generation,
                outcome="denied",
                reason_code="quest_read_consent_required",
            )
            raise ConsentDeniedError("quest read consent required")
        return (owner_id, app_grant)

    def read_quest_context(
        self,
        principal: VerifiedPrincipal,
        query: str,
        *,
        max_tokens: int = 1500,
    ) -> dict[str, Any]:
        """Return Quest context pack filtered to consented sources with attribution prefixes."""
        owner_id, app_grant = self._require_quest_read_grant(principal)
        pack = self.client.context_pack(owner_id, query, max_tokens=max_tokens)
        ref_map = self._record_ref_map(owner_id)
        fact_index = self._fact_source_index(owner_id)
        source_cache: dict[str, ConsentGrant] = {}
        conv_cache: dict[str, ConsentGrant] = {}

        visible_facts: list[dict[str, Any]] = []
        visible_fids: set[str] = set()
        for f in pack.get("facts") or []:
            fid = str(f.get("id") or "")
            _, source_ids = self._resolve_fact_sources(f, ref_map, fact_index)
            consented_sources = [
                s for s in source_ids
                if self._source_consented_for_quest(owner_id, s, source_cache, conv_cache)
            ]
            if not consented_sources:
                continue
            prov = str(f.get("provenance") or "user_supplied")
            status = str(f.get("status") or "active")
            is_demo = bool(f.get("demo_data"))
            trust_tier, prefix = _trust_and_prefix(prov, status, is_demo)
            enriched = dict(f)
            enriched["trust_tier"] = trust_tier
            enriched["display_prefix"] = prefix
            enriched["source_ids"] = consented_sources
            visible_facts.append(enriched)
            visible_fids.add(fid)

        open_changes = [
            ch for ch in (pack.get("open_changes") or [])
            if str(ch.get("fact_id") or "") in visible_fids
        ]
        out = dict(pack)
        out["facts"] = visible_facts
        out["open_changes"] = open_changes
        self._record_audit(
            owner_id=owner_id,
            actor_id=owner_id,
            host_app="quest",
            action="read_quest_context",
            scope_kind="app",
            scope_id="quest",
            target_ids=sorted(visible_fids),
            consent_generation=app_grant.generation,
            outcome="ok",
            receipt={"fact_count": len(visible_facts)},
        )
        return out

    def read_quest_timeline(
        self,
        principal: VerifiedPrincipal,
        *,
        limit: int = 100,
    ) -> list[MemoryFactView]:
        """Return Quest timeline facts filtered to consented sources."""
        owner_id, app_grant = self._require_quest_read_grant(principal)
        tl = self.client.get_timeline(owner_id, limit=limit)
        ref_map = self._record_ref_map(owner_id)
        fact_index = self._fact_source_index(owner_id)
        source_cache: dict[str, ConsentGrant] = {}
        conv_cache: dict[str, ConsentGrant] = {}

        views: list[MemoryFactView] = []
        for item in tl.get("items") or []:
            evidence_ids, source_ids = self._resolve_fact_sources(item, ref_map, fact_index)
            consented_sources = [
                s for s in source_ids
                if self._source_consented_for_quest(owner_id, s, source_cache, conv_cache)
            ]
            if not consented_sources:
                continue
            views.append(self._to_fact_view(item, evidence_ids=evidence_ids, source_ids=consented_sources))
        self._record_audit(
            owner_id=owner_id,
            actor_id=owner_id,
            host_app="quest",
            action="read_quest_timeline",
            scope_kind="app",
            scope_id="quest",
            target_ids=[v.fact_id for v in views],
            consent_generation=app_grant.generation,
            outcome="ok",
            receipt={"count": len(views)},
        )
        return views

    def read_quest_hypotheses(
        self,
        principal: VerifiedPrincipal,
    ) -> list[MemoryFactView]:
        """Return Quest hypotheses ('I noticed ...') filtered to consented sources."""
        owner_id, app_grant = self._require_quest_read_grant(principal)
        hyps = self.client.get_hypotheses(owner_id)
        ref_map = self._record_ref_map(owner_id)
        fact_index = self._fact_source_index(owner_id)
        source_cache: dict[str, ConsentGrant] = {}
        conv_cache: dict[str, ConsentGrant] = {}

        views: list[MemoryFactView] = []
        for item in hyps.get("hypotheses") or []:
            evidence_ids, source_ids = self._resolve_fact_sources(item, ref_map, fact_index)
            consented_sources = [
                s for s in source_ids
                if self._source_consented_for_quest(owner_id, s, source_cache, conv_cache)
            ]
            if not consented_sources:
                continue
            enriched = dict(item)
            enriched.setdefault("status", "hypothesis")
            views.append(self._to_fact_view(enriched, evidence_ids=evidence_ids, source_ids=consented_sources))
        self._record_audit(
            owner_id=owner_id,
            actor_id=owner_id,
            host_app="quest",
            action="read_quest_hypotheses",
            scope_kind="app",
            scope_id="quest",
            target_ids=[v.fact_id for v in views],
            consent_generation=app_grant.generation,
            outcome="ok",
            receipt={"count": len(views)},
        )
        return views

    def _fact_hidden_by_revoked_source(self, owner_id: str, fact_id: str) -> bool:
        """Return True if owner_id previously wrote fact_id under a source whose consent is now revoked."""
        events = self.audit_store.list_events(owner_id, limit=500)
        for ev in events:
            if ev.get("action") == "write_consented" and fact_id in (ev.get("target_ids") or []):
                src_kind = ev.get("scope_id")
                if isinstance(src_kind, str) and src_kind in SOURCE_KINDS:
                    if not self.consent_store.get_consent(owner_id, "source", src_kind).enabled:
                        return True
        return False

    def read_why_fact(
        self,
        principal: VerifiedPrincipal,
        fact_id: str,
        *,
        host_app: AppId,
    ) -> dict[str, Any]:
        """Return evidence provenance for a fact, filtered to consented sources."""
        owner_id = _require_app_principal(principal, host_app)
        app_grant = self.consent_store.get_consent(owner_id, "app", host_app)
        if not app_grant.read_enabled:
            raise ConsentDeniedError(f"{host_app} read consent required")

        try:
            why = self.client.get_why_fact(owner_id, fact_id)
        except MemoryBridgeError as exc:
            if exc.status_code == 404 and self._fact_hidden_by_revoked_source(owner_id, fact_id):
                raise ConsentDeniedError("fact evidence source consent is revoked or denied") from exc
            raise
        source_cache: dict[str, ConsentGrant] = {}
        conv_cache: dict[str, ConsentGrant] = {}
        raw_evidence = list(why.get("evidence") or [])
        filtered_evidence: list[dict[str, Any]] = []
        for ev in raw_evidence:
            src_id = str(ev.get("source") or "")
            if host_app == "messenger":
                src_kind = _source_kind_from_source_id(src_id)
                if src_kind == "messenger":
                    s_grant = self.consent_store.get_consent(owner_id, "source", "messenger")
                    c_grant = self.consent_store.get_consent(owner_id, "conversation", src_id)
                    if s_grant.enabled and c_grant.ai_mode in ("session", "save"):
                        filtered_evidence.append(ev)
                elif app_grant.allow_cross_source_recall and self._source_consented_for_quest(
                    owner_id, src_id, source_cache, conv_cache
                ):
                    filtered_evidence.append(ev)
            elif host_app == "community":
                if _source_kind_from_source_id(src_id) == "community":
                    s_grant = self.consent_store.get_consent(owner_id, "source", "community")
                    if s_grant.enabled:
                        filtered_evidence.append(ev)
            else:
                if self._source_consented_for_quest(owner_id, src_id, source_cache, conv_cache):
                    filtered_evidence.append(ev)

        if not filtered_evidence:
            raise ConsentDeniedError("fact evidence source consent is revoked or denied")

        trust_tier, prefix = _trust_and_prefix(
            str(why.get("provenance") or "user_supplied"),
            str(why.get("status") or "active"),
            bool(why.get("demo_data")),
        )
        out = dict(why)
        out["evidence"] = filtered_evidence
        out["trust_tier"] = trust_tier
        out["display_prefix"] = prefix
        return out

    # ------------------------------------------------------- Community reads
    def read_community_interest_features(
        self,
        principal: VerifiedPrincipal,
        *,
        limit: int = 20,
    ) -> list[InterestFeature]:
        """Return strictly projected InterestFeature DTOs for Community (empty for minors or unconsented export)."""
        owner_id = _require_app_principal(principal, "community")

        # D11 hard fence: minor-protected accounts receive zero cross-app personalisation.
        if principal.is_minor_protected:
            return []

        app_grant = self.consent_store.get_consent(owner_id, "app", "community")
        if not app_grant.read_enabled:
            self._record_audit(
                owner_id=owner_id,
                actor_id=owner_id,
                host_app="community",
                action="read_community_interest_features",
                scope_kind="app",
                scope_id="community",
                target_ids=[],
                consent_generation=app_grant.generation,
                outcome="denied",
                reason_code="community_read_consent_required",
            )
            raise ConsentDeniedError("community read consent required")

        if not app_grant.allow_interest_export:
            return []

        lim = max(1, min(int(limit), 100))
        consent_sig = self.consent_store.consent_generation_sig(owner_id)
        facts_version_map = getattr(self.client, "facts_version", None)
        facts_version = int(facts_version_map.get(owner_id, 0)) if isinstance(facts_version_map, dict) else 0

        with self._lock:
            cached = self._db.execute(
                """
                SELECT consent_generation_sig, facts_version, features_json
                FROM cs_interest_projection_cache
                WHERE owner_id = ?
                """,
                (owner_id,),
            ).fetchone()
        # Without a client-side facts_version (live HTTP client) the cache cannot be proven fresh: recompute.
        cache_provable = isinstance(facts_version_map, dict)
        if cache_provable and cached is not None and cached[0] == consent_sig and int(cached[1]) == facts_version:
            raw_items = json.loads(cached[2]) if isinstance(cached[2], str) else (cached[2] or [])
            return [InterestFeature(**item) for item in raw_items[:lim]]

        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        facts = self.client.search_facts(owner_id, "", limit=500)
        ref_map = self._record_ref_map(owner_id)
        source_cache: dict[str, ConsentGrant] = {}
        conv_cache: dict[str, ConsentGrant] = {}

        aggregated: dict[tuple[str, str], dict[str, Any]] = {}
        for fact in facts:
            if fact.get("erased_at") is not None:
                continue
            status = str(fact.get("status") or "active")
            if status in ("superseded", "ended", "history"):
                continue
            if fact.get("sensitive_cat") is not None:
                continue
            fact_text = str(fact.get("text") or "")
            if pre_write(fact_text) is not None:
                continue
            if fact.get("text_orig") and pre_write(str(fact.get("text_orig"))) is not None:
                continue

            _, source_ids = self._resolve_fact_sources(fact, ref_map, {})
            exportable_sources: list[tuple[str, str, int]] = []
            for src_id in source_ids:
                src_kind = _source_kind_from_source_id(src_id)
                if not src_kind:
                    continue
                s_grant = source_cache.get(src_kind)
                if s_grant is None:
                    s_grant = self.consent_store.get_consent(owner_id, "source", src_kind)
                    source_cache[src_kind] = s_grant
                if not (s_grant.enabled and s_grant.allow_interest_export):
                    continue
                eff_gen = max(app_grant.generation, s_grant.generation)
                if src_kind == "messenger":
                    c_grant = conv_cache.get(src_id)
                    if c_grant is None:
                        c_grant = self.consent_store.get_consent(owner_id, "conversation", src_id)
                        conv_cache[src_id] = c_grant
                    if not (c_grant.ai_mode == "save" and c_grant.allow_interest_export):
                        continue
                    eff_gen = max(eff_gen, c_grant.generation)
                exportable_sources.append((src_kind, src_id, eff_gen))

            if not exportable_sources:
                continue

            src_kind, _, eff_gen = exportable_sources[0]
            topic_slug = _safe_topic_slug(str(fact.get("subject_path") or fact.get("subject_id") or "general"))
            topic_label = topic_slug.replace("-", " ").replace("_", " ").title()
            if pre_write(topic_label) is not None:
                continue

            source_app = _source_app_for_kind(src_kind)
            provenance = str(fact.get("provenance") or "user_supplied")
            confidence_tier: Literal["confirmed", "qualified_hypothesis"] = (
                "confirmed"
                if status == "active" and provenance in ("user_supplied", "provider_confirmed", "demo_fixture")
                else "qualified_hypothesis"
            )

            valid_from_str = str(fact.get("valid_from") or now_iso)
            try:
                age_days = max(0.0, (now_dt - _parse_iso(valid_from_str)).total_seconds() / 86400.0)
            except MemoryBridgeError:
                age_days = 0.0
            if confidence_tier == "confirmed":
                # R-ND: user_supplied / confirmed facts do not decay away.
                weight = 0.95
            else:
                weight = max(_DECAY_FLOOR, min(1.0, 0.70 * math.exp(-_DECAY_LAMBDA * age_days)))

            fid = str(fact.get("id") or "")
            token_digest = hashlib.sha256(f"{owner_id}:{fid}:{eff_gen}".encode("utf-8")).hexdigest()[:16]
            why_this_token = f"why_{token_digest}"
            source_app_title = source_app.title()
            why_this_text = (
                f"Based on your confirmed {topic_label} interest from {source_app_title}"
                if confidence_tier == "confirmed"
                else f"Based on repeated {topic_label} activity in {source_app_title}"
            )
            is_demo = bool(fact.get("demo_data")) or provenance == "demo_fixture"

            key = (topic_slug, source_app)
            existing = aggregated.get(key)
            if existing is None or weight > existing["weight"]:
                aggregated[key] = {
                    "feature_id": f"feat_{topic_slug}_{source_app}",
                    "topic_slug": topic_slug,
                    "topic_label": topic_label,
                    "weight": round(float(weight), 4),
                    "confidence_tier": confidence_tier,
                    "source_app": source_app,
                    "why_this_token": why_this_token,
                    "why_this_text": why_this_text,
                    "as_of": valid_from_str,
                    "consent_generation": eff_gen,
                    "demo_data": is_demo,
                }

        items = sorted(aggregated.values(), key=lambda x: (-x["weight"], x["topic_slug"]))
        with self._lock:
            self._db.execute(
                """
                INSERT INTO cs_interest_projection_cache (
                    owner_id, consent_generation_sig, facts_version, features_json, computed_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(owner_id) DO UPDATE SET
                    consent_generation_sig = excluded.consent_generation_sig,
                    facts_version = excluded.facts_version,
                    features_json = excluded.features_json,
                    computed_at = excluded.computed_at
                """,
                (owner_id, consent_sig, facts_version, json.dumps(items), now_iso),
            )
            self._db.commit()

        features = [InterestFeature(**item) for item in items[:lim]]
        self._record_audit(
            owner_id=owner_id,
            actor_id=owner_id,
            host_app="community",
            action="read_community_interest_features",
            scope_kind="app",
            scope_id="community",
            target_ids=[f.feature_id for f in features],
            consent_generation=app_grant.generation,
            outcome="ok",
            receipt={"count": len(features)},
        )
        return features

    def read_community_own_activity(
        self,
        principal: VerifiedPrincipal,
        *,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return owner's own Community-origin activity refs only (zero Quest/Gmail/Messenger data)."""
        owner_id = _require_app_principal(principal, "community")
        app_grant = self.consent_store.get_consent(owner_id, "app", "community")
        if not app_grant.read_enabled:
            raise ConsentDeniedError("community read consent required")

        lim = max(1, min(int(limit), 200))
        with self._lock:
            ref_rows = self._db.execute(
                """
                SELECT record_id, source_id, created_at
                FROM cs_memory_record_refs
                WHERE owner_id = ? AND source_kind = 'community' AND erased_at IS NULL
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (owner_id, lim),
            ).fetchall()
            sig_rows = self._db.execute(
                """
                SELECT id, source_id, topic_slug, visit_at, promoted_fact_id
                FROM cs_two_visit_signals
                WHERE owner_id = ? AND source_kind = 'community' AND erased_at IS NULL
                ORDER BY visit_at DESC
                LIMIT ?
                """,
                (owner_id, lim),
            ).fetchall()

        activities: list[dict[str, Any]] = []
        for rid, src_id, created_at in ref_rows:
            rid_str = str(rid)
            kind = (
                "saved_discussion"
                if rid_str.startswith("cmsave:")
                else ("authored_post" if rid_str.startswith("cmpost:") else "community_signal")
            )
            activities.append(
                {
                    "record_id": rid_str,
                    "source_kind": "community",
                    "source_id": str(src_id),
                    "kind": kind,
                    "label": "saved from Community, topic only",
                    "created_at": str(created_at),
                }
            )
        for sid, src_id, topic_slug, visit_at, promoted_fid in sig_rows:
            activities.append(
                {
                    "record_id": f"cmsig:{sid}",
                    "source_kind": "community",
                    "source_id": str(src_id),
                    "topic_slug": str(topic_slug),
                    "promoted_fact_id": promoted_fid,
                    "kind": "topic_signal",
                    "label": "saved from Community, topic only",
                    "created_at": str(visit_at),
                }
            )
        activities.sort(key=lambda x: x["created_at"], reverse=True)
        return activities[:lim]

    # ------------------------------------------------------- Messenger reads
    def read_messenger_chat_scope(
        self,
        principal: VerifiedPrincipal,
        conversation_id: str,
        *,
        group_consent: GroupConsentSnapshot,
        query: str = "",
        limit: int = 20,
    ) -> list[MemoryFactView]:
        """Return Messenger facts strictly scoped to `messenger:<conversation_id>`."""
        owner_id = _require_app_principal(principal, "messenger")
        conv_scope_id = canonical_conversation_scope_id(conversation_id)
        conv_id = conv_scope_id[len("messenger:") :]

        app_grant = self.consent_store.get_consent(owner_id, "app", "messenger")
        source_grant = self.consent_store.get_consent(owner_id, "source", "messenger")
        conv_grant = self.consent_store.get_consent(owner_id, "conversation", conv_scope_id)
        eff_gen = max(app_grant.generation, source_grant.generation, conv_grant.generation)

        if not (app_grant.read_enabled and source_grant.enabled):
            self._record_audit(
                owner_id=owner_id,
                actor_id=owner_id,
                host_app="messenger",
                action="read_messenger_chat_scope",
                scope_kind="conversation",
                scope_id=conv_scope_id,
                target_ids=[],
                consent_generation=eff_gen,
                outcome="denied",
                reason_code="messenger_read_consent_required",
            )
            raise ConsentDeniedError("messenger app and source consent required")

        if conv_grant.ai_mode not in ("session", "save"):
            self._record_audit(
                owner_id=owner_id,
                actor_id=owner_id,
                host_app="messenger",
                action="read_messenger_chat_scope",
                scope_kind="conversation",
                scope_id=conv_scope_id,
                target_ids=[],
                consent_generation=eff_gen,
                outcome="denied",
                reason_code=f"conversation_ai_mode_{conv_grant.ai_mode}",
            )
            raise ConsentDeniedError("messenger conversation ai_mode is off")

        if (
            group_consent.conversation_id != conv_id
            or not group_consent.caller_is_member
            or not group_consent.all_active_members_ai_enabled
        ):
            self._record_audit(
                owner_id=owner_id,
                actor_id=owner_id,
                host_app="messenger",
                action="read_messenger_chat_scope",
                scope_kind="conversation",
                scope_id=conv_scope_id,
                target_ids=[],
                consent_generation=eff_gen,
                outcome="denied",
                reason_code="group_consent_denied",
            )
            raise ConsentDeniedError("messenger group consent check failed")

        raw_facts = self.client.search_facts(
            owner_id,
            query,
            limit=max(1, int(limit)),
            source_prefix=conv_scope_id,
        )
        ref_map = self._record_ref_map(owner_id)
        views: list[MemoryFactView] = []
        for f in raw_facts:
            evidence_ids, source_ids = self._resolve_fact_sources(f, ref_map, {})
            if not source_ids or not all(s == conv_scope_id for s in source_ids):
                continue
            views.append(self._to_fact_view(f, evidence_ids=evidence_ids, source_ids=source_ids))

        self._record_audit(
            owner_id=owner_id,
            actor_id=owner_id,
            host_app="messenger",
            action="read_messenger_chat_scope",
            scope_kind="conversation",
            scope_id=conv_scope_id,
            target_ids=[v.fact_id for v in views],
            consent_generation=eff_gen,
            outcome="ok",
            receipt={"count": len(views)},
        )
        return views

    def read_messenger_owner_recall(
        self,
        principal: VerifiedPrincipal,
        conversation_id: str,
        *,
        query: str,
        limit: int = 10,
    ) -> list[MemoryFactView]:
        """Opt-in private owner recall inside Messenger across consented sources."""
        owner_id = _require_app_principal(principal, "messenger")
        conv_scope_id = canonical_conversation_scope_id(conversation_id)
        app_grant = self.consent_store.get_consent(owner_id, "app", "messenger")
        conv_grant = self.consent_store.get_consent(owner_id, "conversation", conv_scope_id)
        eff_gen = max(app_grant.generation, conv_grant.generation)

        if not (app_grant.read_enabled and app_grant.allow_cross_source_recall):
            raise ConsentDeniedError("messenger cross-source owner recall is disabled")
        if conv_grant.ai_mode not in ("session", "save"):
            raise ConsentDeniedError("messenger conversation ai_mode is off")

        lim = max(1, int(limit))
        raw_facts = self.client.search_facts(owner_id, query, limit=lim * 3)
        ref_map = self._record_ref_map(owner_id)
        source_cache: dict[str, ConsentGrant] = {}
        conv_cache: dict[str, ConsentGrant] = {}
        views: list[MemoryFactView] = []

        for f in raw_facts:
            evidence_ids, source_ids = self._resolve_fact_sources(f, ref_map, {})
            consented_sources: list[str] = []
            for s in source_ids:
                if s == conv_scope_id:
                    s_grant = self.consent_store.get_consent(owner_id, "source", "messenger")
                    if s_grant.enabled:
                        consented_sources.append(s)
                elif self._source_consented_for_quest(owner_id, s, source_cache, conv_cache):
                    consented_sources.append(s)
            if not consented_sources:
                continue
            views.append(self._to_fact_view(f, evidence_ids=evidence_ids, source_ids=consented_sources))
            if len(views) >= lim:
                break

        self._record_audit(
            owner_id=owner_id,
            actor_id=owner_id,
            host_app="messenger",
            action="read_messenger_owner_recall",
            scope_kind="conversation",
            scope_id=conv_scope_id,
            target_ids=[v.fact_id for v in views],
            consent_generation=eff_gen,
            outcome="ok",
            receipt={"count": len(views)},
        )
        return views

    # --------------------------------------------------- forget delegations
    def _require_forget_coordinator(self) -> Any:
        if self._forget_coordinator is None:
            raise MemoryBridgeUnavailable("forget coordinator is not configured")
        return self._forget_coordinator

    def forget_records(
        self,
        principal: VerifiedPrincipal,
        record_ids: list[str],
        *,
        host_app: AppId,
        idempotency_key: str,
    ) -> ForgetReceipt:
        _require_app_principal(principal, host_app)
        return self._require_forget_coordinator().forget_records(
            principal,
            record_ids,
            host_app=host_app,
            idempotency_key=idempotency_key,
        )

    def forget_conversation(
        self,
        principal: VerifiedPrincipal,
        conversation_id: str,
        *,
        idempotency_key: str,
    ) -> ForgetReceipt:
        _require_verified_principal(principal)
        if principal.app_id not in (None, "messenger", "quest"):
            raise ConsentDeniedError(
                f"app session {principal.app_id!r} cannot forget messenger conversation",
                code="app_scope_mismatch",
                status_code=403,
            )
        return self._require_forget_coordinator().forget_conversation(
            principal,
            conversation_id,
            idempotency_key=idempotency_key,
        )

    def forget_source(
        self,
        principal: VerifiedPrincipal,
        source_kind: SourceKind,
        *,
        host_app: AppId,
        idempotency_key: str,
    ) -> ForgetReceipt:
        _require_app_principal(principal, host_app)
        return self._require_forget_coordinator().forget_source(
            principal,
            source_kind,
            host_app=host_app,
            idempotency_key=idempotency_key,
        )

    def forget_fact(
        self,
        principal: VerifiedPrincipal,
        fact_id: str,
        *,
        host_app: AppId,
        idempotency_key: str,
    ) -> ForgetReceipt:
        _require_app_principal(principal, host_app)
        return self._require_forget_coordinator().forget_fact(
            principal,
            fact_id,
            host_app=host_app,
            idempotency_key=idempotency_key,
        )
