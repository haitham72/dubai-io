"""Tests for CS-B3 per-app reads: two-user isolation, Quest reads, Community allowlist/D11, Messenger chat scope, and own activity."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app import db as db_mod
from tests.fixtures.contest_shared.db_fixtures import cs_postgres_isolation  # noqa: F401
from tests.fixtures.contest_shared.memory_bridge_fixtures import memory_bridge_env  # noqa: F401
from app.identity.models import AgeBand, AppId, VerifiedPrincipal
from app.memory_bridge.bridge import MemoryBridge
from app.memory_bridge.models import (
    ConsentDeniedError,
    GroupConsentSnapshot,
    InterestFeature,
    MemoryBridgeError,
    MemoryRecordInput,
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


def _setup(tmp_path: Path, client, name: str = "reads.db"):
    db = db_mod.connect(tmp_path / name)
    bridge = MemoryBridge(db, client)
    return db, client, bridge


def test_mb_two_user_isolation(tmp_path: Path, memory_bridge_env) -> None:
    """MB-02: User A reads own vault/context/timeline/why/chat/interests/audit; User B sees zero User A data."""
    db, _, bridge = _setup(tmp_path, memory_bridge_env.client, "iso.db")
    try:
        alice_id = memory_bridge_env.owner_id("alice")
        bob_id = memory_bridge_env.owner_id("bob")
        alice_q = _principal(alice_id, app_id="quest")
        alice_c = _principal(alice_id, app_id="community")
        alice_m = _principal(alice_id, app_id="messenger")
        bob_q = _principal(bob_id, app_id="quest")
        bob_c = _principal(bob_id, app_id="community")
        bob_m = _principal(bob_id, app_id="messenger")

        # Enable consent for both Alice and Bob.
        for u_q, u_c, u_m in ((alice_q, alice_c, alice_m), (bob_q, bob_c, bob_m)):
            bridge.set_source_consent(u_q, "quest", enabled=True, allow_interest_export=True)
            bridge.set_source_consent(u_m, "messenger", enabled=True)
            bridge.set_app_consent(u_q, "quest", read_enabled=True, write_enabled=True)
            bridge.set_app_consent(
                u_c, "community", read_enabled=True, write_enabled=True, allow_interest_export_to_community=True
            )
            bridge.set_app_consent(u_m, "messenger", read_enabled=True, write_enabled=True)
            bridge.set_conversation_consent(u_m, "conv-shared", ai_mode="save")

        r_a = bridge.write_consented(
            alice_q,
            MemoryRecordInput(
                record_id="qmsg:alice1",
                source_kind="quest",
                source_id="quest:t1",
                host_app="quest",
                author_id=alice_id,
                text="Alice private running goal 10km",
                valid_time="2026-11-23T09:00:00+00:00",
                subject_path="fitness/running",
                explicit_user_confirm=True,
            ),
        )
        alice_fid = r_a.fact_ids[0]
        bridge.write_consented(
            alice_m,
            MemoryRecordInput(
                record_id="mgmsg:alice1",
                source_kind="messenger",
                source_id="messenger:conv-shared",
                host_app="messenger",
                author_id=alice_id,
                text="Alice plans to bring dates to picnic",
                valid_time="2026-11-23T09:05:00+00:00",
                subject_path="plans/picnic",
                explicit_user_confirm=True,
            ),
            group_consent=GroupConsentSnapshot("conv-shared", True, True, True, 1),
        )

        # Happy path: Alice reads her own data across all surfaces.
        assert len(bridge.read_quest_context(alice_q, "running")["facts"]) == 1
        assert len(bridge.read_quest_timeline(alice_q)) == 2
        assert bridge.read_why_fact(alice_q, alice_fid, host_app="quest")["fact_id"] == alice_fid
        assert len(bridge.read_community_interest_features(alice_c)) == 1
        assert len(bridge.read_messenger_chat_scope(
            alice_m, "conv-shared", group_consent=GroupConsentSnapshot("conv-shared", True, True, True, 1)
        )) == 1
        assert len(bridge.list_audit_events(alice_q)) >= 2

        # Failure path: Bob sees zero Alice data and gets 404 on Alice's fact why.
        assert bridge.read_quest_context(bob_q, "running")["facts"] == []
        assert bridge.read_quest_timeline(bob_q) == []
        assert bridge.read_community_interest_features(bob_c) == []
        assert bridge.read_community_own_activity(bob_c) == []
        assert bridge.read_messenger_chat_scope(
            bob_m, "conv-shared", group_consent=GroupConsentSnapshot("conv-shared", True, True, True, 1)
        ) == []
        assert all(ev["owner_id"] == bob_id for ev in bridge.list_audit_events(bob_q))
        with pytest.raises(MemoryBridgeError) as exc_info:
            bridge.read_why_fact(bob_q, alice_fid, host_app="quest")
        assert exc_info.value.status_code == 404
    finally:
        db.close()


def test_quest_source_revocation_hides_facts_immediately(tmp_path: Path, memory_bridge_env) -> None:
    """Revoking source consent or setting Messenger ai_mode='session' hides those facts from Quest reads."""
    db, _, bridge = _setup(tmp_path, memory_bridge_env.client, "quest_revoke.db")
    try:
        alice_id = memory_bridge_env.owner_id("alice")
        alice_q = _principal(alice_id, app_id="quest")
        alice_m = _principal(alice_id, app_id="messenger")
        bridge.set_source_consent(alice_q, "quest", enabled=True)
        bridge.set_source_consent(alice_m, "messenger", enabled=True)
        bridge.set_app_consent(alice_q, "quest", read_enabled=True, write_enabled=True)
        bridge.set_app_consent(alice_m, "messenger", read_enabled=True, write_enabled=True)
        bridge.set_conversation_consent(alice_m, "conv-1", ai_mode="save")

        rq = bridge.write_consented(
            alice_q,
            MemoryRecordInput(
                record_id="qmsg:1",
                source_kind="quest",
                source_id="quest:t1",
                host_app="quest",
                author_id=alice_id,
                text="I study Arabic calligraphy",
                valid_time="2026-11-23T09:00:00+00:00",
                subject_path="arts/calligraphy",
                explicit_user_confirm=True,
            ),
        )
        bridge.write_consented(
            alice_m,
            MemoryRecordInput(
                record_id="mgmsg:1",
                source_kind="messenger",
                source_id="messenger:conv-1",
                host_app="messenger",
                author_id=alice_id,
                text="Meeting Friday at Kite Beach",
                valid_time="2026-11-23T09:10:00+00:00",
                subject_path="plans/meetup",
                explicit_user_confirm=True,
            ),
            group_consent=GroupConsentSnapshot("conv-1", True, True, True, 1),
        )
        assert len(bridge.read_quest_timeline(alice_q)) == 2

        # Demote Messenger conversation to 'session' -> Quest excludes Messenger thread immediately.
        bridge.set_conversation_consent(alice_m, "conv-1", ai_mode="session")
        tl_after_session = bridge.read_quest_timeline(alice_q)
        assert len(tl_after_session) == 1
        assert tl_after_session[0].fact_id == rq.fact_ids[0]

        # Revoke Quest source -> Quest timeline/context empty and read_why_fact denied.
        bridge.set_source_consent(alice_q, "quest", enabled=False)
        assert bridge.read_quest_timeline(alice_q) == []
        assert bridge.read_quest_context(alice_q, "calligraphy")["facts"] == []
        with pytest.raises(ConsentDeniedError):
            bridge.read_why_fact(alice_q, rq.fact_ids[0], host_app="quest")
    finally:
        db.close()


def test_mb_community_strict_allowlist_and_d11_minor_gate(tmp_path: Path, memory_bridge_env) -> None:
    """MB-07 & MB-11: Strict InterestFeature DTO only, zero private text/IDs, immediate toggle-off, and [] for minors."""
    db, _, bridge = _setup(tmp_path, memory_bridge_env.client, "comm_allowlist.db")
    try:
        alice_id = memory_bridge_env.owner_id("alice")
        alice_q = _principal(alice_id, app_id="quest")
        alice_c = _principal(alice_id, app_id="community")
        alice_m = _principal(alice_id, app_id="messenger")

        bridge.set_source_consent(alice_q, "quest", enabled=True, allow_interest_export=True)
        bridge.set_source_consent(alice_q, "gmail", enabled=True, allow_interest_export=True)
        bridge.set_source_consent(alice_m, "messenger", enabled=True, allow_interest_export=False)
        bridge.set_app_consent(alice_q, "quest", read_enabled=True, write_enabled=True)
        bridge.set_app_consent(alice_m, "messenger", read_enabled=True, write_enabled=True)
        bridge.set_conversation_consent(alice_m, "conv-secret-99", ai_mode="save", allow_interest_export=False)
        # Community read_enabled=True, allow_interest_export_to_community=False initially (default OFF).
        bridge.set_app_consent(
            alice_c, "community", read_enabled=True, write_enabled=False, allow_interest_export_to_community=False
        )

        # Write a clean Quest interest, a sensitive health fact (owner_private), a Gmail fact, and a Messenger fact.
        bridge.write_consented(
            alice_q,
            MemoryRecordInput(
                record_id="qmsg:padel",
                source_kind="quest",
                source_id="quest:t1",
                host_app="quest",
                author_id=alice_id,
                text="PRIVATE_QUEST_TEXT: Omar and I play padel at Marina",
                valid_time="2026-11-23T10:00:00+00:00",
                subject_path="hobbies/padel",
                explicit_user_confirm=True,
            ),
        )
        bridge.write_consented(
            alice_q,
            MemoryRecordInput(
                record_id="qmsg:health",
                source_kind="quest",
                source_id="quest:t1",
                host_app="quest",
                author_id=alice_id,
                text="I visited the clinic for blood test",
                valid_time="2026-11-23T10:05:00+00:00",
                subject_path="health/checkup",
                scope="owner_private",
                explicit_user_confirm=True,
                allow_sensitive_confirmed=True,
            ),
        )
        bridge.write_consented(
            alice_q,
            MemoryRecordInput(
                record_id="gmail:1",
                source_kind="gmail",
                source_id="gmail:msg-77",
                host_app="connector",
                author_id=alice_id,
                text="SECRET_GMAIL_SUBJECT: Flight booking to Salalah",
                valid_time="2026-11-23T10:10:00+00:00",
                subject_path="travel/salalah",
                explicit_user_confirm=True,
            ),
        )
        bridge.write_consented(
            alice_m,
            MemoryRecordInput(
                record_id="mgmsg:secret",
                source_kind="messenger",
                source_id="messenger:conv-secret-99",
                host_app="messenger",
                author_id=alice_id,
                text="SECRET_CHAT_TEXT: Surprise gift at Mall",
                valid_time="2026-11-23T10:15:00+00:00",
                subject_path="shopping/gifts",
                explicit_user_confirm=True,
            ),
            group_consent=GroupConsentSnapshot("conv-secret-99", True, True, True, 1),
        )

        # Default export OFF -> returns [].
        assert bridge.read_community_interest_features(alice_c) == []

        # Enable allow_interest_export_to_community=True -> returns strict InterestFeature DTOs only.
        bridge.set_app_consent(
            alice_c, "community", read_enabled=True, write_enabled=False, allow_interest_export_to_community=True
        )
        features = bridge.read_community_interest_features(alice_c)
        assert len(features) == 2
        assert all(isinstance(f, InterestFeature) for f in features)
        assert {f.topic_slug for f in features} == {"padel", "salalah"}
        assert all(f.weight > 0.0 for f in features)

        payload_dump = json.dumps([f.__dict__ for f in features])
        for forbidden in (
            "PRIVATE_QUEST_TEXT",
            "SECRET_GMAIL_SUBJECT",
            "SECRET_CHAT_TEXT",
            "conv-secret-99",
            "Omar",
            "clinic",
            "blood test",
            "health",
            "gifts",
        ):
            assert forbidden not in payload_dump

        # Cache hit works, and toggling OFF immediately clears results on next call.
        assert db.execute("SELECT 1 FROM cs_interest_projection_cache WHERE owner_id = ?", (alice_id,)).fetchone() is not None
        bridge.set_app_consent(
            alice_c, "community", read_enabled=True, write_enabled=False, allow_interest_export_to_community=False
        )
        assert db.execute("SELECT 1 FROM cs_interest_projection_cache WHERE owner_id = ?", (alice_id,)).fetchone() is None
        assert bridge.read_community_interest_features(alice_c) == []

        # Minor-protected accounts always receive [] on read_community_interest_features.
        for band in ("under_13", "teen_13_17", "unknown"):
            minor_c = _principal(memory_bridge_env.owner_id(f"minor_{band}"), app_id="community", age_band=band)  # type: ignore[arg-type]
            assert bridge.read_community_interest_features(minor_c) == []
    finally:
        db.close()


def test_mb_messenger_chat_scope_and_group_gate(tmp_path: Path, memory_bridge_env) -> None:
    """MB-08: Chat-scoped reads isolate conv-A from conv-B and enforce group + ai_mode gates."""
    db, _, bridge = _setup(tmp_path, memory_bridge_env.client, "messenger_scope.db")
    try:
        alice_id = memory_bridge_env.owner_id("alice")
        alice_m = _principal(alice_id, app_id="messenger")
        alice_q = _principal(alice_id, app_id="quest")
        bridge.set_source_consent(alice_m, "messenger", enabled=True)
        bridge.set_source_consent(alice_q, "quest", enabled=True)
        bridge.set_app_consent(alice_q, "quest", read_enabled=True, write_enabled=True)
        bridge.set_app_consent(
            alice_m, "messenger", read_enabled=True, write_enabled=True, allow_cross_source_recall=False
        )
        bridge.set_conversation_consent(alice_m, "conv-A", ai_mode="save")
        bridge.set_conversation_consent(alice_m, "conv-B", ai_mode="session")

        # Write Quest fact and Messenger conv-A fact.
        bridge.write_consented(
            alice_q,
            MemoryRecordInput(
                record_id="qmsg:1",
                source_kind="quest",
                source_id="quest:t1",
                host_app="quest",
                author_id=alice_id,
                text="I prefer morning flights",
                valid_time="2026-11-23T08:00:00+00:00",
                subject_path="travel/flights",
                explicit_user_confirm=True,
            ),
        )
        bridge.write_consented(
            alice_m,
            MemoryRecordInput(
                record_id="mgmsg:a1",
                source_kind="messenger",
                source_id="messenger:conv-A",
                host_app="messenger",
                author_id=alice_id,
                text="Team agreed on Tuesday launch",
                valid_time="2026-11-23T09:00:00+00:00",
                subject_path="work/launch",
                explicit_user_confirm=True,
            ),
            group_consent=GroupConsentSnapshot("conv-A", True, True, True, 1),
        )

        # Happy: conv-A returns conv-A facts only.
        a_facts = bridge.read_messenger_chat_scope(
            alice_m,
            "conv-A",
            group_consent=GroupConsentSnapshot("conv-A", True, True, True, 1),
        )
        assert len(a_facts) == 1 and "Tuesday launch" in a_facts[0].text

        # conv-B (ai_mode="session") sees zero conv-A facts (no cross-chat leakage).
        b_facts = bridge.read_messenger_chat_scope(
            alice_m,
            "conv-B",
            group_consent=GroupConsentSnapshot("conv-B", True, True, True, 1),
        )
        assert b_facts == []

        # ai_mode="session" blocks writes.
        with pytest.raises(ConsentDeniedError):
            bridge.write_consented(
                alice_m,
                MemoryRecordInput(
                    record_id="mgmsg:b1",
                    source_kind="messenger",
                    source_id="messenger:conv-B",
                    host_app="messenger",
                    author_id=alice_id,
                    text="Should not save in session mode",
                    valid_time="2026-11-23T09:05:00+00:00",
                    explicit_user_confirm=True,
                ),
                group_consent=GroupConsentSnapshot("conv-B", True, True, True, 1),
            )

        # One off member or non-member blocks chat-scope read & write.
        with pytest.raises(ConsentDeniedError):
            bridge.read_messenger_chat_scope(
                alice_m,
                "conv-A",
                group_consent=GroupConsentSnapshot("conv-A", True, False, True, 2),
            )
        with pytest.raises(ConsentDeniedError):
            bridge.read_messenger_chat_scope(
                alice_m,
                "conv-A",
                group_consent=GroupConsentSnapshot("conv-A", False, True, True, 2),
            )

        # ai_mode="off" blocks read_messenger_chat_scope.
        bridge.set_conversation_consent(alice_m, "conv-C", ai_mode="off")
        with pytest.raises(ConsentDeniedError):
            bridge.read_messenger_chat_scope(
                alice_m,
                "conv-C",
                group_consent=GroupConsentSnapshot("conv-C", True, True, True, 1),
            )

        # Opt-in cross-source owner recall requires allow_cross_source_recall=True.
        with pytest.raises(ConsentDeniedError):
            bridge.read_messenger_owner_recall(alice_m, "conv-A", query="flights")

        bridge.set_app_consent(
            alice_m, "messenger", read_enabled=True, write_enabled=True, allow_cross_source_recall=True
        )
        client = bridge.client
        [quest_fact] = client.search_facts(alice_id, "flights", source_prefix="quest:t1")
        client.set_memory_lowered(alice_id, fact_id=quest_fact["id"])
        assert not client.search_facts(alice_id, "flights", source_prefix="quest:t1")

        recall = bridge.read_messenger_owner_recall(alice_m, "conv-A", query="flights")
        assert len(recall) == 1 and recall[0].fact_id == quest_fact["id"]
        [refreshed] = client.search_facts(alice_id, "flights", source_prefix="quest:t1")
        assert refreshed["weight"] == pytest.approx(0.35)
    finally:
        db.close()


def test_mb_community_own_activity_and_isolation(tmp_path: Path, memory_bridge_env) -> None:
    """MB-12: Community own activity shows saved discussions & authored posts (topic only) and hides when erased."""
    db, client, bridge = _setup(tmp_path, memory_bridge_env.client, "comm_activity.db")
    try:
        alice_id = memory_bridge_env.owner_id("alice")
        bob_id = memory_bridge_env.owner_id("bob")
        alice_c = _principal(alice_id, app_id="community")
        alice_q = _principal(alice_id, app_id="quest")
        bob_c = _principal(bob_id, app_id="community")

        for u_c, u_q in ((alice_c, alice_q), (bob_c, _principal(bob_id, app_id="quest"))):
            bridge.set_source_consent(u_c, "community", enabled=True, allow_interest_export=True)
            bridge.set_source_consent(u_q, "quest", enabled=True)
            bridge.set_app_consent(u_c, "community", read_enabled=True, write_enabled=True)
            bridge.set_app_consent(u_q, "quest", read_enabled=True, write_enabled=True)

        # Write Quest private fact (must never appear in read_community_own_activity).
        bridge.write_consented(
            alice_q,
            MemoryRecordInput(
                record_id="qmsg:private1",
                source_kind="quest",
                source_id="quest:t1",
                host_app="quest",
                author_id=alice_id,
                text="SECRET_QUEST_ENTRY",
                valid_time="2026-11-23T09:00:00+00:00",
                explicit_user_confirm=True,
            ),
        )

        # Save a Community discussion (cmsave:*) and author a Community post (cmpost:*).
        bridge.write_consented(
            alice_c,
            MemoryRecordInput(
                record_id="cmsave:s1",
                source_kind="community",
                source_id="community:post:p10",
                host_app="community",
                author_id=alice_id,
                text="Saved discussion about neighborhood cycling lanes",
                valid_time="2026-11-23T10:00:00+00:00",
                subject_path="community/cycling",
                explicit_user_confirm=False,
            ),
        )
        bridge.write_consented(
            alice_c,
            MemoryRecordInput(
                record_id="cmpost:p11",
                source_kind="community",
                source_id="community:post:p11",
                host_app="community",
                author_id=alice_id,
                text="Organizing weekend beach cleanup at Jumeirah",
                valid_time="2026-11-23T10:05:00+00:00",
                subject_path="community/volunteering",
                explicit_user_confirm=True,
            ),
        )

        act = bridge.read_community_own_activity(alice_c)
        assert len(act) == 2
        assert all(item["label"] == "saved from Community, topic only" for item in act)
        assert {item["kind"] for item in act} == {"saved_discussion", "authored_post"}
        assert "SECRET_QUEST_ENTRY" not in json.dumps(act)
        assert bridge.read_community_own_activity(bob_c) == []

        # Simulate forget cascade erasing refs -> disappears from own activity & Quest immediately.
        db.execute(
            "UPDATE cs_memory_record_refs SET erased_at = '2026-11-23T12:00:00+00:00' WHERE owner_id = ? AND source_kind = 'community'",
            (alice_id,),
        )
        db.commit()
        client.forget_source(alice_id, ["cmsave:s1", "cmpost:p11"])

        assert bridge.read_community_own_activity(alice_c) == []
        quest_tl = bridge.read_quest_timeline(alice_q)
        assert len(quest_tl) == 1 and "SECRET_QUEST_ENTRY" in quest_tl[0].text
    finally:
        db.close()
