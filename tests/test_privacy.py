"""WP-C gate matrix: >= 40 synthetic cases (EN / Egyptian Arabic / Arabizi,
Dubai false positives, third-party health/faith/money, first-person logistics,
credentials). No real personal data; persona names are invented.

Convention: pre_write returns None (persist) or a content-free category.
"""
import pytest

from temporal_memory.models import Entity, FactEntity, OutFact
from temporal_memory.privacy import policy, sensitive
from temporal_memory.privacy.sensitive import ScreenUnavailable, pre_write

# (text, known_people, expected_category); None = passes the gate.
MATRIX = [
    # --- ordinary EN: persist -------------------------------------------
    ("Had lunch with Omar, he's testing the Dubai-io beta", (), None),
    ("Applied to QamarTech via LinkedIn", (), None),
    ("Bought groceries at Carrefour for 120 AED", (), None),
    ("Flight to Cairo on 1 Dec", (), None),
    ("Gym session: push pull legs split", (), None),
    ("Raseef milestone: beta ready", (), None),
    ("Omar installed the beta on 26 Oct", ("Omar",), None),
    ("Meeting with Sara about the Atlas API", ("Sara",), None),
    # --- Dubai allowlist: persist ----------------------------------------
    ("Sheikh Zayed Road is closed", (), None),
    ("My Golden Visa was approved", (), None),
    ("Paid via Dubai Police app for the fine", (), None),
    ("Green Visa renewal in January", (), None),
    ("The government entity portal is down", (), None),
    # --- third-party health/faith/relationship/money: family_third_party --
    ("Mom has high blood pressure", (), "family_third_party"),
    ("My father takes heart medication", (), "family_third_party"),
    ("Omar was diagnosed with diabetes", ("Omar",), "family_third_party"),
    ("She is fasting for Ramadan", (), "family_third_party"),
    ("My sister's divorce was finalised", (), "family_third_party"),
    ("Ahmed earns 20000 salary", ("Ahmed",), "family_third_party"),
    ("His loan was rejected", (), "family_third_party"),
    ("My colleague fasts during Ramadan", (), "family_third_party"),
    ("Omar was arrested last night", ("Omar",), "family_third_party"),
    ("Dubai Police arrested my neighbour", (), "family_third_party"),
    ("امي تعبانة وراحت المستشفى", (), "family_third_party"),
    ("ابويا عنده السكر", (), "family_third_party"),
    ("مراته رفعت عليه قضية", (), "family_third_party"),
    # --- non-family third-party private content: still blocked ------------
    ("Someone stole my bike near the marina", (), "third_party_private"),
    # --- faith content without a person: held for review, not family ------
    ("Sheikh Ahmed donated to the mosque", (), "religion"),
    # --- self health/politics/visa: held for review, not family -----------
    ("I have high blood pressure", (), "health"),
    ("Voted in the election", (), "politics"),
    ("My visa expires in March", (), "ethnicity_nationality"),
    ("دكتور الأسنان قالي أعمل تقويم", (), "health"),
    # --- credentials: always blocked --------------------------------------
    ("My Wi-Fi password is Dubai1234", (), "credential"),
    ("OTP 482910 for login", (), "credential"),
    ("كلمة السر بتاعة الحساب", (), "credential"),
    ("My Emirates ID number is 784-1990-1234567-1", (), "credential"),
    # --- first-person logistics the user stated: persist ------------------
    ("Mom visits 1 Dec", (), None),
    ("I'm running a half marathon", (), None),
    ("انا مسافر دبي يوم الجمعة", (), None),
    ("I took a loan for the car", (), None),
    ("I paid the DEWA bill, 340 AED", (), None),
    # --- Arabic boundary traps: persist -----------------------------------
    ("ضغط شغل كبير الشهر ده", (), None),
    ("بتصحي بدري عشان الشغل", (), None),
    ("شاي بسكر قليل", (), None),
    # --- Arabizi mix -------------------------------------------------------
    ("mom is sick, fel mostashfa", (), "family_third_party"),
    ("el password beta3 el wifi", (), "credential"),
]


@pytest.mark.parametrize("text,known,expected", MATRIX,
                         ids=[f"case{i:02d}" for i in range(len(MATRIX))])
def test_gate_matrix(text, known, expected):
    assert pre_write(text, known_people=known) == expected


def test_matrix_size_floor():
    assert len(MATRIX) >= 40


def test_single_categories_list():
    assert sensitive.CATEGORY_LIST[0] == "family_third_party"
    assert set(sensitive.CATEGORY_LIST) == {"family_third_party", *sensitive.CATEGORIES}
    assert "credential" in sensitive.CATEGORIES


def test_credential_wins_over_other_hits():
    assert pre_write("My password is 123, says the doctor") == "credential"


# ------------------------------------------------------------- may_promote
def _ent(kind="person", relation=None):
    return Entity(id="e1", owner="o1", kind=kind, name="X", relation_to_user=relation)


def test_promote_self_two_days():
    assert policy.may_promote(_ent(relation="self"), 2, False) is True


def test_promote_self_one_day_no_confirm():
    assert policy.may_promote(_ent(relation="self"), 1, False) is False


def test_promote_user_owned_place_two_days():
    assert policy.may_promote(_ent(kind="place"), 2, False) is True


def test_promote_org_needs_two_days():
    assert policy.may_promote(_ent(kind="org"), 1, False) is False


def test_third_party_person_never_auto_promotes():
    assert policy.may_promote(_ent(relation="friend"), 30, False) is False


def test_unknown_relation_person_is_third_party():
    assert policy.may_promote(_ent(relation=None), 30, False) is False


def test_third_party_promotes_on_user_tap():
    assert policy.may_promote(_ent(relation="friend"), 1, True) is True


# --------------------------------------------------------------- gate_fact
def _fact(text, worker_refs=(), text_orig=None):
    return OutFact(text=text, text_orig=text_orig, subject_path="life/general",
                   entities=[FactEntity(entity_id=r) for r in worker_refs],
                   op="new", target=None, valid_from="2026-10-26", evidence=["wab-0001"],
                   sensitive=None)


def test_gate_fact_ordinary_internal_passes_without_model():
    assert policy.gate_fact(_fact("Had lunch with Omar"), "internal-cloud") is None


def test_gate_fact_credential_blocked_for_every_worker():
    for kind in ("internal-cloud", "internal-local", "agent-cli", "owner-hook"):
        assert policy.gate_fact(_fact("OTP 482910 for login"), kind) == "credential"


def test_gate_fact_third_party_layer1_no_model_needed():
    f = _fact("Mom has high blood pressure")
    assert policy.gate_fact(f, "internal-cloud") == "family_third_party"


def test_gate_fact_layer2_only_for_untrusted_workers():
    f = _fact("Omar started a new treatment plan", worker_refs=("new:Omar",))

    def canned(labels):
        return {t: "health" for t in labels}

    import temporal_memory.privacy.policy as pol

    orig = sensitive.screen
    calls = []
    try:
        pol.screen = lambda labels: (calls.append(labels), canned(labels))[1]
        assert pol.gate_fact(f, "agent-cli") == "health"
        assert pol.gate_fact(f, "owner-hook") == "health"
        assert len(calls) == 2
        assert pol.gate_fact(f, "internal-cloud") is None
        assert len(calls) == 2
    finally:
        pol.screen = orig


def test_gate_fact_layer2_fail_closed_on_classifier_outage():
    import temporal_memory.privacy.policy as pol

    orig = pol.screen
    try:
        def boom(labels):
            raise ScreenUnavailable("down")

        pol.screen = boom
        with pytest.raises(ScreenUnavailable):
            pol.gate_fact(_fact("Omar started a new treatment plan",
                                worker_refs=("new:Omar",)), "agent-cli")
    finally:
        pol.screen = orig


# ------------------------------------------------------------------- screen
def test_screen_pluggable_classifier_and_dedup():
    seen = []

    def canned(labels):
        seen.extend(labels)
        return {t: ("health" if t == labels[0] else "none") for t in labels}

    out = sensitive.screen(["a b", "a b", "plain work note"], classify=canned)
    assert out == {"a b": "health"}
    assert seen == ["a b", "plain work note"]


def test_screen_skipped_label_is_blocking():
    out = sensitive.screen(["mystery label"], classify=lambda labels: {})
    assert out == {"mystery label": "unscreened"}


def test_screen_classifier_exception_is_fail_closed():
    def boom(labels):
        raise ConnectionError("no route")

    with pytest.raises(ScreenUnavailable):
        sensitive.screen(["anything"], classify=boom)


def test_screen_layer1_fallback_when_classifier_clears():
    out = sensitive.screen(["OTP 9912"], classify=lambda labels: {"OTP 9912": "none"})
    assert out == {"OTP 9912": "credential"}


def test_screen_default_classifier_needs_model_env(monkeypatch):
    monkeypatch.delenv("TM_CLASSIFIER_MODEL", raising=False)
    with pytest.raises(ScreenUnavailable):
        sensitive.screen(["anything"])
