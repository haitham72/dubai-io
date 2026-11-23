"""Tests for CS-B4 AuditStore: immutability, idempotency, owner isolation, and Rule 9 hygiene."""
from __future__ import annotations

import json
import pytest

from app.memory_bridge.audit import AuditStore
from app.memory_bridge.models import ConsentDeniedError, ForgetReceipt, MemoryBridgeError
from tests.fixtures.contest_shared.memory_fixtures import (
    SYNTH_OWNER_A,
    SYNTH_OWNER_B,
    make_sqlite_db,
)


def test_audit_record_list_and_newest_first_order(tmp_path):
    db = make_sqlite_db(tmp_path, "audit_order.db")
    audit = AuditStore(db)

    ev1 = audit.record_event(
        owner_id=SYNTH_OWNER_A,
        actor_id=SYNTH_OWNER_A,
        host_app="quest",
        action="memory.forget_records",
        scope_kind="record",
        scope_id="qmsg:1",
        target_ids=("qmsg:1",),
        consent_generation=2,
        outcome="ok",
        reason_code="completed",
        receipt={"records_forgotten": 1, "facts_erased": 1, "status": "completed"},
        idempotency_key="aud-key-1",
    )
    ev2 = audit.record_event(
        owner_id=SYNTH_OWNER_A,
        actor_id=SYNTH_OWNER_A,
        host_app="community",
        action="memory.forget_source",
        scope_kind="source",
        scope_id="community",
        target_ids=("cmsave:1", "cmpost:2"),
        consent_generation=3,
        outcome="ok",
        reason_code="completed",
        receipt={"records_forgotten": 2, "facts_erased": 1, "status": "completed"},
        idempotency_key="aud-key-2",
    )

    events = audit.list_events(SYNTH_OWNER_A)
    assert [e["id"] for e in events] == [ev2["id"], ev1["id"]]
    assert events[0]["target_ids"] == ["cmsave:1", "cmpost:2"]
    assert events[0]["consent_generation"] == 3
    assert events[1]["receipt"]["records_forgotten"] == 1

    # Limit parameter is respected
    assert [e["id"] for e in audit.list_events(SYNTH_OWNER_A, limit=1)] == [ev2["id"]]

    # Owner-scoped idempotency lookup
    fetched = audit.get_by_idempotency_key(SYNTH_OWNER_A, "aud-key-1")
    assert fetched is not None
    assert fetched["id"] == ev1["id"]


def test_audit_idempotency_replay_immutable_and_cross_owner_isolation(tmp_path):
    db = make_sqlite_db(tmp_path, "audit_iso.db")
    audit = AuditStore(db)

    first = audit.record_event(
        owner_id=SYNTH_OWNER_A,
        actor_id=SYNTH_OWNER_A,
        host_app="messenger",
        action="memory.forget_conversation",
        scope_kind="conversation",
        scope_id="messenger:conv-a",
        target_ids=("mgmsg:m-a1",),
        consent_generation=2,
        outcome="ok",
        reason_code="completed",
        receipt={"records_forgotten": 1, "status": "completed"},
        idempotency_key="shared-idem-key",
    )

    # Replaying with the same owner & idempotency_key returns the original immutable row
    replay = audit.record_event(
        owner_id=SYNTH_OWNER_A,
        actor_id=SYNTH_OWNER_A,
        host_app="messenger",
        action="memory.forget_conversation",
        scope_kind="conversation",
        scope_id="messenger:conv-a",
        target_ids=("mgmsg:m-other",),
        consent_generation=99,
        outcome="error",
        reason_code="tampered",
        receipt={"records_forgotten": 99, "status": "completed"},
        idempotency_key="shared-idem-key",
    )
    assert replay["id"] == first["id"]
    assert replay["consent_generation"] == 2
    assert replay["outcome"] == "ok"
    assert replay["target_ids"] == ["mgmsg:m-a1"]
    assert len(audit.list_events(SYNTH_OWNER_A)) == 1

    # Owner B cannot list Owner A's audit events or read by Owner A's idempotency_key
    assert audit.list_events(SYNTH_OWNER_B) == []
    assert audit.get_by_idempotency_key(SYNTH_OWNER_B, "shared-idem-key") is None

    # Owner B attempting to reuse Owner A's idempotency_key fails closed
    with pytest.raises(ConsentDeniedError) as exc_info:
        audit.record_event(
            owner_id=SYNTH_OWNER_B,
            actor_id=SYNTH_OWNER_B,
            host_app="quest",
            action="memory.forget_records",
            target_ids=("qmsg:b-1",),
            idempotency_key="shared-idem-key",
        )
    assert exc_info.value.status_code == 403
    assert len(audit.list_events(SYNTH_OWNER_B)) == 0


def test_audit_rule9_hygiene_strips_raw_text_secrets_and_tokens(tmp_path):
    db = make_sqlite_db(tmp_path, "audit_rule9.db")
    audit = AuditStore(db)

    secret_text = "My Wi-Fi key is BarshaL0bby!2026"
    secret_tok = "tok_live_do_not_persist_998877"
    secret_otp = "OTP 482910 for login"

    receipt_model = ForgetReceipt(
        idempotency_key="rule9-key-1",
        owner_id=SYNTH_OWNER_A,
        scope_kind="record",
        scope_id="qmsg:1",
        consent_generation=2,
        temporal_generation=4,
        records_forgotten=1,
        facts_erased=1,
        facts_trimmed=0,
        jobs_requeued=0,
        projections_invalidated=True,
        status="completed",
        recorded_at="2026-11-23T19:00:00+00:00",
    )

    ev = audit.record_event(
        owner_id=SYNTH_OWNER_A,
        actor_id=SYNTH_OWNER_A,
        host_app="quest",
        action="memory.forget_records",
        scope_kind="record",
        scope_id="qmsg:1",
        target_ids=("qmsg:1",),
        consent_generation=2,
        outcome="quarantined",
        reason_code=secret_otp,
        receipt={
            "text": secret_text,
            "text_orig": secret_text,
            "secret": "super-secret-value",
            "token": secret_tok,
            "access_token": secret_tok,
            "password": "Password123!",
            "nested": {
                "raw_text": secret_text,
                "note": secret_otp,
                "facts_erased": 1,
            },
            "category": "credential",
            "records_forgotten": 1,
            "receipt_copy": receipt_model,
        },
        idempotency_key="rule9-key-1",
    )

    # Verify stored row in SQL directly contains zero leaked secrets/text
    raw_row = db.execute(
        "SELECT reason_code, receipt_json FROM cs_memory_audit WHERE id = ?",
        (ev["id"],),
    ).fetchone()
    assert raw_row is not None
    raw_reason, raw_receipt_json = raw_row[0], raw_row[1]
    assert raw_reason == "redacted"
    for forbidden_val in (secret_text, secret_tok, "super-secret-value", "Password123!", "482910"):
        assert forbidden_val not in raw_receipt_json
        assert forbidden_val not in json.dumps(ev)

    stored_receipt = ev["receipt"]
    for forbidden_key in ("text", "text_orig", "secret", "token", "access_token", "password"):
        assert forbidden_key not in stored_receipt
    assert "raw_text" not in stored_receipt["nested"]
    assert stored_receipt["nested"]["note"] == "[redacted]"
    assert stored_receipt["nested"]["facts_erased"] == 1
    assert stored_receipt["category"] == "credential"
    assert stored_receipt["records_forgotten"] == 1
    assert stored_receipt["receipt_copy"]["temporal_generation"] == 4


def test_audit_validation_and_reconciliation_trail(tmp_path):
    db = make_sqlite_db(tmp_path, "audit_reconcile.db")
    audit = AuditStore(db)

    with pytest.raises(MemoryBridgeError):
        audit.record_event(
            owner_id="",
            actor_id=SYNTH_OWNER_A,
            host_app="quest",
            action="memory.forget_records",
        )
    with pytest.raises(MemoryBridgeError):
        audit.record_event(
            owner_id=SYNTH_OWNER_A,
            actor_id=SYNTH_OWNER_A,
            host_app="quest",
            action="memory.forget_records",
            outcome="bogus_outcome",
        )

    pending = audit.record_event(
        owner_id=SYNTH_OWNER_A,
        actor_id=SYNTH_OWNER_A,
        host_app="messenger",
        action="memory.forget_conversation",
        scope_kind="conversation",
        scope_id="messenger:conv-a",
        target_ids=("mgmsg:m-a1",),
        consent_generation=2,
        outcome="partial",
        reason_code="pending_reconciliation",
        receipt={"status": "pending_reconciliation", "temporal_generation": None},
        idempotency_key="rec-key-1",
    )
    assert pending["outcome"] == "partial"

    completed = audit.record_reconciliation(
        owner_id=SYNTH_OWNER_A,
        actor_id=SYNTH_OWNER_A,
        host_app="messenger",
        action="memory.forget_conversation",
        scope_kind="conversation",
        scope_id="messenger:conv-a",
        target_ids=("mgmsg:m-a1",),
        consent_generation=2,
        reason_code="reconciled",
        receipt={"status": "completed", "temporal_generation": 5, "records_forgotten": 1},
        idempotency_key="rec-key-1",
    )
    assert completed["outcome"] == "ok"
    assert completed["receipt"]["status"] == "completed"

    # Both partial and completed rows remain in append-only history, newest first
    history = audit.list_events(SYNTH_OWNER_A)
    assert [h["outcome"] for h in history] == ["ok", "partial"]

    # Active idempotency pointer resolves to completed
    active = audit.get_by_idempotency_key(SYNTH_OWNER_A, "rec-key-1")
    assert active is not None
    assert active["id"] == completed["id"]
    assert active["receipt"]["status"] == "completed"
