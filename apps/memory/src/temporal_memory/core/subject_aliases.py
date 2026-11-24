"""Subject aliases so a query token can find a fact that never says that word.

Seeds follow the Dubai-life leaves in ``docs/references/residence-ontology-tree.md``
(tech/devices/phone, lifestyle/food, civic). The backfill writes the set onto
the subject; search matches query tokens against labels and these aliases.
"""
from __future__ import annotations

from typing import Any

from temporal_memory.db.db import fold_text
from temporal_memory.models import Candidate

# leaf or alias token -> the set stored with that subject
SUBJECT_ALIAS_SEEDS: dict[str, tuple[str, ...]] = {
    "phone": ("phone", "mobile", "iphone", "samsung", "موبايل", "تليفون"),
    "laptop": ("laptop", "macbook", "notebook", "لابتوب"),
    "tablet": ("tablet", "ipad"),
    "restaurant": ("restaurant", "restaurants", "dining", "مطعم"),
    "cafe": ("cafe", "cafes", "coffee", "مقهى"),
    "gym": ("gym", "fitness", "نادي"),
    "salik": ("salik", "toll", "سالك"),
    "dewa": ("dewa", "electricity", "ديوا"),
    "metro": ("metro", "nol", "rta", "هيئة"),
}


def aliases_for_text(subject_path: str, text: str) -> list[str]:
    """Alias set to store when this fact's path or text hits a seeded subject."""
    blob = fold_text(f"{subject_path} {text}")
    tokens = set(blob.split())
    leaf = fold_text((subject_path or "").strip("/").split("/")[-1]) if subject_path else ""
    found: list[str] = []
    for key, aliases in SUBJECT_ALIAS_SEEDS.items():
        key_folded = fold_text(key)
        alias_folded = {fold_text(alias) for alias in aliases if fold_text(alias)}
        if leaf == key_folded or key_folded in tokens or tokens & alias_folded:
            found.extend(aliases)
    return list(dict.fromkeys(found))


def write_subject_aliases(conn: Any, owner: str, subject_id: str, aliases: list[str]) -> None:
    for alias in aliases:
        folded = fold_text(alias)
        if not folded:
            continue
        conn.execute(
            """
            INSERT INTO subject_aliases (owner, subject_id, alias, alias_folded)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (owner, subject_id, alias_folded) DO NOTHING
            """,
            (owner, subject_id, alias.strip(), folded),
        )


def subject_channel_candidates(
    db: Any,
    owner: str,
    query: str,
    *,
    source_prefix: str | None = None,
    limit: int = 50,
) -> list[Candidate]:
    """Match query tokens to subject labels, path segments, aliases, and fact text.

    A fact whose text is only "iPhone 13 Pro Max" is returned on the subject
    channel for the query "phone" when that subject carries the phone alias set.
    That match is token equality, so "phone" is not a substring of the fact text.
    Text-token hits use the fts channel. A source prefix must match every
    surviving evidence record before the limit is applied.
    """
    tokens = [tok for tok in fold_text(query).split() if tok]
    if not tokens or limit <= 0:
        return []
    with db.connection() as conn:
        rows = conn.execute(
            """
            SELECT vf.id, vf.text, vf.text_orig, vf.valid_from,
                   lower(s.label) AS label,
                   lower(s.path) AS path,
                   COALESCE(array_agg(DISTINCT a.alias_folded) FILTER (WHERE a.alias_folded IS NOT NULL), '{}') AS aliases
            FROM visible_facts vf
            JOIN subjects s ON s.owner = vf.owner AND s.id = vf.subject_id
            LEFT JOIN subject_aliases a ON a.owner = vf.owner AND a.subject_id = vf.subject_id
            WHERE vf.owner = %s AND vf.status = 'active'
            GROUP BY vf.id, vf.text, vf.text_orig, vf.valid_from, s.label, s.path
            """,
            (owner,),
        ).fetchall()
        source_rows = conn.execute(
            """
            SELECT fe.fact_id, r.source
            FROM fact_evidence fe
            JOIN records r ON r.owner = fe.owner AND r.id = fe.record_id
            WHERE fe.owner = %s AND r.erased_at IS NULL
            """,
            (owner,),
        ).fetchall()
    sources: dict[str, list[str]] = {}
    for source_row in source_rows:
        sources.setdefault(str(source_row["fact_id"]), []).append(str(source_row["source"]))
    token_set = set(tokens)
    ranked: list[tuple[str, str, Candidate]] = []
    for row in rows:
        fact_sources = sources.get(str(row["id"]), [])
        if source_prefix is not None:
            if not fact_sources or not all(src.startswith(source_prefix) for src in fact_sources):
                continue
        segments = {seg for seg in (row["path"] or "").split("/") if seg}
        label = fold_text(row["label"] or "")
        raw_aliases = row["aliases"] or []
        if isinstance(raw_aliases, str):
            raw_aliases = [part for part in raw_aliases.strip("{}").split(",") if part]
        alias_set = {fold_text(item) for item in raw_aliases if item}
        subject_hit = bool(label in token_set or segments & token_set or alias_set & token_set)
        text_tokens = set(fold_text(f"{row['text']} {row['text_orig'] or ''}").split())
        if subject_hit:
            channel: Any = "subject"
            score = 2.0
        elif token_set & text_tokens:
            channel = "fts"
            score = 1.0
        else:
            continue
        ranked.append((
            str(row["valid_from"] or ""),
            str(row["id"]),
            Candidate(str(row["id"]), score, channel),
        ))
    ranked.sort(key=lambda item: item[1])
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item[2] for item in ranked[:limit]]
