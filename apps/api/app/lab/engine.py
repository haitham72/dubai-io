"""The generic extraction engine. Everything source-specific lives in a skill (skills/); this file only:
  1. asks the registry for the skill of the source (whatsapp -> chat, gmail -> email, ...),
  2. cuts the source into units, packs units into model calls sized to the *loaded* context,
  3. asks the extraction LLM for the fields the skill's schema allows (never a feeling),
  4. lets code decide the rest: evidence, fail-closed sensitivity, name spelling, entity checks,
  5. scores sentiment + emotion with the two local classifiers (scoring.py),
  6. stores the row, projects topics / people into annotations, opens follow-ups,
  7. embeds the memory text so it is semantically searchable (the follow-up agent queries it).
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone

from app.config import settings

from . import llm, scoring
from .extract import norm
from .sensitive import categories_hit, filter_statement
from .skills import Context, Skill, Unit, skill_for
from .store import Lab


def pack(items: list, budget: int, cost, max_items: int) -> list[list]:
    packs, cur, used = [], [], 0
    for it in items:
        c = cost(it)
        if cur and (used + c > budget or len(cur) >= max_items):
            packs.append(cur)
            cur, used = [], 0
        cur.append(it)
        used += c
    return packs + ([cur] if cur else [])


def spread(items: list, n: int) -> list:
    """n items evenly spaced over the whole timeline (design tests on a long source without a long run)."""
    if n <= 0 or len(items) <= n:
        return items
    step = len(items) / n
    return [items[int(i * step)] for i in range(n)]


def version(skill: Skill) -> str:
    return f"{skill.name}-v2"


def _run(units: list[Unit], skill: Skill, ctx: Context, system: str, stats: Counter) -> list[tuple[Unit, dict | None]]:
    user = "\n".join(f"ROW {i}\n{skill.render(u, ctx)}\n" for i, u in enumerate(units, 1))
    try:
        stats["llm_calls"] += 1
        res = llm.chat_json(system, user, skill.schema, name="memory_rows", max_tokens=skill.max_output)
    except llm.ContextOverflow:
        if len(units) < 2:
            raise
        stats["overflow_splits"] += 1
        mid = len(units) // 2
        return _run(units[:mid], skill, ctx, system, stats) + _run(units[mid:], skill, ctx, system, stats)
    by_n = {int(it["row"]): it for it in res.get("items", []) if isinstance(it.get("row"), int)}
    return [(u, by_n.get(i)) for i, u in enumerate(units, 1)]


def _clamp(x, lo, hi) -> float:
    try:
        return max(lo, min(hi, float(x)))
    except (TypeError, ValueError):
        return 0.0


def _store(lab: Lab, skill: Skill, ctx: Context, unit: Unit, item: dict, now: str, stats: Counter, dropped: Counter) -> None:
    draft = skill.to_row(unit, item, ctx)
    for key, n in (draft.get("counters") or {}).items():
        stats[key] += n
    by_model = bool(draft["flagged"])
    by_keyword = any(text and filter_statement(text) for text in (draft["memory"], draft["user_text"], *draft["followups"], *draft["filter_texts"]))
    flagged = by_model or by_keyword
    if flagged:  # which layer withheld it? (the iteration log needs to know where the over-blocking comes from)
        stats["flagged_by_model"] += by_model
        stats["flagged_by_keyword_only"] += (by_keyword and not by_model)
        for text in (draft["memory"], draft["user_text"], *draft["followups"], *draft["filter_texts"]):
            for cat in categories_hit(text or ""):
                stats[f"keyword_category_{cat}"] += 1  # which never-infer list is firing
    if flagged:  # fail closed: nothing derived from this unit but harmless topic labels
        dropped["flagged_row"] += 1
        # a topic can itself name the sensitive subject ("health"), so a flagged row keeps no topics either
        draft.update(memory="", user_text="", followups=[], multimodal=[], extra={}, people=[], suggestions=[], topics=[])
    kept = []
    for t in draft["topics"]:
        cat = filter_statement(t)
        if cat:
            dropped[cat] += 1
        else:
            kept.append(t)
    names = [n for n in draft["names"] if not filter_statement(n)]
    people = [n for n in draft["people"] if not filter_statement(n)]

    sentiment, emotions, other, scorers = None, {}, None, None
    if not flagged:
        groups, scorers = scoring.score_groups(skill.score_texts(unit, draft, ctx))
        if groups.get("owner"):
            sentiment, emotions = groups["owner"]["sentiment"], groups["owner"]["emotions"]
        other = groups.get("other")
        stats["rows_scored" if (groups.get("owner") or other) else "rows_unscored"] += 1

    rid = lab.add_row(
        chat=ctx.source, kind=skill.name, first_idx=unit.first_idx, last_idx=unit.last_idx, n_msgs=len(unit.evidence),
        t_start=unit.t_start, t_end=unit.t_end, t_avg=unit.t_avg, topics=kept, names=names, user_text=draft["user_text"],
        memory=draft["memory"], multimodal=draft["multimodal"], emotions=emotions,
        sentiment=sentiment, scores_other=other, scorers=scorers,
        salience={t: round(_clamp(v, 0, 1), 2) for t, v in draft["salience"].items() if t in kept},
        extra=draft["extra"], sensitive=int(flagged), text_hash=unit.text_hash, prompt_version=version(skill),
        model=settings.lab_model, as_of=now,
    )
    for t in kept:
        lab.add_annotation(rid, ctx.source, "topic", t, norm(t), unit.evidence, valid_from=unit.t_avg, as_of=now)
    for who in people:
        lab.add_annotation(rid, ctx.source, "person", who, norm(who), unit.evidence, valid_from=unit.t_avg, as_of=now)
    questions = [("model", q) for q in draft["followups"]]
    if not flagged:  # deterministic questions: things we truthfully cannot see (an image, an attachment)
        questions += skill.extra_followups(unit, draft, ctx)
    for kind, q in questions:
        lab.add_followup(rid, q, now)
        stats["followups_opened" if kind == "model" else f"followups_{kind}"] += 1
    lab.sync_followup_flag(rid)
    for alias, canonical in draft["suggestions"]:
        lab.add_alias_suggestion(ctx.source, alias, canonical)
        stats["alias_suggestions"] += 1
    stats["rows_stored"] += 1


def process(lab: Lab, connector_id: str, source: str, ctx: Context, *, sample: int = 0, days: int = 0) -> dict:
    skill = skill_for(connector_id)
    records = lab.load_messages(connector_id, source)
    system = skill.system(ctx)
    context = llm.loaded_context()
    budget = min(skill.pack_tokens, llm.input_budget(context, llm.est_tokens(system) + llm.est_tokens(json.dumps(skill.schema)),
                                                     skill.max_output))
    all_units = skill.units(records, ctx)
    if days and all_units:  # only the most recent N days of this source (relative to its newest unit)
        cutoff = (max(datetime.fromisoformat(u.t_end) for u in all_units) - timedelta(days=days)).isoformat()
        all_units = [u for u in all_units if u.t_end >= cutoff]
    chosen = spread(all_units, sample)
    pending = [u for u in chosen if not lab.row_done(source, u.first_idx, u.last_idx, u.text_hash, version(skill))]
    stats: Counter = Counter(skill=skill.name, rows_total=len(all_units), context=context, pack_budget_tokens=budget,
                             rows_skipped_done=len(chosen) - len(pending))
    dropped: Counter = Counter()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    est = llm.est_tokens
    for group in pack(pending, budget, lambda u: skill.cost(u, est), settings.lab_pack_items or skill.pack_items):
        for unit, item in _run(group, skill, ctx, system, stats):
            if item is None:
                stats["rows_missing_from_model"] += 1  # not stored: the next run retries it
                continue
            _store(lab, skill, ctx, unit, item, now, stats, dropped)
        lab.db.commit()
    stats["dropped_by_category"] = dict(dropped)
    stats["scorers"] = scoring.get_scorer().info()
    stats["llm_usage"] = {**{k: round(v, 1) for k, v in llm.USAGE.items()},
                          "completion_tokens_per_second": round(llm.USAGE["completion_tokens"] / llm.USAGE["seconds"], 1) if llm.USAGE["seconds"] else None}
    embed_memory(lab, stats)
    return dict(stats)


def embed_memory(lab: Lab, stats: Counter | dict) -> None:
    """Semantic index of the memories: every row's memory + topics gets a vector the follow-up agent queries."""
    from . import index

    try:
        stats["memory_embedded"] = index.build_windows(lab)["windows"]
    except llm.LabLLMError as exc:  # the embedding model is down: rows stay, search falls back to keywords
        stats["memory_embedding"] = f"unavailable: {str(exc)[:120]}"
