"""Validation, storage, and Forget cleanup for LLM-proposed topic-tree words (E10)."""
from __future__ import annotations

from collections import Counter
from threading import RLock
from typing import Any, Iterable

from temporal_memory.db.db import fold_text
from temporal_memory.live.topics import eligible_subject
from temporal_memory.models import NewTerm
from temporal_memory.privacy.sensitive import pre_write
from temporal_memory.vocab.loader import (
    WEIGHT_FLOOR,
    LearnedTermNode,
    OwnerLearnedIndex,
    VocabTree,
    get_vocab,
)

_STATS_LOCK = RLock()
_RUN_PROPOSAL_STATS: Counter[str] = Counter()

# Derived dynamic weight for one learned_term_sources row joined with records r.
# Never deletes rows (D18): erased records, rejected facts (had_fact with 0 live facts), or aged/low-confidence facts drop to WEIGHT_FLOOR.
_SOURCE_WEIGHT_EXPR = """
CASE
    WHEN r.id IS NULL OR r.erased_at IS NOT NULL THEN 0.05
    WHEN EXISTS (
        SELECT 1 FROM fact_evidence fe
        JOIN facts f ON f.owner = fe.owner AND f.id = fe.fact_id
        WHERE fe.owner = lts.owner AND fe.record_id = lts.record_id AND f.erased_at IS NULL
    ) THEN (
        SELECT MAX(
            GREATEST(
                0.05,
                LEAST(
                    1.0,
                    COALESCE(f.confidence, 1.0)
                    * CASE WHEN f.status = 'active' THEN 1.0 ELSE 0.3 END
                    * CASE
                        WHEN f.provenance IN ('user_supplied', 'provider_confirmed') THEN 1.0
                        WHEN COALESCE(substr(f.valid_from, 1, 10), '') ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
                             AND (CURRENT_DATE - substr(f.valid_from, 1, 10)::date) > 30
                        THEN EXP(-GREATEST(0, (CURRENT_DATE - substr(f.valid_from, 1, 10)::date) - 30)::double precision / 30.0)
                        ELSE 1.0
                    END
                )
            )
        )
        FROM fact_evidence fe
        JOIN facts f ON f.owner = fe.owner AND f.id = fe.fact_id
        WHERE fe.owner = lts.owner AND fe.record_id = lts.record_id AND f.erased_at IS NULL
    )
    WHEN lts.had_fact THEN 0.05
    WHEN r.meta ? 'weight' THEN GREATEST(0.05, LEAST(1.0, (r.meta->>'weight')::double precision))
    ELSE 1.0
END
""".strip()


def reset_proposal_stats() -> None:
    with _STATS_LOCK:
        _RUN_PROPOSAL_STATS.clear()


def get_proposal_stats() -> dict[str, int]:
    with _STATS_LOCK:
        return dict(_RUN_PROPOSAL_STATS)


def _add_stats(counts: dict[str, int]) -> None:
    with _STATS_LOCK:
        for k, v in counts.items():
            if v:
                _RUN_PROPOSAL_STATS[k] += v


def load_owner_learned_index(conn: Any, owner: str) -> OwnerLearnedIndex:
    """Load an owner's learned terms ordered by source-derived weight (floor last)."""
    try:
        rows = conn.execute(
            f"""
            SELECT lt.term, lt.term_folded, lt.parent_path, lt.path, lt.provenance,
                   COALESCE(MAX({_SOURCE_WEIGHT_EXPR}), {WEIGHT_FLOOR}) AS weight
            FROM learned_terms lt
            LEFT JOIN learned_term_sources lts
                   ON lts.owner = lt.owner AND lts.term_folded = lt.term_folded
            LEFT JOIN records r
                   ON r.owner = lts.owner AND r.id = lts.record_id
            WHERE lt.owner = %s
            GROUP BY lt.term, lt.term_folded, lt.parent_path, lt.path, lt.provenance
            ORDER BY weight DESC, lt.path ASC
            """,
            (owner,),
        ).fetchall()
    except Exception:
        return OwnerLearnedIndex()
    return OwnerLearnedIndex(
        [
            LearnedTermNode(
                term=r["term"],
                term_folded=r["term_folded"],
                parent_path=r["parent_path"],
                path=r["path"],
                provenance=r["provenance"] or "inferred",
                weight=round(float(r["weight"] or WEIGHT_FLOOR), 4),
            )
            for r in rows
        ]
    )


def apply_new_terms(
    conn: Any,
    owner: str,
    proposals: Iterable[NewTerm],
    batch_record_ids: set[str],
    *,
    vocab: VocabTree | None = None,
) -> dict[str, int]:
    """Validate and persist LLM-proposed words for one owner inside the applier transaction."""
    stats = {
        "proposals": 0,
        "kept": 0,
        "dropped": 0,
        "no_source": 0,
        "no_branch": 0,
        "ambiguous": 0,
        "rule9": 0,
        "curated_clash": 0,
    }
    proposal_list = list(proposals or ())
    if not proposal_list:
        return stats

    tree = vocab or get_vocab()
    learned_idx = load_owner_learned_index(conn, owner)

    # Fetch live record ids of this owner within this batch once.
    live_batch_rids: set[str] = set()
    if batch_record_ids:
        rows = conn.execute(
            "SELECT id FROM records WHERE owner = %s AND id = ANY(%s) AND erased_at IS NULL",
            (owner, list(batch_record_ids)),
        ).fetchall()
        live_batch_rids = {r["id"] for r in rows}

    for prop in proposal_list:
        stats["proposals"] += 1
        raw_term = (prop.term or "").strip()
        term_folded = fold_text(raw_term)
        ev_ids = list(dict.fromkeys(str(r).strip() for r in (prop.evidence or ()) if str(r).strip()))

        # 1) no_source: requires non-empty evidence owned by this owner in this batch
        if not term_folded or not ev_ids or any(rid not in live_batch_rids for rid in ev_ids):
            stats["dropped"] += 1
            stats["no_source"] += 1
            continue

        # 2) ambiguous / no_branch (check ambiguous before `parent_path is None`!)
        parent_path, status = tree.resolve_is_a(prop.is_a, learned=learned_idx)
        if status == "ambiguous":
            stats["dropped"] += 1
            stats["ambiguous"] += 1
            continue
        if status == "no_branch" or parent_path is None:
            stats["dropped"] += 1
            stats["no_branch"] += 1
            continue

        # 3) rule9: blocked/sensitive ancestor prefix (sensitive / people / family / relationships) or sensitive term text
        parts = parent_path.split("/")
        prefix_blocked = any(
            (node := tree.by_path.get("/".join(parts[:k]))) is not None and (node.blocks_proposals or node.sensitive)
            for k in range(1, len(parts) + 1)
        )
        if (
            prefix_blocked
            or not eligible_subject(f"{parent_path}/{term_folded}", raw_term)
            or pre_write(raw_term) is not None
        ):
            stats["dropped"] += 1
            stats["rule9"] += 1
            continue

        # 4) curated_clash: already curated in the tree or lexicon (unless updating an existing learned sighting)
        existing_learned = learned_idx.by_term.get(term_folded)
        if existing_learned is None:
            if (
                term_folded in tree.curated_token_to_paths
                or term_folded in tree.lexicon_words
                or any(term_folded in n.folded_terms for n in tree.nodes)
            ):
                stats["dropped"] += 1
                stats["curated_clash"] += 1
                continue

        # Keep: second sighting adds source(s) without duplicating the learned term.
        if existing_learned is not None:
            conn.execute(
                "UPDATE learned_terms SET updated_at = now() WHERE owner = %s AND term_folded = %s",
                (owner, term_folded),
            )
            kept_term_folded = existing_learned.term_folded
        else:
            slug = term_folded.replace(" ", "_")
            full_path = f"{parent_path}/{slug}"
            conn.execute(
                """
                INSERT INTO learned_terms (owner, term_folded, term, parent_path, path, provenance)
                VALUES (%s, %s, %s, %s, %s, 'inferred')
                ON CONFLICT (owner, term_folded) DO UPDATE SET updated_at = now()
                """,
                (owner, term_folded, raw_term, parent_path, full_path),
            )
            kept_term_folded = term_folded
            learned_idx = OwnerLearnedIndex(
                [
                    *learned_idx.nodes,
                    LearnedTermNode(
                        term=raw_term,
                        term_folded=term_folded,
                        parent_path=parent_path,
                        path=full_path,
                        provenance="inferred",
                    ),
                ]
            )

        for rid in ev_ids:
            conn.execute(
                """
                INSERT INTO learned_term_sources (owner, term_folded, record_id, had_fact)
                VALUES (
                    %s, %s, %s,
                    EXISTS (SELECT 1 FROM fact_evidence fe WHERE fe.owner = %s AND fe.record_id = %s)
                )
                ON CONFLICT (owner, term_folded, record_id) DO UPDATE
                    SET had_fact = learned_term_sources.had_fact OR EXCLUDED.had_fact
                """,
                (owner, kept_term_folded, rid, owner, rid),
            )
        stats["kept"] += 1

    _add_stats(stats)
    return stats


def list_owner_learned_terms(conn: Any, owner: str) -> list[dict[str, Any]]:
    """Return all learned terms with weight and source record IDs for one owner (D18: floor kept, sorted desc)."""
    rows = conn.execute(
        f"""
        SELECT lt.term, lt.term_folded, lt.parent_path, lt.path, lt.provenance, lt.created_at,
               COALESCE(MAX({_SOURCE_WEIGHT_EXPR}), {WEIGHT_FLOOR}) AS weight,
               COALESCE(
                   array_agg(lts.record_id ORDER BY lts.record_id)
                       FILTER (WHERE lts.record_id IS NOT NULL),
                   ARRAY[]::TEXT[]
               ) AS source_record_ids
        FROM learned_terms lt
        LEFT JOIN learned_term_sources lts
               ON lts.owner = lt.owner AND lts.term_folded = lt.term_folded
        LEFT JOIN records r
               ON r.owner = lts.owner AND r.id = lts.record_id
        WHERE lt.owner = %s
        GROUP BY lt.term, lt.term_folded, lt.parent_path, lt.path, lt.provenance, lt.created_at
        ORDER BY weight DESC, lt.path ASC
        """,
        (owner,),
    ).fetchall()
    return [
        {
            "term": r["term"],
            "term_folded": r["term_folded"],
            "parent_path": r["parent_path"],
            "path": r["path"],
            "provenance": r["provenance"],
            "weight": round(float(r["weight"] or WEIGHT_FLOOR), 4),
            "source_record_ids": list(r["source_record_ids"] or []),
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]
