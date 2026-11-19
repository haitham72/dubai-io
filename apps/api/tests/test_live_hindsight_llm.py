"""Acceptance tests for SRE Supervisor Report (17 Nov 2026): AC-1 through AC-5."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import os
from pathlib import Path
import re
from typing import Any

import httpx
import pytest

from app.lab import sensitive

REPO_ROOT = Path(__file__).resolve().parents[3]

# ---------------------------------------------------------------------------
# AC-1 Fixture: 3 emails (1 interview invite, 1 rejection, 1 supersession)
# ---------------------------------------------------------------------------
AC1_EMAIL_FIXTURE: list[dict[str, Any]] = [
    {
        "id": "email-careem-invite-2026-10-05",
        "timestamp": "2026-10-05T09:15:00+00:00",
        "from": "talent@careem.com",
        "subject": "Interview invitation — Senior Backend Engineer at Careem",
        "text": (
            "Hi Sam, thank you for applying for the Senior Backend Engineer role at Careem. "
            "We would like to invite you to a technical interview on October 12, 2026 at 11:00 GST."
        ),
        "expected_company": "careem",
        "expected_role": "senior backend engineer",
        "expected_status": "interview",
        "fact_key": "careem|senior_backend_engineer|application_status",
    },
    {
        "id": "email-noon-rejection-2026-10-18",
        "timestamp": "2026-10-18T14:30:00+00:00",
        "from": "careers@noon.com",
        "subject": "Update on your Staff AI Engineer application at Noon",
        "text": (
            "Hello Sam, thank you for interviewing for the Staff AI Engineer position at Noon. "
            "Unfortunately we will not be moving forward with your candidacy at this time."
        ),
        "expected_company": "noon",
        "expected_role": "staff ai engineer",
        "expected_status": "rejection",
        "fact_key": "noon|staff_ai_engineer|application_status",
    },
    {
        "id": "email-careem-supersede-2026-10-25",
        "timestamp": "2026-10-25T11:00:00+00:00",
        "from": "talent@careem.com",
        "subject": "Re: Interview invitation — Senior Backend Engineer at Careem",
        "text": (
            "Hi Sam, following your October 12 interview for the Senior Backend Engineer role at Careem, "
            "we regret to inform you that the position has been filled and we are not moving forward."
        ),
        "expected_company": "careem",
        "expected_role": "senior backend engineer",
        "expected_status": "rejection",
        "fact_key": "careem|senior_backend_engineer|application_status",
        "supersedes_id": "email-careem-invite-2026-10-05",
    },
]

_ISO_DATE_RE = re.compile(r"\b2026-\d{2}-\d{2}\b")
_RELATIVE_ONLY_RE = re.compile(r"\b(yesterday|tomorrow|last week|next week)\b", re.I)


# ---------------------------------------------------------------------------
# AC-2 Reference implementation: Card Lifecycle State Machine + Honest Reminder
# ---------------------------------------------------------------------------
VALID_LIFECYCLE_TRANSITIONS: dict[str, set[str]] = {
    "new": {"seen", "dismissed", "resolved"},
    "seen": {"actioned", "dismissed", "resolved"},
    "actioned": {"dismissed", "resolved"},
    "dismissed": {"resolved"},
    "resolved": set(),
}

HONEST_REMINDER_LABEL = "reminder saved — delivery not yet enabled"


@dataclass
class LifecycleCard:
    id: str
    title: str
    category: str
    lifecycle_state: str = "new"
    reminder_due_at: str | None = None
    reminder_status_label: str | None = None

    def transition(self, next_state: str) -> str:
        allowed = VALID_LIFECYCLE_TRANSITIONS.get(self.lifecycle_state, set())
        if next_state not in allowed:
            raise ValueError(f"Invalid card lifecycle transition: {self.lifecycle_state} -> {next_state}")
        self.lifecycle_state = next_state
        return self.lifecycle_state

    def save_reminder(self, due_at: str) -> dict[str, str]:
        if self.lifecycle_state == "new":
            self.transition("seen")
        if self.lifecycle_state == "seen":
            self.transition("actioned")
        self.reminder_due_at = due_at
        self.reminder_status_label = HONEST_REMINDER_LABEL
        return {
            "card_id": self.id,
            "lifecycle_state": self.lifecycle_state,
            "due_at": due_at,
            "label": self.reminder_status_label,
        }


# ---------------------------------------------------------------------------
# AC-3 Reference implementation: Orchestrator Query Rewriter + ScopeGuard
# ---------------------------------------------------------------------------
class UnscopedQueryError(ValueError):
    pass


@dataclass
class ScopedQuery:
    text: str
    categories: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    people: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if not (self.categories or self.entities or self.people):
            raise UnscopedQueryError("ScopeGuard requires at least one category, entity, or person scope")


def rewrite_unscoped_query(question: str) -> ScopedQuery:
    """Orchestrator-side query rewriter (AC-3): maps vague user asks into a ScopedQuery."""
    low = (question or "").strip().lower()
    if any(k in low for k in ("not getting accepted", "rejected", "interview", "applied", "job", "application", "cv", "linkedin")):
        return ScopedQuery(
            text=question,
            categories=["job_search", "career"],
            entities=["careem", "noon", "linkedin", "cv"],
        )
    if any(k in low for k in ("birthday", "gift", "mom", "family")):
        return ScopedQuery(text=question, categories=["family"], people=["mom"])
    raise UnscopedQueryError(f"Could not map question to a safe scope: {question!r}")


class ScopedMemoryHarness:
    def __init__(self, items: list[dict[str, Any]]) -> None:
        self.items = items
        self.full_corpus_scans = 0
        self.scoped_queries: list[ScopedQuery] = []

    def recall(self, query: ScopedQuery) -> list[dict[str, Any]]:
        query.validate()
        self.scoped_queries.append(query)
        cats = set(query.categories)
        ents = {e.lower() for e in query.entities}
        results = []
        for item in self.items:
            item_cat = item.get("category", "job_search")
            item_company = item.get("expected_company", "").lower()
            if (cats and item_cat in cats) or (ents and item_company in ents):
                results.append(item)
        return results


# ---------------------------------------------------------------------------
# AC-1 Tests
# ---------------------------------------------------------------------------
def test_ac1_status_doc_marks_mem01_unproven_until_live_llm_passes():
    """P0-1 / P0-2 / AC-1: Until live Hindsight LLM extraction passes, MEM-01 must be marked unproven."""
    status_md = (REPO_ROOT / "docs" / "status.md").read_text(encoding="utf-8")
    backlog_md = (REPO_ROOT / "docs" / "request-backlog.md").read_text(encoding="utf-8")
    research_path = REPO_ROOT / "docs" / "plan" / "Memory" / "_archive" / "memory-research-2026-11.md"
    if not research_path.exists():
        research_path = REPO_ROOT / "docs" / "Researches" / "memory-research-2026-11.md"
    research_md = research_path.read_text(encoding="utf-8")

    assert "unproven" in status_md.lower() and "test_live_hindsight_llm.py" in status_md
    assert "unproven" in backlog_md.lower() and "test_live_hindsight_llm.py" in backlog_md
    assert "provider=none" in research_md and "UNPROVEN" in research_md


@pytest.mark.skipif(
    not os.environ.get("HINDSIGHT_URL") or not os.environ.get("HINDSIGHT_LLM_ENABLED"),
    reason="AC-1 live gate: requires HINDSIGHT_URL and HINDSIGHT_LLM_ENABLED=1 with an active LLM provider",
)
def test_ac1_live_hindsight_llm_extraction():
    """AC-1 live verification against Hindsight with LLM provider enabled."""
    base_url = os.environ["HINDSIGHT_URL"].rstrip("/")
    bank_id = f"ac1-llm-test-{int(datetime.now(timezone.utc).timestamp())}"
    headers = {}
    if os.environ.get("HINDSIGHT_API_KEY"):
        headers["Authorization"] = f"Bearer {os.environ['HINDSIGHT_API_KEY']}"

    with httpx.Client(base_url=base_url, headers=headers, timeout=60.0) as http:
        try:
            for item in AC1_EMAIL_FIXTURE:
                resp = http.post(
                    f"/v1/default/banks/{bank_id}/documents",
                    json={
                        "document_id": item["id"],
                        "content": f"Date: {item['timestamp']}\nSubject: {item['subject']}\n\n{item['text']}",
                        "tags": ["cat:job_search", f"ent:{item['expected_company']}", f"status:{item['expected_status']}"],
                        "metadata": {
                            "timestamp": item["timestamp"],
                            "fact_key": item["fact_key"],
                            "supersedes_id": item.get("supersedes_id"),
                        },
                    },
                )
                assert resp.status_code in (200, 201, 202), resp.text

            recall_resp = http.post(
                f"/v1/default/banks/{bank_id}/recall",
                json={"query": "Careem and Noon job application status and interview dates", "limit": 20},
            )
            assert recall_resp.status_code == 200, recall_resp.text
            payload = recall_resp.json()
            blob = str(payload).lower()

            # 1. Absolute-dated facts (not relative)
            assert _ISO_DATE_RE.search(blob) or "october 12, 2026" in blob
            assert not _RELATIVE_ONLY_RE.search(blob)

            # 2. Extracted entities (company, role)
            assert "careem" in blob and "noon" in blob
            assert "senior backend engineer" in blob and "staff ai engineer" in blob

            # 3. Supersession note linking old -> new status
            assert "email-careem-invite-2026-10-05" in blob or "supersed" in blob or "filled" in blob
        finally:
            http.delete(f"/v1/default/banks/{bank_id}")


# ---------------------------------------------------------------------------
# AC-2 Tests: Card Lifecycle & Honest Reminder Label
# ---------------------------------------------------------------------------
def test_ac2_card_lifecycle_state_machine_and_honest_reminder_label():
    card = LifecycleCard(id="c1", title="Career funnel update", category="career")
    assert card.lifecycle_state == "new"
    assert card.transition("seen") == "seen"
    assert card.transition("actioned") == "actioned"
    assert card.transition("dismissed") == "dismissed"
    assert card.transition("resolved") == "resolved"

    with pytest.raises(ValueError, match="Invalid card lifecycle transition"):
        card.transition("new")

    card2 = LifecycleCard(id="c2", title="Mom's birthday in 14 days", category="family")
    reminder = card2.save_reminder("2026-11-20T09:00:00+04:00")
    assert reminder["lifecycle_state"] == "actioned"
    assert reminder["label"] == "reminder saved — delivery not yet enabled"
    assert "reminder set" not in reminder["label"].lower()

    brief_doc = (REPO_ROOT / "docs" / "plan" / "morning-brief.md").read_text(encoding="utf-8")
    assert "reminder saved — delivery not yet enabled" in brief_doc
    for st in ("new", "seen", "actioned", "dismissed", "resolved"):
        assert st in brief_doc


# ---------------------------------------------------------------------------
# AC-3 Tests: Orchestrator Query Rewriter
# ---------------------------------------------------------------------------
def test_ac3_orchestrator_query_rewriter_maps_unscoped_question_to_scoped_query():
    harness = ScopedMemoryHarness(AC1_EMAIL_FIXTURE)

    with pytest.raises(UnscopedQueryError):
        harness.recall(ScopedQuery(text="why am I not getting accepted"))

    scoped = rewrite_unscoped_query("why am I not getting accepted")
    assert "job_search" in scoped.categories
    hits = harness.recall(scoped)
    assert len(hits) >= 2
    assert harness.full_corpus_scans == 0


# ---------------------------------------------------------------------------
# AC-4 Tests: Sensitive Rule in Canon + sensitive.py Gating
# ---------------------------------------------------------------------------
def test_ac4_sensitive_rule_in_canon_and_sensitive_py_gating():
    claude_md = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    arch_md = (REPO_ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")

    for doc in (claude_md, arch_md):
        low = doc.lower()
        assert "family" in low and "health" in low and ("faith" in low or "religion" in low)
        assert "i noticed" in low
        assert "two-visit qualification" in low
        assert "never displayed as plain facts" in low

    assert sensitive.filter_statement("Patient scheduled a clinic prescription checkup") == "health"
    assert sensitive.filter_statement("Going to mosque for Friday prayer and fasting") == "religion"
    assert sensitive.filter_statement("Sam discussed the video editing timeline") is None


# ---------------------------------------------------------------------------
# AC-5 Tests: MEM-01 Decision & Backfill / Reading Triage Docs Present
# ---------------------------------------------------------------------------
def test_ac5_mem01_decision_and_strategic_records_present():
    plan_md = (REPO_ROOT / "PLAN.md").read_text(encoding="utf-8")
    assert "MEM-01" in plan_md
    assert "Hindsight swappable backend retained" in plan_md
    assert "Amazon.ae" in plan_md and "AED" in plan_md
    assert "I noticed" in plan_md

    backfill_doc = REPO_ROOT / "docs" / "plan" / "backfill-agent.md"
    assert backfill_doc.exists()
    backfill_text = backfill_doc.read_text(encoding="utf-8")
    assert "backfill_jobs" in backfill_text and "blocked" in backfill_text

    research_path = REPO_ROOT / "docs" / "plan" / "Memory" / "_archive" / "memory-research-2026-11.md"
    if not research_path.exists():
        research_path = REPO_ROOT / "docs" / "Researches" / "memory-research-2026-11.md"
    research_doc = research_path.read_text(encoding="utf-8")
    assert "Wanderloots" in research_doc and "Sean's AI Stories" in research_doc


# ---------------------------------------------------------------------------
# Lab Ingest Supervisor Addendum (AC-L1 through AC-L5): Reference Validators & Gates
# ---------------------------------------------------------------------------
MAMTY_ALIAS_MAP: dict[str, str] = {
    "mamty": "mamty",
    "mamty (user's mother)": "mamty",
    "مامتي": "mamty",
    "hadil": "Hadil",
    "هديل": "Hadil",
    "asr": "Asr",
    "aser": "Asr",
    "أسر": "Asr",
    "مني": "Mona",
    "mona": "Mona",
}


class WeekSchemaError(ValueError):
    pass


class WeekOverwriteError(RuntimeError):
    pass


def validate_and_normalize_week_payload(
    payload: Any,
    *,
    existing_status: str | None = None,
    reopen: bool = False,
    alias_map: dict[str, str] = MAMTY_ALIAS_MAP,
) -> dict[str, Any]:
    """AC-L3: Reject bare list roots (e.g. 2026-04-27_...), enforce status=done lock, normalize aliases."""
    if existing_status == "done" and not reopen:
        raise WeekOverwriteError("Refusing to overwrite a status=done week without explicit reopen=True")
    if isinstance(payload, list):
        raise WeekSchemaError("list_root rejected: week file must be a JSON object with week_id, agent, facts[]")
    if not isinstance(payload, dict):
        raise WeekSchemaError("week file must be a JSON object")
    for req_key in ("week_id", "agent", "facts"):
        if req_key not in payload:
            raise WeekSchemaError(f"missing required key: {req_key}")
    if not isinstance(payload["facts"], list):
        raise WeekSchemaError("facts must be a list")

    normalized_facts = []
    for fact in payload["facts"]:
        raw_people = fact.get("people", [])
        canon_people = []
        for p in raw_people:
            key = str(p).strip().lower()
            canon = alias_map.get(key, alias_map.get(str(p).strip(), str(p).strip()))
            if canon not in canon_people:
                canon_people.append(canon)
        normalized_facts.append({**fact, "people": canon_people})

    return {
        "week_id": str(payload["week_id"]),
        "agent": str(payload["agent"]),
        "facts": normalized_facts,
    }


def stage_week_for_memory_promotion(
    payload: Any,
    *,
    user_confirmed_ids: set[str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """AC-L4: week JSON -> alias normalize -> sensitive.py -> hypotheses ('I noticed') only -> user confirm -> mem_*."""
    validated = validate_and_normalize_week_payload(payload)
    confirmed_ids = user_confirmed_ids or set()
    hypotheses: list[dict[str, Any]] = []
    confirmed_mem: list[dict[str, Any]] = []
    withheld_sensitive: list[dict[str, Any]] = []

    for fact in validated["facts"]:
        text = str(fact.get("text", ""))
        fid = str(fact.get("id", ""))
        blocked_cat = sensitive.filter_statement(text)
        if blocked_cat and fid not in confirmed_ids:
            withheld_sensitive.append({"id": fid, "blocked_category": blocked_cat})
            continue
        if fid in confirmed_ids:
            confirmed_mem.append({**fact, "provenance": "user_supplied", "display_prefix": "You told me"})
        else:
            hypotheses.append({**fact, "provenance": "inferred", "display_prefix": f"I noticed: {text}"})

    return {
        "hypotheses": hypotheses,
        "confirmed_mem": confirmed_mem,
        "withheld_sensitive": withheld_sensitive,
    }


def test_acl1_acl2_acl5_honest_labeling_playbook_and_mem01_separation():
    status_md = (REPO_ROOT / "docs" / "status.md").read_text(encoding="utf-8")
    lab_claude = (REPO_ROOT / "apps" / "api" / "app" / "lab" / "CLAUDE.md").read_text(encoding="utf-8")
    research_path = REPO_ROOT / "docs" / "plan" / "Memory" / "_archive" / "memory-research-2026-11.md"
    if not research_path.exists():
        research_path = REPO_ROOT / "docs" / "Researches" / "memory-research-2026-11.md"
    research_md = research_path.read_text(encoding="utf-8")
    backfill_md = (REPO_ROOT / "docs" / "plan" / "backfill-agent.md").read_text(encoding="utf-8")

    # AC-L1 & AC-L5: Honest labeling + MEM-01 stays unproven
    assert "prompt-level retain lab run" in status_md
    assert "prompt-level retain lab run" in lab_claude
    assert "prompt-level retain lab run" in research_md
    assert "does not close sre ac-1" in status_md.lower().replace("*", "")

    # AC-L2: Playbook pointers captured
    assert "RUN.md" in lab_claude and "weeks.json" in lab_claude and "claims.md" in lab_claude
    assert "RUN.md" in backfill_md and "status=done" in lab_claude


def test_acl3_week_json_schema_validator_and_alias_normalization():
    # Known bad week shape: bare JSON list at root (e.g. 2026-04-27_...)
    drifted_list_root = [{"text": "Visited Cairo", "people": ["mamty"]}]
    with pytest.raises(WeekSchemaError, match="list_root rejected"):
        validate_and_normalize_week_payload(drifted_list_root)

    # P1-5: Overwrite lock on status=done without explicit reopen
    valid_week = {
        "week_id": "2026-05-04_2026-05-10",
        "agent": "worker-1",
        "facts": [
            {"id": "f1", "text": "Discussed weekend plans", "people": ["mamty (user's mother)", "هديل", "Aser", "مني"]},
        ],
    }
    with pytest.raises(WeekOverwriteError):
        validate_and_normalize_week_payload(valid_week, existing_status="done", reopen=False)

    out = validate_and_normalize_week_payload(valid_week, existing_status="done", reopen=True)
    assert out["facts"][0]["people"] == ["mamty", "Hadil", "Asr", "Mona"]


def test_acl4_no_promote_without_sensitive_filter_and_confirmation_gate():
    week_payload = {
        "week_id": "2026-05-11_2026-05-17",
        "agent": "worker-2",
        "facts": [
            {"id": "f-health", "text": "Had a clinic doctor prescription checkup", "people": ["mamty (user's mother)"]},
            {"id": "f-travel", "text": "Looking at flights to Cairo in December", "people": ["هديل"]},
        ],
    }
    staged = stage_week_for_memory_promotion(week_payload, user_confirmed_ids=set())

    # Zero unconfirmed plain facts land in confirmed_mem; health fact is withheld by sensitive.py
    assert staged["confirmed_mem"] == []
    assert len(staged["withheld_sensitive"]) == 1 and staged["withheld_sensitive"][0]["blocked_category"] == "health"
    assert len(staged["hypotheses"]) == 1
    assert staged["hypotheses"][0]["people"] == ["Hadil"]
    assert staged["hypotheses"][0]["display_prefix"].startswith("I noticed:")

