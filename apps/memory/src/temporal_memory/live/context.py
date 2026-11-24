"""L1 instant context pack (<150 ms, zero LLM).

Ported from:
- `fold`: g:\\Haitham\\VsCode\\contest\\apps\\api\\app\\lab\\circle.py:22-31
- `rrf`: g:\\Haitham\\VsCode\\contest\\apps\\api\\app\\lab\\searchlib.py:73-79
- Whole-word alias match & `_extract_date`:
  C:\\Users\\h.ibrahim\\Documents\\Claude\\Projects\\temporal_note\\mcp_server\\memory_tools.py:55-136,464-487
"""
from __future__ import annotations

from collections import defaultdict
import copy
from datetime import date, datetime, timedelta, timezone
import re
from typing import Any, Iterable

from temporal_memory.models import Entity, EntitySubject, Fact, GraphStore, HELD_BACK_ROOTS, Link, Subject

_DIACRITICS = re.compile("[\u064b-\u065f\u0670\u0640]")
_LETTERS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه"})
_TOKEN_RE = re.compile(r"[0-9a-zA-Z\u0621-\u064a\u0660-\u0669]+")
_CAP_CANDIDATE_RE = re.compile(r"(?:@[a-zA-Z0-9_]{2,}|\b[A-Z][a-zA-Z]{2,}(?:\s+[A-Z][a-zA-Z]{2,})?\b)")
_NON_NAME_WORDS = frozenset(
    "The This That What Where When Why How Who Which Did Does Do Ask Send Check Update Please Sorry Thanks Hello "
    "Monday Tuesday Wednesday Thursday Friday Saturday Sunday January February March April May June July August "
    "September October November December Jan Feb Mar Apr Jun Jul Aug Sep Oct Nov Dec Today Yesterday Tomorrow "
    "AED Dubai".split()
)
_CTX_STOPWORDS = frozenset(
    "is are was were be been the and or of to in on at for with by from as that this these those "
    "what where when why how who which did does do has have had his her their him them she he they we you me my".split()
)
_ALIAS_STOPWORDS = frozenset({
    "the", "and", "for", "with", "team", "dev", "devs", "new", "guy", "ai", "app",
    "project", "backend", "frontend", "mobile", "design", "manager", "lead",
    "hr", "it", "md", "ceo", "cfo", "user", "person", "people", "someone", "flat",
})
_MIN_AUTO_ALIAS_LEN = 3
_HELD_BACK_ROOTS = frozenset(HELD_BACK_ROOTS)

_DEFAULT_STORE: GraphStore | None = None
_ALIAS_CACHE: dict[str, tuple[Any, dict[str, list[Entity]], dict[str, Entity]]] = {}
_PACK_CACHE: dict[str, tuple[Any, dict[tuple[str, int], dict[str, Any]]]] = {}

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
_AED_PATTERNS = (
    re.compile(r"\bAED\s*([0-9][0-9,]*(?:\.[0-9]+)?(?:\s*-\s*[0-9][0-9,]*)?\s*[kK]?)\b", re.I),
    re.compile(r"\b([0-9][0-9,]*(?:\.[0-9]+)?\s*[kK]?)\s*(?:AED|درهم)\b", re.I),
)


def set_default_store(store: GraphStore | None) -> None:
    """Register the process default GraphStore used when context_pack omits `store`."""
    global _DEFAULT_STORE
    _DEFAULT_STORE = store


def invalidate_alias_cache(owner: str | None = None) -> None:
    """Clear cached alias and context-pack caches for one owner or all owners."""
    if owner is None:
        _ALIAS_CACHE.clear()
        _PACK_CACHE.clear()
    else:
        _ALIAS_CACHE.pop(owner, None)
        _PACK_CACHE.pop(owner, None)


def fold(text: str) -> str:
    """Spelling-insensitive normalization for English, Arabic, and Arabizi tokens."""
    cleaned = _DIACRITICS.sub("", (text or "").lower()).translate(_LETTERS)
    return re.sub(r"[\W_]+", " ", cleaned).strip()


def fold_tokens(text: str) -> list[str]:
    """Tokenize folded text while keeping Arabizi alphanumeric forms (e.g. 3omar)."""
    cleaned = _DIACRITICS.sub("", (text or "").lower()).translate(_LETTERS)
    return [tok for tok in _TOKEN_RE.findall(cleaned) if len(tok) >= 2]


def rrf(rankings: list[list[str]], k: int = 60) -> list[str]:
    """Reciprocal Rank Fusion over ranked document ID lists."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for pos, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + pos + 1)
    return [doc_id for doc_id, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))]


def extract_date(text: str, *, reference_date: date | None = None) -> list[dict[str, Any]]:
    """Extract ISO, Month-day, and relative dates (returns list of parsed hits)."""
    today = reference_date or date.today()
    hits: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _push(iso: str, raw: str, retrospective: bool) -> None:
        if iso not in seen:
            seen.add(iso)
            hits.append({"iso": iso, "raw": raw, "retrospective": retrospective})

    for m in re.finditer(r"\b(\d{4}-\d{2}-\d{2})\b", text or ""):
        _push(m.group(1), m.group(1), m.group(1) != today.isoformat())
    low = fold(text)
    if "yesterday" in low or "امس" in low:
        iso = (today - timedelta(days=1)).isoformat()
        _push(iso, "yesterday", True)
    if "last week" in low or "الاسبوع الماضي" in low or "الاسبوع اللي فات" in low:
        _push((today - timedelta(days=7)).isoformat(), "last week", True)
    if re.search(r"\b(last month|a month ago)\b", low):
        _push((today - timedelta(days=30)).isoformat(), "last month", True)
    for m in re.finditer(r"\b(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", low):
        try:
            d = date(today.year, _MONTHS[m.group(2)[:3]], int(m.group(1)))
            _push(d.isoformat(), m.group(0), d != today)
        except ValueError:
            pass
    for m in re.finditer(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})\b", low):
        try:
            d = date(today.year, _MONTHS[m.group(1)[:3]], int(m.group(2)))
            _push(d.isoformat(), m.group(0), d != today)
        except ValueError:
            pass
    return hits


def extract_aed(text: str) -> list[dict[str, Any]]:
    """Extract AED amounts (e.g. 'AED 48,000', '28-32k AED', '5400 درهم')."""
    hits: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    for rx in _AED_PATTERNS:
        for m in rx.finditer(text or ""):
            span = m.span()
            if any(not (span[1] <= s[0] or span[0] >= s[1]) for s in seen):
                continue
            seen.add(span)
            raw_num = m.group(1).replace(",", "").lower().strip()
            amount: float | None = None
            try:
                if "-" in raw_num:
                    hi = raw_num.split("-")[-1].strip()
                    mult = 1000.0 if hi.endswith("k") else 1.0
                    amount = float(hi.rstrip("k")) * mult
                else:
                    mult = 1000.0 if raw_num.endswith("k") else 1.0
                    amount = float(raw_num.rstrip("k")) * mult
            except ValueError:
                pass
            hits.append({"raw": m.group(0).strip(), "amount_aed": amount, "currency": "AED"})
    return hits


def _call_optional(store: Any, name: str, *args: Any, default: Any = None, **kwargs: Any) -> Any:
    fn = getattr(store, name, None)
    return fn(*args, **kwargs) if callable(fn) else default


def _version_tuple(store: Any, owner: str) -> tuple[int, int, int]:
    av = _call_optional(store, "alias_version", owner, default=0)
    fv = _call_optional(store, "facts_version", owner, default=0)
    pv = _call_optional(store, "privacy_revision", owner, default=0)
    return (int(av or 0), int(fv or 0), int(pv or 0))


def _build_alias_index(
    store: Any,
    owner: str,
    *,
    version: tuple[int, int, int] | None = None,
) -> tuple[dict[str, list[Entity]], dict[str, Entity]]:
    entities: list[Entity] = _call_optional(store, "list_entities", owner, default=[])
    ver_key: Any = version if version is not None else (
        len(entities),
        tuple((e.id, tuple(e.aliases), e.status) for e in entities),
    )
    cached = _ALIAS_CACHE.get(owner)
    if cached and cached[0] == ver_key:
        return cached[1], cached[2]

    alias_map: dict[str, list[Entity]] = defaultdict(list)
    by_id: dict[str, Entity] = {}
    for ent in entities:
        if ent.status == "merged":
            continue
        by_id[ent.id] = ent
        candidates: set[str] = set()
        for raw_alias in [ent.name, *ent.aliases]:
            phrase = " ".join(fold_tokens(raw_alias))
            if phrase and phrase not in _ALIAS_STOPWORDS and len(phrase) >= 2:
                candidates.add(phrase)
            for part in fold_tokens(raw_alias):
                if len(part) >= _MIN_AUTO_ALIAS_LEN and part not in _ALIAS_STOPWORDS:
                    candidates.add(part)
        for key in candidates:
            if ent not in alias_map[key]:
                alias_map[key].append(ent)

    _ALIAS_CACHE[owner] = (ver_key, dict(alias_map), by_id)
    return _ALIAS_CACHE[owner][1], by_id


def _match_aliases(
    query_tokens: list[str],
    alias_map: dict[str, list[Entity]],
) -> tuple[list[tuple[str, list[Entity]]], set[str]]:
    """Whole-word n-gram match over folded tokens; longest phrase wins at each start index."""
    hits: list[tuple[str, list[Entity]]] = []
    matched_tokens: set[str] = set()
    i, n = 0, len(query_tokens)
    while i < n:
        matched_span: tuple[int, str, list[Entity]] | None = None
        for width in (3, 2, 1):
            if i + width > n:
                continue
            phrase = " ".join(query_tokens[i : i + width])
            cands = alias_map.get(phrase)
            if cands:
                matched_span = (width, phrase, cands)
                break
        if matched_span:
            width, phrase, cands = matched_span
            hits.append((phrase, cands))
            matched_tokens.update(query_tokens[i : i + width])
            i += width
        else:
            i += 1
    return hits, matched_tokens


def _resolve_collisions(
    hits: list[tuple[str, list[Entity]]],
    query_tokens: set[str],
    links: list[Link],
    entity_subjects: list[EntitySubject],
    subjects_by_id: dict[str, Subject],
    facts: list[Fact],
) -> tuple[list[dict[str, Any]], set[str]]:
    """Resolve ambiguous aliases using co-occurring entities, subject overlap, and recency."""
    unambiguous_ids: set[str] = {cands[0].id for _, cands in hits if len(cands) == 1}
    linked_neighbors: dict[str, set[str]] = defaultdict(set)
    for lnk in links:
        linked_neighbors[lnk.src].add(lnk.dst)
        linked_neighbors[lnk.dst].add(lnk.src)

    ent_subj_tokens: dict[str, set[str]] = defaultdict(set)
    ent_subj_ids: dict[str, set[str]] = defaultdict(set)
    for es in entity_subjects:
        ent_subj_ids[es.entity_id].add(es.subject_id)
        subj = subjects_by_id.get(es.subject_id)
        if subj and subj.sensitive_cat is None:
            ent_subj_tokens[es.entity_id].update(fold_tokens(subj.label))
            ent_subj_tokens[es.entity_id].update(fold_tokens(subj.path))

    ent_fact_tokens: dict[str, set[str]] = defaultdict(set)
    for f in facts:
        toks = set(fold_tokens(f.text))
        if f.text_orig:
            toks.update(fold_tokens(f.text_orig))
        for fe in f.entities:
            ent_fact_tokens[fe.entity_id].update(toks)
            if fe.role:
                ent_fact_tokens[fe.entity_id].update(fold_tokens(fe.role))

    chosen: dict[str, dict[str, Any]] = {}
    ambiguous_ids: set[str] = set()

    def _recency_val(ent: Entity) -> str:
        return ent.last_seen or ent.first_seen or ""

    for phrase, cands in hits:
        if len(cands) == 1:
            e = cands[0]
            chosen.setdefault(e.id, {"entity": e, "matched_via": phrase, "ambiguous": False, "confidence": "high"})
            continue

        scored: list[tuple[float, str, float, Entity]] = []
        for e in cands:
            ctx = 0.0
            for uid in unambiguous_ids:
                if uid in linked_neighbors.get(e.id, ()):
                    ctx += 3.0
                if ent_subj_ids.get(e.id, set()) & ent_subj_ids.get(uid, set()):
                    ctx += 2.0
            meaningful_q = query_tokens - _CTX_STOPWORDS - {phrase}
            overlap = meaningful_q & (ent_subj_tokens.get(e.id, set()) | ent_fact_tokens.get(e.id, set()))
            ctx += 1.5 * len(overlap)
            scored.append((ctx, _recency_val(e), e.salience, e))

        scored.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
        has_clear_ctx = len(scored) > 1 and scored[0][0] > scored[1][0]
        if has_clear_ctx:
            winner = scored[0][3]
            chosen.setdefault(winner.id, {"entity": winner, "matched_via": phrase, "ambiguous": False, "confidence": "high"})
        else:
            for _, _, _, cand in scored:
                ambiguous_ids.add(cand.id)
                chosen.setdefault(cand.id, {"entity": cand, "matched_via": phrase, "ambiguous": True, "confidence": "low"})

    ordered = sorted(
        chosen.values(),
        key=lambda r: (0 if not r["ambiguous"] else 1, -r["entity"].salience, r["entity"].name),
    )
    return ordered, ambiguous_ids


def _extract_candidates(text: str, matched_tokens: set[str], existing_names: set[str]) -> list[str]:
    found: list[str] = []
    for m in _CAP_CANDIDATE_RE.finditer(text or ""):
        parts = [w for w in m.group(0).strip().split() if w not in _NON_NAME_WORDS]
        raw = " ".join(parts)
        if not raw:
            continue
        ftoks = set(fold_tokens(raw))
        if not ftoks or ftoks <= matched_tokens or fold(raw) in existing_names:
            continue
        if raw not in found:
            found.append(raw)
    return found


def _is_sensitive_hidden(fact: Fact, subjects_by_id: dict[str, Subject]) -> bool:
    if fact.provenance in ("user_supplied", "provider_confirmed"):
        return False
    subj = subjects_by_id.get(fact.subject_id)
    if subj is None:
        return False
    root = (subj.path or "").split("/")[0].strip().lower()
    return subj.sensitive_cat is not None or root in _HELD_BACK_ROOTS


def _review_state(prov: str, is_demo: bool) -> str:
    if is_demo or prov == "demo_fixture":
        return "demo"
    if prov in ("user_supplied", "provider_confirmed"):
        return "confirmed"
    return "pending_review"


def _envelope_provenance(items: Iterable[str], *, is_demo: bool) -> str:
    if is_demo:
        return "demo_fixture"
    vals = {p for p in items if p}
    if not vals:
        return "inferred"
    if vals <= {"user_supplied", "provider_confirmed"}:
        return "user_supplied"
    return "inferred"


def context_pack(owner: str, text: str, max_tokens: int = 1500, *, store: GraphStore | None = None) -> dict:
    """Build deterministic L1 context pack using bounded SQL retrieval (no LLM, p95 < 150 ms)."""
    st: Any = store or _DEFAULT_STORE
    if st is None:
        raise RuntimeError("No GraphStore configured for live.context_pack")

    now_iso = datetime.now(timezone.utc).isoformat()
    ver = _version_tuple(st, owner)
    cache_key = (fold(text), max_tokens)
    cached_owner = _PACK_CACHE.get(owner)
    if cached_owner and cached_owner[0] == ver and cache_key in cached_owner[1]:
        hit_pack = copy.deepcopy(cached_owner[1][cache_key])
        hit_pack["as_of"] = now_iso
        return hit_pack

    owner_obj = _call_optional(st, "get_owner", owner, default=None)
    is_demo = bool(owner_obj and owner_obj.kind == "demo")

    alias_map, by_id = _build_alias_index(st, owner, version=ver)
    subjects: list[Subject] = _call_optional(st, "list_subjects", owner, default=[])
    subjects_by_id = {s.id: s for s in subjects}
    links: list[Link] = _call_optional(st, "list_links", owner, default=[])
    entity_subjects: list[EntitySubject] = _call_optional(st, "list_entity_subjects", owner, default=[])

    q_tokens = fold_tokens(text)
    alias_hits, matched_toks = _match_aliases(q_tokens, alias_map)
    ambig_eids = sorted({c.id for _, cands in alias_hits if len(cands) > 1 for c in cands})
    ambig_facts: list[Fact] = (
        st.visible_facts(owner, entity_ids=ambig_eids, limit=80) if ambig_eids else []
    )
    resolved_entities, _ = _resolve_collisions(
        alias_hits, set(q_tokens), links, entity_subjects, subjects_by_id, ambig_facts
    )
    matched_eids = {item["entity"].id for item in resolved_entities}

    q_tok_set = set(q_tokens)
    hinted_sids: set[str] = {es.subject_id for es in entity_subjects if es.entity_id in matched_eids}
    for subj in subjects:
        if subj.sensitive_cat is None and (q_tok_set & set(fold_tokens(subj.label + " " + subj.path))):
            hinted_sids.add(subj.id)

    search_fn = getattr(st, "search_candidates", None)
    get_facts_fn = getattr(st, "get_facts", None)
    candidate_facts: list[Fact] = []
    if callable(search_fn) and callable(get_facts_fn):
        cands = search_fn(
            owner,
            text,
            entity_ids=list(matched_eids) or None,
            subject_ids=list(hinted_sids) or None,
            limit=50,
        )
        ranked_ids = [c.fact_id for c in cands]
        candidate_facts = get_facts_fn(owner, ranked_ids)
    else:
        seen_ids: set[str] = set()
        if matched_eids or hinted_sids:
            for f in st.visible_facts(
                owner,
                entity_ids=list(matched_eids) or None,
                subject_ids=list(hinted_sids) or None,
                limit=50,
            ):
                if f.id not in seen_ids:
                    seen_ids.add(f.id)
                    candidate_facts.append(f)
        for f in st.visible_facts(owner, limit=50):
            if f.id not in seen_ids:
                seen_ids.add(f.id)
                candidate_facts.append(f)

    candidate_facts = [
        f for f in candidate_facts
        if f.status != "history" and not _is_sensitive_hidden(f, subjects_by_id)
    ]

    # Open changes related to matched entities or top retrieved facts (bounded SQL query when supported)
    top_fids = [f.id for f in candidate_facts[:16]]
    open_changes: list[dict[str, Any]] = []
    open_fn = getattr(st, "list_open_changes", None)
    if callable(open_fn):
        for f, sup_text in open_fn(owner, entity_ids=list(matched_eids), fact_ids=top_fids, limit=8):
            if _is_sensitive_hidden(f, subjects_by_id):
                continue
            open_changes.append({
                "fact_id": f.id,
                "status": f.status,
                "summary": f"{f.text} (was until {f.valid_to or '?'})" + (f" -> {sup_text}" if sup_text else ""),
                "valid_from": f.valid_from,
                "valid_to": f.valid_to,
                "superseded_by": f.superseded_by,
                "provenance": f.provenance,
                "as_of": now_iso,
            })
    else:
        fact_pool = list(candidate_facts)
        if matched_eids:
            seen_pool = {f.id for f in fact_pool}
            for f in st.visible_facts(owner, entity_ids=list(matched_eids), limit=50):
                if f.id not in seen_pool:
                    fact_pool.append(f)
                    seen_pool.add(f.id)
        by_fid = {f.id: f for f in fact_pool}
        relevant_fids = set(top_fids)
        for f in fact_pool:
            if f.status not in ("superseded", "ended") or _is_sensitive_hidden(f, subjects_by_id):
                continue
            if not ((f.id in relevant_fids) or any(fe.entity_id in matched_eids for fe in f.entities)):
                continue
            sup = by_fid.get(f.superseded_by) if f.superseded_by else None
            if sup is None and f.superseded_by and callable(get_facts_fn):
                res = get_facts_fn(owner, [f.superseded_by])
                sup = res[0] if res else None
            open_changes.append({
                "fact_id": f.id,
                "status": f.status,
                "summary": f"{f.text} (was until {f.valid_to or '?'})" + (f" -> {sup.text}" if sup else ""),
                "valid_from": f.valid_from,
                "valid_to": f.valid_to,
                "superseded_by": f.superseded_by,
                "provenance": f.provenance,
                "as_of": now_iso,
            })
            if len(open_changes) >= 8:
                break

    char_budget = max(200, max_tokens * 4)
    used_chars = 0

    es_by_eid: dict[str, list[EntitySubject]] = defaultdict(list)
    for es in entity_subjects:
        subj = subjects_by_id.get(es.subject_id)
        if subj and subj.sensitive_cat is not None:
            continue
        es_by_eid[es.entity_id].append(es)

    sal_eids = [item["entity"].id for item in resolved_entities]
    sal_map: dict[str, float] = (
        (_call_optional(st, "entity_salience_map", owner, entity_ids=sal_eids, default={}) or {})
        if sal_eids
        else {}
    )

    entity_cards: list[dict[str, Any]] = []
    for item in resolved_entities:
        ent: Entity = item["entity"]
        ent_prov = getattr(ent, "provenance", "inferred") or "inferred"
        roles = [
            {
                "subject_id": es.subject_id,
                "subject": subjects_by_id[es.subject_id].label if es.subject_id in subjects_by_id else es.subject_id,
                "role": es.role,
            }
            for es in es_by_eid.get(ent.id, [])
        ]
        card = {
            "id": ent.id,
            "name": ent.name,
            "kind": ent.kind,
            "status": ent.status,
            "relation_to_user": ent.relation_to_user,
            "closeness_tier": ent.closeness_tier,
            "closeness_suggested": getattr(ent, "closeness_suggested", None),
            "aliases": ent.aliases,
            "salience": sal_map.get(ent.id, ent.salience),
            "roles_per_subject": roles,
            "ambiguous": item["ambiguous"],
            "confidence": item["confidence"],
            "matched_via": item["matched_via"],
            "provenance": ent_prov,
            "review_state": _review_state(ent_prov, is_demo),
            "as_of": ent.last_seen or now_iso,
        }
        est = len(ent.name) + 60 + sum(len(str(r)) for r in roles)
        if used_chars + est <= char_budget:
            entity_cards.append(card)
            used_chars += est

    packed_facts: list[dict[str, Any]] = []
    for f in candidate_facts:
        est = len(f.text) + len(f.text_orig or "") + 64
        if packed_facts and used_chars + est > char_budget:
            break
        packed_facts.append({
            "id": f.id,
            "text": f.text,
            "text_orig": f.text_orig,
            "subject_id": f.subject_id,
            "valid_from": f.valid_from,
            "valid_to": f.valid_to,
            "status": f.status,
            "superseded_by": f.superseded_by,
            "provenance": f.provenance,
            "review_state": _review_state(f.provenance, is_demo),
            "as_of": f.valid_from or now_iso,
            "demo_data": is_demo or f.provenance == "demo_fixture",
        })
        used_chars += est

    existing_folded = {fold(e.name) for e in by_id.values()} | {fold(a) for e in by_id.values() for a in e.aliases}
    candidate_names = _extract_candidates(text, matched_toks, existing_folded)
    env_prov = _envelope_provenance(
        [*(f["provenance"] for f in packed_facts), *(e["provenance"] for e in entity_cards)],
        is_demo=is_demo,
    )

    result = {
        "owner": owner,
        "entities": entity_cards,
        "facts": packed_facts,
        "open_changes": open_changes[:8],
        "candidate_names": candidate_names,
        "dates": extract_date(text),
        "aed_amounts": extract_aed(text),
        "tokens_est": max(1, used_chars // 4),
        "provenance": env_prov,
        "as_of": now_iso,
        "demo_data": is_demo,
    }
    bucket = _PACK_CACHE.setdefault(owner, (ver, {}))
    if bucket[0] != ver:
        _PACK_CACHE[owner] = (ver, {cache_key: copy.deepcopy(result)})
    else:
        if len(bucket[1]) >= 128:
            bucket[1].clear()
        bucket[1][cache_key] = copy.deepcopy(result)
    return result
