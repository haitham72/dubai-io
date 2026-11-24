"""Chronological /story endpoint: deterministic cited timeline first + optional grounded narration (U5)."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
import re
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query
import httpx

from temporal_memory.api.vault import (
    AuthContext,
    _envelope_provenance,
    _is_sensitive_subject,
    _iter_all_visible,
    _meta,
    call_opt,
    get_store,
    require_owner_access,
)
from temporal_memory.config import get_settings
from temporal_memory.models import Fact, GraphStore, Subject
from temporal_memory.privacy.sensitive import ScreenUnavailable, pre_write, screen

try:
    import anthropic  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    anthropic = None  # type: ignore[assignment]

router = APIRouter(prefix="/v1/owners/{owner}", tags=["story"])

STORY_VERSION = "story@1"
_MAX_PROMPT_CHARS = 8000  # ~2k tokens of screened facts
_NARRATOR_OVERRIDE: Callable[[str, list[dict[str, Any]]], tuple[Any, float, str]] | None = None
_CLASSIFIER_OVERRIDE: Callable[[list[str]], dict[str, str]] | None = None

_STORY_SYSTEM = (
    "You write a short factual chronological summary strictly from the provided numbered memory facts. "
    'Return STRICT JSON ONLY: {"sentences": [{"text": "...", "fact_ids": ["f1"]}]}. '
    "Every sentence MUST cite one or more exact fact_ids from the input list. "
    "Never invent facts, dates, reasons, or IDs, and never mention health, religion, private family matters, or credentials."
)
_CITE_TAG_RE = re.compile(r"\[([A-Za-z0-9_,-]+(?:\s*,\s*[A-Za-z0-9_,-]+)*)\]")


def set_narrator(fn: Callable[[str, list[dict[str, Any]]], tuple[Any, float, str]] | None) -> None:
    """Test/runtime hook overriding the LLM narrator call."""
    global _NARRATOR_OVERRIDE
    _NARRATOR_OVERRIDE = fn


def set_screen_classifier(fn: Callable[[list[str]], dict[str, str]] | None) -> None:
    """Test hook overriding Rule-9 layer-2 classification for narrated story sentences."""
    global _CLASSIFIER_OVERRIDE
    _CLASSIFIER_OVERRIDE = fn


def _cache_versions(store: Any, owner: str) -> tuple[int, int, int]:
    db_obj = getattr(store, "db", None)
    if db_obj is not None:
        with db_obj.connection() as conn:
            row = conn.execute(
                """
                SELECT o.facts_version,
                       o.privacy_revision,
                       COALESCE((SELECT MAX(r.generation) FROM records r WHERE r.owner = o.id), 0) AS rec_gen
                FROM owners o
                WHERE o.id = %s
                """,
                (owner,),
            ).fetchone()
        if row:
            return int(row["rec_gen"] or 0), int(row["facts_version"] or 0), int(row["privacy_revision"] or 0)
    gen = int(call_opt(store, "owner_generation", owner, default=0) or 0)
    fver = int(call_opt(store, "facts_version", owner, default=0) or 0)
    prev = int(call_opt(store, "privacy_revision", owner, default=0) or 0)
    return gen, fver, prev


def _query_hash(entity: str | None, subject: str | None, date_from: str | None, date_to: str | None, narrate: bool) -> str:
    raw = json.dumps(
        {
            "entity": (entity or "").strip().lower(),
            "subject": (subject or "").strip().lower(),
            "from": (date_from or "")[:10],
            "to": (date_to or "")[:10],
            "narrate": bool(narrate),
        },
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _version_key(narrate: bool) -> str:
    if not narrate:
        return STORY_VERSION
    if _NARRATOR_OVERRIDE is not None:
        return f"{STORY_VERSION}:narrate:override:{id(_NARRATOR_OVERRIDE)}"
    cfg = get_settings()
    runner = os.environ.get("TM_STORY_RUNNER", "lmstudio")
    model = os.environ.get("TM_STORY_MODEL") or cfg.lmstudio_model
    return f"{STORY_VERSION}:narrate:{runner}:{model}"


def _read_cache(store: Any, owner: str, versions: tuple[int, int, int], qhash: str, vkey: str) -> dict[str, Any] | None:
    db_obj = getattr(store, "db", None)
    if db_obj is None:
        return None
    rec_gen, facts_ver, priv_rev = versions
    try:
        with db_obj.connection() as conn:
            row = conn.execute(
                """
                SELECT payload_json
                FROM story_cache
                WHERE owner = %s
                  AND record_generation = %s
                  AND facts_version = %s
                  AND privacy_revision = %s
                  AND query_hash = %s
                  AND version_key = %s
                """,
                (owner, rec_gen, facts_ver, priv_rev, qhash, vkey),
            ).fetchone()
        if row and row["payload_json"]:
            payload = dict(row["payload_json"])
            payload["cached"] = True
            return payload
    except Exception:
        return None
    return None


def _write_cache(
    store: Any,
    owner: str,
    versions: tuple[int, int, int],
    qhash: str,
    vkey: str,
    payload: dict[str, Any],
) -> None:
    db_obj = getattr(store, "db", None)
    if db_obj is None:
        return
    rec_gen, facts_ver, priv_rev = versions
    to_store = {k: v for k, v in payload.items() if k != "cached"}
    try:
        with db_obj.transaction() as conn:
            conn.execute(
                """
                INSERT INTO story_cache (
                    owner, record_generation, facts_version, privacy_revision,
                    query_hash, version_key, payload_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (owner, record_generation, facts_version, privacy_revision, query_hash, version_key)
                DO UPDATE SET payload_json = EXCLUDED.payload_json, created_at = now()
                """,
                (owner, rec_gen, facts_ver, priv_rev, qhash, vkey, json.dumps(to_store, ensure_ascii=False)),
            )
    except Exception:
        pass


def _resolve_entity_ids(store: Any, owner: str, entity_query: str) -> set[str]:
    needle = entity_query.strip().casefold()
    entities = call_opt(store, "list_entities", owner, default=[]) or []
    matched: set[str] = set()
    for e in entities:
        if e.id.casefold() == needle or (e.name or "").casefold() == needle:
            matched.add(e.id)
        elif any((a or "").casefold() == needle for a in (e.aliases or [])):
            matched.add(e.id)
    if not matched and db_matches_needle(needle):
        matched.add(entity_query.strip())
    return matched


def db_matches_needle(needle: str) -> bool:
    return bool(needle)


def _resolve_subject_ids(subjects: list[Subject], subject_query: str) -> set[str]:
    needle = subject_query.strip().casefold().strip("/")
    matched_paths: list[str] = []
    matched_ids: set[str] = set()
    for s in subjects:
        spath = (s.path or "").casefold().strip("/")
        if s.id.casefold() == needle or spath == needle or (s.label or "").casefold() == needle:
            matched_ids.add(s.id)
            if spath:
                matched_paths.append(spath)
        elif spath.startswith(needle + "/") or needle == spath.split("/")[0]:
            matched_ids.add(s.id)
    for s in subjects:
        spath = (s.path or "").casefold().strip("/")
        if any(spath == p or spath.startswith(p + "/") for p in matched_paths):
            matched_ids.add(s.id)
    return matched_ids


def _reason_map(store: Any, owner: str, facts: list[Fact]) -> dict[str, str]:
    out: dict[str, str] = {}
    missing_ids: list[str] = []
    for f in facts:
        rt = (getattr(f, "reason_text", None) or "").strip()
        if rt:
            out[f.id] = rt
        else:
            missing_ids.append(f.id)

    db_obj = getattr(store, "db", None)
    if db_obj is not None and missing_ids:
        try:
            with db_obj.connection() as conn:
                rows = conn.execute(
                    """
                    SELECT id, reason_text
                    FROM facts
                    WHERE owner = %s AND id = ANY(%s)
                      AND (erased_at IS NULL)::int = 1
                      AND reason_text IS NOT NULL AND reason_text <> ''
                    """,
                    (owner, missing_ids),
                ).fetchall()
            for r in rows:
                clean = (r["reason_text"] or "").strip()
                if clean:
                    out[r["id"]] = clean
        except Exception:
            pass
    return out


def _month_spend_usd(store: Any, owner: str) -> float:
    db_obj = getattr(store, "db", None)
    if db_obj is not None:
        try:
            with db_obj.connection() as conn:
                row = conn.execute(
                    """
                    SELECT COALESCE(SUM(cost_usd), 0.0) AS total
                    FROM job_attempts
                    WHERE owner = %s
                      AND finished_at >= date_trunc('month', now())
                    """,
                    (owner,),
                ).fetchone()
            return float(row["total"] or 0.0) if row else 0.0
        except Exception:
            pass

    month_prefix = datetime.now(timezone.utc).strftime("%Y-%m")
    jobs = call_opt(store, "list_jobs", default=[]) or []
    owner_jids = {j.id for j in jobs if getattr(j, "owner", None) == owner}
    attempts = call_opt(store, "list_attempts", default=[]) or []
    total = 0.0
    for a in attempts:
        if owner_jids and a.job_id not in owner_jids:
            continue
        fin = (getattr(a, "finished_at", None) or "")[:7]
        if not fin or fin == month_prefix:
            total += float(getattr(a, "cost_usd", 0.0) or 0.0)
    return total


def _deterministic_timeline(facts: list[Fact], reasons: dict[str, str]) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for f in sorted(facts, key=lambda x: (x.valid_from or "", x.id)):
        as_of = (f.valid_from or "")[:10] or "undated"
        body = (f.text or "").strip().rstrip(".")
        if f.status == "superseded":
            until = (f.valid_to or "")[:10]
            span_note = f" (was active until {until}; superseded)" if until else " (superseded)"
        elif f.status == "ended":
            until = (f.valid_to or "")[:10]
            span_note = f" (was active until {until}; ended)" if until else " (ended)"
        else:
            span_note = ""
        reason_val = reasons.get(f.id) or "reason unknown"
        reason_suffix = f" [reason: {reason_val}]" if reason_val != "reason unknown" else ""
        text = f"[{as_of}] {body}{span_note}.{reason_suffix} [{f.id}]"
        lines.append(
            {
                "text": text,
                "fact_ids": [f.id],
                "as_of": f.valid_from,
                "valid_to": f.valid_to,
                "status": f.status,
                "provenance": f.provenance,
                "reason": reason_val,
            }
        )
    return lines


def _build_narration_prompt(owner: str, facts: list[Fact], reasons: dict[str, str]) -> tuple[str, list[dict[str, Any]]]:
    fact_items: list[dict[str, Any]] = []
    lines: list[str] = []
    used_chars = 0
    for f in sorted(facts, key=lambda x: (x.valid_from or "", x.id)):
        r_str = reasons.get(f.id) or "reason unknown"
        interval = f"{f.valid_from or '?'}..{f.valid_to or 'present'}"
        line = f"[{f.id}] ({interval}, {f.status}, {f.provenance}, reason={r_str}): {f.text}"
        if used_chars + len(line) + 1 > _MAX_PROMPT_CHARS and lines:
            break
        lines.append(line)
        used_chars += len(line) + 1
        fact_items.append({"id": f.id, "valid_from": f.valid_from, "valid_to": f.valid_to, "status": f.status, "text": f.text, "reason": r_str})
    prompt = f"Owner: {owner}\nFacts:\n" + "\n".join(lines)
    return prompt, fact_items


def _call_lmstudio(prompt: str, model: str) -> tuple[str, float, str]:
    cfg = get_settings()
    used_model = model or cfg.lmstudio_model
    url = f"{cfg.lmstudio_url.rstrip('/')}/chat/completions"
    payload = {
        "model": used_model,
        "messages": [
            {"role": "system", "content": _STORY_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 1200,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    resp = httpx.post(url, json=payload, timeout=30.0)
    resp.raise_for_status()
    out = resp.json()
    content = ((out.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    return str(content), 0.0, used_model


def _call_anthropic(prompt: str, model: str) -> tuple[str, float, str]:
    if anthropic is None:
        raise RuntimeError("anthropic package unavailable")
    cfg = get_settings()
    api_key = cfg.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")
    used_model = model or cfg.cloud_model
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=used_model,
        max_tokens=1200,
        temperature=0,
        system=_STORY_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    parts = [getattr(b, "text", "") for b in (getattr(resp, "content", None) or [])]
    usage = getattr(resp, "usage", None)
    tin = int(getattr(usage, "input_tokens", 0) or 0)
    tout = int(getattr(usage, "output_tokens", 0) or 0)
    cost = round((tin * cfg.cloud_rate_in_per_1m + tout * cfg.cloud_rate_out_per_1m) / 1_000_000, 6)
    return "".join(parts), cost, used_model


def _run_narrator(prompt: str, fact_items: list[dict[str, Any]]) -> tuple[Any, float, str]:
    if _NARRATOR_OVERRIDE is not None:
        return _NARRATOR_OVERRIDE(prompt, fact_items)
    cfg = get_settings()
    preferred = (os.environ.get("TM_STORY_RUNNER") or "").strip().lower()
    if preferred == "anthropic":
        return _call_anthropic(prompt, os.environ.get("TM_STORY_MODEL") or cfg.cloud_model)
    # Local Qwen first, then internal cloud fallback (D-b).
    try:
        return _call_lmstudio(prompt, os.environ.get("TM_STORY_MODEL") or cfg.lmstudio_model)
    except Exception:
        return _call_anthropic(prompt, os.environ.get("TM_CLOUD_MODEL") or cfg.cloud_model)


def _parse_narrated_sentences(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, dict):
        data = raw
    elif isinstance(raw, list):
        data = {"sentences": raw}
    else:
        txt = str(raw or "").strip()
        i, j = txt.find("{"), txt.rfind("}")
        if i >= 0 and j > i:
            try:
                data = json.loads(txt[i : j + 1])
            except Exception:
                data = {}
        else:
            data = {}
        if not data and txt:
            # Fallback line-by-line parser for bracketed citations like "Sentence text [f1, f2]."
            parsed_lines = []
            for seg in re.split(r"(?<=[.!?])\s+|\n+", txt):
                s = seg.strip()
                if not s:
                    continue
                tags: list[str] = []
                for m in _CITE_TAG_RE.finditer(s):
                    tags.extend(p.strip() for p in m.group(1).split(",") if p.strip())
                parsed_lines.append({"text": s, "fact_ids": tags})
            return parsed_lines

    out: list[dict[str, Any]] = []
    for item in data.get("sentences") or []:
        if isinstance(item, dict) and item.get("text"):
            out.append({
                "text": str(item["text"]).strip(),
                "fact_ids": [str(fid).strip() for fid in (item.get("fact_ids") or []) if str(fid).strip()],
            })
    return out


def _screen_sentences(sentences: list[dict[str, Any]], visible_ids: set[str]) -> tuple[list[dict[str, Any]], int]:
    accepted: list[dict[str, Any]] = []
    dropped = 0
    candidate_texts: list[str] = []
    prelim: list[dict[str, Any]] = []

    for s in sentences:
        txt = (s.get("text") or "").strip()
        fids = list(dict.fromkeys(str(fid).strip() for fid in (s.get("fact_ids") or []) if str(fid).strip()))
        # Require non-empty cited fact_ids subset of retrieved visible set, and pass pre_write Layer 1.
        if not txt or not fids or not (set(fids) <= visible_ids):
            dropped += 1
            continue
        if pre_write(txt) is not None:
            dropped += 1
            continue
        prelim.append({"text": txt, "fact_ids": fids})
        candidate_texts.append(txt)

    if not prelim:
        return [], dropped

    # Run Layer-2 Rule-9 screen cleanly (fail closed on ScreenUnavailable or any flagged sentence).
    try:
        blocked = screen(candidate_texts, classify=_CLASSIFIER_OVERRIDE)
    except ScreenUnavailable:
        return [], dropped + len(prelim)

    for item in prelim:
        if item["text"] in blocked:
            dropped += 1
            continue
        accepted.append(item)
    return accepted, dropped


@router.get("/story")
def get_story(
    owner: str,
    entity: str | None = Query(default=None),
    subject: str | None = Query(default=None),
    date_from: str | None = Query(default=None, alias="from"),
    date_to: str | None = Query(default=None, alias="to"),
    narrate: bool = Query(default=False),
    _: AuthContext = Depends(require_owner_access),
    store: GraphStore = Depends(get_store),
) -> dict[str, Any]:
    now_iso, is_demo = _meta(store, owner)
    versions = _cache_versions(store, owner)
    qhash = _query_hash(entity, subject, date_from, date_to, narrate)
    vkey = _version_key(narrate)

    cached = _read_cache(store, owner, versions, qhash, vkey)
    if cached is not None:
        return cached

    subjects: list[Subject] = call_opt(store, "list_subjects", owner, default=[]) or []
    subj_by_id = {s.id: s for s in subjects}

    entity_ids: set[str] | None = None
    if entity and entity.strip():
        entity_ids = _resolve_entity_ids(store, owner, entity)

    subject_ids: set[str] | None = None
    if subject and subject.strip():
        subject_ids = _resolve_subject_ids(subjects, subject)

    all_visible = _iter_all_visible(store, owner, date_from=date_from, date_to=date_to)
    screened_facts: list[Fact] = []
    for f in all_visible:
        if f.status in ("history", "hypothesis"):
            continue
        if entity_ids is not None:
            f_eids = {fe.entity_id for fe in (f.entities or [])}
            if not (f_eids & entity_ids):
                continue
        if subject_ids is not None and f.subject_id not in subject_ids:
            continue
        subj = subj_by_id.get(f.subject_id)
        if _is_sensitive_subject(subj):
            continue
        root = ((subj.path if subj else "") or "").split("/")[0].strip().lower()
        if root == "people-family" and f.provenance not in ("user_supplied", "provider_confirmed"):
            continue
        if pre_write(f.text) is not None or (f.text_orig and pre_write(f.text_orig) is not None):
            continue
        screened_facts.append(f)

    reasons = _reason_map(store, owner, screened_facts)
    timeline = _deterministic_timeline(screened_facts, reasons)
    deterministic_text = "\n".join(line["text"] for line in timeline)

    mode = "template"
    fallback_reason: str | None = None
    cost_usd = 0.0
    model_used: str | None = None
    dropped_sentences = 0
    sentences: list[dict[str, Any]] = [
        {"text": line["text"], "fact_ids": list(line["fact_ids"])} for line in timeline
    ]
    story_text = deterministic_text

    if narrate and screened_facts:
        cfg = get_settings()
        spent = _month_spend_usd(store, owner)
        if spent >= cfg.governor_usd_per_month:
            fallback_reason = "over_budget"
        else:
            prompt, fact_items = _build_narration_prompt(owner, screened_facts, reasons)
            try:
                raw_narration, cost_usd, model_used = _run_narrator(prompt, fact_items)
                parsed_sents = _parse_narrated_sentences(raw_narration)
                accepted, dropped_sentences = _screen_sentences(parsed_sents, {f.id for f in screened_facts})
                if accepted:
                    mode = "narrated"
                    sentences = accepted
                    story_text = " ".join(s["text"] for s in accepted)
                else:
                    fallback_reason = "no_grounded_sentences"
                    cost_usd = 0.0
            except Exception as exc:
                fallback_reason = f"runner_failed: {type(exc).__name__}"
                cost_usd = 0.0
                model_used = None

    all_fact_ids = list(dict.fromkeys(fid for s in sentences for fid in s["fact_ids"]))
    as_of = max((f.valid_from for f in screened_facts if f.valid_from), default=None) or now_iso
    payload: dict[str, Any] = {
        "owner": owner,
        "mode": mode,
        "fallback_reason": fallback_reason,
        "cached": False,
        "story": story_text,
        "sentences": sentences,
        "timeline": timeline,
        "fact_ids": all_fact_ids,
        "dropped_sentences": dropped_sentences,
        "model": model_used,
        "cost_usd": cost_usd,
        "provenance": _envelope_provenance((f.provenance for f in screened_facts), is_demo=is_demo),
        "as_of": as_of,
        "demo_data": is_demo,
    }
    _write_cache(store, owner, versions, qhash, vkey, payload)
    return payload
