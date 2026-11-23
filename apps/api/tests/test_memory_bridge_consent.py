"""Tests for CS-B3 ConsentStore, D11 minor fence on consent, generation bumps, and cache invalidation."""
from __future__ import annotations

from pathlib import Path
import sys
import threading

import pytest

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app import db as db_mod
from app.identity.models import AgeBand, AppId, VerifiedPrincipal
from app.memory_bridge.bridge import MemoryBridge
from app.memory_bridge.consent import ConsentStore
from app.memory_bridge.fake_client import FakeTemporalMemoryClient
from app.memory_bridge.models import (
    ConsentDeniedError,
    ForgetReceipt,
    GroupConsentSnapshot,
    MemoryBridgeError,
    MemoryRecordInput,
    MinorProtectionError,
)


def _principal(
    user_id: str,
    *,
    app_id: AppId | None = None,
    age_band: AgeBand = "adult_18_plus",
) -> VerifiedPrincipal:
    return VerifiedPrincipal(
        user_id=user_id,
        app_id=app_id,
        capabilities=frozenset(),
        auth_mode="verified_app_session" if app_id else "verified_jwt",
        age_band=age_band,
    )


def _make_bridge(tmp_path: Path, name: str = "consent.db", *, forget_coordinator=None):
    db = db_mod.connect(tmp_path / name)
    client = FakeTemporalMemoryClient()
    bridge = MemoryBridge(db, client, forget_coordinator=forget_coordinator)
    return db, client, bridge


def test_mb_default_off_consent(tmp_path: Path) -> None:
    """MB-01: Default-off consent blocks writes/reads until explicitly enabled for adult_18_plus."""
    db, client, bridge = _make_bridge(tmp_path)
    try:
        alice_quest = _principal("usr_alice", app_id="quest")
        alice_comm = _principal("usr_alice", app_id="community")
        alice_msg = _principal("usr_alice", app_id="messenger")

        # Default grants are all off with generation=1.
        src_grant = bridge.get_consent(alice_quest, "source", "quest")
        app_grant = bridge.get_consent(alice_quest, "app", "quest")
        conv_grant = bridge.get_consent(alice_msg, "conversation", "messenger:conv-1")
        assert src_grant.enabled is False and src_grant.allow_interest_export is False and src_grant.generation == 1
        assert app_grant.read_enabled is False and app_grant.write_enabled is False and app_grant.generation == 1
        assert conv_grant.ai_mode == "off" and conv_grant.generation == 1
        assert bridge.list_consents(alice_quest) == []

        # Failure path: fresh user cannot write or read across Quest, Community, or Messenger.
        with pytest.raises(ConsentDeniedError):
            bridge.write_consented(
                alice_quest,
                MemoryRecordInput(
                    record_id="qmsg:1",
                    source_kind="quest",
                    source_id="quest:t1",
                    host_app="quest",
                    author_id="usr_alice",
                    text="I enjoy padel on weekends",
                    valid_time="2026-11-23T10:00:00+00:00",
                    explicit_user_confirm=True,
                ),
            )
        with pytest.raises(ConsentDeniedError):
            bridge.read_quest_context(alice_quest, "padel")
        with pytest.raises(ConsentDeniedError):
            bridge.read_community_own_activity(alice_comm)
        with pytest.raises(ConsentDeniedError):
            bridge.read_community_interest_features(alice_comm)
        with pytest.raises(ConsentDeniedError):
            bridge.read_messenger_chat_scope(
                alice_msg,
                "conv-1",
                group_consent=GroupConsentSnapshot("conv-1", True, True, True, 1),
            )

        # Happy path: enable source + app consent -> Quest write and read succeed.
        g_src, _ = bridge.set_source_consent(alice_quest, "quest", enabled=True)
        g_app = bridge.set_app_consent(alice_quest, "quest", read_enabled=True, write_enabled=True)
        assert g_src.enabled is True and g_src.generation == 2
        assert g_app.read_enabled is True and g_app.write_enabled is True and g_app.generation == 2

        receipt = bridge.write_consented(
            alice_quest,
            MemoryRecordInput(
                record_id="qmsg:1",
                source_kind="quest",
                source_id="quest:t1",
                host_app="quest",
                author_id="usr_alice",
                text="I enjoy padel on weekends",
                valid_time="2026-11-23T10:00:00+00:00",
                subject_path="hobbies/padel",
                explicit_user_confirm=True,
            ),
        )
        assert receipt.ok is True and receipt.status == "applied"
        ctx = bridge.read_quest_context(alice_quest, "padel")
        assert len(ctx["facts"]) == 1
        assert ctx["facts"][0]["display_prefix"] == "You told me"

        # list_consents returns both persisted scopes and supports filtering.
        all_grants = bridge.list_consents(alice_quest)
        assert len(all_grants) == 2
        assert len(bridge.list_consents(alice_quest, scope_kind="source")) == 1
        assert len(bridge.list_consents(alice_quest, scope_kind="app")) == 1
    finally:
        db.close()


def test_consent_monotonic_generation_and_sync_cache_invalidation(tmp_path: Path) -> None:
    """Every consent toggle increments generation monotonically and deletes cs_interest_projection_cache."""
    db = db_mod.connect(tmp_path / "gen.db")
    try:
        store = ConsentStore(db)
        alice = _principal("usr_alice")
        bob = _principal("usr_bob")

        # Seed projection cache rows for Alice and Bob.
        for uid in ("usr_alice", "usr_bob"):
            db.execute(
                """
                INSERT INTO cs_interest_projection_cache (
                    owner_id, consent_generation_sig, facts_version, features_json, computed_at
                ) VALUES (?, 'sig1', 1, '[]', '2026-11-23T10:00:00+00:00')
                """,
                (uid,),
            )
        db.commit()

        g1 = store.set_source_consent(alice, "quest", enabled=True, allow_interest_export=True)
        assert g1.generation == 2
        assert (
            db.execute("SELECT 1 FROM cs_interest_projection_cache WHERE owner_id = ?", ("usr_alice",)).fetchone()
            is None
        )
        # Bob's cache stays intact.
        assert (
            db.execute("SELECT 1 FROM cs_interest_projection_cache WHERE owner_id = ?", ("usr_bob",)).fetchone()
            is not None
        )

        g2 = store.set_source_consent(alice, "quest", enabled=False)
        assert g2.generation == 3
        assert g2.allow_interest_export is False

        c1 = store.set_conversation_consent(alice, "conv-9", ai_mode="session")
        assert c1.scope_id == "messenger:conv-9"
        assert c1.generation == 2
        assert c1.enabled is True and c1.write_enabled is False

        c2 = store.set_conversation_consent(alice, "messenger:conv-9", ai_mode="save", allow_interest_export=True)
        assert c2.scope_id == "messenger:conv-9"
        assert c2.generation == 3
        assert c2.write_enabled is True and c2.allow_interest_export is True
    finally:
        db.close()


@pytest.mark.parametrize("age_band", ["under_13", "teen_13_17", "unknown"])
def test_d11_minor_fence_blocks_enabling_interest_export_on_consent(tmp_path: Path, age_band: AgeBand) -> None:
    """D11: Minor-protected accounts cannot enable cross-app interest export on any consent scope."""
    db = db_mod.connect(tmp_path / f"minor_{age_band}.db")
    try:
        store = ConsentStore(db)
        minor = _principal(f"usr_minor_{age_band}", age_band=age_band)

        with pytest.raises(MinorProtectionError):
            store.set_source_consent(minor, "quest", enabled=True, allow_interest_export=True)

        with pytest.raises(MinorProtectionError):
            store.set_app_consent(
                minor,
                "community",
                read_enabled=True,
                write_enabled=False,
                allow_interest_export_to_community=True,
            )

        with pytest.raises(MinorProtectionError):
            store.set_conversation_consent(
                minor,
                "conv-minor",
                ai_mode="save",
                allow_interest_export=True,
            )

        # Verify nothing was persisted with export enabled.
        assert store.list_consents(minor.user_id) == []
    finally:
        db.close()


def test_consent_validation_and_revoke_delegation(tmp_path: Path) -> None:
    """Invalid scope/mode fails closed and revoke delegates to forget_coordinator when injected."""
    calls: list[tuple[str, str]] = []

    class _FakeForgetCoordinator:
        def forget_source(self, principal, source_kind, *, host_app, idempotency_key):
            calls.append(("source", source_kind))
            return ForgetReceipt(
                idempotency_key=idempotency_key,
                owner_id=principal.user_id,
                scope_kind="source",
                scope_id=source_kind,
                consent_generation=3,
                temporal_generation=1,
                records_forgotten=1,
                facts_erased=1,
                facts_trimmed=0,
                jobs_requeued=0,
                projections_invalidated=True,
                status="completed",
                recorded_at="2026-11-23T12:00:00+00:00",
            )

        def forget_conversation(self, principal, conversation_id, *, idempotency_key):
            calls.append(("conversation", conversation_id))
            return ForgetReceipt(
                idempotency_key=idempotency_key,
                owner_id=principal.user_id,
                scope_kind="conversation",
                scope_id=f"messenger:{conversation_id}",
                consent_generation=3,
                temporal_generation=2,
                records_forgotten=2,
                facts_erased=1,
                facts_trimmed=0,
                jobs_requeued=0,
                projections_invalidated=True,
                status="completed",
                recorded_at="2026-11-23T12:00:00+00:00",
            )

    db, _, bridge = _make_bridge(tmp_path, "deleg.db", forget_coordinator=_FakeForgetCoordinator())
    try:
        alice = _principal("usr_alice")
        with pytest.raises(MemoryBridgeError):
            bridge.set_source_consent(alice, "invalid_src", enabled=True)  # type: ignore[arg-type]
        with pytest.raises(MemoryBridgeError):
            bridge.set_app_consent(alice, "invalid_app", read_enabled=True, write_enabled=True)  # type: ignore[arg-type]
        with pytest.raises(MemoryBridgeError):
            bridge.set_conversation_consent(alice, "", ai_mode="save")
        with pytest.raises(MemoryBridgeError):
            bridge.set_conversation_consent(alice, "conv-1", ai_mode="invalid")  # type: ignore[arg-type]
        with pytest.raises(MemoryBridgeError):
            bridge.consent_store.get_consent("usr_alice", "bad_kind", "quest")  # type: ignore[arg-type]

        # Enable then revoke source -> forget_coordinator invoked.
        _, r_enable = bridge.set_source_consent(alice, "quest", enabled=True)
        assert r_enable is None
        g_rev, r_rev = bridge.set_source_consent(alice, "quest", enabled=False, forget_on_revoke=True)
        assert g_rev.enabled is False and r_rev is not None and r_rev.status == "completed"

        # Enable then withdraw conversation -> forget_coordinator invoked.
        bridge.set_conversation_consent(alice, "conv-1", ai_mode="save")
        g_conv_off, r_conv = bridge.set_conversation_consent(
            alice, "conv-1", ai_mode="off", forget_on_withdraw=True
        )
        assert g_conv_off.ai_mode == "off" and r_conv is not None and r_conv.scope_id == "messenger:conv-1"
        assert calls == [("source", "quest"), ("conversation", "conv-1")]
    finally:
        db.close()


def test_consent_store_thread_safety(tmp_path: Path) -> None:
    """Concurrent consent toggles preserve monotonic generation under RLock."""
    db = db_mod.connect(tmp_path / "threads.db")
    try:
        store = ConsentStore(db)
        alice = _principal("usr_alice")
        errors: list[Exception] = []

        def _worker(idx: int) -> None:
            try:
                for step in range(10):
                    store.set_source_consent(alice, "quest", enabled=((idx + step) % 2 == 0))
            except Exception as exc:  # pragma: no cover
                errors.append(exc)

        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        final_grant = store.get_consent("usr_alice", "source", "quest")
        assert final_grant.generation == 41  # 1 default + 40 toggles
    finally:
        db.close()
