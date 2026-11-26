"""Similar-query retrieval & clustering over anonymised vocab signals (E13b, D21).

Privacy contract: `vocab_query_signals` stores only a keyed HMAC-SHA256 hash of
the owner id (key: `TM_SIGNAL_HMAC_KEY` env / server secret — never a plain
hash) plus folded terms — never raw owner ids or raw PII sentences. Only
user-typed queries are logged (`record_query_signal` requires
`source="user_typed"`; automatic `/context` calls are never written). Every
term is screened through `privacy/sensitive.py` (layer-1 `pre_write` +
layer-2 `screen`, fail-closed) before it is written or returned as a
candidate, and learned terms sourced from Google Limited Use channels
(gmail/calendar/youtube/takeout/google) are excluded from every aggregate.
Account deletion purges signals via `purge_owner_query_signals`. All counts
exposed here are aggregates (`distinct_owners`); zero owner ids ever leave
this module.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any, Iterable, Sequence

from temporal_memory.core.embed import EMBED_DIM, EMBED_MODEL
from temporal_memory.db.db import fold_text
from temporal_memory.privacy import sensitive
from temporal_memory.vocab.loader import arabic_variants, get_vocab_with_approved

# Google Limited Use: learned terms whose citing records come from these source
# prefixes (or whose provenance names them) never enter shared aggregates.
GOOGLE_SOURCES = ("gmail", "calendar", "youtube", "takeout", "google")
_GOOGLE_LIKE = " OR ".join(
    f"lower(r.source) LIKE '{src}%'" for src in GOOGLE_SOURCES
)
_GOOGLE_PROVENANCE = "|".join(GOOGLE_SOURCES)
LEARNED_GOOGLE_FILTER = (
    "NOT EXISTS ("
    "SELECT 1 FROM learned_term_sources lts "
    "JOIN records r ON r.owner = lts.owner AND r.id = lts.record_id "
    "WHERE lts.owner = lt.owner AND lts.term_folded = lt.term_folded "
    f"AND ({_GOOGLE_LIKE}))"
    f" AND lt.provenance !~* '{_GOOGLE_PROVENANCE}'"
)


def _hmac_key() -> bytes | None:
    """Server secret for owner hashing: `TM_SIGNAL_HMAC_KEY` only.

    Fail closed when unset — never fall back to the admin token or any other
    secret, and never use a plain unkeyed hash.
    """
    key = (os.environ.get("TM_SIGNAL_HMAC_KEY") or "").strip()
    if not key:
        return None
    return key.encode("utf-8")


def hash_owner(owner: str) -> str | None:
    """Keyed one-way owner key (HMAC-SHA256 hex), or None when HMAC is unset."""
    key = _hmac_key()
    if key is None:
        return None
    return hmac.new(key, (owner or "").encode("utf-8"), hashlib.sha256).hexdigest()


def passes_privacy(term: str) -> bool:
    """Two-layer fail-closed gate: layer-1 `pre_write`, then layer-2 `screen`.

    An unavailable classifier raises `ScreenUnavailable`, which blocks the term
    (fail closed) instead of publishing unscreened output.
    """
    if not (term or "").strip():
        return False
    if sensitive.pre_write(term) is not None:
        return False
    try:
        blocked = sensitive.screen([term])
    except sensitive.ScreenUnavailable:
        return False
    return term not in blocked


def _content_tokens(folded: str) -> list[str]:
    return [t for t in folded.split() if len(t) >= 2]


def layer1_pass(term: str) -> bool:
    """Cheap deterministic pre-filter (layer-1 only) for tight DB loops."""
    return bool((term or "").strip()) and sensitive.pre_write(term) is None


def layer2_blocked(terms: Iterable[str]) -> set[str]:
    """Batched layer-2 screen; fail-closed: an unavailable classifier blocks all."""
    unique = list(dict.fromkeys(t for t in terms if (t or "").strip()))
    if not unique:
        return set()
    try:
        blocked = sensitive.screen(unique)
    except sensitive.ScreenUnavailable:
        return set(unique)
    return {t for t in unique if t in blocked}


def record_query_signal(
    conn: Any,
    owner: str,
    query_text: str,
    *,
    source: str,
    hit_count: int = 1,
    resolved_branch: str | None = None,
    embedding: Sequence[float] | None = None,
    embedding_model: str | None = None,
) -> list[str]:
    """Record anonymised per-token signals for an explicitly user-typed query.

    `source` is mandatory (E13b Phase A): only `source="user_typed"` is
    logged — automatic `/context` calls must pass `source="context"` and are
    never written. Each folded token (`len >= 2`) is screened with
    `passes_privacy` before writing; blocked tokens are skipped, never
    stored. Upserts `(owner_hash, term_folded, query_folded)` bumping
    `hit_count`. Returns the folded terms actually stored.
    """
    if source != "user_typed":
        return []
    owner_hash = hash_owner(owner)
    if owner_hash is None:
        return []  # TM_SIGNAL_HMAC_KEY unset → fail closed, do not record
    folded_query = fold_text(query_text or "")
    tokens = list(dict.fromkeys(_content_tokens(folded_query)))
    if not tokens or not (owner or "").strip():
        return []
    vec_lit: str | None = None
    if embedding is not None and len(embedding) == EMBED_DIM:
        from temporal_memory.core.embed import vector_literal

        vec_lit = vector_literal(embedding)
    stored: list[str] = []
    for tok in tokens:
        if not passes_privacy(tok):
            continue
        if vec_lit is not None:
            conn.execute(
                """
                INSERT INTO vocab_query_signals
                    (owner_hash, term_folded, query_folded, embedding, embedding_model, hit_count, resolved_branch)
                VALUES (%s, %s, %s, %s::public.vector, %s, 1, %s)
                ON CONFLICT (owner_hash, term_folded, query_folded) DO UPDATE SET
                    hit_count = vocab_query_signals.hit_count + 1,
                    resolved_branch = COALESCE(EXCLUDED.resolved_branch, vocab_query_signals.resolved_branch),
                    embedding = COALESCE(EXCLUDED.embedding, vocab_query_signals.embedding),
                    updated_at = now()
                """,
                (owner_hash, tok, folded_query, vec_lit, embedding_model or EMBED_MODEL, resolved_branch),
            )
        else:
            conn.execute(
                """
                INSERT INTO vocab_query_signals (owner_hash, term_folded, query_folded, hit_count, resolved_branch)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (owner_hash, term_folded, query_folded) DO UPDATE SET
                    hit_count = vocab_query_signals.hit_count + 1,
                    resolved_branch = COALESCE(EXCLUDED.resolved_branch, vocab_query_signals.resolved_branch),
                    updated_at = now()
                """,
                (owner_hash, tok, folded_query, 1, resolved_branch),
            )
        stored.append(tok)
    _ = hit_count  # accepted for caller context; persistence is per-signal hit_count
    return stored


def purge_owner_query_signals(conn: Any, owner: str) -> int:
    """Account deletion: drop every query-signal row for `owner` (HMAC-keyed).

    `vocab_query_signals` has no FK (the key is one-way), so account deletion
    must call this explicitly. Returns the number of rows deleted.
    """
    if not (owner or "").strip():
        return 0
    owner_hash = hash_owner(owner)
    if owner_hash is None:
        return 0  # cannot address rows without the HMAC key
    cur = conn.execute(
        "DELETE FROM vocab_query_signals WHERE owner_hash = %s", (owner_hash,)
    )
    return int(cur.rowcount or 0)


def _lexical_score(query_vars: set[str], signal_terms: Iterable[str]) -> float:
    qtokens = {t for t in query_vars if len(t) >= 2}
    if not qtokens:
        return 0.0
    hits = sum(1 for t in signal_terms if t in qtokens)
    return hits / len(qtokens)


def find_similar_queries_and_terms(
    conn: Any,
    query_text: str,
    *,
    top_k: int = 15,
    min_sim: float = 0.68,
    query_embedding: Sequence[float] | None = None,
) -> list[dict[str, Any]]:
    """Rank anonymised similar queries/terms for `query_text`.

    Combines pgvector cosine similarity over stored `bge-m3` signal embeddings
    with folded/Arabic-normalized lexical overlap (`fold_text`,
    `arabic_variants`), plus per-owner `learned_terms` recurrence folded into
    the same aggregate owner counts (Google Limited Use sources excluded,
    deleted owners excluded). The curated `vocab/tree.json` side is lexical
    (the tree ships no vectors): each candidate resolves its nearest curated
    `parent_path` via alias matching, including the approved-proposal overlay.

    Returns at most `top_k` dicts with aggregate `distinct_owners` only —
    zero owner ids: `term`, `term_folded`, `distinct_owners`, `parent_path`,
    `similarity`.
    """
    folded_query = fold_text(query_text or "")
    qtokens = _content_tokens(folded_query)
    if not qtokens:
        return []
    query_vars: set[str] = set()
    for tok in qtokens:
        query_vars.update(arabic_variants(tok))

    # Per-term aggregates: owners (hashed), best semantic sim, lexical hits, parents.
    owners: dict[str, set[str]] = {}
    sem_best: dict[str, float] = {}
    parents: dict[str, dict[str, int]] = {}

    def _note(term: str, owner_hash: str, parent: str | None = None) -> None:
        owners.setdefault(term, set()).add(owner_hash)
        if parent:
            votes = parents.setdefault(term, {})
            votes[parent] = votes.get(parent, 0) + 1

    tree = get_vocab_with_approved(conn)
    curated_parents: dict[str, str] = {}
    for var in query_vars:
        for path in tree.curated_token_to_paths.get(var, ()):
            curated_parents.setdefault(var, path)

    # 1) Lexical pass over anonymised signals.
    try:
        sig_rows = conn.execute(
            "SELECT term_folded, query_folded, owner_hash FROM vocab_query_signals"
        ).fetchall()
    except Exception:
        sig_rows = []
    for row in sig_rows:
        term = row["term_folded"] or ""
        if not term or not passes_privacy(term):
            continue
        sig_terms = set(_content_tokens(f"{term} {row['query_folded'] or ''}"))
        lex = _lexical_score(query_vars, sig_terms | {term})
        if lex <= 0.0:
            continue
        parent = curated_parents.get(term)
        if parent is None:
            for var in arabic_variants(term):
                hit = tree.curated_token_to_paths.get(var)
                if hit:
                    parent = hit[0]
                    break
        _note(term, row["owner_hash"], parent)
        if lex >= min_sim:
            sem_best[term] = max(sem_best.get(term, 0.0), lex)

    # 2) Semantic pass over stored bge-m3 embeddings.
    vec = list(query_embedding) if query_embedding is not None else None
    if vec is None:
        try:
            from temporal_memory.core.embed import embed_query

            vec = embed_query(folded_query)
        except Exception:
            vec = None
    if vec is not None and len(vec) == EMBED_DIM:
        from temporal_memory.core.embed import vector_literal

        try:
            sem_rows = conn.execute(
                """
                SELECT term_folded, owner_hash,
                       1.0 - (embedding <=> %s::public.vector) AS sim
                FROM vocab_query_signals
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s::public.vector ASC
                LIMIT 200
                """,
                (vector_literal(vec), vector_literal(vec)),
            ).fetchall()
        except Exception:
            sem_rows = []
        for row in sem_rows:
            term = row["term_folded"] or ""
            try:
                sim = float(row["sim"])
            except (TypeError, ValueError):
                continue
            if sim < min_sim or not passes_privacy(term):
                continue
            parent = curated_parents.get(term)
            _note(term, row["owner_hash"], parent)
            sem_best[term] = max(sem_best.get(term, 0.0), sim)

    # 3) Recurring per-owner learned_terms folded into the same aggregates
    #    (alive owners only; Google Limited Use sources excluded).
    try:
        learned_rows = conn.execute(
            "SELECT lt.term_folded, lt.owner FROM learned_terms lt "
            "JOIN owners o ON o.id = lt.owner "
            f"WHERE {LEARNED_GOOGLE_FILTER}"
        ).fetchall()
    except Exception:
        learned_rows = []
    for row in learned_rows:
        term = row["term_folded"] or ""
        if not term or not passes_privacy(term):
            continue
        sig_terms = set(_content_tokens(term))
        if _lexical_score(query_vars, sig_terms | {term}) <= 0.0:
            continue
        owner_hash = hash_owner(row["owner"] or "")
        if owner_hash is None:
            continue
        _note(term, owner_hash)

    # Combine + resolve nearest curated parent per surviving term.
    ranked: list[dict[str, Any]] = []
    for term, owner_set in owners.items():
        sim = sem_best.get(term, 0.0)
        if sim < min_sim:
            continue
        parent_path: str | None = None
        votes = parents.get(term) or {}
        if votes:
            parent_path = max(sorted(votes), key=lambda p: votes[p])
        if parent_path is None:
            resolved, status = tree.resolve_is_a(term)
            if status == "ok":
                parent_path = resolved
        ranked.append(
            {
                "term": term,
                "term_folded": term,
                "distinct_owners": len(owner_set),
                "parent_path": parent_path,
                "similarity": round(float(sim), 4),
            }
        )
    ranked.sort(key=lambda r: (-r["similarity"], -r["distinct_owners"], r["term"]))
    return ranked[: max(0, top_k)]
