"""MB-04 tests for Rule 9 fail-closed privacy gate (`memory_bridge/sensitive.py`)."""
from __future__ import annotations

import pytest

from app.memory_bridge import (
    CATEGORIES,
    CATEGORY_LIST,
    ScreenUnavailable,
    gate_record,
    pre_write,
    screen,
)
from tests.fixtures.contest_shared.memory_fixtures import (
    SENSITIVE_MB04_MATRIX,
    SYNTH_OWNER_A,
    SYNTH_OWNER_B,
    make_record_input,
)


def test_canonical_eight_categories():
    assert len(CATEGORY_LIST) == 8
    assert CATEGORY_LIST[0] == "family_third_party"
    assert set(CATEGORY_LIST) == {"family_third_party", *CATEGORIES}
    assert set(CATEGORIES) == {
        "health",
        "religion",
        "ethnicity_nationality",
        "gender_sexuality",
        "politics",
        "third_party_private",
        "credential",
    }


@pytest.mark.parametrize(
    "text,known_people,expected",
    SENSITIVE_MB04_MATRIX,
    ids=[f"mb04_case_{i:02d}" for i in range(len(SENSITIVE_MB04_MATRIX))],
)
def test_mb04_gate_matrix(text, known_people, expected):
    assert pre_write(text, known_people=known_people) == expected


def test_credential_always_wins_and_blocks_even_when_confirmed():
    assert pre_write("My password is 123, says the doctor") == "credential"

    for cred_text in (
        "OTP 482910 for login",
        "My IBAN is AE070331234567890123456",
        "Wi-Fi key for the flat is BarshaL0bby!2026",
        "كلمة السر بتاعة الحساب هي Secret1!9",
    ):
        item = make_record_input(
            author_id=SYNTH_OWNER_A,
            text=cred_text,
            scope="owner_private",
            explicit_user_confirm=True,
            allow_sensitive_confirmed=True,
        )
        res = gate_record(item, owner_id=SYNTH_OWNER_A)
        assert res.allowed is False
        assert res.quarantined is True
        assert res.category == "credential"
        assert res.sensitive_cat is None
        # Zero leaked secret text in result fields
        assert cred_text not in repr(res)


def test_gate_record_explicit_confirm_rules():
    # Inferred / unconfirmed Rule 9 content is quarantined fail-closed
    unconfirmed = make_record_input(
        author_id=SYNTH_OWNER_A,
        text="I have high blood pressure",
        explicit_user_confirm=False,
        allow_sensitive_confirmed=False,
    )
    r_unconf = gate_record(unconfirmed, owner_id=SYNTH_OWNER_A)
    assert r_unconf.allowed is False
    assert r_unconf.quarantined is True
    assert r_unconf.category == "health"
    assert "blood pressure" not in repr(r_unconf)

    # First-person explicit owner confirmation allowed ONLY as owner_private
    confirmed = make_record_input(
        author_id=SYNTH_OWNER_A,
        text="I have high blood pressure",
        scope="owner_private",
        explicit_user_confirm=True,
        allow_sensitive_confirmed=True,
    )
    r_conf = gate_record(confirmed, owner_id=SYNTH_OWNER_A)
    assert r_conf.allowed is True
    assert r_conf.quarantined is False
    assert r_conf.effective_scope == "owner_private"
    assert r_conf.sensitive_cat == "health"

    # Cross-app or chat_scoped cannot accept confirmed sensitive content
    cross_app = make_record_input(
        author_id=SYNTH_OWNER_A,
        text="I have high blood pressure",
        scope="cross_app_interest",
        explicit_user_confirm=True,
        allow_sensitive_confirmed=True,
    )
    assert gate_record(cross_app, owner_id=SYNTH_OWNER_A).allowed is False

    # Other author (author_id != owner_id) or missing verified owner_id fails closed
    other_author = make_record_input(
        author_id=SYNTH_OWNER_B,
        text="I have high blood pressure",
        scope="owner_private",
        explicit_user_confirm=True,
        allow_sensitive_confirmed=True,
    )
    assert gate_record(other_author, owner_id=SYNTH_OWNER_A).allowed is False
    assert gate_record(confirmed, owner_id=None).allowed is False

    # family_third_party and third_party_private are NEVER confirmable
    for blocked_text, expected_cat in (
        ("Mom has high blood pressure", "family_third_party"),
        ("Someone stole my bike near the marina", "third_party_private"),
    ):
        item = make_record_input(
            author_id=SYNTH_OWNER_A,
            text=blocked_text,
            scope="owner_private",
            explicit_user_confirm=True,
            allow_sensitive_confirmed=True,
        )
        res = gate_record(item, owner_id=SYNTH_OWNER_A)
        assert res.allowed is False
        assert res.category == expected_cat


def test_gate_record_checks_text_orig_for_hidden_sensitive_content():
    item = make_record_input(
        author_id=SYNTH_OWNER_A,
        text="Met with family",
        text_orig="امي تعبانة وراحت المستشفى",
    )
    res = gate_record(item, owner_id=SYNTH_OWNER_A)
    assert res.allowed is False
    assert res.category == "family_third_party"


def test_layer2_screen_and_fail_closed_behavior(monkeypatch):
    seen: list[str] = []

    def canned(labels: list[str]) -> dict[str, str]:
        seen.extend(labels)
        return {lbl: ("health" if "treatment" in lbl else "none") for lbl in labels}

    out = screen(["treatment plan", "treatment plan", "sprint planning"], classify=canned)
    assert out == {"treatment plan": "health"}
    assert seen == ["treatment plan", "sprint planning"]

    # Skipped label -> fail-closed "unscreened"
    skipped = screen(["opaque note"], classify=lambda labels: {})
    assert skipped == {"opaque note": "unscreened"}

    # Layer 1 fallback catches credentials even when classifier returns "none"
    cred = screen(["OTP 9912"], classify=lambda labels: {"OTP 9912": "none"})
    assert cred == {"OTP 9912": "credential"}

    # Classifier exception -> ScreenUnavailable
    def boom(labels: list[str]) -> dict[str, str]:
        raise ConnectionError("classifier down")

    with pytest.raises(ScreenUnavailable):
        screen(["anything"], classify=boom)

    # Missing TM_CLASSIFIER_MODEL -> ScreenUnavailable
    monkeypatch.delenv("TM_CLASSIFIER_MODEL", raising=False)
    with pytest.raises(ScreenUnavailable):
        screen(["anything"])


def test_gate_record_layer2_integration_and_fail_closed():
    clean_item = make_record_input(text="Started a new treatment plan")

    # Layer 2 catches semantic health meaning missed by Layer 1
    res = gate_record(
        clean_item,
        owner_id=SYNTH_OWNER_A,
        screen_fn=lambda labels: {lbl: "health" for lbl in labels},
    )
    assert res.allowed is False
    assert res.category == "health"

    # Layer 2 skipped label -> blocked as unscreened
    res_skip = gate_record(
        clean_item,
        owner_id=SYNTH_OWNER_A,
        screen_fn=lambda labels: {},
    )
    assert res_skip.allowed is False
    assert res_skip.category == "unscreened"

    # Layer 2 outage -> ScreenUnavailable propagates fail-closed
    def fail_screen(labels: list[str]) -> dict[str, str]:
        raise RuntimeError("timeout")

    with pytest.raises(ScreenUnavailable):
        gate_record(clean_item, owner_id=SYNTH_OWNER_A, screen_fn=fail_screen)
