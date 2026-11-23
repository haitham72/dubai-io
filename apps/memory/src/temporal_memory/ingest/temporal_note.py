"""Temporal Note importer: ENTITY_ALIASES.md seeding and timeline.md parsing."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import re
from typing import Any
import uuid

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - fallback parser handles environments without PyYAML
    yaml = None

from temporal_memory.db.db import Database, fold_text
from temporal_memory.ingest import triage
from temporal_memory.models import EntityKind, Record, Relation

_HEADING_RE = re.compile(r"^#{2,6}\s+(.+?)\s*$")
_KV_RE = re.compile(r"^\s*[-*]\s+(?:\*\*([^*:]+?):?\*\*:?\s*|([^:]+?):\s*)(.*)$")
_FENCE_START_RE = re.compile(r"^```ya?ml\s*$", re.I)
_FENCE_END_RE = re.compile(r"^```\s*$")
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_VALID_KINDS = frozenset({"person", "place", "org", "project", "event"})
_VALID_RELS = frozenset({"self", "friend", "colleague", "family"})


def _strip_quotes(val: str) -> str:
    s = val.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in {'"', "'", "`"}:
        return s[1:-1].strip()
    return s


def _parse_aliases_value(raw: str) -> list[str]:
    tokens = re.split(r"[,،;]+", raw.strip())
    out: list[str] = []
    seen: set[str] = set()
    for tok in tokens:
        cleaned = _strip_quotes(tok)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            out.append(cleaned)
    return out


def parse_entity_aliases_md(path: str | Path) -> list[dict[str, Any]]:
    """Parse ENTITY_ALIASES.md sections into structured entity/alias dicts."""
    lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for raw_line in lines:
        line = raw_line.rstrip()
        m_head = _HEADING_RE.match(line.strip())
        if m_head:
            if current is not None:
                entries.append(current)
            heading = _strip_quotes(m_head.group(1))
            current = {
                "heading": heading,
                "canonical_name": heading,
                "role": "",
                "kind": "",
                "relation_to_user": "",
                "aliases": [],
            }
            continue

        if current is None:
            continue

        m_kv = _KV_RE.match(line)
        if not m_kv:
            continue
        raw_key = (m_kv.group(1) or m_kv.group(2) or "").strip().rstrip(":").lower()
        val = m_kv.group(3).strip()
        if not val:
            continue

        if raw_key in {"canonical name", "canonical", "name"}:
            current["canonical_name"] = _strip_quotes(val)
        elif raw_key in {"role", "description"}:
            current["role"] = _strip_quotes(val)
        elif raw_key in {"kind", "type"}:
            current["kind"] = _strip_quotes(val).lower()
        elif raw_key in {"relation", "relation_to_user"}:
            current["relation_to_user"] = _strip_quotes(val).lower()
        elif raw_key in {"also referred to as", "aliases", "alias", "aka"}:
            current["aliases"].extend(_parse_aliases_value(val))

    if current is not None:
        entries.append(current)

    for entry in entries:
        deduped: list[str] = []
        seen: set[str] = set()
        for al in [entry["heading"], *entry["aliases"]]:
            if al and al not in seen and al != entry["canonical_name"]:
                seen.add(al)
                deduped.append(al)
        entry["aliases"] = deduped

    return entries


def _infer_kind_and_relation(entry: dict[str, Any]) -> tuple[EntityKind, Relation | None]:
    explicit_kind = str(entry.get("kind") or "").lower()
    explicit_rel = str(entry.get("relation_to_user") or "").lower()
    role = str(entry.get("role") or "").lower()

    rel: Relation | None = explicit_rel if explicit_rel in _VALID_RELS else None  # type: ignore[assignment]
    if rel is None:
        if re.search(r"\b(self|owner|myself)\b", role):
            rel = "self"
        elif re.search(r"\b(friend|buddy|pal|bestie)\b", role):
            rel = "friend"
        elif re.search(r"\b(family|mother|mom|father|dad|sister|brother|wife|husband|spouse|cousin|uncle|aunt|parent|sibling)\b", role):
            rel = "family"
        elif re.search(r"\b(colleague|coworker|co-worker|manager|boss|teammate|mentor|partner|recruiter|client)\b", role):
            rel = "colleague"

    kind: EntityKind = explicit_kind if explicit_kind in _VALID_KINDS else "person"  # type: ignore[assignment]
    if explicit_kind not in _VALID_KINDS:
        if re.search(r"\b(project|app|product|startup|repo|platform|initiative|venture)\b", role):
            kind = "project"
        elif re.search(r"\b(company|org|organization|employer|bank|university|school|firm|agency|studio|team)\b", role):
            kind = "org"
        elif re.search(r"\b(place|city|neighborhood|cafe|restaurant|park|office|venue|country|building|location)\b", role):
            kind = "place"
        elif re.search(r"\b(event|conference|trip|wedding|summit|hackathon|meetup)\b", role):
            kind = "event"

    return kind, rel


def seed_entity_aliases(db: Database, owner: str, path: str | Path) -> int:
    """Upsert active entities and user-supplied aliases from ENTITY_ALIASES.md."""
    entries = parse_entity_aliases_md(path)
    if not entries:
        return 0

    added_aliases = 0
    with db.transaction() as conn:
        existing_rows = conn.execute(
            "SELECT id, name, relation_to_user FROM entities WHERE owner = %s AND erased_at IS NULL",
            (owner,),
        ).fetchall()
        by_folded_name: dict[str, dict[str, Any]] = {}
        for r in existing_rows:
            fn = fold_text(r["name"])
            if fn:
                by_folded_name.setdefault(fn, dict(r))

        for entry in entries:
            canon = str(entry["canonical_name"]).strip()
            folded_canon = fold_text(canon)
            if not folded_canon:
                continue

            kind, rel = _infer_kind_and_relation(entry)
            existing = by_folded_name.get(folded_canon)
            if existing is not None:
                eid = str(existing["id"])
                conn.execute(
                    """
                    UPDATE entities
                    SET status = 'active',
                        relation_to_user = COALESCE(relation_to_user, %s)
                    WHERE owner = %s AND id = %s
                    """,
                    (rel, owner, eid),
                )
            else:
                eid = f"e_{uuid.uuid4().hex[:12]}"
                conn.execute(
                    """
                    INSERT INTO entities (id, owner, kind, name, status, relation_to_user)
                    VALUES (%s, %s, %s, %s, 'active', %s)
                    """,
                    (eid, owner, kind, canon, rel),
                )
                by_folded_name[folded_canon] = {"id": eid, "name": canon, "relation_to_user": rel}

            candidates = [canon, *entry.get("aliases", [])]
            seen_folded: set[str] = set()
            for alias in candidates:
                clean_alias = str(alias).strip()
                af = fold_text(clean_alias)
                if not af or af in seen_folded:
                    continue
                seen_folded.add(af)
                res = conn.execute(
                    """
                    INSERT INTO entity_aliases (owner, entity_id, alias, alias_folded, source)
                    VALUES (%s, %s, %s, %s, 'user_supplied')
                    ON CONFLICT (owner, alias_folded, entity_id) DO UPDATE SET
                        source = 'user_supplied',
                        alias = EXCLUDED.alias
                    WHERE entity_aliases.source <> 'user_supplied'
                    RETURNING 1
                    """,
                    (owner, eid, clean_alias, af),
                ).fetchone()
                if res is not None:
                    added_aliases += 1

        if added_aliases > 0:
            conn.execute(
                "UPDATE owners SET alias_version = alias_version + 1 WHERE id = %s",
                (owner,),
            )

    return added_aliases


def _fallback_yaml_load(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    current_key: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.lstrip().startswith("- ") and current_key is not None:
            item = _strip_quotes(line.lstrip()[2:])
            existing = out.get(current_key)
            if isinstance(existing, list):
                existing.append(item)
            else:
                out[current_key] = [item]
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            k = key.strip()
            v = val.strip()
            current_key = k
            if not v:
                out[k] = []
            elif v.startswith("[") and v.endswith("]"):
                inner = v[1:-1].strip()
                out[k] = [_strip_quotes(x) for x in inner.split(",") if _strip_quotes(x)] if inner else []
            else:
                out[k] = _strip_quotes(v)
    return out


def _load_yaml_block(block: str) -> dict[str, Any]:
    if yaml is not None:
        loaded = yaml.safe_load(block)
        if isinstance(loaded, dict):
            return loaded
    return _fallback_yaml_load(block)


def _format_at(meta: dict[str, Any]) -> str:
    raw = meta.get("date") or meta.get("retrospective") or meta.get("period") or ""
    if isinstance(raw, datetime):
        return raw.replace(tzinfo=None).isoformat(timespec="seconds")
    if isinstance(raw, date):
        return f"{raw.isoformat()}T00:00:00"
    s = str(raw).strip()
    if _ISO_DATE_RE.match(s):
        return f"{s}T00:00:00"
    return s


def _clean_wikilinks(text: str) -> str:
    return _WIKILINK_RE.sub(lambda m: (m.group(2) or m.group(1)).strip(), text)


def _clean_prose(lines: list[str]) -> str:
    trimmed = list(lines)
    while trimmed and (not trimmed[0].strip() or trimmed[0].strip() == "---"):
        trimmed.pop(0)
    while trimmed and (
        not trimmed[-1].strip()
        or trimmed[-1].strip() == "---"
        or trimmed[-1].lstrip().startswith("#")
    ):
        trimmed.pop()
    return _clean_wikilinks("\n".join(trimmed)).strip()


def _format_timeline_text(meta: dict[str, Any], prose: str) -> str:
    hints: list[str] = []
    for key in ("incident", "thread", "location", "period", "retrospective", "severity", "emotion", "note"):
        val = meta.get(key)
        if val is not None and str(val).strip():
            hints.append(f"{key}: {_clean_wikilinks(str(val).strip())}")

    for list_key in ("entities", "links", "tags"):
        vals = meta.get(list_key)
        if isinstance(vals, str) and vals.strip():
            vals = [v.strip() for v in vals.split(",") if v.strip()]
        if isinstance(vals, list):
            cleaned_vals = [_clean_wikilinks(str(v).strip()) for v in vals if str(v).strip()]
            if cleaned_vals:
                hints.append(f"{list_key}: {', '.join(cleaned_vals)}")

    hint_line = f"[{' | '.join(hints)}]" if hints else ""
    if hint_line and prose:
        return f"{hint_line}\n{prose}"
    return hint_line or prose


def parse_timeline_md(path: str | Path, owner: str) -> list[Record]:
    """Parse timeline.md YAML blocks and prose paragraphs into temporal_note Records."""
    lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    blocks: list[tuple[dict[str, Any], str]] = []

    in_yaml = False
    yaml_lines: list[str] = []
    prose_lines: list[str] = []
    current_meta: dict[str, Any] | None = None

    for line in lines:
        stripped = line.strip()
        if not in_yaml and _FENCE_START_RE.match(stripped):
            if current_meta is not None:
                blocks.append((current_meta, _clean_prose(prose_lines)))
                prose_lines = []
            in_yaml = True
            yaml_lines = []
            continue

        if in_yaml and _FENCE_END_RE.match(stripped):
            in_yaml = False
            current_meta = _load_yaml_block("\n".join(yaml_lines))
            prose_lines = []
            continue

        if in_yaml:
            yaml_lines.append(line)
        elif current_meta is not None:
            prose_lines.append(line)

    if current_meta is not None:
        blocks.append((current_meta, _clean_prose(prose_lines)))

    records: list[Record] = []
    for idx, (meta, prose) in enumerate(blocks):
        text = _format_timeline_text(meta, prose)
        if not text:
            continue
        records.append(
            Record(
                id=f"tn-{idx:04d}",
                owner=owner,
                source="temporal_note",
                at=_format_at(meta),
                author="owner",
                text=text,
                generation=0,
            )
        )
    return records


def _find_case_insensitive(directory: Path, target_name: str) -> Path | None:
    exact = directory / target_name
    if exact.is_file():
        return exact
    low = target_name.lower()
    for child in directory.iterdir():
        if child.is_file() and child.name.lower() == low:
            return child
    return None


def import_temporal_note(
    db: Database,
    owner: str,
    path: str | Path,
    *,
    split: bool = True,
) -> dict[str, Any]:
    """Seed user-supplied aliases and ingest timeline records through triage.ingest_records."""
    target = Path(path)
    aliases_seeded = 0
    records: list[Record] = []

    if target.is_dir():
        aliases_file = _find_case_insensitive(target, "ENTITY_ALIASES.md")
        if aliases_file is not None:
            aliases_seeded = seed_entity_aliases(db, owner, aliases_file)
        timeline_file = _find_case_insensitive(target, "timeline.md")
        if timeline_file is not None:
            records = parse_timeline_md(timeline_file, owner)
    elif target.is_file():
        if "alias" in target.stem.lower():
            aliases_seeded = seed_entity_aliases(db, owner, target)
        else:
            records = parse_timeline_md(target, owner)
            if not records:
                aliases_seeded = seed_entity_aliases(db, owner, target)
    else:
        raise FileNotFoundError(f"temporal_note path not found: {target}")

    summary = triage.ingest_records(db, owner, records, split=split)
    summary["aliases_seeded"] = aliases_seeded
    return summary
