"""Synthetic test fixtures for CS-B2 memory_bridge tests (no real user data)."""
from __future__ import annotations

from pathlib import Path

from app import db as db_mod
from app.memory_bridge.fake_client import FakeTemporalMemoryClient
from app.memory_bridge.models import MemoryRecordInput
from app.memory_bridge.schema import ensure_memory_bridge_schema

SYNTH_OWNER_A = "usr_synth_alpha"
SYNTH_OWNER_B = "usr_synth_beta"


def make_sqlite_db(tmp_path: Path, name: str = "cs_b2.db"):
    db = db_mod.connect(tmp_path / name)
    ensure_memory_bridge_schema(db)
    return db


def make_seeded_fake_client() -> FakeTemporalMemoryClient:
    client = FakeTemporalMemoryClient()
    client.ensure_owner(SYNTH_OWNER_A, label="Synth Alpha", display_name="Alpha Test")
    client.ensure_owner(SYNTH_OWNER_B, label="Synth Beta", display_name="Beta Test")

    # Owner A: Quest note + two Messenger chats + multi-source fact
    client.upsert_record_and_enqueue(
        SYNTH_OWNER_A,
        record_id="qmsg:q-1",
        source="quest:thread-1",
        at="2026-11-20T09:00:00Z",
        author=SYNTH_OWNER_A,
        text="Alpha works on Dubai Chambers backend sprints.",
        enqueue="none",
        direct_fact={
            "id": "fact-q-1",
            "text": "Alpha works on Dubai Chambers backend sprints.",
            "subject_path": "career/dubai-chambers",
            "valid_from": "2026-11-20T09:00:00Z",
            "evidence": ["qmsg:q-1"],
            "provenance": "user_supplied",
        },
    )
    client.upsert_record_and_enqueue(
        SYNTH_OWNER_A,
        record_id="mgmsg:m-a1",
        source="messenger:conv-a",
        at="2026-11-21T10:00:00Z",
        author=SYNTH_OWNER_A,
        text="Shipped chat milestone for conv-a.",
        enqueue="extract.live",
        direct_fact={
            "id": "fact-mg-a1",
            "text": "Shipped chat milestone for conv-a.",
            "subject_path": "projects/conv-a",
            "valid_from": "2026-11-21T10:00:00Z",
            "evidence": ["mgmsg:m-a1"],
            "provenance": "user_supplied",
        },
    )
    client.upsert_record_and_enqueue(
        SYNTH_OWNER_A,
        record_id="mgmsg:m-b1",
        source="messenger:conv-b",
        at="2026-11-21T11:00:00Z",
        author=SYNTH_OWNER_A,
        text="Reviewed conv-b budget plan.",
        enqueue="none",
        direct_fact={
            "id": "fact-mg-b1",
            "text": "Reviewed conv-b budget plan.",
            "subject_path": "projects/conv-b",
            "valid_from": "2026-11-21T11:00:00Z",
            "evidence": ["mgmsg:m-b1"],
            "provenance": "user_supplied",
        },
    )
    # Owner B: completely separate owner
    client.upsert_record_and_enqueue(
        SYNTH_OWNER_B,
        record_id="qmsg:b-1",
        source="quest:thread-b",
        at="2026-11-22T08:00:00Z",
        author=SYNTH_OWNER_B,
        text="Beta prefers cycling in Al Qudra.",
        enqueue="none",
        direct_fact={
            "id": "fact-b-1",
            "text": "Beta prefers cycling in Al Qudra.",
            "subject_path": "lifestyle/cycling",
            "valid_from": "2026-11-22T08:00:00Z",
            "evidence": ["qmsg:b-1"],
            "provenance": "user_supplied",
        },
    )
    return client


def make_record_input(
    *,
    record_id: str = "qmsg:100",
    source_kind: str = "quest",
    source_id: str = "quest:t1",
    host_app: str = "quest",
    author_id: str = SYNTH_OWNER_A,
    text: str = "Working on backend unit tests.",
    text_orig: str | None = None,
    scope: str = "owner_private",
    explicit_user_confirm: bool = False,
    allow_sensitive_confirmed: bool = False,
) -> MemoryRecordInput:
    return MemoryRecordInput(
        record_id=record_id,
        source_kind=source_kind,  # type: ignore[arg-type]
        source_id=source_id,
        host_app=host_app,  # type: ignore[arg-type]
        author_id=author_id,
        text=text,
        valid_time="2026-11-23T12:00:00Z",
        scope=scope,  # type: ignore[arg-type]
        text_orig=text_orig,
        explicit_user_confirm=explicit_user_confirm,
        allow_sensitive_confirmed=allow_sensitive_confirmed,
    )


# Synthetic MB-04 matrix: (text, known_people, expected_category_or_none)
SENSITIVE_MB04_MATRIX: list[tuple[str, tuple[str, ...], str | None]] = [
    # Ordinary clean EN
    ("Had lunch with Omar, testing the Dubai-io beta", (), None),
    ("Bought groceries at Carrefour for 120 AED", (), None),
    ("Raseef milestone: beta ready", (), None),
    ("Omar installed the beta on 26 Oct", ("Omar",), None),
    # Dubai allowlist
    ("Sheikh Zayed Road is closed", (), None),
    ("My Golden Visa was approved", (), None),
    ("Blue Visa application submitted", (), None),
    ("Green Visa renewal in January", (), None),
    ("Paid via Dubai Police app for the fine", (), None),
    ("The government entity portal is down", (), None),
    # Work-pressure & Arabic boundary traps (clean)
    ("ضغط شغل كبير الشهر ده", (), None),
    ("ضغط العمل زاد الأسبوع ده", (), None),
    ("ضَغْطُ الشُّغْلِ عالي", (), None),
    ("بتصحي بدري عشان الشغل", (), None),
    ("شاي بسكر قليل", (), None),
    # Arabic sensitive traps
    ("عندي ضغط الدم مرتفع", (), "health"),
    ("دكتور الأسنان قالي أعمل تقويم", (), "health"),
    ("امي تعبانة وراحت المستشفى", (), "family_third_party"),
    ("ابويا عنده السكر", (), "family_third_party"),
    ("مراته رفعت عليه قضية", (), "family_third_party"),
    ("كلمة السر بتاعة الحساب", (), "credential"),
    # Arabizi traps
    ("mom is sick, fel mostashfa", (), "family_third_party"),
    ("my brother went for 3omra", (), "family_third_party"),
    ("el basword beta3 el wifi", (), "credential"),
    # Non-family / self Rule 9 categories
    ("I have high blood pressure", (), "health"),
    ("Sheikh Ahmed donated to the mosque", (), "religion"),
    ("My visa expires in March", (), "ethnicity_nationality"),
    ("Voted in the election", (), "politics"),
    ("Someone stole my bike near the marina", (), "third_party_private"),
    ("Dubai Police arrested my neighbour", (), "family_third_party"),
    # Credentials & Wi-Fi / token heuristics
    ("My Wi-Fi password is Dubai1234", (), "credential"),
    ("OTP 482910 for login", (), "credential"),
    ("wifi: BarshaL0bby!2026", (), "credential"),
    ("Wi-Fi key for the flat is BarshaL0bby!2026", (), "credential"),
    ("Token is Abcdef1!99", (), "credential"),
    ("the Wi-Fi was slow", (), None),
    ("Time: 12:30", (), None),
]
