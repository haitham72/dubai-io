"""Tests for weekly reflect_week hypotheses, multi-day guard, trivia filter, and Rule 9 privacy."""
from __future__ import annotations

import json

from temporal_memory.api import export_md
from temporal_memory.reflect import reflect_week
from tests.fixtures.fake_store import FakeGraphStore


def test_reflect_week_enforces_two_days_trivia_and_rule9():
    st = FakeGraphStore.from_karim_slice()

    canned = json.dumps({
        "user_md": "# USER Profile",
        "claims": [
            # Valid: spans f008 (2026-10-23) and f010 (2026-11-09) after widening or week1 f001 (10-20) + f008 (10-23)
            {"section": "Values", "text": "Values close friendships and organizing Omar's wedding.", "evidence": ["f001", "f008"]},
            # Invalid: single distinct day (both f001 and f003 are 2026-10-20)
            {"section": "Identity", "text": "Prefers Al Barsha apartments.", "evidence": ["f001", "f003"]},
            # Invalid: Rule 9 health/religion must never be inferred
            {"section": "Identity", "text": "Visits the mosque for Ramadan prayers and diabetes checkups.", "evidence": ["f001", "f008"]},
        ],
        "milestones": [
            # Valid multi-day milestone (f008 on 10-23, f015 on 10-22)
            {"title": "Support Omar Farouk wedding prep", "subject_path": "quests/wedding-prep", "state": "in_progress", "evidence": ["f008", "f015"]},
            # Invalid: trivia OTP / subscription / delivery must be rejected
            {"title": "Verify SkillForge OTP login code", "subject_path": "quests/otp", "state": "done", "evidence": ["f008", "f015"]},
            {"title": "Track Aramex delivery parcel", "subject_path": "quests/delivery", "state": "done", "evidence": ["f008", "f015"]},
            # Invalid: single-day milestone rejected
            {"title": "One-day test task", "subject_path": "quests/single", "state": "planned", "evidence": ["f001", "f003"]},
            # Invalid: Rule 9 sensitive category
            {"title": "Complete thyroid diabetes lab test", "subject_path": "quests/health", "state": "in_progress", "evidence": ["f008", "f015"]},
        ],
    })

    verdict = reflect_week(
        "karim",
        "2026-10-20",
        store=st,
        runner_fn=lambda _bundle, _runner, _model: canned,
    )

    assert verdict.ok is True
    assert "insufficient_distinct_days" in verdict.reasons
    assert "trivia_milestone_rejected" in verdict.reasons
    assert "sensitive_never_inferred" in verdict.reasons
    assert verdict.quarantined  # caught health/religion attempts

    # Only 1 hypothesis claim persisted (status='hypothesis', provenance='inferred')
    assert len(verdict.applied_fact_ids) == 1
    hyps = [f for f in st.visible_facts("karim", limit=100) if f.status == "hypothesis"]
    assert len(hyps) == 1
    assert hyps[0].provenance == "inferred"
    assert hyps[0].text.startswith("I noticed")

    # Only the legitimate multi-day milestone added; trivia/single-day/sensitive rejected
    titles = [m.title for m in st.list_milestones("karim")]
    assert "Support Omar Farouk wedding prep" in titles
    assert "Verify SkillForge OTP login code" not in titles
    assert "Track Aramex delivery parcel" not in titles
    assert "One-day test task" not in titles
    assert "Complete thyroid diabetes lab test" not in titles

    # Surfaced in noticed.md
    tree = export_md.render("karim", store=st)
    assert "I noticed Values close friendships" in tree["_staging/hypotheses-to-confirm.md"]


def test_reflect_week_excludes_forgotten_facts():
    st = FakeGraphStore.from_karim_slice()
    st.forget_source("karim", ["wab-0032"])  # forgets f008!

    canned = json.dumps({
        "user_md": "",
        "claims": [
            {"section": "Values", "text": "Values close friendships.", "evidence": ["f001", "f008"]},
        ],
        "milestones": [],
    })
    verdict = reflect_week("karim", "2026-10-20", store=st, runner_fn=lambda _b, _r, _m: canned)
    # Since f008 was forgotten, only f001 remains (1 fact, 1 day) -> rejected!
    assert verdict.applied_fact_ids == []
    assert "insufficient_distinct_days" in verdict.reasons
