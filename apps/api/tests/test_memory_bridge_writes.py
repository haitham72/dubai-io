"""Tests for CS-B3 write path: D11 minor fence, spoof rejection, third-party rule, two-visit signals, and supersession."""
from __future__ import annotations

from dataclasses import make_dataclass
from pathlib import Path
import sys

import pytest

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app import db as db_mod
from app.identity.models import AgeBand, AppId, VerifiedPrincipal
from app.memory_bridge.bridge import MemoryBridge
from app.memory_bridge.fake_client import FakeTemporalMemoryClient
from app.memory_bridge.models import (
    ConsentDeniedError,
    GroupConsentSnapshot,
    MemoryBridgeError,
    MemoryRecordInput,
    MinorProtectionError,
    SensitiveContentError,
)
from app.memory_bridge.sensitive import ScreenUnavailable


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


def _setup(tmp_path: Path, name: str = "writes.db", *, screen_fn=None):
    db = db_mod.connect(tmp_path / name)
    client = FakeTemporalMemoryClient()
    bridge = MemoryBridge(db, client, screen_fn=screen_fn)
    return db, client, bridge


@pytest.mark.parametrize("age_band", ["under_13", "teen_13_17", "unknown"])
def test_mb_minor_age_gate_blocks_writes_and_signals(tmp_path: Path, age_band: AgeBand) -> None:
    """MB-11: Minor-protected accounts fail closed on write_consented and record_behavioral_signal."""
    db, client, bridge = _setup(tmp_path, f"minor_w_{age_band}.db")
    try:
        minor = _principal(f"usr_minor_{age_band}", app_id="quest", age_band=age_band)
        bridge.set_source_consent(minor, "quest", enabled=True)
        bridge.set_app_consent(minor, "quest", read_enabled=True, write_enabled=True)

        with pytest.raises(MinorProtectionError):
            bridge.write_consented(
                minor,
                MemoryRecordInput(
                    record_id="qmsg:minor1",
                    source_kind="quest",
                    source_id="quest:t1",
                    host_app="quest",
                    author_id=minor.user_id,
                    text="I like astronomy",
                    valid_time="2026-11-23T10:00:00+00:00",
                    explicit_user_confirm=True,
                ),
            )

        with pytest.raises(MinorProtectionError):
            bridge.record_behavioral_signal(
                minor,
                source_kind="quest",
                source_id="quest:t1",
                topic_slug="astronomy",
                option_key="visit_1",
                at="2026-11-23T10:00:00+00:00",
            )

        assert db.execute("SELECT COUNT(*) FROM cs_memory_record_refs WHERE owner_id = ?", (minor.user_id,)).fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM cs_two_visit_signals WHERE owner_id = ?", (minor.user_id,)).fetchone()[0] == 0
        assert client.facts.get(minor.user_id, []) == []
    finally:
        db.close()


def test_mb_no_owner_or_provenance_spoof(tmp_path: Path) -> None:
    """MB-03: Server sets owner_id and provenance; caller spoof attempts and stale generations are rejected."""
    db, client, bridge = _setup(tmp_path, "spoof.db")
    try:
        alice_q = _principal("usr_alice", app_id="quest")
        bridge.set_source_consent(alice_q, "quest", enabled=True)
        bridge.set_app_consent(alice_q, "quest", read_enabled=True, write_enabled=True)

        # Happy path: demo_data sets provenance="demo_fixture", normal sets "user_supplied",
        # and cs_memory_record_refs stores zero raw text.
        r_normal = bridge.write_consented(
            alice_q,
            MemoryRecordInput(
                record_id="qmsg:1",
                source_kind="quest",
                source_id="quest:t1",
                host_app="quest",
                author_id="usr_alice",
                text="I love specialty coffee in Alserkal",
                valid_time="2026-11-23T10:00:00+00:00",
                subject_path="food/coffee",
                explicit_user_confirm=True,
            ),
        )
        assert r_normal.owner_id == "usr_alice"
        assert r_normal.provenance == "user_supplied"
        assert r_normal.trust_tier == "T0_user_confirmed"

        r_demo = bridge.write_consented(
            alice_q,
            MemoryRecordInput(
                record_id="qmsg:demo1",
                source_kind="quest",
                source_id="quest:t1",
                host_app="quest",
                author_id="usr_alice",
                text="I enjoy desert stargazing",
                valid_time="2026-11-23T11:00:00+00:00",
                subject_path="outdoors/stargazing",
                explicit_user_confirm=True,
                demo_data=True,
            ),
        )
        assert r_demo.provenance == "demo_fixture"
        assert r_demo.trust_tier == "T3_demo_fixture"

        # Verify metadata-only cs_memory_record_refs (no text column / no text stored).
        ref_cols = [r[1] for r in db.execute("PRAGMA table_info(cs_memory_record_refs)").fetchall()]
        assert "text" not in ref_cols

        # Failure: caller attempting to override owner or provenance via subclass attributes.
        SpoofInput = make_dataclass(
            "SpoofInput",
            [("owner", str, "usr_bob"), ("provenance", str, "user_supplied")],
            bases=(MemoryRecordInput,),
            frozen=True,
        )
        with pytest.raises(ConsentDeniedError):
            bridge.write_consented(
                alice_q,
                SpoofInput(
                    record_id="qmsg:spoof1",
                    source_kind="quest",
                    source_id="quest:t1",
                    host_app="quest",
                    author_id="usr_alice",
                    text="Spoofed owner",
                    valid_time="2026-11-23T11:00:00+00:00",
                    explicit_user_confirm=True,
                ),
            )

        # Failure: cross-app spoof (quest session trying to write community host_app).
        with pytest.raises(ConsentDeniedError):
            bridge.write_consented(
                alice_q,
                MemoryRecordInput(
                    record_id="cmpost:1",
                    source_kind="community",
                    source_id="community:post:1",
                    host_app="community",
                    author_id="usr_alice",
                    text="Cross app spoof",
                    valid_time="2026-11-23T11:00:00+00:00",
                ),
            )

        # Failure: invalid source_id prefix.
        with pytest.raises(MemoryBridgeError):
            bridge.write_consented(
                alice_q,
                MemoryRecordInput(
                    record_id="qmsg:badsrc",
                    source_kind="quest",
                    source_id="gmail:123",
                    host_app="quest",
                    author_id="usr_alice",
                    text="Mismatched source_id",
                    valid_time="2026-11-23T11:00:00+00:00",
                ),
            )

        # Failure: stale expected_consent_generation rejected.
        with pytest.raises(ConsentDeniedError):
            bridge.write_consented(
                alice_q,
                MemoryRecordInput(
                    record_id="qmsg:stale",
                    source_kind="quest",
                    source_id="quest:t1",
                    host_app="quest",
                    author_id="usr_alice",
                    text="Stale generation",
                    valid_time="2026-11-23T11:00:00+00:00",
                ),
                expected_consent_generation=999,
            )
    finally:
        db.close()


def test_mb_third_party_message_rule(tmp_path: Path) -> None:
    """MB-05: Third-party messages store Record evidence only and never confirmed facts about owner."""
    db, client, bridge = _setup(tmp_path, "third_party.db")
    try:
        alice_msg = _principal("usr_alice", app_id="messenger")
        alice_comm = _principal("usr_alice", app_id="community")
        bridge.set_source_consent(alice_msg, "messenger", enabled=True)
        bridge.set_app_consent(alice_msg, "messenger", read_enabled=True, write_enabled=True)
        bridge.set_conversation_consent(alice_msg, "conv-A", ai_mode="save")
        bridge.set_source_consent(alice_comm, "community", enabled=True)
        bridge.set_app_consent(alice_comm, "community", read_enabled=True, write_enabled=True)

        group_ok = GroupConsentSnapshot("conv-A", True, True, True, 1)

        # Failure / third-party confirmation attempt rejected.
        with pytest.raises(ConsentDeniedError):
            bridge.write_consented(
                alice_msg,
                MemoryRecordInput(
                    record_id="mgmsg:spoof_confirm",
                    source_kind="messenger",
                    source_id="messenger:conv-A",
                    host_app="messenger",
                    author_id="usr_bob",
                    text="Alice loves sushi",
                    valid_time="2026-11-23T10:00:00+00:00",
                    explicit_user_confirm=True,
                ),
                group_consent=group_ok,
            )

        # Third-party unconfirmed chat message -> stored as Record evidence ONLY (zero facts).
        rec_only = bridge.write_consented(
            alice_msg,
            MemoryRecordInput(
                record_id="mgmsg:bob1",
                source_kind="messenger",
                source_id="messenger:conv-A",
                host_app="messenger",
                author_id="usr_bob",
                text="Let us meet at JBR at 7pm",
                valid_time="2026-11-23T10:05:00+00:00",
                explicit_user_confirm=False,
            ),
            group_consent=group_ok,
        )
        assert rec_only.ok is True
        assert rec_only.fact_ids == []
        assert "mgmsg:bob1" in client.records["usr_alice"]
        assert client.facts.get("usr_alice", []) == []

        # Third-party authored Community post rejected.
        with pytest.raises(ConsentDeniedError):
            bridge.write_consented(
                alice_comm,
                MemoryRecordInput(
                    record_id="cmpost:99",
                    source_kind="community",
                    source_id="community:post:99",
                    host_app="community",
                    author_id="usr_bob",
                    text="Bob's community post",
                    valid_time="2026-11-23T10:10:00+00:00",
                ),
            )
    finally:
        db.close()


def test_write_rule9_sensitive_quarantine_and_allowlist(tmp_path: Path) -> None:
    """Rule 9 allows Dubai allowlist and quarantines credentials/sensitive text with category-only audit."""
    db, client, bridge = _setup(tmp_path, "rule9.db")
    try:
        alice = _principal("usr_alice", app_id="quest")
        bridge.set_source_consent(alice, "quest", enabled=True)
        bridge.set_app_consent(alice, "quest", read_enabled=True, write_enabled=True)

        # Happy: Dubai allowlist + work-pressure passes.
        ok_rec = bridge.write_consented(
            alice,
            MemoryRecordInput(
                record_id="qmsg:allow1",
                source_kind="quest",
                source_id="quest:t1",
                host_app="quest",
                author_id="usr_alice",
                text="Renewed Golden Visa on Sheikh Zayed Road despite ضغط الشغل",
                valid_time="2026-11-23T10:00:00+00:00",
                subject_path="admin/visa",
                explicit_user_confirm=True,
            ),
        )
        assert ok_rec.ok is True and ok_rec.status == "applied" and len(ok_rec.fact_ids) == 1

        # Failure: credential quarantined even with explicit_user_confirm=True, zero secret text in audit.
        secret_text = "My OTP verification code is 918273 and IBAN AE070331234567890123456"
        q_cred = bridge.write_consented(
            alice,
            MemoryRecordInput(
                record_id="qmsg:cred1",
                source_kind="quest",
                source_id="quest:t1",
                host_app="quest",
                author_id="usr_alice",
                text=secret_text,
                valid_time="2026-11-23T10:05:00+00:00",
                explicit_user_confirm=True,
                allow_sensitive_confirmed=True,
            ),
        )
        assert q_cred.ok is False and q_cred.status == "quarantined" and q_cred.quarantine_category == "credential"
        assert "qmsg:cred1" not in client.records.get("usr_alice", {})

        audit_rows = bridge.list_audit_events(alice)
        serialized = str(audit_rows)
        assert "918273" not in serialized
        assert "AE070331234567890123456" not in serialized
        assert any(ev["outcome"] == "quarantined" and ev["receipt"].get("category") == "credential" for ev in audit_rows)
    finally:
        db.close()

    # Layer 2 ScreenUnavailable fails closed.
    def _broken_screen(_labels: list[str]) -> dict[str, str]:
        raise ScreenUnavailable("down")

    db2, _, bridge2 = _setup(tmp_path, "screen_down.db", screen_fn=_broken_screen)
    try:
        alice2 = _principal("usr_alice", app_id="quest")
        bridge2.set_source_consent(alice2, "quest", enabled=True)
        bridge2.set_app_consent(alice2, "quest", read_enabled=True, write_enabled=True)
        with pytest.raises(ScreenUnavailable):
            bridge2.write_consented(
                alice2,
                MemoryRecordInput(
                    record_id="qmsg:screen1",
                    source_kind="quest",
                    source_id="quest:t1",
                    host_app="quest",
                    author_id="usr_alice",
                    text="I enjoy desert cycling",
                    valid_time="2026-11-23T10:00:00+00:00",
                    explicit_user_confirm=True,
                ),
            )
    finally:
        db2.close()


def test_mb_two_visit_qualification(tmp_path: Path) -> None:
    """MB-06: Single click or <6h visits never qualify; >=6h or >=2 distinct days promote hypothesis."""
    db, client, bridge = _setup(tmp_path, "twovisit.db")
    try:
        alice_comm = _principal("usr_alice", app_id="community")
        alice_quest = _principal("usr_alice", app_id="quest")
        bridge.set_source_consent(alice_comm, "community", enabled=True, allow_interest_export=True)
        bridge.set_app_consent(
            alice_comm,
            "community",
            read_enabled=True,
            write_enabled=True,
            allow_interest_export_to_community=True,
        )
        bridge.set_app_consent(alice_quest, "quest", read_enabled=True, write_enabled=True)

        # Visit 1: 10:00 -> not qualified.
        s1 = bridge.record_behavioral_signal(
            alice_comm,
            source_kind="community",
            source_id="community:group:grp_cycling",
            topic_slug="desert-cycling",
            option_key="join_group",
            at="2026-11-23T08:00:00+00:00",
        )
        assert s1["qualified"] is False and s1["promoted_fact_id"] is None
        assert bridge.read_quest_hypotheses(alice_quest) == []
        assert bridge.read_community_interest_features(alice_comm) == []

        # Visit 2: 2 hours later (< 6h, same day) -> still not qualified!
        s2 = bridge.record_behavioral_signal(
            alice_comm,
            source_kind="community",
            source_id="community:post:p_cycling",
            topic_slug="desert-cycling",
            option_key="save_post",
            at="2026-11-23T10:00:00+00:00",
        )
        assert s2["qualified"] is False and s2["promoted_fact_id"] is None
        assert bridge.read_quest_hypotheses(alice_quest) == []

        # Visit 3: 7 hours after Visit 1 (>= 6h) -> qualifies and promotes as hypothesis!
        s3 = bridge.record_behavioral_signal(
            alice_comm,
            source_kind="community",
            source_id="community:group:grp_cycling",
            topic_slug="desert-cycling",
            option_key="rsvp_ride",
            at="2026-11-23T15:00:00+00:00",
        )
        assert s3["qualified"] is True and s3["promoted_fact_id"] is not None

        hyps = bridge.read_quest_hypotheses(alice_quest)
        assert len(hyps) == 1
        assert hyps[0].display_prefix == "I noticed"
        assert hyps[0].provenance == "inferred"
        assert hyps[0].status == "hypothesis"

        feats = bridge.read_community_interest_features(alice_comm)
        assert len(feats) == 1
        assert feats[0].topic_slug == "desert-cycling"
        assert feats[0].confidence_tier == "qualified_hypothesis"
    finally:
        db.close()


def test_mb_supersession_and_correction(tmp_path: Path) -> None:
    """MB-09: confirm promotes hypothesis; edit/supersede closes prior fact; reject hides immediately."""
    db, client, bridge = _setup(tmp_path, "resolve.db")
    try:
        alice_q = _principal("usr_alice", app_id="quest")
        alice_c = _principal("usr_alice", app_id="community")
        bridge.set_source_consent(alice_q, "quest", enabled=True, allow_interest_export=True)
        bridge.set_app_consent(alice_q, "quest", read_enabled=True, write_enabled=True)
        bridge.set_source_consent(alice_c, "community", enabled=True, allow_interest_export=True)
        bridge.set_app_consent(
            alice_c,
            "community",
            read_enabled=True,
            write_enabled=True,
            allow_interest_export_to_community=True,
        )

        # Create hypothesis via two-visit across 2 distinct calendar days.
        bridge.record_behavioral_signal(
            alice_c,
            source_kind="community",
            source_id="community:group:g1",
            topic_slug="padel",
            option_key="v1",
            at="2026-11-22T23:30:00+00:00",
        )
        promoted = bridge.record_behavioral_signal(
            alice_c,
            source_kind="community",
            source_id="community:group:g1",
            topic_slug="padel",
            option_key="v2",
            at="2026-11-23T00:30:00+00:00",
        )
        fid = promoted["promoted_fact_id"]
        assert fid is not None

        # Warm Community projection cache.
        assert bridge.read_community_interest_features(alice_c)[0].confidence_tier == "qualified_hypothesis"

        # 1. Confirm promotes hypothesis -> user_supplied & invalidates Community cache.
        res_conf = bridge.resolve_fact(alice_q, fid, action="confirm", host_app="quest")
        assert res_conf["status"] == "active"
        assert bridge.read_quest_hypotheses(alice_q) == []
        assert bridge.read_community_interest_features(alice_c)[0].confidence_tier == "confirmed"

        # 2. Edit / supersede closes old fact and creates replacement.
        res_edit = bridge.resolve_fact(
            alice_q,
            fid,
            action="edit",
            host_app="quest",
            new_text="Plays padel twice a week in Al Quoz",
            valid_from="2026-11-23T12:00:00+00:00",
        )
        new_fid = res_edit["new_fact_id"]
        assert res_edit["status"] == "superseded" and new_fid is not None

        # Sensitive edit fails closed.
        with pytest.raises(SensitiveContentError):
            bridge.resolve_fact(
                alice_q,
                new_fid,
                action="supersede",
                host_app="quest",
                new_text="My password is SecretPassword1!",
            )

        # 3. Reject hides immediately from timeline, search, and Community projection.
        res_rej = bridge.resolve_fact(alice_q, new_fid, action="reject", host_app="quest")
        assert res_rej["status"] == "rejected"
        assert all(v.fact_id != new_fid for v in bridge.read_quest_timeline(alice_q))
        assert bridge.read_community_interest_features(alice_c) == []
    finally:
        db.close()
