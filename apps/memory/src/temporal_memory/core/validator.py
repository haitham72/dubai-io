"""Validator v2: 8-stage deterministic safety, fence, schema, and privacy gate (WP-A)."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import re
from typing import Optional

from temporal_memory.db.db import fold_text
from temporal_memory.models import (
    Attempt,
    ExtractionOutput,
    Job,
    JobBundle,
    OutFact,
    Owner,
    Record,
    Verdict,
    WorkerKind,
)

from temporal_memory.privacy.policy import gate_fact as _gate_fact


VALID_ENTITY_KINDS = frozenset({"person", "place", "org", "project", "event"})
VALID_RELATIONS = frozenset({"self", "friend", "colleague", "family", "null", None})
# E9b: explicit past-tense end verbs only ("cancelled", "called off", "quit", "unsubscribed", "withdrew", "paused").
# Whole words, so "quitting"/"cancellation policy" do not fire.
_END_CUE = re.compile(
    r"(?<![A-Za-z])(?:cancell?ed|called off|quit|unsubscribed|withdrew|paused|dropped out|terminated)(?![A-Za-z])", re.I
)

VALID_FACT_OPS = frozenset({"new", "update", "end"})
VALID_LINK_RELS = frozenset(
    {
        "WORKS_AT",
        "WORKS_ON",
        "FRIEND_OF",
        "FAMILY_OF",
        "COLLEAGUE_OF",
        "MANAGES",
        "LIVES_IN",
        "LOCATED_IN",
        "APPLIED_TO",
        "INTERVIEWS_WITH",
        "MEMBER_OF",
        "STUDIES",
        "OWNS",
        "PART_OF",
        "ATTENDS",
        "RELATED_TO",
    }
)

_RECORD_ID_RE = re.compile(r"^(g|n|wa[bgf]?)-?\d+$", re.I)
_RAW_ENTITY_RE = re.compile(r"^e\d+\|")
_INJECTION_RE = re.compile(
    r"(ignore\s+(?:all\s+)?previous|system\s*:|you\s+are\s+now|https?://|```)",
    re.I,
)
_STOPWORDS = frozenset(
    {
        "the", "and", "for", "with", "that", "this", "from", "into", "about",
        "has", "have", "had", "was", "were", "are", "been", "being", "will",
        "would", "could", "should", "can", "may", "might", "not", "but", "his",
        "her", "their", "our", "your", "she", "him", "them", "they", "you",
        "who", "what", "when", "where", "which", "how", "why", "all", "any",
        "some", "one", "two", "new", "old", "now", "still", "also", "very",
    }
)


def _parse_iso(ts: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _strip_new_prefix(ref: str) -> str:
    s = ref.strip()
    return s[4:].strip() if s.startswith("new:") else s


def _fact_hashes(subject_path: str, text: str) -> tuple[str, str, str]:
    folded = fold_text(text)
    norm_subj = subject_path.strip().lower()
    h_folded = hashlib.sha256(folded.encode("utf-8")).hexdigest()
    h_raw = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
    h_subj = hashlib.sha256(f"{norm_subj}|{folded}".encode("utf-8")).hexdigest()
    return h_folded, h_raw, h_subj


_FACT_DROPS = frozenset(
    {
        "evidence_outside_input",
        "evidence_span_mismatch",
        "target_outside_context",
        "credential_in_fact",
        "duplicate_fact",
        "prefilled_slot_changed",
    }
)


def _reason_holds(fact: OutFact, records_by_id: dict[str, Record]) -> bool:
    """True when reason_text is absent or is an exact span of a cited record."""
    if not fact.reason_text:
        return True
    rec_id = fact.reason_record_id or (fact.evidence[0] if fact.evidence else None)
    rec = records_by_id.get(rec_id) if rec_id else None
    if rec is None:
        return False
    text = rec.text or ""
    if fact.reason_start is not None and fact.reason_end is not None:
        start, end = int(fact.reason_start), int(fact.reason_end)
        if start < 0 or end > len(text) or start >= end:
            return False
        return text[start:end] == fact.reason_text
    return fact.reason_text in text


def _clear_reason(fact: OutFact) -> None:
    fact.reason_text = None
    fact.reason_record_id = None
    fact.reason_start = None
    fact.reason_end = None


def _check_evidence_span(
    fact: OutFact,
    cited_records: list[Record],
    out_entities_by_ref: dict[str, list[str]],
    ctx_entities_by_id: dict[str, list[str]],
) -> bool:
    cited_folded = fold_text(" ".join(f"{r.author} {r.text}" for r in cited_records))
    cited_tokens = set(cited_folded.split())

    token_sources: list[str] = [fact.text]
    if fact.text_orig:
        token_sources.append(fact.text_orig)
    for fe in fact.entities:
        token_sources.extend(out_entities_by_ref.get(fe.entity_id, []))
        token_sources.extend(ctx_entities_by_id.get(fe.entity_id, []))

    candidates: list[str] = []
    for src in token_sources:
        for tok in fold_text(src).split():
            if len(tok) >= 3 and (tok not in _STOPWORDS or tok.isdigit()):
                candidates.append(tok)

    if not candidates:
        return True
    return any(
        tok in cited_tokens or (len(tok) >= 4 and tok in cited_folded)
        for tok in candidates
    )


def validate(
    job: Job,
    bundle: JobBundle,
    attempt: Attempt,
    *,
    existing_hashes: set[str] | None = None,
    existing_norm_subjects: set[tuple[str, str]] | None = None,
    current_generation: int | None = None,
    now: datetime | None = None,
    owner_obj: Owner | None = None,
) -> Verdict:
    """Run all 8 Validator v2 checks in order and return a Verdict."""
    reasons: list[str] = []
    fatal: list[str] = []
    quarantined: dict[str, int] = {}

    # 1) Fence / lease / generation
    if job.state != "leased":
        reasons.append("job_not_leased")
    if not job.fence_token or job.fence_token != attempt.fence_token:
        reasons.append("fence_stale")
    if job.lease_expires_at:
        now_dt = now or datetime.now(timezone.utc)
        if now_dt.tzinfo is None:
            now_dt = now_dt.replace(tzinfo=timezone.utc)
        exp_dt = _parse_iso(job.lease_expires_at)
        if exp_dt is None or exp_dt <= now_dt:
            reasons.append("lease_expired")
    if current_generation is not None and current_generation > job.input_version:
        reasons.append("generation_stale")

    # 2) Strict schema / output presence & size caps
    out = attempt.output
    if (
        out is None
        or not isinstance(out, ExtractionOutput)
        or not isinstance(out.entities, list)
        or not isinstance(out.facts, list)
        or not isinstance(out.links, list)
    ):
        reasons.append("schema_invalid")
        return Verdict(ok=False, reasons=list(dict.fromkeys(reasons)), quarantined=quarantined)

    if len(out.facts) > 100:
        reasons.append("size_cap_exceeded")
    for fact in out.facts:
        if not fact.text or not fact.text.strip() or not fact.subject_path or not fact.subject_path.strip():
            reasons.append("schema_invalid")
        if len(fact.text or "") > 500 or (fact.text_orig and len(fact.text_orig) > 500):
            reasons.append("size_cap_exceeded")

    # Lookup helpers for checks 3–5
    allowed_input = set(job.input_ref)
    records_by_id = {r.id: r for r in bundle.records}
    out_entities_by_ref: dict[str, list[str]] = {}
    for ent in out.entities:
        out_entities_by_ref[ent.ref] = [_strip_new_prefix(ent.ref), *ent.aliases]

    ctx_entities_raw = bundle.context.get("entities", [])
    ctx_entities_by_id: dict[str, list[str]] = {}
    ctx_self_ids: set[str] = set()
    self_folded: set[str] = set()
    for ce in ctx_entities_raw:
        if not isinstance(ce, dict) or "id" not in ce:
            continue
        names = [ce.get("name", ""), *(ce.get("aliases") or [])]
        ctx_entities_by_id[ce["id"]] = [n for n in names if n]
        if ce.get("relation_to_user") == "self":
            ctx_self_ids.add(ce["id"])
            for n in names:
                f = fold_text(n)
                if f:
                    self_folded.add(f)
    if owner_obj is not None:
        for s in [owner_obj.display_name, *owner_obj.self_aliases]:
            f = fold_text(s)
            if f:
                self_folded.add(f)

    # 3) Evidence check. A bad fact is dropped later; it does not reject the day.
    fact_drops: dict[int, list[str]] = {}

    def _drop(idx: int, reason: str) -> None:
        fact_drops.setdefault(idx, []).append(reason)

    for idx, fact in enumerate(out.facts):
        if not _reason_holds(fact, records_by_id):
            _clear_reason(fact)
        if not fact.evidence or not set(fact.evidence).issubset(allowed_input):
            _drop(idx, "evidence_outside_input")
        elif bundle.records:
            cited = [records_by_id[rid] for rid in fact.evidence if rid in records_by_id]
            if cited and not _check_evidence_span(
                fact, cited, out_entities_by_ref, ctx_entities_by_id
            ):
                _drop(idx, "evidence_span_mismatch")

    # 3b) E7: the LLM may not change or restate a slot the receipt pre-pass filled in.
    from temporal_memory.ingest.receipts import conflicts_with_prefilled, prefilled_from_context  # lazy: ingest imports queue

    prefilled = prefilled_from_context(bundle.context)
    if prefilled:
        for idx, fact in enumerate(out.facts):
            if idx not in fact_drops and conflicts_with_prefilled(fact, prefilled):
                _drop(idx, "prefilled_slot_changed")

    for lnk in out.links:
        if not lnk.evidence or not set(lnk.evidence).issubset(allowed_input):
            reasons.append("evidence_outside_input")
            fatal.append("evidence_outside_input")

    # 4) Target check for update / end
    context_fact_ids = {
        f["id"] for f in bundle.context.get("facts", []) if isinstance(f, dict) and "id" in f
    }
    for idx, fact in enumerate(out.facts):
        if idx in fact_drops:
            continue
        if fact.op == "new" and _END_CUE.search(fact.text or ""):
            # E9b: the model reports a cancellation/quit as a plain new fact; record it as the end event it is.
            fact.op = "end"
            fact.target = None
        if fact.op in ("update", "end"):
            if not fact.target or fact.target not in context_fact_ids:
                if fact.op == "end":
                    # E9b: a cancellation/stop with no known fact to close is still an end event; keep it with no
                    # target (the applier records it as ended). A made-up target id is never followed.
                    fact.target = None
                else:
                    _drop(idx, "target_outside_context")

    # 5) Entity guards & enum validation
    for ent in out.entities:
        ref = (ent.ref or "").strip()
        name = _strip_new_prefix(ref)
        if (
            _RECORD_ID_RE.match(ref)
            or _RECORD_ID_RE.match(name)
            or _RAW_ENTITY_RE.match(ref)
            or any(_RECORD_ID_RE.match(a.strip()) or _RAW_ENTITY_RE.match(a.strip()) for a in ent.aliases)
        ):
            reasons.append("entity_is_record_id")
        if (
            not name
            or len(name) > 80
            or any(ord(c) < 32 for c in name)
            or any(len(a) > 80 or any(ord(c) < 32 for c in a) for a in ent.aliases)
        ):
            reasons.append("entity_name_invalid")
        if ent.relation_to_user not in (None, "self"):
            ent_folded = {fold_text(name), *(fold_text(a) for a in ent.aliases)}
            if ref in ctx_self_ids or (ent_folded & self_folded):
                reasons.append("entity_self_as_third_party")
        if ent.kind not in VALID_ENTITY_KINDS or ent.relation_to_user not in VALID_RELATIONS:
            reasons.append("schema_invalid")

    for fact in out.facts:
        if fact.op not in VALID_FACT_OPS:
            reasons.append("schema_invalid")
        for fe in fact.entities:
            cname = _strip_new_prefix(fe.entity_id)
            if _RECORD_ID_RE.match(cname) or _RAW_ENTITY_RE.match(fe.entity_id):
                reasons.append("entity_is_record_id")
            if not cname or len(cname) > 80:
                reasons.append("entity_name_invalid")

    for lnk in out.links:
        if lnk.rel not in VALID_LINK_RELS:
            reasons.append("schema_invalid")
        for endpoint in (lnk.src, lnk.dst):
            cname = _strip_new_prefix(endpoint)
            if _RECORD_ID_RE.match(cname) or _RAW_ENTITY_RE.match(endpoint):
                reasons.append("entity_is_record_id")
            if not cname or len(cname) > 80:
                reasons.append("entity_name_invalid")

    # 6) Privacy gate. Credentials drop that fact alone.
    for idx, fact in enumerate(out.facts):
        if idx in fact_drops:
            continue
        cat = _gate_fact(fact, attempt.worker_kind)
        if cat == "credential" or fact.sensitive == "credential":
            _drop(idx, "credential_in_fact")
        elif cat and not fact.sensitive:
            fact.sensitive = cat
            quarantined[cat] = quarantined.get(cat, 0) + 1
        elif fact.sensitive:
            quarantined[fact.sensitive] = quarantined.get(fact.sensitive, 0) + 1

    # 7) Injection guard
    inspected_strings: list[str] = []
    for fact in out.facts:
        inspected_strings.append(fact.text or "")
        if fact.text_orig:
            inspected_strings.append(fact.text_orig)
        for fe in fact.entities:
            if fe.role:
                inspected_strings.append(fe.role)
    for ent in out.entities:
        inspected_strings.append(ent.ref or "")
        inspected_strings.extend(ent.aliases)
    if any(_INJECTION_RE.search(s) for s in inspected_strings if s):
        reasons.append("prompt_injection_detected")

    # 8) Dedupe (within attempt and against existing store)
    seen_hashes: set[str] = set(existing_hashes or ())
    seen_norm_subjects: set[tuple[str, str]] = {
        (s.strip().lower(), fold_text(t)) for s, t in (existing_norm_subjects or ())
    }
    for idx, fact in enumerate(out.facts):
        if idx in fact_drops:
            continue
        norm_key = (fact.subject_path.strip().lower(), fold_text(fact.text))
        hashes = _fact_hashes(fact.subject_path, fact.text)
        if norm_key in seen_norm_subjects or any(h in seen_hashes for h in hashes):
            _drop(idx, "duplicate_fact")
        else:
            seen_norm_subjects.add(norm_key)
            seen_hashes.update(hashes)

    if fact_drops:
        kept: list[OutFact] = []
        for idx, fact in enumerate(out.facts):
            if idx in fact_drops:
                reasons.extend(fact_drops[idx])
            else:
                kept.append(fact)
        out.facts[:] = kept

    if (
        attempt.model_observed
        and attempt.model
        and attempt.model_observed.strip().lower() != attempt.model.strip().lower()
    ):
        reasons.append("model_mismatch")

    unique_reasons = list(dict.fromkeys(reasons))
    nonfatal = _FACT_DROPS | {"model_mismatch"}
    dropped_only = all(r in nonfatal for r in unique_reasons)
    return Verdict(
        ok=dropped_only and not fatal,
        reasons=unique_reasons,
        quarantined=quarantined,
    )
