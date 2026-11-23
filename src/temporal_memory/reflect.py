"""Weekly batch reflection layer -> Quest USER.md + hypothesis milestones (WP-B).

Ported from:
- G:\\Haitham\\lab-data\\memory-bakeoff\\weekbench\\reflect.py
- Canonical privacy patterns: g:\\Haitham\\VsCode\\contest\\apps\\api\\app\\lab\\sensitive.py:15-23
"""
from __future__ import annotations

from datetime import date, timedelta
import json
import os
import re
from typing import Any, Callable
import uuid

from json_repair import loads as repair_json_loads

from temporal_memory.api.vault import call_opt
from temporal_memory.models import Attempt, ExtractionOutput, GraphStore, Job, JobBundle, Milestone, Record, Verdict

SECTIONS = ("Identity", "Personality", "Values", "Strengths & Tensions", "Interests", "Drive", "Relationships")
_TRIVIA_RE = re.compile(
    r"\b(sign[- ]?up|otp|one[- ]?time (?:password|code|delivery)|verification code|login|log[- ]?in|"
    r"subscription|newsletter|account link|linked account|delivery|parcel|shipment|tracking|winback|promo)\b",
    re.I,
)
# Fail-closed fallback Rule 9 regexes when WP-C privacy.sensitive is not yet merged
_SENSITIVE_FALLBACK: dict[str, re.Pattern[str]] = {
    "health": re.compile(
        r"\b(health\w*|medic\w*|sick|illness|cancer|diagnos\w*|diabetes|surgery|hospital|clinic|pregnan\w*|"
        r"therapy|therapist|anxiety|depress\w*|symptom\w*|doctor|blood|prescription|thyroid)\b|"
        r"مرض|مستشفى|دكتور|علاج|تحليل|صحة|حمل",
        re.I,
    ),
    "religion": re.compile(
        r"\b(relig\w*|muslim|christian|jewish|hindu|allah|god|quran|bible|church|mosque|umrah|3omra|hajj|"
        r"ramadan|fasting|prayer|pray\w*|halal|haram)\b|صلاة|قرآن|عمرة|حج|رمضان|صيام|مسجد",
        re.I,
    ),
    "ethnicity_nationality": re.compile(r"\b(ethnic\w*|nationality|citizenship|visa)\b|جنسية", re.I),
    "gender_sexuality": re.compile(r"\b(gay|lesbian|bisexual|transgender|lgbt\w*|sexuality|divorce)\b|طلاق", re.I),
    "politics": re.compile(r"\b(politic\w*|election|parliament|regime)\b|سياس\w*", re.I),
    "third_party_private": re.compile(r"\b(affair|arrest\w*|bankrupt\w*|lawsuit|court case|personal loan|debt)\b|محكمة|شرطة", re.I),
    "credential": re.compile(r"\b(password|passcode|pin code|otp|cvv|iban|emirates id)\b|كلمة السر|كلمة المرور", re.I),
}

_REFLECT_SYSTEM = (
    "You maintain a Quest-style user profile and milestone hypothesis tracker. Return STRICT JSON only: "
    '{"user_md": "...", "claims": [{"section": "...", "text": "I noticed ...", "evidence": ["f1", "f2"]}], '
    '"milestones": [{"title": "...", "subject_path": "quests/...", "state": "done|in_progress|planned", '
    '"evidence": ["f1", "f2"]}]}. '
    "Rules: USER.md has sections: " + ", ".join(SECTIONS) + ". Every claim and milestone is a HYPOTHESIS only, "
    "needs >= 2 supporting facts across >= 2 distinct days, never infers family/health/faith/third-party private "
    "or credentials, and never turns sign-ups, OTPs, subscriptions, or deliveries into milestones."
)
_REFLECT_SCHEMA = {
    "type": "object",
    "required": ["user_md", "claims", "milestones"],
    "properties": {
        "user_md": {"type": "string"},
        "claims": {"type": "array", "items": {"type": "object"}},
        "milestones": {"type": "array", "items": {"type": "object"}},
    },
}

_DEFAULT_STORE: GraphStore | None = None


def set_default_store(store: GraphStore | None) -> None:
    global _DEFAULT_STORE
    _DEFAULT_STORE = store


def _check_sensitive(text: str) -> str | None:
    """Use canonical WP-C privacy.sensitive if present; otherwise fail-closed fallback regexes."""
    try:
        from temporal_memory.privacy import sensitive as wp_c_sensitive  # type: ignore
        hit = wp_c_sensitive.filter_statement(text)
        if hit:
            return hit
    except ImportError:
        pass
    for cat, rx in _SENSITIVE_FALLBACK.items():
        if rx.search(text or ""):
            return cat
    return None


def _parse_json(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, Attempt):
        if raw.output is not None and isinstance(raw.output, dict):
            return raw.output
        raw = getattr(raw, "raw_text", "") or ""
    text = str(raw or "")
    i, j = text.find("{"), text.rfind("}")
    if i < 0 or j < i:
        return {}
    try:
        return json.loads(text[i : j + 1])
    except json.JSONDecodeError:
        out = repair_json_loads(text[i : j + 1])
        return out if isinstance(out, dict) else {}


def _distinct_days(ev_ids: list[str], fact_by_id: dict[str, Any]) -> tuple[list[str], set[str]]:
    clean_ids = list(dict.fromkeys(str(fid) for fid in ev_ids if str(fid) in fact_by_id))
    days = {fact_by_id[fid].valid_from[:10] for fid in clean_ids if getattr(fact_by_id[fid], "valid_from", None)}
    return clean_ids, days


def reflect_week(
    owner: str,
    week_start: str,
    *,
    store: GraphStore | None = None,
    runner_fn: Callable[[JobBundle, str, str], Any] | None = None,
    runner: str | None = None,
    model: str | None = None,
) -> Verdict:
    """Generate hypothesis USER.md + milestone candidates for [week_start, week_start + 6d]."""
    st: Any = store or _DEFAULT_STORE
    if st is None:
        raise RuntimeError("No GraphStore configured for reflect.reflect_week")

    w0 = date.fromisoformat(week_start[:10])
    w_end = (w0 + timedelta(days=6)).isoformat()

    all_visible = st.visible_facts(owner, limit=10_000)
    non_sens = [
        f
        for f in all_visible
        if f.status != "history" and f.status != "hypothesis" and not _check_sensitive(f.text)
    ]
    fact_by_id = {f.id: f for f in non_sens}
    week_facts = [
        f for f in non_sens if w0.isoformat() <= (f.valid_from or "")[:10] <= w_end
    ]

    prior_md = call_opt(st, "get_user_md", owner, default="") or ""
    bundle = JobBundle(
        job=Job(
            id=f"reflect-{uuid.uuid4().hex[:8]}",
            owner=owner,
            kind="reflect.week",
            priority=3,
            pool="internal",
            input_ref=[f.id for f in week_facts],
            input_version=call_opt(st, "owner_generation", owner, default=0),
            context_hash=f"{owner}:{week_start}",
            prompt_version="reflect@1",
            day=week_start[:10],
        ),
        records=[
            Record(id=f.id, owner=owner, source="facts", at=f.valid_from, author=owner, text=f.text)
            for f in week_facts
        ],
        context={
            "week_start": week_start[:10],
            "week_end": w_end,
            "prev_user_md": prior_md,
            "facts": [{"id": f.id, "valid_from": f.valid_from, "text": f.text} for f in week_facts],
        },
        system_prompt=_REFLECT_SYSTEM,
        output_schema=_REFLECT_SCHEMA,
    )

    chosen_runner = runner or os.environ.get("TM_REFLECT_RUNNER", "anthropic")
    chosen_model = model or os.environ.get("TM_REFLECT_MODEL") or os.environ.get("TM_CLOUD_MODEL", "")
    if runner_fn is None:
        from temporal_memory.core import extract as core_extract  # type: ignore
        raw_out = core_extract.run(bundle, chosen_runner, chosen_model)
    else:
        raw_out = runner_fn(bundle, chosen_runner, chosen_model)

    payload = _parse_json(raw_out)
    reasons: list[str] = []
    quarantined: dict[str, int] = {}
    applied_fact_ids: list[str] = []

    # 1. Validate and persist hypothesis profile claims
    accepted_claims: list[dict[str, Any]] = []
    for item in payload.get("claims") or []:
        if not isinstance(item, dict) or not item.get("text"):
            continue
        text = str(item["text"]).strip()
        ev_ids, days = _distinct_days(item.get("evidence") or [], fact_by_id)
        sens_cat = _check_sensitive(text)
        if not sens_cat:
            for fid in ev_ids:
                sens_cat = _check_sensitive(fact_by_id[fid].text)
                if sens_cat:
                    break
        if sens_cat:
            quarantined[sens_cat] = quarantined.get(sens_cat, 0) + 1
            reasons.append("sensitive_never_inferred")
            continue
        if len(ev_ids) < 2 or len(days) < 2:
            reasons.append("insufficient_distinct_days")
            continue
        hyp_text = text if text.startswith("I noticed") else f"I noticed {text}"
        accepted_claims.append({**item, "text": hyp_text, "evidence": ev_ids, "days": sorted(days)})
        saved_id = call_opt(
            st,
            "add_hypothesis_fact",
            owner,
            text=hyp_text,
            subject_path=f"profile/{str(item.get('section', 'general')).lower().replace(' ', '-')}",
            valid_from=min(days),
            evidence=ev_ids,
            default=None,
        )
        if saved_id:
            applied_fact_ids.append(saved_id)

    # 2. Validate and persist goal / milestone hypotheses
    for ms in payload.get("milestones") or []:
        if not isinstance(ms, dict) or not ms.get("title"):
            continue
        title = str(ms["title"]).strip()
        ev_ids, days = _distinct_days(ms.get("evidence") or [], fact_by_id)
        blob = " ".join([title, *[fact_by_id[fid].text for fid in ev_ids]])
        sens_cat = _check_sensitive(blob)
        if sens_cat:
            quarantined[sens_cat] = quarantined.get(sens_cat, 0) + 1
            reasons.append("sensitive_never_inferred")
            continue
        if _TRIVIA_RE.search(blob):
            reasons.append("trivia_milestone_rejected")
            continue
        if len(ev_ids) < 2 or len(days) < 2:
            reasons.append("insufficient_distinct_days")
            continue
        state = ms.get("state") if ms.get("state") in ("done", "in_progress", "planned") else "in_progress"
        call_opt(
            st,
            "add_hypothesis_milestone",
            owner,
            title=title,
            subject_path=str(ms.get("subject_path") or "quests/general"),
            state=state,
            evidence_fact_ids=ev_ids,
            default=None,
        )

    # Render safe USER.md from validated claims if supplied, else keep prior safe md
    if accepted_claims:
        by_sec: dict[str, list[str]] = {s: [] for s in SECTIONS}
        for c in accepted_claims:
            sec = c.get("section") if c.get("section") in by_sec else "Identity"
            by_sec[sec].append(f"- {c['text']} (unconfirmed) `[ev: {', '.join(c['evidence'])}]`")
        md_lines = [f"# USER Profile ({owner})", ""]
        for sec in SECTIONS:
            md_lines.append(f"## {sec}")
            md_lines.extend(by_sec[sec] or ["- _(unconfirmed)_"])
            md_lines.append("")
        call_opt(st, "set_user_md", owner, "\n".join(md_lines), default=None)
    elif isinstance(payload.get("user_md"), str) and not _check_sensitive(payload["user_md"]) and accepted_claims:
        call_opt(st, "set_user_md", owner, payload["user_md"], default=None)

    return Verdict(
        ok=True,
        reasons=list(dict.fromkeys(reasons)),
        applied_fact_ids=applied_fact_ids,
        quarantined=quarantined,
    )
