"""Subject aliases derived from the unified topic-tree vocabulary (E10)."""
from __future__ import annotations

from typing import Any

from temporal_memory.db.db import fold_text
from temporal_memory.vocab.loader import get_vocab


def aliases_for_text(subject_path: str, text: str) -> list[str]:
    """Alias set to store when this fact's path or text hits a vocabulary node."""
    return get_vocab().aliases_for_text(subject_path, text)


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
