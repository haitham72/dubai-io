"""Retrieval building blocks over memory rows: dense (embedded memory), lexical (BM25), rank fusion, and
query translation. `index.search` is the production path; `evaluate.py` runs the same pieces as variants so
every default here was MEASURED, not assumed (see the iteration log).

Why each piece exists:
  dense      the memory text is embedded on store; finds paraphrases and synonyms.
  lexical    BM25 over memory + topics + names; finds exact names and rare words a small embedding blurs.
  fusion     reciprocal rank fusion of the two lists - no score calibration needed.
  translate  memories are written in English, the chat (and the user's questions) are often Arabic. The
             embedding model is English-centred, so a non-English query is rewritten to English first.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from math import log

from . import llm

STOP = frozenset("""a an the and or of to in on at for with by from is are was were be been it its this that these those
as but not no yes he she they his her their him them i you we me my your our about into over after before""".split())

_translations: dict[str, str] = {}


def tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"\w+", (text or "").lower()) if t not in STOP and len(t) > 1]


def is_foreign(text: str) -> bool:
    """True when most letters are not Latin (Arabic etc.): such a query needs translating into the memory language."""
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and sum(1 for c in letters if ord(c) > 0x024F) / len(letters) > 0.3


def doc_text(row: dict, mode: str = "full") -> str:
    """What represents a row. modes: memory | memory_topics | full."""
    topics = ", ".join(row.get("topics") or [])
    if mode == "memory":
        return row["memory"]
    if mode == "memory_topics":
        return f"{row['memory']} Topics: {topics}"
    names = ", ".join(row.get("names") or [])
    return f"{row['memory']} {row.get('user_text') or ''} Topics: {topics}. People: {names}."


def bm25_rank(docs: dict[str, str], query: str, k1: float = 1.5, b: float = 0.75) -> list[str]:
    """Row ids with a positive BM25 score, best first. Pure Python: fine for thousands of rows."""
    toks = {i: Counter(tokens(t)) for i, t in docs.items()}
    n = len(toks)
    if not n:
        return []
    avg = sum(sum(c.values()) for c in toks.values()) / n or 1.0
    df = Counter(w for c in toks.values() for w in c)
    scores: dict[str, float] = {}
    for q in set(tokens(query)):
        if q not in df:
            continue
        idf = log(1 + (n - df[q] + 0.5) / (df[q] + 0.5))
        for i, c in toks.items():
            if q in c:
                dl = sum(c.values())
                scores[i] = scores.get(i, 0.0) + idf * c[q] * (k1 + 1) / (c[q] + k1 * (1 - b + b * dl / avg))
    return [i for i, _ in sorted(scores.items(), key=lambda kv: -kv[1])]


def dense_rank(query_vec: list[float], vectors: dict[str, list[float]], ids: set[str] | None = None) -> list[str]:
    scored = [(llm.cosine(query_vec, v), i) for i, v in vectors.items() if ids is None or i in ids]
    return [i for _, i in sorted(scored, reverse=True)]


def rrf(rankings: list[list[str]], k: int = 60) -> list[str]:
    """Reciprocal rank fusion: robust way to merge a dense and a lexical list."""
    score: dict[str, float] = {}
    for ranking in rankings:
        for pos, i in enumerate(ranking):
            score[i] = score.get(i, 0.0) + 1.0 / (k + pos + 1)
    return [i for i, _ in sorted(score.items(), key=lambda kv: -kv[1])]


TRANSLATE_SYSTEM = """Translate the user's search query into plain English. Keep names as they are. Output JSON only."""
TRANSLATE_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["english"],
                    "properties": {"english": {"type": "string"}}}


def translate(query: str) -> str:
    """Non-English query -> English (cached). On any model failure the original query is used, never an error."""
    if not is_foreign(query):
        return query
    if query not in _translations:
        try:
            _translations[query] = (llm.chat_json(TRANSLATE_SYSTEM, query, TRANSLATE_SCHEMA, name="translate",
                                                  max_tokens=200).get("english") or query).strip()
        except llm.LabLLMError:
            return query
    return _translations[query]


def usable(rows: list[dict], since: str | None = None, until: str | None = None) -> list[dict]:
    """Rows that may be searched: they have a memory, are not withheld, and fall in the date range."""
    out = []
    for r in rows:
        if not r["memory"] or r["sensitive"]:
            continue
        day = r["t_avg"][:10]
        if (since and day < since) or (until and day > until):
            continue
        out.append(r)
    return out


def search_rows(rows: list[dict], vectors: dict[str, list[float]], query: str, *, k: int = 8, hybrid: bool = True,
                do_translate: bool = True, doc_mode: str = "full") -> tuple[list[tuple[str, float]], str]:
    """-> ([(row id, rank score)], mode used). Falls back to lexical-only when the embedding model is unavailable."""
    q_en = translate(query) if do_translate else query
    ids = {r["id"] for r in rows}
    by_id = {r["id"]: r for r in rows}
    lex = bm25_rank({i: doc_text(by_id[i], doc_mode) for i in ids}, q_en) if hybrid else []
    dense: list[str] = []
    mode = "hybrid" if hybrid else "dense"
    try:
        dense = dense_rank(llm.embed([q_en], kind="query")[0], vectors, ids)
    except llm.LabLLMError:
        mode = "lexical"
        lex = bm25_rank({i: doc_text(by_id[i], doc_mode) for i in ids}, q_en)
    fused = rrf([x for x in (dense[: max(k * 3, 20)], lex[: max(k * 3, 20)]) if x]) if (dense and lex) else (dense or lex)
    return [(i, 1.0 / (rank + 1)) for rank, i in enumerate(fused[:k])], mode


def day(ts: str) -> str:
    return datetime.fromisoformat(ts).strftime("%Y-%m-%d")
