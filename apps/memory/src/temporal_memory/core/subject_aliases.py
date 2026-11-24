"""Subject aliases so a query token can find a fact that never says that word.

Seeds follow the Dubai-life leaves in ``docs/references/residence-ontology-tree.md``
(tech/devices/phone, lifestyle/food, civic). The backfill writes the set onto
the subject. Retrieval matches folded query tokens in SQL.
"""
from __future__ import annotations

from typing import Any

from temporal_memory.db.db import fold_text

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
