"""PostgreSQL 17 multi-channel retrieval, RRF fusion, and SQL salience helpers (U1c)."""
from __future__ import annotations

from collections import defaultdict
import contextvars
from datetime import date, timedelta
import os
import re
from typing import Any, Iterable, Literal

from temporal_memory.config import get_settings
from temporal_memory.db.db import Database, fold_text
from temporal_memory.models import Candidate

# E9b: how the semantic channel went on the latest search in this context: ok | no_embeddings |
# embedder_unavailable | disabled | skipped. The live context pack surfaces it so degradation is honest.
LAST_SEMANTIC: contextvars.ContextVar[str] = contextvars.ContextVar("tm_last_semantic", default="skipped")

ChannelName = Literal["fts", "entity", "subject", "date", "semantic"]

_PER_CHANNEL_LIMIT = 60

_STOPWORDS = frozenset({
    "a", "again", "an", "and", "are", "as", "at", "be", "been", "being", "but", "by", "can",
    "could", "did", "do", "does", "doing", "done", "for", "from", "had", "has", "have",
    "he", "her", "here", "hers", "him", "his", "how", "i", "if", "in", "into", "is",
    "it", "its", "just", "me", "more", "most", "my", "no", "not", "now", "of", "ok",
    "on", "or", "our", "out", "over", "said", "say", "she", "should", "so", "some",
    "still", "than", "that", "the", "their", "them", "then", "there", "these", "they",
    "this", "those", "to", "too", "up", "us", "was", "we", "were", "what", "when",
    "where", "which", "who", "whom", "why", "will", "with", "would", "you", "your",
    # Arabic & Arabizi stopwords
    "من", "في", "على", "الى", "إلى", "عن", "مع", "هل", "ما", "ماذا", "متى", "امتى",
    "اين", "أين", "فين", "مين", "منو", "ليش", "لماذا", "كيف", "اي", "أي", "ايه",
    "اللي", "التي", "الذي", "هذا", "هذه", "ذلك", "هو", "هي", "هم", "انا", "أنا",
    "انت", "أنت", "كان", "كانت", "يكون", "لا", "لم", "لن", "قد", "او", "أو", "و",
    "el", "al", "fe", "fi", "min", "men", "3an", "emta", "fein", "meen", "eih",
    "delwa2ty", "delwati", "leh", "ezay", "ya",
})
_NOISE_TOKENS = frozenset({
    "ok", "okay", "lol", "lmao", "rofl", "haha", "hahaha", "hehe", "kk", "k",
    "thx", "thanks", "ty", "yep", "yup", "nope", "nice", "cool", "wow", "gm", "gn", "hi", "hey",
})

# Lightweight EN <-> AR <-> Arabizi everyday domain bridges for Postgres simple FTS + subjects.
_SYNONYM_GROUPS: tuple[tuple[str, ...], ...] = (
    ("wedding", "marry", "marriage", "bride", "groom", "فرح", "زفاف", "عرس", "زواج", "fara7"),
    ("course", "cohort", "class", "classes", "training", "كورس", "دورة", "تدريب", "الوكلاء"),
    ("start", "starts", "started", "begin", "begins", "يبدأ", "يبدا", "بدا", "بتبدأ", "hayebda2", "yebda2"),
    ("price", "cost", "aed", "سعر", "بكام", "كم", "تمن", "bekam", "درهم"),
    ("car", "camry", "autohub", "vehicle", "سيارة", "عربية", "عربيه", "كامري"),
    ("gym", "fitness", "workout", "train", "trainer", "coach", "fitzone", "peakform", "جيم", "نادي", "الجيم", "تمرين", "يمرن", "بيمرني", "بيمرن", "مدرب", "كوتش"),
    ("rent", "flat", "apartment", "housing", "landlord", "building", "lobby", "lease", "ايجار", "إيجار", "شقة", "شقه", "سكن"),
    ("interview", "hiring", "round", "recruiter", "offer", "مقابلة", "توظيف"),
    ("work", "works", "job", "office", "company", "boss", "manager", "شغل", "عمل", "يشتغل", "شركة", "مدير", "مديره", "مديرة", "مديرتي"),
    ("mom", "mother", "mama", "ماما", "امي", "أمي", "الوالدة"),
    ("father", "dad", "baba", "بابا", "ابي", "أبي", "والد", "والدي"),
    ("doctor", "clinic", "hospital", "medical", "health", "دكتور", "عيادة", "مستشفى", "صحة"),
    ("travel", "flight", "trip", "airport", "hotel", "سفر", "رحلة", "طيران", "مطار", "فندق"),
    ("restaurant", "cafe", "coffee", "dinner", "lunch", "food", "مطعم", "كافيه", "قهوة", "عشاء", "غداء", "أكل"),
    ("project", "app", "beta", "ship", "testflight", "مشروع", "تطبيق"),
    ("sport", "sports", "surf", "surfing", "football", "soccer", "padel", "tennis", "swim", "swimming", "basketball",
     "cycling", "yoga", "climbing", "volleyball", "cricket", "golf", "run", "running", "marathon", "رياضة", "كورة", "سباحة"),
    ("run", "running", "marathon", "10k", "half", "جري", "ماراثون"),
)

_SYNONYM_MAP: dict[str, tuple[str, ...]] = {}
for _grp in _SYNONYM_GROUPS:
    _folded = tuple(dict.fromkeys(fold_text(w) for w in _grp if fold_text(w)))
    for _tok in _folded:
        _SYNONYM_MAP[_tok] = _folded

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
_SAFE_TS_TOKEN = re.compile(r"^[0-9a-z\u0621-\u064a\u0660-\u0669]+$")
_NON_SENSITIVE_CLAUSE = (
    "(s.id IS NULL OR (s.sensitive_cat IS NULL AND split_part(s.path, '/', 1) NOT IN ('health', 'faith')) "
    "OR vf.provenance IN ('user_supplied', 'provider_confirmed'))"
)


def _like_prefix(prefix: str) -> str:
    return prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _append_fast_filters(
    clauses: list[str],
    params: list[Any],
    *,
    owner: str,
    date_from: str | None = None,
    date_to: str | None = None,
    source_prefix: str | None = None,
    avoid_partial_erased_index: bool = False,
) -> None:
    """Fast pre-filters on base `facts f` table; `visible_facts` visibility is verified in batch after channel LIMIT."""
    clauses.append("f.owner = %s")
    # For PK lookups (f.id = ANY(...)), prevent Postgres from picking partial index idx_facts_owner_hash(WHERE erased_at IS NULL).
    clauses.append("(f.erased_at IS NULL)::int = 1" if avoid_partial_erased_index else "f.erased_at IS NULL")
    clauses.append("f.status <> 'history'")
    params.append(owner)
    clauses.append(
        "(s.id IS NULL OR (s.sensitive_cat IS NULL AND split_part(s.path, '/', 1) NOT IN ('health', 'faith')) "
        "OR f.provenance IN ('user_supplied', 'provider_confirmed'))"
    )
    if date_from is not None:
        clauses.append("substr(f.valid_from, 1, 10) >= %s")
        params.append(date_from[:10])
    if date_to is not None:
        clauses.append("substr(f.valid_from, 1, 10) <= %s")
        params.append(date_to[:10])
    if source_prefix is not None:
        like = _like_prefix(source_prefix)
        clauses.append(
            "EXISTS (SELECT 1 FROM fact_evidence fe "
            "JOIN records r ON r.owner = fe.owner AND r.id = fe.record_id "
            "WHERE fe.owner = f.owner AND fe.fact_id = f.id "
            "AND r.erased_at IS NULL AND r.source LIKE %s ESCAPE '\\')"
        )
        clauses.append(
            "NOT EXISTS (SELECT 1 FROM fact_evidence fe "
            "JOIN records r ON r.owner = fe.owner AND r.id = fe.record_id "
            "WHERE fe.owner = f.owner AND fe.fact_id = f.id "
            "AND r.erased_at IS NULL AND r.source NOT LIKE %s ESCAPE '\\')"
        )
        params.extend([like, like])


def _content_tokens(query: str) -> list[str]:
    raw = [t for t in fold_text(query).split() if len(t) >= 2 and t not in _STOPWORDS]
    if not raw:
        raw = [t for t in fold_text(query).split() if t]
    return list(dict.fromkeys(raw))


def _arabic_variants(tok: str) -> list[str]:
    out = [tok]
    # Strip definite article / common attached Arabic proclitics for stem hits
    if any("\u0621" <= ch <= "\u064a" for ch in tok):
        if tok.startswith("ال") and len(tok) >= 4:
            out.append(tok[2:])
        if len(tok) >= 4 and tok[0] in ("و", "ب", "ل", "ك", "ف") and tok[1:].startswith("ال"):
            out.append(tok[3:])
        if len(tok) >= 5 and tok[0] in ("ب", "ي", "ت") and tok.endswith(("ني", "نا", "كم", "هم", "ها")):
            out.append(tok[1:-2])
    return out


def _expand_terms(tokens: Iterable[str], *, max_terms: int = 40) -> tuple[list[str], list[str]]:
    """Return (primary_terms, expanded_terms) sanitized for simple tsquery."""
    primary: list[str] = []
    expanded: list[str] = []
    seen_p: set[str] = set()
    seen_e: set[str] = set()

    def _add(target: list[str], seen: set[str], term: str) -> None:
        for part in fold_text(term).split():
            if _SAFE_TS_TOKEN.fullmatch(part) and part not in seen:
                seen.add(part)
                target.append(part)

    for tok in tokens:
        for var in _arabic_variants(tok):
            _add(primary, seen_p, var)
            _add(expanded, seen_e, var)
            for syn in _SYNONYM_MAP.get(var, ()):
                _add(expanded, seen_e, syn)
    return primary[:20], expanded[:max_terms]


def extract_query_dates(text: str, *, reference_date: date | None = None) -> list[str]:
    """Extract ISO dates or year prefixes mentioned in a natural-language query."""
    today = reference_date or date.today()
    hits: list[str] = []
    seen: set[str] = set()

    def _push(val: str) -> None:
        if val not in seen:
            seen.add(val)
            hits.append(val)

    for m in re.finditer(r"\b(\d{4}-\d{2}-\d{2})\b", text or ""):
        _push(m.group(1))
    low = fold_text(text)
    if "yesterday" in low or "امس" in low:
        _push((today - timedelta(days=1)).isoformat())
    if "last week" in low or "الاسبوع الماضي" in low:
        _push((today - timedelta(days=7)).isoformat())
    for m in re.finditer(r"\b(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", low):
        try:
            _push(date(today.year, _MONTHS[m.group(2)[:3]], int(m.group(1))).isoformat())
        except ValueError:
            pass
    for m in re.finditer(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})\b", low):
        try:
            _push(date(today.year, _MONTHS[m.group(1)[:3]], int(m.group(2))).isoformat())
        except ValueError:
            pass
    for m in re.finditer(r"\b((?:19|20)\d{2})\b", low):
        _push(m.group(1))
    return hits


def _match_seed_entities(conn: Any, owner: str, tokens: list[str]) -> list[str]:
    """Match entity aliases by n-gram phrase and strip-ال variants; resolve simple collisions."""
    if not tokens:
        return []
    alias_rows = conn.execute(
        """
        SELECT ea.entity_id, ea.alias_folded, e.salience
        FROM entity_aliases ea
        JOIN entities e ON e.owner = ea.owner AND e.id = ea.entity_id
        WHERE ea.owner = %s AND e.erased_at IS NULL AND e.status <> 'merged'
        """,
        (owner,),
    ).fetchall()
    if not alias_rows:
        return []

    by_key: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for row in alias_rows:
        af = row["alias_folded"] or ""
        if not af:
            continue
        pair = (row["entity_id"], float(row["salience"] or 0.0))
        if pair not in by_key[af]:
            by_key[af].append(pair)
        for part in af.split():
            if len(part) >= 3:
                for var in _arabic_variants(part):
                    if pair not in by_key[var]:
                        by_key[var].append(pair)

    candidates_per_phrase: list[list[str]] = []
    tok_variants = [_arabic_variants(t) for t in tokens]
    n = len(tokens)
    i = 0
    while i < n:
        hit_eids: list[str] | None = None
        for width in (3, 2, 1):
            if i + width > n:
                continue
            phrase = " ".join(tokens[i : i + width])
            if phrase in by_key:
                hit_eids = [eid for eid, _ in by_key[phrase]]
                i += width
                break
            if width == 1:
                for var in tok_variants[i]:
                    if var in by_key:
                        hit_eids = [eid for eid, _ in by_key[var]]
                        break
                    for syn in _SYNONYM_MAP.get(var, ()):
                        if syn in by_key:
                            hit_eids = [eid for eid, _ in by_key[syn]]
                            break
                    if hit_eids is not None:
                        break
                if hit_eids is not None:
                    i += 1
                    break
        if hit_eids is not None:
            candidates_per_phrase.append(hit_eids)
        else:
            i += 1

    if not candidates_per_phrase:
        return []

    unambiguous = {eids[0] for eids in candidates_per_phrase if len(eids) == 1}
    all_ambig = sorted({eid for eids in candidates_per_phrase if len(eids) > 1 for eid in eids})
    if not all_ambig:
        return list(dict.fromkeys(eids[0] for eids in candidates_per_phrase))

    # Disambiguate colliding aliases using query-token overlap + link/subject neighbors
    fact_rows = conn.execute(
        """
        SELECT fe.entity_id, vf.text, vf.text_orig, s.label AS s_label, s.path AS s_path
        FROM fact_entities fe
        JOIN visible_facts vf ON vf.owner = fe.owner AND vf.id = fe.fact_id
        LEFT JOIN subjects s ON s.owner = vf.owner AND s.id = vf.subject_id
        WHERE fe.owner = %s AND fe.entity_id = ANY(%s)
          AND (s.id IS NULL OR (s.sensitive_cat IS NULL AND split_part(s.path, '/', 1) NOT IN ('health', 'faith'))
               OR vf.provenance IN ('user_supplied', 'provider_confirmed'))
        LIMIT 200
        """,
        (owner, all_ambig),
    ).fetchall()
    ent_tokens: dict[str, set[str]] = defaultdict(set)
    for row in fact_rows:
        blob = f"{row['text']} {row['text_orig'] or ''} {row['s_label'] or ''} {row['s_path'] or ''}"
        ent_tokens[row["entity_id"]].update(_expand_terms(_content_tokens(blob))[1])

    q_expanded = set(_expand_terms(tokens)[1])
    neighbors: set[str] = set()
    if unambiguous:
        lnk_rows = conn.execute(
            """
            SELECT src, dst FROM links
            WHERE owner = %s AND erased_at IS NULL
              AND (src = ANY(%s) OR dst = ANY(%s))
            """,
            (owner, list(unambiguous), list(unambiguous)),
        ).fetchall()
        for lr in lnk_rows:
            neighbors.add(lr["src"])
            neighbors.add(lr["dst"])

    selected: list[str] = list(unambiguous)
    for eids in candidates_per_phrase:
        if len(eids) == 1:
            continue
        scored = []
        for eid in eids:
            ov = len(q_expanded & ent_tokens.get(eid, set()))
            nb = 2 if eid in neighbors else 0
            scored.append((ov * 1.5 + nb, eid))
        scored.sort(key=lambda item: (-item[0], item[1]))
        if scored[0][0] > scored[1][0]:
            selected.append(scored[0][1])
        else:
            selected.extend(eids)
    return list(dict.fromkeys(selected))


def _match_seed_subjects(conn: Any, owner: str, expanded_tokens: list[str]) -> list[str]:
    if not expanded_tokens:
        return []
    q_set = set(expanded_tokens)
    rows = conn.execute(
        """
        SELECT id, path, label, sensitive_cat
        FROM subjects
        WHERE owner = %s
        """,
        (owner,),
    ).fetchall()
    matched: list[str] = []
    for r in rows:
        if r["sensitive_cat"] is not None:
            continue
        s_toks = set(_expand_terms(_content_tokens(f"{r['path']} {r['label']}"))[1])
        if q_set & s_toks:
            matched.append(r["id"])
    return matched


def search_candidates(
    db: Database,
    owner: str,
    query: str,
    *,
    entity_ids: list[str] | None = None,
    subject_ids: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    source_prefix: str | None = None,
    limit: int = 50,
) -> list[Candidate]:
    """Multi-channel Postgres retrieval over visible_facts fused with weighted RRF."""
    if limit <= 0:
        return []

    q_clean = (query or "").strip()
    tokens = _content_tokens(q_clean)
    primary_terms, expanded_terms = _expand_terms(tokens)

    channel_ranks: list[tuple[ChannelName, float, list[str]]] = []
    status_by_id: dict[str, str] = {}
    sem_sims: dict[str, float] = {}

    with db.connection() as conn:
        # 1. FTS channel (GIN index on facts.tsv — tight AND first, relax to OR if < 15 hits)
        if primary_terms or expanded_terms:
            ts_primary = " | ".join(primary_terms) if primary_terms else ""
            ts_expanded = " | ".join(expanded_terms) if expanded_terms else ts_primary
            clauses: list[str] = []
            params: list[Any] = []
            _append_fast_filters(
                clauses, params, owner=owner, date_from=date_from, date_to=date_to, source_prefix=source_prefix
            )
            fts_ids: list[str] = []
            seen_fts: set[str] = set()
            if len(primary_terms) >= 2:
                ts_and = " & ".join(primary_terms[:6])
                and_rows = conn.execute(
                    f"""
                    SELECT f.id, f.status, ts_rank(f.tsv, to_tsquery('simple', %s)) AS rnk
                    FROM facts f
                    LEFT JOIN subjects s ON s.owner = f.owner AND s.id = f.subject_id
                    WHERE {' AND '.join(clauses)}
                      AND f.tsv @@ to_tsquery('simple', %s)
                    ORDER BY rnk DESC, f.valid_from DESC, f.id ASC
                    LIMIT %s
                    """,
                    (ts_and, *params, ts_and, _PER_CHANNEL_LIMIT),
                ).fetchall()
                for r in and_rows:
                    fts_ids.append(r["id"])
                    seen_fts.add(r["id"])
                    status_by_id[r["id"]] = r["status"]

            if len(fts_ids) < 15:
                or_rows = conn.execute(
                    f"""
                    SELECT f.id, f.status, ts_rank(f.tsv, to_tsquery('simple', %s)) AS rnk
                    FROM facts f
                    LEFT JOIN subjects s ON s.owner = f.owner AND s.id = f.subject_id
                    WHERE {' AND '.join(clauses)}
                      AND f.tsv @@ to_tsquery('simple', %s)
                    ORDER BY rnk DESC, f.valid_from DESC, f.id ASC
                    LIMIT %s
                    """,
                    (ts_expanded, *params, ts_expanded, _PER_CHANNEL_LIMIT),
                ).fetchall()
                for r in or_rows:
                    if r["id"] not in seen_fts:
                        fts_ids.append(r["id"])
                        seen_fts.add(r["id"])
                        status_by_id[r["id"]] = r["status"]
            if fts_ids:
                channel_ranks.append(("fts", 1.0, fts_ids[:_PER_CHANNEL_LIMIT]))

        # 2. Entity / Alias + 1-hop link expansion channel
        seed_eids = list(entity_ids) if entity_ids is not None else _match_seed_entities(conn, owner, tokens)
        if seed_eids:
            ent_fid_rows = conn.execute(
                "SELECT DISTINCT fact_id FROM fact_entities WHERE owner = %s AND entity_id = ANY(%s)",
                (owner, seed_eids),
            ).fetchall()
            ent_fids = [r["fact_id"] for r in ent_fid_rows]
            if ent_fids:
                clauses = []
                params = []
                _append_fast_filters(
                    clauses,
                    params,
                    owner=owner,
                    date_from=date_from,
                    date_to=date_to,
                    source_prefix=source_prefix,
                    avoid_partial_erased_index=True,
                )
                rows = conn.execute(
                    f"""
                    SELECT f.id, f.status
                    FROM facts f
                    LEFT JOIN subjects s ON s.owner = f.owner AND s.id = f.subject_id
                    WHERE {' AND '.join(clauses)}
                      AND f.id = ANY(%s)
                    ORDER BY f.valid_from DESC, f.id ASC
                    LIMIT %s
                    """,
                    (*params, ent_fids, _PER_CHANNEL_LIMIT),
                ).fetchall()
                direct_e_ids = [r["id"] for r in rows]
                for r in rows:
                    status_by_id[r["id"]] = r["status"]
                if direct_e_ids:
                    channel_ranks.append(("entity", 1.4, direct_e_ids))

            hop_rows = conn.execute(
                """
                SELECT DISTINCT CASE WHEN ln.src = ANY(%s) THEN ln.dst ELSE ln.src END AS neighbor_id
                FROM links ln
                WHERE ln.owner = %s AND ln.erased_at IS NULL
                  AND (ln.src = ANY(%s) OR ln.dst = ANY(%s))
                LIMIT 40
                """,
                (seed_eids, owner, seed_eids, seed_eids),
            ).fetchall()
            neighbor_eids = [r["neighbor_id"] for r in hop_rows if r["neighbor_id"] and r["neighbor_id"] not in seed_eids]
            if neighbor_eids:
                hop_fid_rows = conn.execute(
                    "SELECT DISTINCT fact_id FROM fact_entities WHERE owner = %s AND entity_id = ANY(%s)",
                    (owner, neighbor_eids[:20]),
                ).fetchall()
                hop_fids = [r["fact_id"] for r in hop_fid_rows]
                if hop_fids:
                    clauses = []
                    params = []
                    _append_fast_filters(
                        clauses,
                        params,
                        owner=owner,
                        date_from=date_from,
                        date_to=date_to,
                        source_prefix=source_prefix,
                        avoid_partial_erased_index=True,
                    )
                    hrows = conn.execute(
                        f"""
                        SELECT f.id, f.status
                        FROM facts f
                        LEFT JOIN subjects s ON s.owner = f.owner AND s.id = f.subject_id
                        WHERE {' AND '.join(clauses)}
                          AND f.id = ANY(%s)
                        ORDER BY f.valid_from DESC, f.id ASC
                        LIMIT %s
                        """,
                        (*params, hop_fids, _PER_CHANNEL_LIMIT),
                    ).fetchall()
                    hop_ids = [r["id"] for r in hrows]
                    for r in hrows:
                        status_by_id[r["id"]] = r["status"]
                    if hop_ids:
                        channel_ranks.append(("entity", 0.65, hop_ids))

        # 3. Subject + descendants channel.
        # Topic aliases are a SQL seed (indexed equality on folded query tokens),
        # then the same descendant walk and Rule-9 filter as a path/label hit.
        seed_sids = list(subject_ids) if subject_ids is not None else _match_seed_subjects(conn, owner, expanded_terms)
        if tokens:
            alias_rows = conn.execute(
                """
                SELECT DISTINCT subject_id
                FROM subject_aliases
                WHERE owner = %s AND alias_folded = ANY(%s)
                """,
                (owner, tokens),
            ).fetchall()
            seen_seeds = set(seed_sids)
            for row in alias_rows:
                sid = row["subject_id"]
                if sid and sid not in seen_seeds:
                    seed_sids.append(sid)
                    seen_seeds.add(sid)
        if seed_sids:
            desc_rows = conn.execute(
                """
                SELECT DISTINCT s2.id
                FROM subjects s1
                JOIN subjects s2 ON s2.owner = s1.owner
                  AND (s2.path = s1.path OR s2.path LIKE s1.path || '/%%')
                WHERE s1.owner = %s AND s1.id = ANY(%s)
                """,
                (owner, seed_sids),
            ).fetchall()
            all_sids = [r["id"] for r in desc_rows] or seed_sids
            clauses = []
            params = []
            _append_fast_filters(
                clauses, params, owner=owner, date_from=date_from, date_to=date_to, source_prefix=source_prefix
            )
            clauses.append("f.subject_id = ANY(%s)")
            params.append(all_sids)
            srows = conn.execute(
                f"""
                SELECT f.id, f.status
                FROM facts f
                LEFT JOIN subjects s ON s.owner = f.owner AND s.id = f.subject_id
                WHERE {' AND '.join(clauses)}
                ORDER BY f.valid_from DESC, f.id ASC
                LIMIT %s
                """,
                (*params, _PER_CHANNEL_LIMIT),
            ).fetchall()
            subj_fids = [r["id"] for r in srows]
            for r in srows:
                status_by_id[r["id"]] = r["status"]
            if subj_fids:
                channel_ranks.append(("subject", 0.9, subj_fids))

        # 4. Date channel (explicit range or dates extracted from query)
        q_dates = extract_query_dates(q_clean)
        if date_from is not None or date_to is not None or q_dates:
            clauses = []
            params = []
            _append_fast_filters(
                clauses, params, owner=owner, date_from=date_from, date_to=date_to, source_prefix=source_prefix
            )
            if date_from is None and date_to is None and q_dates:
                date_preds = []
                for d in q_dates:
                    if len(d) == 4:
                        date_preds.append("f.valid_from LIKE %s")
                        params.append(d + "%")
                    else:
                        dt = date.fromisoformat(d)
                        lo = (dt - timedelta(days=2)).isoformat()
                        hi = (dt + timedelta(days=2)).isoformat()
                        date_preds.append("(substr(f.valid_from, 1, 10) BETWEEN %s AND %s)")
                        params.extend([lo, hi])
                clauses.append(f"({' OR '.join(date_preds)})")
            drows = conn.execute(
                f"""
                SELECT f.id, f.status
                FROM facts f
                LEFT JOIN subjects s ON s.owner = f.owner AND s.id = f.subject_id
                WHERE {' AND '.join(clauses)}
                ORDER BY f.valid_from DESC, f.id ASC
                LIMIT %s
                """,
                (*params, _PER_CHANNEL_LIMIT),
            ).fetchall()
            date_fids = [r["id"] for r in drows]
            for r in drows:
                status_by_id[r["id"]] = r["status"]
            if date_fids:
                channel_ranks.append(("date", 0.35, date_fids))

        # Fallback: when empty query yielded no signal channels
        if not channel_ranks and not q_clean:
            clauses = []
            params = []
            _append_fast_filters(
                clauses, params, owner=owner, date_from=date_from, date_to=date_to, source_prefix=source_prefix
            )
            frows = conn.execute(
                f"""
                SELECT f.id, f.status
                FROM facts f
                LEFT JOIN subjects s ON s.owner = f.owner AND s.id = f.subject_id
                WHERE {' AND '.join(clauses)}
                ORDER BY f.valid_from DESC, f.id ASC
                LIMIT %s
                """,
                (*params, limit),
            ).fetchall()
            for r in frows:
                status_by_id[r["id"]] = r["status"]
            if frows:
                channel_ranks.append(("date", 0.5, [r["id"] for r in frows]))

        # 5. Lightweight co-subject expansion from top FTS/entity hits (helps multi-fact/contradiction clusters)
        top_seed_fids = []
        for ch_name, _, rids in channel_ranks:
            if ch_name in ("fts", "entity"):
                for fid in rids[:3]:
                    if fid not in top_seed_fids:
                        top_seed_fids.append(fid)
        if top_seed_fids[:3] and not seed_sids:
            sid_rows = conn.execute(
                """
                SELECT DISTINCT f.subject_id
                FROM facts f
                LEFT JOIN subjects s ON s.owner = f.owner AND s.id = f.subject_id
                WHERE f.owner = %s AND f.id = ANY(%s) AND (f.erased_at IS NULL)::int = 1
                  AND (s.id IS NULL OR (s.sensitive_cat IS NULL AND split_part(s.path, '/', 1) NOT IN ('health', 'faith')))
                """,
                (owner, top_seed_fids[:3]),
            ).fetchall()
            co_sids = [r["subject_id"] for r in sid_rows if r["subject_id"]]
            if co_sids:
                clauses = []
                params = []
                _append_fast_filters(
                    clauses, params, owner=owner, date_from=date_from, date_to=date_to, source_prefix=source_prefix
                )
                clauses.append("f.subject_id = ANY(%s)")
                params.append(co_sids)
                sib_rows = conn.execute(
                    f"""
                    SELECT f.id, f.status
                    FROM facts f
                    LEFT JOIN subjects s ON s.owner = f.owner AND s.id = f.subject_id
                    WHERE {' AND '.join(clauses)}
                    ORDER BY f.valid_from DESC, f.id ASC
                    LIMIT 20
                    """,
                    tuple(params),
                ).fetchall()
                sib_ids = [r["id"] for r in sib_rows]
                for r in sib_rows:
                    status_by_id[r["id"]] = r["status"]
                if sib_ids:
                    channel_ranks.append(("subject", 0.25, sib_ids))

        # 6. Semantic vector top-30 channel (local BAAI/bge-m3 1024-d + pgvector HNSW iterative scan)
        cfg = get_settings()
        sem_tokens = [t for t in tokens if t not in _NOISE_TOKENS]
        LAST_SEMANTIC.set("skipped")
        if not cfg.semantic_enabled:
            LAST_SEMANTIC.set("disabled")
        if cfg.semantic_enabled and q_clean and sem_tokens:
            LAST_SEMANTIC.set("ok")
            if os.environ.get("TM_SEMANTIC_LAZY_EMBED", "1") != "0":
                from temporal_memory.core.embed import ensure_embeddings

                # Separate connection inside: finish the lazy backfill outside this read transaction's snapshot.
                bf = ensure_embeddings(db, owner)
                if bf:
                    LAST_SEMANTIC.set(bf)
            has_emb = conn.execute(
                "SELECT 1 FROM facts WHERE owner = %s AND embedding IS NOT NULL AND erased_at IS NULL AND status <> 'history' LIMIT 1",
                (owner,),
            ).fetchone()
            if has_emb is None and LAST_SEMANTIC.get() == "ok":
                LAST_SEMANTIC.set("no_embeddings")
            if has_emb is not None:
                try:
                    from temporal_memory.core.embed import embed_query, vector_literal

                    q_vec_lit = vector_literal(embed_query(q_clean, model_name=cfg.semantic_model))
                except Exception:
                    q_vec_lit = None
                    LAST_SEMANTIC.set("embedder_unavailable")
                if q_vec_lit is not None:
                    clauses = ["f.embedding IS NOT NULL"]
                    params = []
                    _append_fast_filters(
                        clauses, params, owner=owner, date_from=date_from, date_to=date_to, source_prefix=source_prefix
                    )
                    use_exact = os.environ.get("TM_SEMANTIC_EXACT", "").strip() == "1"
                    if use_exact:
                        conn.execute("SET LOCAL enable_indexscan = off")
                        conn.execute("SET LOCAL enable_bitmapscan = off")
                    else:
                        conn.execute("SET LOCAL hnsw.iterative_scan = relaxed_order")
                    vrows = conn.execute(
                        f"""
                        WITH nearest AS (
                            SELECT f.id, f.status,
                                   1.0 - (f.embedding <=> %s::public.vector) AS sim,
                                   f.valid_from
                            FROM facts f
                            LEFT JOIN subjects s ON s.owner = f.owner AND s.id = f.subject_id
                            WHERE {' AND '.join(clauses)}
                            ORDER BY f.embedding <=> %s::public.vector ASC
                            LIMIT 60
                        )
                        SELECT id, status, sim
                        FROM nearest
                        WHERE sim >= %s
                        ORDER BY sim DESC, valid_from DESC, id ASC
                        LIMIT 30
                        """,
                        (q_vec_lit, *params, q_vec_lit, cfg.semantic_min_sim),
                    ).fetchall()
                    if use_exact:
                        conn.execute("RESET enable_indexscan")
                        conn.execute("RESET enable_bitmapscan")
                    vec_fids = [r["id"] for r in vrows]
                    for r in vrows:
                        status_by_id[r["id"]] = r["status"]
                        sem_sims[r["id"]] = float(r["sim"])
                    if vec_fids:
                        sem_weight = float(os.environ.get("TM_SEMANTIC_WEIGHT", "0.35"))
                        channel_ranks.append(("semantic", sem_weight, vec_fids))

        # Single batch visibility verification (forget_rules + evidence generations) over <=290 candidates.
        # Queries base PK directly with (erased_at IS NULL)::int=1 so Postgres never switches to a slow generic plan on visible_facts.
        all_cand_ids = list({fid for _, _, rids in channel_ranks for fid in rids})
        visible_set: set[str] = set()
        if all_cand_ids:
            cand_rows = conn.execute(
                """
                SELECT f.id, f.text
                FROM facts f
                WHERE f.owner = %s AND f.id = ANY(%s)
                  AND (f.erased_at IS NULL)::int = 1 AND f.status <> 'history'
                """,
                (owner, all_cand_ids),
            ).fetchall()
            if cand_rows:
                cand_ids_alive = [r["id"] for r in cand_rows]
                stale_rows = conn.execute(
                    """
                    SELECT DISTINCT fe.fact_id
                    FROM fact_evidence fe
                    JOIN records r ON r.id = fe.record_id AND r.owner = fe.owner
                    WHERE fe.owner = %s AND fe.fact_id = ANY(%s)
                      AND (r.erased_at IS NOT NULL OR r.generation > fe.record_generation)
                    """,
                    (owner, cand_ids_alive),
                ).fetchall()
                blocked_ids = {r["fact_id"] for r in stale_rows}
                fr_rows = conn.execute(
                    "SELECT kind, value FROM forget_rules WHERE owner = %s",
                    (owner,),
                ).fetchall()
                item_rules = {r["value"] for r in fr_rows if r["kind"] == "item"}
                text_rules = [r["value"].lower() for r in fr_rows if r["kind"] == "text" and r["value"]]
                for r in cand_rows:
                    fid = r["id"]
                    if fid in blocked_ids or fid in item_rules:
                        continue
                    if text_rules:
                        t_low = (r["text"] or "").lower()
                        if any(rule in t_low for rule in text_rules):
                            continue
                    visible_set.add(fid)

    if not channel_ranks:
        return []

    k = 60.0
    scores: dict[str, float] = defaultdict(float)
    best_ch_score: dict[str, tuple[float, ChannelName]] = {}
    for ch, weight, ranked_ids in channel_ranks:
        vis_ranked = [fid for fid in ranked_ids if fid in visible_set]
        for pos, fid in enumerate(vis_ranked):
            eff_weight = weight + (0.9 if ch == "semantic" and sem_sims.get(fid, 0.0) >= 0.62 else 0.0)
            contrib = eff_weight / (k + pos + 1.0)
            scores[fid] += contrib
            prev = best_ch_score.get(fid)
            if prev is None or contrib > prev[0]:
                best_ch_score[fid] = (contrib, ch)

    status_mult = {"active": 1.25, "hypothesis": 0.85, "ended": 0.45, "superseded": 0.35}
    final: list[Candidate] = []
    for fid, raw_score in scores.items():
        mult = status_mult.get(status_by_id.get(fid, "active"), 1.0)
        final.append(Candidate(fact_id=fid, score=round(raw_score * mult, 8), channel=best_ch_score[fid][1]))

    final.sort(key=lambda c: (-c.score, c.fact_id))
    return final[:limit]


def compute_entity_salience_sql(
    conn: Any, owner: str, *, entity_ids: list[str] | None = None
) -> dict[str, float]:
    """Compute read-time SQL salience: 0.5*log(1+mentions_30d) + 0.3*recency + 0.2*confirms."""
    if entity_ids is not None and not entity_ids:
        return {}
    ent_filter = "AND e.id = ANY(%s)" if entity_ids is not None else ""
    params: tuple[Any, ...] = (owner, list(entity_ids)) if entity_ids is not None else (owner,)
    rows = conn.execute(
        f"""
        WITH counts AS (
            SELECT e.id AS entity_id,
                   e.provenance,
                   e.user_confirmed_at,
                   e.last_seen,
                   COUNT(f.id) FILTER (
                       WHERE f.valid_from >= to_char(CURRENT_DATE - 30, 'YYYY-MM-DD')
                   )::int AS mentions_30d,
                   MAX(NULLIF(substr(f.valid_from, 1, 10), '')) AS max_valid_day
            FROM entities e
            LEFT JOIN fact_entities fe ON fe.owner = e.owner AND fe.entity_id = e.id
            LEFT JOIN facts f ON f.owner = fe.owner AND f.id = fe.fact_id
              AND f.erased_at IS NULL AND f.status <> 'history'
            WHERE e.owner = %s AND e.erased_at IS NULL AND e.status <> 'merged' {ent_filter}
            GROUP BY e.id, e.provenance, e.user_confirmed_at, e.last_seen
        )
        SELECT entity_id,
               GREATEST(
                   0.05,
                   0.5 * LN(1.0 + mentions_30d)
                   + 0.3 * EXP(
                       -GREATEST(
                           0,
                           (CURRENT_DATE - COALESCE(
                               CASE WHEN COALESCE(max_valid_day, substr(last_seen, 1, 10), '') ~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$'
                                    THEN COALESCE(max_valid_day, substr(last_seen, 1, 10))::date
                                    ELSE CURRENT_DATE - 90
                               END,
                               CURRENT_DATE - 90
                           ))
                       )::double precision / 30.0
                   )
                   + 0.2 * CASE WHEN provenance = 'user_supplied' OR user_confirmed_at IS NOT NULL THEN 1.0 ELSE 0.0 END
               ) AS sal
        FROM counts
        """,
        params,
    ).fetchall()
    return {r["entity_id"]: round(float(r["sal"]), 4) for r in rows}


def compute_subject_salience_sql(conn: Any, owner: str) -> dict[str, float]:
    """Compute read-time SQL salience per subject: 0.5*log(1+mentions_30d) + 0.3*recency + 0.2*confirms."""
    rows = conn.execute(
        """
        WITH counts AS (
            SELECT s.id AS subject_id,
                   s.provenance,
                   s.user_confirmed_at,
                   COUNT(f.id) FILTER (
                       WHERE f.valid_from >= to_char(CURRENT_DATE - 30, 'YYYY-MM-DD')
                   )::int AS mentions_30d,
                   MAX(NULLIF(substr(f.valid_from, 1, 10), '')) AS max_valid_day
            FROM subjects s
            LEFT JOIN facts f ON f.owner = s.owner AND f.subject_id = s.id
              AND f.erased_at IS NULL AND f.status <> 'history'
            WHERE s.owner = %s
            GROUP BY s.id, s.provenance, s.user_confirmed_at
        )
        SELECT subject_id,
               GREATEST(
                   0.05,
                   0.5 * LN(1.0 + mentions_30d)
                   + 0.3 * EXP(
                       -GREATEST(
                           0,
                           (CURRENT_DATE - COALESCE(
                               CASE WHEN COALESCE(max_valid_day, '') ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
                                    THEN max_valid_day::date
                                    ELSE CURRENT_DATE - 90
                               END,
                               CURRENT_DATE - 90
                           ))
                       )::double precision / 30.0
                   )
                   + 0.2 * CASE WHEN provenance = 'user_supplied' OR user_confirmed_at IS NOT NULL THEN 1.0 ELSE 0.0 END
               ) AS sal
        FROM counts
        """,
        (owner,),
    ).fetchall()
    return {r["subject_id"]: round(float(r["sal"]), 4) for r in rows}
