"""Immutable, owner-scoped, Rule 9-clean audit store for cs_memory_audit."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta, timezone
import json
import re
import threading
from typing import Any
import uuid

from .models import ConsentDeniedError, MemoryBridgeError
from .schema import ensure_memory_bridge_schema
from .sensitive import pre_write

_VALID_OUTCOMES: frozenset[str] = frozenset({"ok", "denied", "quarantined", "partial", "error"})

_FORBIDDEN_KEY_EXACT: frozenset[str] = frozenset(
    {
        "text",
        "text_orig",
        "raw_text",
        "secret",
        "token",
        "password",
        "passwd",
        "pwd",
        "otp",
        "iban",
        "pin",
        "credential",
        "credentials",
        "api_key",
        "apikey",
        "access_token",
        "refresh_token",
        "session_token",
        "bearer",
        "authorization",
        "cookie",
        "body",
        "content",
        "message",
        "messages",
        "prompt",
        "raw",
        "payload",
    }
)

_SAFE_META_STR_KEYS: frozenset[str] = frozenset(
    {
        "id",
        "idempotency_key",
        "owner_id",
        "actor_id",
        "host_app",
        "action",
        "scope_kind",
        "scope_id",
        "status",
        "outcome",
        "reason_code",
        "recorded_at",
        "created_at",
        "category",
        "quarantine_category",
        "fact_id",
        "record_id",
        "job_id",
    }
)

_REASON_CODE_RE = re.compile(r"^[A-Za-z0-9_.:/-]{1,128}$")


def _is_forbidden_key(key: str) -> bool:
    k = str(key).strip().lower()
    if k in _FORBIDDEN_KEY_EXACT:
        return True
    if any(frag in k for frag in ("secret", "password", "passwd", "credential")):
        return True
    if k.endswith(("_text", "_token", "_body", "_content", "_secret", "_key")) and k != "idempotency_key":
        return True
    if k.startswith(("raw_", "token_")):
        return True
    return False


def _sanitize_value(value: Any, *, key_hint: str = "") -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        if key_hint not in _SAFE_META_STR_KEYS and pre_write(value) is not None:
            return "[redacted]"
        return value
    if isinstance(value, Mapping):
        return _sanitize_mapping(value)
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_sanitize_value(v) for v in value]
    if is_dataclass(value) and not isinstance(value, type):
        return _sanitize_mapping(asdict(value))
    return str(value)


def _sanitize_mapping(data: Mapping[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for raw_k, raw_v in data.items():
        k = str(raw_k)
        if _is_forbidden_key(k):
            continue
        cleaned[k] = _sanitize_value(raw_v, key_hint=k.strip().lower())
    return cleaned


def sanitize_receipt(receipt: Any) -> dict[str, Any]:
    """Strip any raw text, secret, or token fields from an audit receipt (Rule 9)."""
    if receipt is None:
        return {}
    if is_dataclass(receipt) and not isinstance(receipt, type):
        return _sanitize_mapping(asdict(receipt))
    if isinstance(receipt, Mapping):
        return _sanitize_mapping(receipt)
    raise TypeError("receipt must be a mapping, dataclass, or None")


def sanitize_reason_code(reason_code: str | None) -> str | None:
    """Ensure reason_code only records a short category/code token, never raw prose or secrets."""
    if reason_code is None:
        return None
    cleaned = str(reason_code).strip()
    if not cleaned:
        return None
    if not _REASON_CODE_RE.fullmatch(cleaned) or pre_write(cleaned) is not None:
        return "redacted"
    return cleaned


def _decode_json_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if isinstance(raw, str) and raw.strip():
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
    return []


def _decode_json_dict(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str) and raw.strip():
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    return {}


_SELECT_COLS = (
    "id, owner_id, actor_id, host_app, action, scope_kind, scope_id, "
    "target_ids_json, consent_generation, outcome, reason_code, receipt_json, "
    "idempotency_key, created_at"
)


def _row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": row[0],
        "owner_id": row[1],
        "actor_id": row[2],
        "host_app": row[3],
        "action": row[4],
        "scope_kind": row[5],
        "scope_id": row[6],
        "target_ids": _decode_json_list(row[7]),
        "consent_generation": int(row[8]),
        "outcome": row[9],
        "reason_code": row[10],
        "receipt": _decode_json_dict(row[11]),
        "idempotency_key": row[12],
        "created_at": row[13],
    }


class AuditStore:
    """Thread-safe, portable SQL store for immutable cs_memory_audit records."""

    def __init__(self, db: Any, *, lock: threading.RLock | None = None) -> None:
        self._db = db
        self._lock = lock if lock is not None else threading.RLock()
        self._last_ts: datetime | None = None
        ensure_memory_bridge_schema(db, lock=self._lock)

    def _next_timestamp_iso(self) -> str:
        with self._lock:
            now = datetime.now(timezone.utc)
            if self._last_ts is not None and now <= self._last_ts:
                now = self._last_ts + timedelta(microseconds=1)
            self._last_ts = now
            return now.isoformat(timespec="microseconds")

    @staticmethod
    def _normalize_key(idempotency_key: str | None) -> str | None:
        if idempotency_key is None:
            return None
        key = str(idempotency_key).strip()
        return key or None

    def check_idempotency_key(self, owner_id: str, idempotency_key: str | None) -> dict[str, Any] | None:
        """Return existing row for owner_id, or raise ConsentDeniedError if key belongs to another owner."""
        key = self._normalize_key(idempotency_key)
        if key is None:
            return None
        with self._lock:
            row = self._db.execute(
                f"SELECT {_SELECT_COLS} FROM cs_memory_audit WHERE idempotency_key = ?",
                (key,),
            ).fetchone()
            if row is None:
                return None
            existing = _row_to_dict(row)
            if existing["owner_id"] != owner_id:
                raise ConsentDeniedError(
                    "idempotency_key belongs to another owner",
                    code="cross_owner_idempotency_key",
                    status_code=403,
                )
            return existing

    def record_event(
        self,
        *,
        owner_id: str,
        actor_id: str,
        host_app: str,
        action: str,
        scope_kind: str | None = None,
        scope_id: str | None = None,
        target_ids: Iterable[str] = (),
        consent_generation: int = 1,
        outcome: str = "ok",
        reason_code: str | None = None,
        receipt: Any = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Append an immutable audit event into cs_memory_audit (idempotent per owner_id + idempotency_key)."""
        if not owner_id or not str(owner_id).strip():
            raise MemoryBridgeError("owner_id is required", code="missing_owner", status_code=400)
        if not actor_id or not str(actor_id).strip():
            raise MemoryBridgeError("actor_id is required", code="missing_actor", status_code=400)
        if outcome not in _VALID_OUTCOMES:
            raise MemoryBridgeError(f"invalid audit outcome: {outcome}", code="invalid_outcome", status_code=400)

        norm_key = self._normalize_key(idempotency_key)
        clean_targets = [str(tid) for tid in target_ids]
        clean_receipt = sanitize_receipt(receipt)
        clean_reason = sanitize_reason_code(reason_code)

        with self._lock:
            existing = self.check_idempotency_key(owner_id, norm_key)
            if existing is not None:
                return existing

            event_id = f"aud_{uuid.uuid4().hex}"
            created_at = self._next_timestamp_iso()
            self._db.execute(
                """
                INSERT INTO cs_memory_audit (
                    id, owner_id, actor_id, host_app, action, scope_kind, scope_id,
                    target_ids_json, consent_generation, outcome, reason_code,
                    receipt_json, idempotency_key, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """.strip(),
                (
                    event_id,
                    owner_id,
                    actor_id,
                    host_app,
                    action,
                    scope_kind,
                    scope_id,
                    json.dumps(clean_targets, ensure_ascii=False),
                    int(consent_generation),
                    outcome,
                    clean_reason,
                    json.dumps(clean_receipt, ensure_ascii=False),
                    norm_key,
                    created_at,
                ),
            )
            self._db.commit()
            return {
                "id": event_id,
                "owner_id": owner_id,
                "actor_id": actor_id,
                "host_app": host_app,
                "action": action,
                "scope_kind": scope_kind,
                "scope_id": scope_id,
                "target_ids": clean_targets,
                "consent_generation": int(consent_generation),
                "outcome": outcome,
                "reason_code": clean_reason,
                "receipt": clean_receipt,
                "idempotency_key": norm_key,
                "created_at": created_at,
            }

    def record_reconciliation(
        self,
        *,
        owner_id: str,
        actor_id: str,
        host_app: str,
        action: str,
        scope_kind: str | None,
        scope_id: str | None,
        target_ids: Iterable[str],
        consent_generation: int,
        reason_code: str | None,
        receipt: Any,
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Append a completion audit row for a prior pending_reconciliation event without altering prior rows' payloads."""
        norm_key = self._normalize_key(idempotency_key)
        if norm_key is None:
            raise MemoryBridgeError("idempotency_key is required for reconciliation", status_code=400)

        clean_targets = [str(tid) for tid in target_ids]
        clean_receipt = sanitize_receipt(receipt)
        clean_reason = sanitize_reason_code(reason_code)

        with self._lock:
            existing = self.check_idempotency_key(owner_id, norm_key)
            if existing is None:
                return self.record_event(
                    owner_id=owner_id,
                    actor_id=actor_id,
                    host_app=host_app,
                    action=action,
                    scope_kind=scope_kind,
                    scope_id=scope_id,
                    target_ids=clean_targets,
                    consent_generation=consent_generation,
                    outcome="ok",
                    reason_code=clean_reason,
                    receipt=clean_receipt,
                    idempotency_key=norm_key,
                )

            if existing["receipt"].get("status") != "pending_reconciliation":
                return existing

            # Move the active idempotency pointer off the historical partial row so the completion
            # row becomes canonical while preserving the partial attempt row in cs_memory_audit.
            self._db.execute(
                "UPDATE cs_memory_audit SET idempotency_key = NULL WHERE id = ? AND owner_id = ?",
                (existing["id"], owner_id),
            )
            event_id = f"aud_{uuid.uuid4().hex}"
            created_at = self._next_timestamp_iso()
            self._db.execute(
                """
                INSERT INTO cs_memory_audit (
                    id, owner_id, actor_id, host_app, action, scope_kind, scope_id,
                    target_ids_json, consent_generation, outcome, reason_code,
                    receipt_json, idempotency_key, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """.strip(),
                (
                    event_id,
                    owner_id,
                    actor_id,
                    host_app,
                    action,
                    scope_kind,
                    scope_id,
                    json.dumps(clean_targets, ensure_ascii=False),
                    int(consent_generation),
                    "ok",
                    clean_reason,
                    json.dumps(clean_receipt, ensure_ascii=False),
                    norm_key,
                    created_at,
                ),
            )
            self._db.commit()
            return {
                "id": event_id,
                "owner_id": owner_id,
                "actor_id": actor_id,
                "host_app": host_app,
                "action": action,
                "scope_kind": scope_kind,
                "scope_id": scope_id,
                "target_ids": clean_targets,
                "consent_generation": int(consent_generation),
                "outcome": "ok",
                "reason_code": clean_reason,
                "receipt": clean_receipt,
                "idempotency_key": norm_key,
                "created_at": created_at,
            }

    def list_events(self, owner_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        """List audit events for a single owner, newest first."""
        if not owner_id:
            return []
        bounded_limit = max(1, min(int(limit), 1000))
        with self._lock:
            rows = self._db.execute(
                f"SELECT {_SELECT_COLS} FROM cs_memory_audit "
                "WHERE owner_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
                (owner_id, bounded_limit),
            ).fetchall()
            return [_row_to_dict(r) for r in rows]

    def get_by_idempotency_key(self, owner_id: str, idempotency_key: str) -> dict[str, Any] | None:
        """Fetch an owner-scoped audit event by idempotency_key (returns None for other owners)."""
        norm_key = self._normalize_key(idempotency_key)
        if not owner_id or norm_key is None:
            return None
        with self._lock:
            row = self._db.execute(
                f"SELECT {_SELECT_COLS} FROM cs_memory_audit WHERE owner_id = ? AND idempotency_key = ?",
                (owner_id, norm_key),
            ).fetchone()
            return _row_to_dict(row) if row is not None else None
