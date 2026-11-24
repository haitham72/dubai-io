"""Promotion policy (WP-C). Implements plan §4 + Rule 9 (planaudit.md §0, v2.1).

- First-person logistics the user stated ("Mom visits 1 Dec") are stored as
  `user_supplied` — ordinary facts, promotable on evidence.
- Third-party private matters (health, faith, relationships, money, legal) are
  never stored or shown without an explicit user opt-in, and a third-party
  person is NEVER auto-promoted: `may_promote` requires `user_confirmed`.
- Credentials never reach here: the validator's canonical gate (sensitive.py
  layer 1) blocks them for every worker kind before policy runs.
"""
from __future__ import annotations

from ..models import Entity, OutFact, SensitiveCat, WorkerKind
from .sensitive import pre_write, screen

# Worker kinds whose output is screened by the layer-2 model, always.
_SCREENED_WORKERS: frozenset[str] = frozenset({"owner-hook", "agent-cli"})


def _candidate_names(fact: OutFact) -> tuple[str, ...]:
    """Names the extractor proposed (`new:<Name>` refs) for actor matching."""
    out = []
    for e in fact.entities or []:
        ref = (e.entity_id or "").strip()
        if ref.startswith("new:") and len(ref) > 4:
            out.append(ref[4:].strip())
    return tuple(n for n in out if n)


def gate_fact(fact: OutFact, worker_kind: WorkerKind) -> SensitiveCat | None:
    """None passes; otherwise the quarantine category (never the text).

    Layer 1 (`pre_write`) always runs, over the English text and the original-
    language span. Layer 2 (`screen`) additionally runs for `owner-hook` and
    `agent-cli` workers. Reflect outputs: WP-B's reflect calls `screen()`
    directly on its hypothesis texts (contract request CR-2 proposes threading
    them through here via an explicit flag instead).
    """
    texts = [t for t in (fact.text, fact.text_orig) if t]
    for text in texts:
        hit = pre_write(text, known_people=_candidate_names(fact))
        if hit:
            return hit
    if worker_kind in _SCREENED_WORKERS and texts:
        blocked = screen(texts)
        if blocked:
            return next(iter(blocked.values()))
    return None


def provenance_for_statement(*, author_is_owner: bool) -> str:
    """`user_supplied` only when the cited records are the owner's own messages.

    An explicit confirm is a separate action: it also sets `user_confirmed_at`.
    Auto-promotion never changes provenance.
    """
    return "user_supplied" if author_is_owner else "inferred"


def may_promote(entity: Entity, distinct_days: int, user_confirmed: bool) -> bool:
    """Promotion gate candidate -> active (plan §4, Rule 9).

    - The user themselves (`relation_to_user == "self"`) and anything that is
      not a third-party person (places, orgs, projects, events): promotable
      after >= 2 distinct days of evidence, or on an explicit user confirm.
    - A third-party person (any person whose relation is not "self", including
      unknown/`None` — fail closed): promotable ONLY on an explicit user tap.
      Accumulated mentions never promote them (no inference-by-accumulation).
    """
    if user_confirmed:
        return True
    if entity.kind == "person" and entity.relation_to_user != "self":
        return False
    return distinct_days >= 2
