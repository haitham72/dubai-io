"""Unified topic-tree vocabulary loader and general-to-specific query expander (E10)."""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
import json
from pathlib import Path
import re
from threading import RLock
from typing import Any, Iterable

from temporal_memory.db.db import fold_text
from temporal_memory.models import CLUSTERS

DEFAULT_TREE_PATH = Path(__file__).with_name("tree.json")
WEIGHT_FLOOR: float = 0.05
_SAFE_TS_TOKEN = re.compile(r"^[0-9a-z\u0621-\u064a\u0660-\u0669]+$")
_BLOCKED_SEGMENTS = frozenset({"health", "faith", "kids_family", "people", "family", "relationships", "people-family", "social", "identity"})


class VocabValidationError(ValueError):
    """Raised when a topic vocabulary file has invalid parents, cycles, clusters, or paths."""


@dataclass(frozen=True)
class VocabNode:
    path: str
    parent: str | None
    label: str
    cluster: str
    fixed: bool
    sensitive: bool
    blocks_proposals: bool
    aliases: tuple[str, ...]
    folded_terms: tuple[str, ...]


@dataclass(frozen=True)
class LearnedTermNode:
    term: str
    term_folded: str
    parent_path: str
    path: str
    provenance: str = "inferred"
    weight: float = 1.0


class OwnerLearnedIndex:
    """In-memory index of one owner's learned terms layered on top of curated nodes."""

    def __init__(self, rows: Iterable[LearnedTermNode] = ()) -> None:
        self.nodes: list[LearnedTermNode] = list(rows)
        self.by_path: dict[str, LearnedTermNode] = {n.path: n for n in self.nodes}
        self.by_term: dict[str, LearnedTermNode] = {n.term_folded: n for n in self.nodes}
        self.children_by_parent: dict[str, list[LearnedTermNode]] = defaultdict(list)
        for n in self.nodes:
            self.children_by_parent[n.parent_path].append(n)
        for children in self.children_by_parent.values():
            children.sort(key=lambda n: (-float(n.weight), n.term_folded))


def arabic_variants(tok: str) -> list[str]:
    """Return surface token plus basic Arabic proclitic/clitic stem variants."""
    out = [tok]
    if any("\u0621" <= ch <= "\u064a" for ch in tok):
        if tok.startswith("ال") and len(tok) >= 4:
            out.append(tok[2:])
        if len(tok) >= 4 and tok[0] in ("و", "ب", "ل", "ك", "ف") and tok[1:].startswith("ال"):
            out.append(tok[3:])
        if len(tok) >= 5 and tok[0] in ("ب", "ي", "ت") and tok.endswith(("ني", "نا", "كم", "هم", "ها")):
            out.append(tok[1:-2])
    return out


class VocabTree:
    """Validated topic hierarchy + bidirectional lexicon for tree expansion & proposal resolution."""

    def __init__(
        self,
        nodes: list[VocabNode],
        lexicon: dict[str, tuple[str, ...]],
    ) -> None:
        self.nodes = tuple(nodes)
        self.by_path: dict[str, VocabNode] = {n.path: n for n in nodes}
        self.children_by_parent: dict[str, tuple[str, ...]] = {}
        tmp_children: dict[str, list[str]] = defaultdict(list)
        self.curated_token_to_paths: dict[str, list[str]] = defaultdict(list)
        self.all_curated_words: set[str] = set()

        for n in nodes:
            if n.parent is not None:
                tmp_children[n.parent].append(n.path)
            for term in n.folded_terms:
                self.all_curated_words.add(term)
                if n.path not in self.curated_token_to_paths[term]:
                    self.curated_token_to_paths[term].append(n.path)
                for part in term.split():
                    if len(part) >= 3:
                        self.all_curated_words.add(part)
                        if n.path not in self.curated_token_to_paths[part]:
                            self.curated_token_to_paths[part].append(n.path)

        for p, ch in tmp_children.items():
            self.children_by_parent[p] = tuple(ch)

        self.lexicon_groups = lexicon
        self.lexicon_map: dict[str, tuple[str, ...]] = {}
        self.lexicon_words: set[str] = set()
        for _gname, words in lexicon.items():
            folded = tuple(dict.fromkeys(fold_text(w) for w in words if fold_text(w)))
            for w in folded:
                self.lexicon_map[w] = folded
                self.lexicon_words.add(w)

        self.alias_count = sum(len(n.aliases) for n in nodes)
        self.lexicon_count = sum(len(v) for v in self.lexicon_groups.values())

    def resolve_is_a(
        self,
        raw_is_a: str,
        *,
        learned: OwnerLearnedIndex | None = None,
    ) -> tuple[str | None, str]:
        """Resolve `is_a` to an unambiguous node path (curated or owner learned).

        Returns `(path, status)` where status is `'ok' | 'no_branch' | 'ambiguous'`.
        """
        q = (raw_is_a or "").strip()
        if not q:
            return None, "no_branch"
        if q in self.by_path:
            return q, "ok"
        if learned is not None and q in learned.by_path:
            return q, "ok"

        qf = fold_text(q)
        if not qf:
            return None, "no_branch"

        # 1) Exact label / alias / folded-term match across curated + owner learned
        exact_paths: list[str] = []
        for n in self.nodes:
            if qf in n.folded_terms and n.path not in exact_paths:
                exact_paths.append(n.path)
        if learned is not None:
            lt = learned.by_term.get(qf)
            if lt is not None and lt.path not in exact_paths:
                exact_paths.append(lt.path)

        if len(exact_paths) == 1:
            return exact_paths[0], "ok"
        if len(exact_paths) > 1:
            return None, "ambiguous"

        # 2) Fallback: token match (check curated word-part index & arabic variants)
        part_hits: list[str] = []
        for var in arabic_variants(qf):
            for p in self.curated_token_to_paths.get(var, ()):
                if p not in part_hits:
                    part_hits.append(p)
            if learned is not None and var in learned.by_term:
                lp = learned.by_term[var].path
                if lp not in part_hits:
                    part_hits.append(lp)

        if len(part_hits) == 1:
            return part_hits[0], "ok"
        if len(part_hits) > 1:
            return None, "ambiguous"
        return None, "no_branch"

    def expand_token(
        self,
        token: str,
        *,
        learned: OwnerLearnedIndex | None = None,
    ) -> list[str]:
        """Expand one folded token via lexicon + matched node & descendants breadth-first (no siblings)."""
        out: list[str] = []
        seen: set[str] = set()

        def _push_phrase(phrase: str) -> None:
            for part in fold_text(phrase).split():
                if _SAFE_TS_TOKEN.fullmatch(part) and part not in seen:
                    seen.add(part)
                    out.append(part)

        vars_list = arabic_variants(fold_text(token))
        for var in vars_list:
            for lex in self.lexicon_map.get(var, ()):
                _push_phrase(lex)

        matched_paths: list[str] = []
        for var in vars_list:
            for p in self.curated_token_to_paths.get(var, ()):
                if p not in matched_paths:
                    matched_paths.append(p)
            if learned is not None and var in learned.by_term:
                lp = learned.by_term[var].path
                if lp not in matched_paths:
                    matched_paths.append(lp)

        # Level-by-level BFS: high-weight learned first, then curated aliases round-robin, then floor learned last.
        level: list[str] = matched_paths
        visited: set[str] = set()
        deferred_floor: list[LearnedTermNode] = []
        while level:
            next_level: list[str] = []
            level_learned: list[LearnedTermNode] = []
            level_curated: list[VocabNode] = []

            for cur in level:
                if cur in visited:
                    continue
                visited.add(cur)
                cnode = self.by_path.get(cur)
                if cnode is not None:
                    level_curated.append(cnode)
                    if learned is not None:
                        for lchild in learned.children_by_parent.get(cur, ()):
                            if lchild.path not in visited:
                                next_level.append(lchild.path)
                    for child_path in self.children_by_parent.get(cur, ()):
                        if child_path not in visited:
                            next_level.append(child_path)
                elif learned is not None:
                    lnode = learned.by_path.get(cur)
                    if lnode is not None:
                        level_learned.append(lnode)
                    for lchild in learned.children_by_parent.get(cur, ()):
                        if lchild.path not in visited:
                            next_level.append(lchild.path)

            level_learned.sort(key=lambda n: (-float(n.weight), n.term_folded))
            for ln in level_learned:
                if float(ln.weight) > WEIGHT_FLOOR:
                    _push_phrase(ln.term)
                else:
                    deferred_floor.append(ln)

            # Round-robin across curated nodes at this level (never expand generic labels when aliases is empty).
            alias_lists = [c.aliases for c in level_curated if c.aliases]
            if alias_lists:
                max_a = max(len(a) for a in alias_lists)
                for idx in range(max_a):
                    for als in alias_lists:
                        if idx < len(als):
                            _push_phrase(als[idx])

            level = next_level

        # D18: terms at the floor come last across the expanded tree, still within the max_terms cap.
        deferred_floor.sort(key=lambda n: (-float(n.weight), n.term_folded))
        for ln in deferred_floor:
            _push_phrase(ln.term)
        return out

    def expand_terms(
        self,
        tokens: Iterable[str],
        *,
        learned: OwnerLearnedIndex | None = None,
        max_terms: int = 40,
    ) -> tuple[list[str], list[str]]:
        """Return (primary_terms, expanded_terms) sanitized for Postgres simple tsquery."""
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
            for var in arabic_variants(tok):
                _add(primary, seen_p, var)
                _add(expanded, seen_e, var)
        for tok in tokens:
            if len(expanded) >= max_terms:
                break
            for exp in self.expand_token(tok, learned=learned):
                _add(expanded, seen_e, exp)
                if len(expanded) >= max_terms:
                    break
        return primary[:20], expanded[:max_terms]

    def aliases_for_text(self, subject_path: str, text: str) -> list[str]:
        """Return curated + leaf aliases matched by subject_path or text (replaces SUBJECT_ALIAS_SEEDS)."""
        blob = fold_text(f"{subject_path} {text}")
        tokens = set(blob.split())
        parts = [fold_text(p) for p in (subject_path or "").strip("/").split("/") if p.strip()]
        leaf = parts[-1] if parts else ""
        found: list[str] = []

        # Direct path match first if ontology path matches
        clean_path = (subject_path or "").strip("/")
        direct = self.by_path.get(clean_path)
        if direct is not None:
            found.extend(direct.aliases)

        for n in self.nodes:
            if not n.aliases:
                continue
            leaf_seg = fold_text(n.path.rsplit("/", 1)[-1])
            alias_folded = {fold_text(a) for a in n.aliases if fold_text(a)}
            if (leaf and leaf == leaf_seg) or (tokens & alias_folded):
                found.extend(n.aliases)
        return list(dict.fromkeys(found))


def load_vocab(path: Path | str | None = None) -> VocabTree:
    """Load and strictly validate the topic-tree vocabulary data file."""
    target = Path(path) if path is not None else DEFAULT_TREE_PATH
    raw = json.loads(target.read_text(encoding="utf-8"))
    raw_nodes = raw.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise VocabValidationError("vocab file must define a non-empty 'nodes' list")

    valid_clusters = set(CLUSTERS)
    by_path_raw: dict[str, dict[str, Any]] = {}
    for entry in raw_nodes:
        p = str(entry.get("path") or "").strip("/")
        if not p:
            raise VocabValidationError("every vocab node must have a non-empty 'path'")
        if p in by_path_raw:
            raise VocabValidationError(f"duplicate vocab path: {p!r}")
        cluster = str(entry.get("cluster") or "").strip()
        if cluster not in valid_clusters:
            raise VocabValidationError(f"invalid cluster {cluster!r} on node {p!r}")
        by_path_raw[p] = {**entry, "path": p}

    # Check every parent exists and detect cycles.
    for p, entry in by_path_raw.items():
        parent = entry.get("parent")
        if parent is not None:
            parent_clean = str(parent).strip("/")
            if parent_clean not in by_path_raw:
                raise VocabValidationError(f"node {p!r} references missing parent {parent_clean!r}")
            entry["parent"] = parent_clean

    visiting: set[str] = set()
    visited: set[str] = set()

    def _visit(p: str) -> None:
        if p in visited:
            return
        if p in visiting:
            raise VocabValidationError(f"cycle detected at vocab path {p!r}")
        visiting.add(p)
        par = by_path_raw[p].get("parent")
        if par is not None:
            _visit(par)
        visiting.remove(p)
        visited.add(p)

    for p in by_path_raw:
        _visit(p)

    # Inherit sensitivity and proposal blocks down the tree.
    eff_cache: dict[str, tuple[bool, bool]] = {}

    def _flags(p: str) -> tuple[bool, bool]:
        if p in eff_cache:
            return eff_cache[p]
        entry = by_path_raw[p]
        own_sens = bool(entry.get("sensitive"))
        segs = {fold_text(s) for s in p.split("/")}
        own_block = bool(entry.get("blocks_proposals")) or own_sens or bool(segs & _BLOCKED_SEGMENTS) or entry["cluster"] == "people-family"
        par = entry.get("parent")
        if par is not None:
            p_sens, p_block = _flags(par)
            own_sens = own_sens or p_sens
            own_block = own_block or p_block
        eff_cache[p] = (own_sens, own_block)
        return own_sens, own_block

    built: list[VocabNode] = []
    for entry in by_path_raw.values():
        p = entry["path"]
        eff_sens, blocks_prop = _flags(p)
        aliases = tuple(str(a).strip() for a in (entry.get("aliases") or []) if str(a).strip())
        label = str(entry.get("label") or p.rsplit("/", 1)[-1]).strip()
        leaf = p.rsplit("/", 1)[-1]
        folded_terms = tuple(
            dict.fromkeys(
                f for f in (fold_text(label), fold_text(leaf), *(fold_text(a) for a in aliases)) if f
            )
        )
        built.append(
            VocabNode(
                path=p,
                parent=entry.get("parent"),
                label=label,
                cluster=entry["cluster"],
                fixed=bool(entry.get("fixed")),
                sensitive=eff_sens,
                blocks_proposals=blocks_prop,
                aliases=aliases,
                folded_terms=folded_terms,
            )
        )

    raw_lex = raw.get("lexicon") or {}
    if not isinstance(raw_lex, dict):
        raise VocabValidationError("vocab 'lexicon' must be an object")
    lexicon: dict[str, tuple[str, ...]] = {}
    for gname, words in raw_lex.items():
        if not isinstance(words, list):
            raise VocabValidationError(f"lexicon group {gname!r} must be a list")
        lexicon[str(gname)] = tuple(str(w).strip() for w in words if str(w).strip())

    return VocabTree(built, lexicon)


_CACHE_LOCK = RLock()
_CACHED_VOCAB: VocabTree | None = None


def get_vocab(*, reload: bool = False) -> VocabTree:
    """Return process-cached validated VocabTree."""
    global _CACHED_VOCAB
    with _CACHE_LOCK:
        if _CACHED_VOCAB is None or reload:
            _CACHED_VOCAB = load_vocab()
        return _CACHED_VOCAB
