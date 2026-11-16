"""Semantic chunking: fill a chunk with chat up to MAX tokens, then cut where the conversation most likely changed.

Principles (from the founder):
  * the best input is the whole thread; if it fits, it is ONE chunk;
  * otherwise chunks are 5k-10k tokens (about 200-400 messages) so the model sees whole conversations;
  * a cut happens only when a chunk reaches its size limit, and it is placed by MEANING, not by the clock.
    Days and pauses are NOT boundaries: people chat across midnight, and they leave a conversation and come back to
    it hours later. So a new day counts for nothing, and a long pause only strengthens a cut that is already a topic
    change; a pause followed by the same words does not cut.

    score(cut before message i) = shift(i) * (0.6 + 0.4 * pause(i))  +  0.1 * fullness
        shift   = 1 - cosine(IDF-weighted words of the 10 messages before, the 10 after)   (TextTiling)
        pause   = min(1, minutes of silence / 240)
        fullness= tokens in the chunk / max_tokens   (a small push toward bigger chunks)

The topic signal is lexical on purpose: the local embedding model (nomic) is English-centred, so its similarities on
Egyptian Arabic chat are unreliable. Words are Arabic-folded and weighted by IDF over the whole thread, so filler
("ايه", "ده") carries no weight. An embedding scorer can be passed in (`scorer=`) and compared on the same thread.

Token cost uses a MEASURED ratio for the lean line format below (qwen3.5 on this chat, from LM Studio usage):
1.9 characters per token, about 25 tokens per message. The old line format with global ids and dates costs 42.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from math import log, sqrt

from .circle import fold
from .parse import Message

CHARS_PER_TOKEN = 1.9  # measured: lean format, Arabic dialect chat, qwen3.5-9b tokenizer
LINE_OVERHEAD_CHARS = 11  # "123 10:49 U: "
DAY_LINE_TOKENS = 8  # "--- 2026-11-13 ---" (a display separator only; it is not a boundary)
PAUSE_SATURATES_MIN = 240
FULLNESS = 0.1
TAIL_FRACTION = 0.3  # never leave a last chunk smaller than this fraction of min_tokens


def message_tokens(m: Message) -> int:
    text = "[image omitted]" if m.kind == "media" else m.text
    return int((len(text) + LINE_OVERHEAD_CHARS) / CHARS_PER_TOKEN) + 1


# ----------------------------------------------------------------------------- boundary scores
def _words(m: Message) -> list[str]:
    if m.kind == "media":
        return []
    return [w for w in (fold(x) for x in re.findall(r"\w+", m.text)) if len(w) > 1]


def boundary_scores(messages: list[Message], window: int = 10) -> list[float]:
    """scores[i] = how good a cut BEFORE messages[i] is (index 0 is never a cut)."""
    n = len(messages)
    bags = [Counter(_words(m)) for m in messages]
    df = Counter(w for b in bags for w in b)
    idf = {w: log((n + 1) / (c + 0.5)) for w, c in df.items()}
    before: Counter = Counter()
    after: Counter = Counter()
    for j in range(0, min(n, window)):
        after.update(bags[j])
    scores = [0.0] * n
    for i in range(1, n):
        before.update(bags[i - 1])
        if i - 1 - window >= 0:
            before.subtract(bags[i - 1 - window])
        after.subtract(bags[i - 1])
        if i - 1 + window < n:
            after.update(bags[i - 1 + window])
        dot = na = nb = 0.0
        for w, c in before.items():
            if c > 0:
                x = c * idf[w]
                na += x * x
                y = after.get(w, 0)
                if y > 0:
                    dot += x * y * idf[w]
        for w, c in after.items():
            if c > 0:
                nb += (c * idf[w]) ** 2
        shift = 1.0 - dot / (sqrt(na) * sqrt(nb)) if na > 0 and nb > 0 else 0.5
        gap_min = (datetime.fromisoformat(messages[i].ts) - datetime.fromisoformat(messages[i - 1].ts)).total_seconds() / 60
        pause = min(1.0, max(gap_min, 0.0) / PAUSE_SATURATES_MIN)
        scores[i] = shift * (0.6 + 0.4 * pause)
    return scores


# ----------------------------------------------------------------------------- splitting
@dataclass
class Chunk:
    index: int
    messages: list[Message]
    context: list[Message] = field(default_factory=list)  # tail of the previous chunk, shown for continuity only
    tokens: int = 0
    reason: str = "full"  # full | end | cut
    cut_score: float = 0.0

    @property
    def first_idx(self) -> int:
        return self.messages[0].idx

    @property
    def last_idx(self) -> int:
        return self.messages[-1].idx


def split(messages: list[Message], *, min_tokens: int = 5000, max_tokens: int = 10000, overlap: int = 8,
          window: int = 10, scorer=boundary_scores) -> list[Chunk]:
    """Chunks of min_tokens..max_tokens (the last may be shorter). A cut happens only at max size, placed by meaning."""
    n = len(messages)
    if not n:
        return []
    cost = [message_tokens(m) + (DAY_LINE_TOKENS if i == 0 or m.ts[:10] != messages[i - 1].ts[:10] else 0)
            for i, m in enumerate(messages)]
    if sum(cost) <= max_tokens:
        return [Chunk(0, list(messages), [], sum(cost), "full")]
    scores = scorer(messages, window) if scorer is boundary_scores else scorer(messages)
    tail_min = int(min_tokens * TAIL_FRACTION)
    chunks: list[Chunk] = []
    start = 0
    while start < n:
        remaining = sum(cost[start:])
        context = messages[max(0, start - overlap):start] if chunks else []
        if remaining <= max_tokens:
            chunks.append(Chunk(len(chunks), messages[start:], context, remaining, "end"))
            break
        acc, candidates = 0, []
        for i in range(start, n):
            acc += cost[i]
            if acc > max_tokens:
                break
            if acc >= min_tokens and i + 1 < n:
                candidates.append((i + 1, acc))  # a cut before messages[i + 1]
        fit = [(c, t) for c, t in candidates if sum(cost[c:]) >= tail_min]
        pool = fit or candidates or [(min(start + 1, n - 1), cost[start])]
        cut, tokens = max(pool, key=lambda ct: (scores[ct[0]] + FULLNESS * ct[1] / max_tokens, ct[0]))
        chunks.append(Chunk(len(chunks), messages[start:cut], context, tokens, "cut", scores[cut]))
        start = cut
    return chunks


# ----------------------------------------------------------------------------- what the model sees
def tags_for(messages: list[Message], owner: str) -> dict[str, str]:
    """U = the user, then P, A, B, ... for the other senders in order of appearance."""
    tags, spare = {}, iter("PABCDEFGHJKLMNQRSTVWXYZ")
    for m in messages:
        if m.sender not in tags:
            tags[m.sender] = "U" if fold(m.sender) == fold(owner) else next(spare)
    return tags


def render(chunk: Chunk, tags: dict[str, str]) -> tuple[str, dict[int, int]]:
    """-> (text for the model, {local id: global message idx}). Local ids run 1..N so a memory can cite a range cheaply."""
    lines: list[str] = []
    if chunk.context:
        lines.append("CONTEXT (already processed - do not write memories for these lines):")
        for m in chunk.context:
            lines.append(f". {m.ts[5:10]} {m.ts[11:16]} {tags.get(m.sender, '?')}: {'[image omitted]' if m.kind == 'media' else m.text}")
        lines.append("CHAT:")
    id_map: dict[int, int] = {}
    day = None
    for local, m in enumerate(chunk.messages, 1):
        if m.ts[:10] != day:
            day = m.ts[:10]
            lines.append(f"--- {day} ---")
        id_map[local] = m.idx
        body = "[image omitted]" if m.kind == "media" else re.sub(r"\s*\n\s*", " / ", m.text)
        lines.append(f"{local} {m.ts[11:16]} {tags.get(m.sender, '?')}: {body}")
    return "\n".join(lines), id_map
