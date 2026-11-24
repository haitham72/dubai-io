"""Quest-like leaves, rendered as markdown files and as JSON cards.

One projection. Postgres reads are bounded (counts, then a per-leaf window).
Health and faith are never a spine. "You told me" is only ``user_supplied``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
import re
from typing import Any

from temporal_memory.models import CLUSTERS, CLUSTER_LABELS

SPINES: dict[str, tuple[str, str]] = {
    "people-family": ("01-people", "People & family"),
    "career": ("02-career-and-craft", "Career"),
    "projects": ("03-projects", "Projects"),
    "learning": ("04-learning-and-ideas", "Learning"),
    "home-money": ("05-home-and-money", "Home & money"),
    "events": ("06-events-and-occasions", "Events"),
    "travel": ("07-travel-and-places", "Travel"),
}

_ROOT_TO_CLUSTER = {
    "career": "career",
    "work": "career",
    "background": "career",
    "learning": "learning",
    "projects": "projects",
    "people-family": "people-family",
    "family": "people-family",
    "identity": "people-family",
    "events": "events",
    "interests": "events",
    "home-money": "home-money",
    "devices": "home-money",
    "lifestyle": "home-money",
    "money": "home-money",
    "travel": "travel",
}

TIER_DIR = {"T1": "inner-circle", "T2": "friends-and-peers", "T3": "professional-network"}
_STATED = frozenset({"user_supplied", "provider_confirmed"})
_HELD = frozenset({"health", "faith", "wellbeing"})
_SNAPSHOT_N = 4
_OPEN_N = 6
_TIMELINE_N = 8
_SPLIT_AT = 12
_USER_SECTIONS = (
    ("Identity", "people-family"),
    ("Core Craft", "career"),
    ("Personality", None),
    ("Values", None),
    ("Strengths & Tensions", None),
    ("Interests", "events"),
    ("Drive", "projects"),
)


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:60] or "item"


def cluster_for_path(path: str) -> str | None:
    """Map a stored subject path onto one of the seven clusters, or drop it."""
    raw = (path or "").strip("/")
    if not raw:
        return None
    lowered = raw.lower()
    root = lowered.split("/")[0]
    if root in _HELD:
        return None
    if "wedding" in lowered or lowered.startswith("lifestyle/food") or lowered.startswith("lifestyle/sports") or lowered.startswith("fun_out"):
        return "events"
    if root in _ROOT_TO_CLUSTER:
        return _ROOT_TO_CLUSTER[root]
    return None


def shown_provenance(value: str | None) -> str:
    if value == "user_supplied":
        return "You told me"
    if value == "demo_fixture":
        return "Demo data"
    return value or "inferred"


@dataclass
class Bullet:
    text: str
    fact_ids: list[str]
    provenance: str
    as_of: str
    status: str = "active"
    valid_to: str | None = None
    text_orig: str | None = None
    record_ids: list[str] = field(default_factory=list)

    def line(self, *, history: bool = False) -> str:
        body = f"was {self.text} until {self.valid_to or '?'}" if history else self.text
        orig = f' ["{self.text_orig}"]' if self.text_orig else ""
        ids = ",".join(self.fact_ids)
        return f"- {body}{orig} · {self.provenance} · as of {self.as_of or '?'} · facts: {ids}"


@dataclass
class Leaf:
    key: str
    title: str
    cluster: str
    path: str
    kind: str
    snapshot: list[Bullet] = field(default_factory=list)
    open_loops: list[Bullet] = field(default_factory=list)
    timeline: list[Bullet] = field(default_factory=list)
    noticed: list[Bullet] = field(default_factory=list)
    fact_count: int = 0
    entity_id: str | None = None
    relation: str | None = None
    tier: str | None = None
    tier_suggested: str | None = None
    aliases: list[str] = field(default_factory=list)
    shared_subjects: list[tuple[str, str]] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    subject_path: str = ""

    def as_card(self) -> dict[str, Any]:
        def pack(bullets: list[Bullet]) -> list[dict[str, Any]]:
            return [
                {
                    "text": b.text if b.status not in ("superseded", "ended") else f"was {b.text} until {b.valid_to or '?'}",
                    "fact_ids": b.fact_ids,
                    "provenance": b.provenance,
                    "as_of": b.as_of,
                }
                for b in bullets
            ]

        noticed = []
        for b in self.noticed:
            noticed.append({
                "text": b.text if b.text.startswith("I noticed") else f"I noticed {b.text}",
                "fact_ids": b.fact_ids,
                "provenance": b.provenance,
                "as_of": b.as_of,
                "actions": ["Confirm", "Not true"],
            })
        return {
            "title": self.title,
            "cluster": self.cluster,
            "path": self.path,
            "kind": self.kind,
            "entity_id": self.entity_id,
            "relation": self.relation,
            "tier": self.tier,
            "tier_suggested": self.tier_suggested,
            "snapshot": pack(self.snapshot),
            "open_loops": pack(self.open_loops),
            "recent_changes": pack(self.timeline),
            "noticed": noticed,
            "shared_subjects": [{"path": p, "role": r} for p, r in self.shared_subjects],
            "fact_ids": [fid for b in (*self.snapshot, *self.open_loops, *self.timeline) for fid in b.fact_ids],
            "provenance": self.snapshot[0].provenance if self.snapshot else None,
            "as_of": self.snapshot[0].as_of if self.snapshot else None,
            "demo_data": any(
                b.provenance == "Demo data"
                for b in (*self.snapshot, *self.open_loops, *self.timeline, *self.noticed)
            ),
        }


@dataclass
class Projection:
    owner: str
    evidence_limits: str
    held_back: dict[str, int]
    leaves: list[Leaf]
    watermarks: list[tuple[str, str]]
    forget_rule_counts: dict[str, int]
    rising: list[tuple[str, int]]
    pending_people: list[str]


def _allow_on_people(provenance: str | None) -> bool:
    return (provenance or "") in _STATED


def _is_open(row: dict[str, Any], today: date) -> bool:
    if row.get("status") == "hypothesis":
        return True
    modality = (row.get("modality") or "").lower()
    if modality in ("planned", "wanted"):
        return True
    event_at = (row.get("event_at") or "")[:10]
    if len(event_at) == 10:
        try:
            when = date.fromisoformat(event_at)
        except ValueError:
            return False
        return today <= when <= today + timedelta(days=30)
    return False


def _bullet(row: dict[str, Any], record_ids: list[str] | None = None) -> Bullet:
    return Bullet(
        text=row["text"],
        fact_ids=[row["id"]],
        provenance=shown_provenance(row.get("provenance")),
        as_of=(row.get("valid_from") or "")[:10],
        status=row.get("status") or "active",
        valid_to=(row.get("valid_to") or None),
        text_orig=row.get("text_orig"),
        record_ids=list(record_ids or []),
    )


def _fill_leaf(leaf: Leaf, rows: list[dict[str, Any]], *, people_only_stated: bool, evidence: dict[str, list[str]], today: date) -> None:
    snap: list[Bullet] = []
    loops: list[Bullet] = []
    history: list[Bullet] = []
    noticed: list[Bullet] = []
    for row in rows:
        if people_only_stated and not _allow_on_people(row.get("provenance")) and row.get("status") != "hypothesis":
            continue
        bullet = _bullet(row, evidence.get(row["id"]))
        if row.get("status") == "hypothesis":
            noticed.append(bullet)
            if len(loops) < _OPEN_N:
                loops.append(bullet)
            continue
        if row.get("status") in ("superseded", "ended"):
            if len(history) < _TIMELINE_N:
                history.append(bullet)
            continue
        if _is_open(row, today) and len(loops) < _OPEN_N:
            loops.append(bullet)
        elif len(snap) < _SNAPSHOT_N:
            snap.append(bullet)
        elif len(history) < _TIMELINE_N:
            history.append(bullet)
    leaf.snapshot = snap
    leaf.open_loops = loops
    leaf.timeline = history
    leaf.noticed = noticed
    ids: list[str] = []
    for b in (*snap, *loops, *history):
        for rid in b.record_ids:
            if rid not in ids:
                ids.append(rid)
    leaf.evidence_ids = ids[:20]


def _subject_md_path(cluster: str, subject_path: str) -> str:
    spine = SPINES[cluster][0]
    parts = [slug(p) for p in subject_path.split("/") if p]
    # Drop the root segment; the spine folder replaces it.
    rest = parts[1:] or parts
    return f"{spine}/{'/'.join(rest)}.md"


def _rows_by_subject(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["subject_id"], []).append(row)
    return grouped


def _assemble(
    owner: str,
    *,
    evidence_limits: str,
    held_back: dict[str, int],
    subjects: list[dict[str, Any]],
    fact_rows: list[dict[str, Any]],
    people: list[dict[str, Any]],
    places: list[dict[str, Any]],
    person_facts: list[dict[str, Any]],
    evidence: dict[str, list[str]],
    watermarks: list[tuple[str, str]],
    forget_rule_counts: dict[str, int],
    rising: list[tuple[str, int]],
    today: date | None = None,
) -> Projection:
    today = today or date.today()
    by_subject = _rows_by_subject(fact_rows)
    leaves: list[Leaf] = []
    for sub in subjects:
        cluster = cluster_for_path(sub["path"])
        if cluster is None:
            continue
        leaf = Leaf(
            key=sub["id"],
            title=sub["label"] or sub["path"],
            cluster=cluster,
            path=_subject_md_path(cluster, sub["path"]),
            kind="subject",
            fact_count=int(sub.get("fact_count") or 0),
            subject_path=sub["path"],
        )
        _fill_leaf(
            leaf,
            by_subject.get(sub["id"], []),
            people_only_stated=cluster == "people-family",
            evidence=evidence,
            today=today,
        )
        if leaf.fact_count or leaf.snapshot or leaf.timeline or leaf.noticed:
            leaves.append(leaf)

    by_person: dict[str, list[dict[str, Any]]] = {}
    for row in person_facts:
        by_person.setdefault(row["entity_id"], []).append(row)

    pending: list[str] = []
    for person in people:
        if (person.get("relation_to_user") or "") == "self":
            continue
        tier = person.get("closeness_tier")
        suggested = person.get("closeness_suggested")
        # A stored closeness_tier is the confirmed tier. A suggestion alone is not.
        if not tier:
            if suggested:
                pending.append(f"{person['name']} ({suggested})")
            continue
        folder = TIER_DIR.get(tier)
        if folder is None:
            continue
        leaf = Leaf(
            key=person["id"],
            title=person["name"],
            cluster="people-family",
            path=f"01-people/{folder}/{slug(person['name'])}.md",
            kind="person",
            entity_id=person["id"],
            relation=person.get("relation_to_user"),
            tier=tier,
            tier_suggested=suggested if suggested and suggested != tier else None,
            aliases=list(person.get("aliases") or []),
            fact_count=len(by_person.get(person["id"], [])),
        )
        roles: list[tuple[str, str]] = []
        for row in by_person.get(person["id"], []):
            role = row.get("role") or ""
            path = row.get("subject_path") or ""
            if path and (path, role) not in roles:
                roles.append((path, role))
        leaf.shared_subjects = roles[:12]
        _fill_leaf(leaf, by_person.get(person["id"], []), people_only_stated=True, evidence=evidence, today=today)
        leaves.append(leaf)

    for place in places:
        leaf = Leaf(
            key=place["id"],
            title=place["name"],
            cluster="travel",
            path=f"07-travel-and-places/{slug(place['name'])}.md",
            kind="place",
            entity_id=place["id"],
            fact_count=len(by_person.get(place["id"], [])),
        )
        _fill_leaf(leaf, by_person.get(place["id"], []), people_only_stated=False, evidence=evidence, today=today)
        if leaf.snapshot or leaf.timeline or leaf.fact_count:
            leaves.append(leaf)

    return Projection(
        owner=owner,
        evidence_limits=evidence_limits,
        held_back=held_back,
        leaves=leaves,
        watermarks=watermarks,
        forget_rule_counts=forget_rule_counts,
        rising=rising,
        pending_people=pending,
    )


def _evidence_block(proj: Projection) -> list[str]:
    lines = [f"_Evidence limits: {proj.evidence_limits}_"]
    if proj.held_back:
        bits = ", ".join(f"{cat} {cnt}" for cat, cnt in sorted(proj.held_back.items()))
        lines.append(f"_Held back (counts only): {bits}_")
    else:
        lines.append("_Held back (counts only): 0_")
    return lines


def leaf_markdown(leaf: Leaf, proj: Projection) -> str:
    aliases = ", ".join(leaf.aliases)
    front = [
        "---",
        f"title: {leaf.title}",
        f"theme: {CLUSTER_LABELS.get(leaf.cluster, leaf.cluster)}",
        f"ontology_id: {leaf.subject_path or leaf.path}",
        f"aliases: {aliases}",
        f"last_verified: {leaf.snapshot[0].as_of if leaf.snapshot else '?'}",
        "---",
        f"# {leaf.title}",
        "",
    ]
    if leaf.kind == "person":
        front.extend([
            f"- **Relation:** {leaf.relation or 'unspecified'}",
            f"- **Tier:** {leaf.tier or 'unconfirmed'}",
            "",
        ])
        if leaf.shared_subjects:
            front.append("## Shared subjects")
            front.extend(f"- {path}: {role or 'mentioned'}" for path, role in leaf.shared_subjects)
            front.append("")
    front.extend(["## Current Snapshot", *([b.line() for b in leaf.snapshot] or ["- _(none yet)_"]), ""])
    front.extend(["## Open Loops & Active Signals", *([b.line() for b in leaf.open_loops] or ["- _(none)_"]), ""])
    history = [b.line(history=b.status in ("superseded", "ended")) for b in leaf.timeline]
    front.extend(["## Timeline & Fact History", *(history or ["- _(none)_"]), ""])
    front.extend(["## Evidence Limits", *_evidence_block(proj), ""])
    return "\n".join(front)


def to_markdown(proj: Projection) -> dict[str, str]:
    out: dict[str, str] = {}
    by_cluster: dict[str, list[Leaf]] = {c: [] for c in CLUSTERS}
    for leaf in proj.leaves:
        by_cluster.setdefault(leaf.cluster, []).append(leaf)
        out[leaf.path] = leaf_markdown(leaf, proj)

    user = [f"# USER Profile ({proj.owner})", ""]
    for title, cluster in _USER_SECTIONS:
        user.append(f"## {title}")
        cited = by_cluster.get(cluster, []) if cluster else []
        if cited:
            for leaf in sorted(cited, key=lambda item: item.path)[:6]:
                user.append(f"- [{leaf.title}]({leaf.path})")
        else:
            user.append("- _(no confirmed leaf yet)_")
        user.append("")
    out["USER.md"] = "\n".join(user)

    now = [f"# NOW ({proj.owner})", "", "## Open loops"]
    loops = [b for leaf in proj.leaves for b in leaf.open_loops]
    now.extend([b.line() for b in loops[:12]] or ["- _(none)_"])
    now.extend(["", "## Next 30 days"])
    dated = [b for b in loops if b.as_of]
    now.extend([b.line() for b in dated[:8]] or ["- _(none)_"])
    now.extend(["", "## Rising topics"])
    now.extend([f"- {path} · {count} recent facts" for path, count in proj.rising[:8]] or ["- _(none)_"])
    now.extend(["", "## Pending confirmations"])
    noticed = [b for leaf in proj.leaves for b in leaf.noticed]
    now.extend([b.line() for b in noticed[:8]] or ["- _(none)_"])
    for name in proj.pending_people:
        now.append(f"- I noticed {name} · inferred · Confirm / Not true")
    now.append("")
    out["NOW.md"] = "\n".join(now)

    index = [f"# Memories ({proj.owner})", ""]
    for cluster in CLUSTERS:
        spine, label = SPINES[cluster]
        group = sorted(by_cluster.get(cluster, []), key=lambda item: item.path)
        index.append(f"## {label}")
        if group:
            for leaf in group:
                index.append(f"- [{leaf.title}]({leaf.path}) — {leaf.fact_count} facts")
        else:
            index.append("- _(none yet)_")
        index.append("")
    out["MEMORIES.md"] = "\n".join(index)

    sources = [
        f"# Sources ({proj.owner})",
        "",
        "## Watermarks",
        *([f"- {src}: {at}" for src, at in proj.watermarks] or ["- _(none)_"]),
        "",
        "## Evidence limits",
        f"- {proj.evidence_limits}",
        "",
        "## Never Remember",
    ]
    if proj.forget_rule_counts:
        for kind, cnt in sorted(proj.forget_rule_counts.items()):
            sources.append(f"- {kind}: {cnt} rule(s)")
    else:
        sources.append("- _(no forget rules)_")
    sources.extend(["", "## Held back (counts only)"])
    if proj.held_back:
        for cat, cnt in sorted(proj.held_back.items()):
            sources.append(f"- **{cat}:** {cnt}")
    else:
        sources.append("- _(0 items held back)_")
    sources.append("")
    out["SOURCES.md"] = "\n".join(sources)

    mech = ["# Mechanical index", "", "Subject path → evidence record ids. No model wrote this file.", ""]
    for leaf in sorted((leaf for leaf in proj.leaves if leaf.kind == "subject"), key=lambda item: item.subject_path):
        ids = ", ".join(leaf.evidence_ids) or "(none in this window)"
        mech.append(f"- `{leaf.subject_path}` → {ids}")
    mech.append("")
    out["MECHANICAL_INDEX.md"] = "\n".join(mech)

    staging_h = ["# Hypotheses to confirm", ""]
    if noticed or proj.pending_people:
        for b in noticed:
            text = b.text if b.text.startswith("I noticed") else f"I noticed {b.text}"
            staging_h.append(f"- {text} `[Confirm / Not true]` · {b.provenance} · facts: {','.join(b.fact_ids)}")
        for name in proj.pending_people:
            staging_h.append(f"- I noticed {name} `[Confirm / Not true]` · inferred")
    else:
        staging_h.append("- _(no open hypotheses)_")
    staging_h.append("")
    out["_staging/hypotheses-to-confirm.md"] = "\n".join(staging_h)

    splits = ["# Proposed tree splits", "", "Proposals only. Nothing here is applied to the tree.", ""]
    proposed = [leaf for leaf in proj.leaves if leaf.kind == "subject" and leaf.fact_count >= _SPLIT_AT]
    if proposed:
        for leaf in proposed:
            splits.append(
                f"- Propose a split of `{leaf.path}` ({leaf.fact_count} facts). Not applied."
            )
    else:
        splits.append("- _(no leaf has 12 or more facts)_")
    splits.append("")
    out["_staging/proposed-tree-splits.md"] = "\n".join(splits)
    return out


_FACT_SQL = """
SELECT f.id, f.text, f.text_orig, f.subject_id, f.valid_from, f.valid_to, f.status,
       f.provenance, f.modality, f.event_at, f.predicate
FROM (
    SELECT f.*, ROW_NUMBER() OVER (
        PARTITION BY f.subject_id ORDER BY f.valid_from DESC, f.id ASC
    ) AS rn
    FROM facts f
    JOIN subjects s ON s.owner = f.owner AND s.id = f.subject_id
    WHERE f.owner = %s AND f.erased_at IS NULL AND f.status <> 'history'
      AND s.sensitive_cat IS NULL
      AND split_part(s.path, '/', 1) NOT IN ('health', 'faith', 'wellbeing')
      AND NOT EXISTS (
          SELECT 1 FROM fact_evidence fe
          JOIN records r ON r.owner = fe.owner AND r.id = fe.record_id
          WHERE fe.owner = f.owner AND fe.fact_id = f.id
            AND (r.erased_at IS NOT NULL OR r.generation > fe.record_generation)
      )
      AND NOT EXISTS (
          SELECT 1 FROM forget_rules fr
          WHERE fr.owner = f.owner AND (
              (fr.kind = 'item' AND fr.value = f.id)
              OR (fr.kind = 'text' AND position(lower(fr.value) IN lower(f.text)) > 0)
          )
      )
) f
WHERE f.rn <= %s
"""


def _load_evidence(conn: Any, owner: str, fact_ids: list[str]) -> dict[str, list[str]]:
    if not fact_ids:
        return {}
    rows = conn.execute(
        """
        SELECT fact_id, record_id FROM fact_evidence
        WHERE owner = %s AND fact_id = ANY(%s)
        ORDER BY record_id ASC
        """,
        (owner, fact_ids),
    ).fetchall()
    out: dict[str, list[str]] = {}
    for row in rows:
        out.setdefault(row["fact_id"], []).append(row["record_id"])
    return out


def projection(db: Any, owner: str) -> Projection:
    """Build the §9 projection with bounded SQL. Does not scan every fact text."""
    with db.connection() as conn:
        owner_row = conn.execute(
            "SELECT evidence_limits FROM owners WHERE id = %s",
            (owner,),
        ).fetchone()
        limits = (owner_row["evidence_limits"] if owner_row else None) or (
            "voice notes not read; history before import start not seen"
        )
        subjects = conn.execute(
            """
            SELECT s.id, s.path, s.label, COUNT(f.id) AS fact_count,
                   COUNT(f.id) FILTER (
                       WHERE f.valid_from >= to_char(CURRENT_DATE - 21, 'YYYY-MM-DD')
                   ) AS recent
            FROM subjects s
            JOIN facts f ON f.owner = s.owner AND f.subject_id = s.id
            WHERE s.owner = %s AND f.erased_at IS NULL AND f.status <> 'history'
              AND s.sensitive_cat IS NULL
              AND split_part(s.path, '/', 1) NOT IN ('health', 'faith', 'wellbeing')
            GROUP BY s.id, s.path, s.label
            ORDER BY s.path ASC
            """,
            (owner,),
        ).fetchall()
        fact_rows = conn.execute(_FACT_SQL, (owner, _SNAPSHOT_N + _TIMELINE_N)).fetchall()
        people = conn.execute(
            """
            SELECT id, name, relation_to_user, closeness_tier, closeness_suggested,
                   tier_confirmed_at, kind
            FROM entities
            WHERE owner = %s AND erased_at IS NULL AND kind = 'person' AND status <> 'merged'
            ORDER BY name ASC
            """,
            (owner,),
        ).fetchall()
        alias_rows = conn.execute(
            "SELECT entity_id, alias FROM entity_aliases WHERE owner = %s ORDER BY alias ASC",
            (owner,),
        ).fetchall()
        places = conn.execute(
            """
            SELECT id, name FROM entities
            WHERE owner = %s AND erased_at IS NULL AND kind = 'place' AND status <> 'merged'
            ORDER BY name ASC
            """,
            (owner,),
        ).fetchall()
        person_facts = conn.execute(
            """
            SELECT entity_id, id, text, text_orig, subject_id, subject_path, role,
                   valid_from, valid_to, status, provenance, modality, event_at
            FROM (
                SELECT fe.entity_id, f.id, f.text, f.text_orig, f.subject_id, s.path AS subject_path,
                       fe.role, f.valid_from, f.valid_to, f.status, f.provenance, f.modality, f.event_at,
                       ROW_NUMBER() OVER (
                           PARTITION BY fe.entity_id ORDER BY f.valid_from DESC, f.id ASC
                       ) AS rn
                FROM fact_entities fe
                JOIN facts f ON f.owner = fe.owner AND f.id = fe.fact_id
                JOIN subjects s ON s.owner = f.owner AND s.id = f.subject_id
                WHERE fe.owner = %s AND f.erased_at IS NULL AND f.status <> 'history'
                  AND s.sensitive_cat IS NULL
                  AND split_part(s.path, '/', 1) NOT IN ('health', 'faith', 'wellbeing')
            ) q
            WHERE rn <= %s
            """,
            (owner, _SNAPSHOT_N + _TIMELINE_N),
        ).fetchall()
        quarantined = conn.execute(
            """
            SELECT category, COUNT(*) AS n FROM quarantine
            WHERE owner = %s
            GROUP BY category
            """,
            (owner,),
        ).fetchall()
        hidden = conn.execute(
            """
            SELECT COUNT(*) AS n FROM facts f
            JOIN subjects s ON s.owner = f.owner AND s.id = f.subject_id
            WHERE f.owner = %s AND f.erased_at IS NULL AND f.status <> 'history'
              AND (s.sensitive_cat IS NOT NULL OR split_part(s.path, '/', 1) IN ('health', 'faith', 'wellbeing'))
            """,
            (owner,),
        ).fetchone()
        watermarks = conn.execute(
            """
            SELECT source, MAX(at) AS at FROM records
            WHERE owner = %s AND erased_at IS NULL
            GROUP BY source ORDER BY source ASC
            """,
            (owner,),
        ).fetchall()
        rules = conn.execute(
            "SELECT kind, COUNT(*) AS n FROM forget_rules WHERE owner = %s GROUP BY kind",
            (owner,),
        ).fetchall()
        fact_ids = [r["id"] for r in fact_rows] + [r["id"] for r in person_facts]
        evidence = _load_evidence(conn, owner, list(dict.fromkeys(fact_ids)))

    aliases: dict[str, list[str]] = {}
    for row in alias_rows:
        aliases.setdefault(row["entity_id"], []).append(row["alias"])
    people_dicts = []
    for row in people:
        item = dict(row)
        item["aliases"] = aliases.get(row["id"], [])
        people_dicts.append(item)
    held = {row["category"]: int(row["n"]) for row in quarantined}
    hidden_n = int(hidden["n"]) if hidden else 0
    if hidden_n:
        held["sensitive"] = held.get("sensitive", 0) + hidden_n
    rising = [
        (row["path"], int(row["recent"]))
        for row in sorted(subjects, key=lambda r: (-int(r["recent"]), r["path"]))
        if int(row["recent"]) > 0
    ]
    return _assemble(
        owner,
        evidence_limits=limits,
        held_back=held,
        subjects=[dict(row) for row in subjects],
        fact_rows=[dict(row) for row in fact_rows],
        people=people_dicts,
        places=[dict(row) for row in places],
        person_facts=[dict(row) for row in person_facts],
        evidence=evidence,
        watermarks=[(row["source"], row["at"]) for row in watermarks],
        forget_rule_counts={row["kind"]: int(row["n"]) for row in rules},
        rising=rising[:8],
    )


def projection_from_store(store: Any, owner: str) -> Projection:
    """Same leaves from an in-memory store. The Postgres path does not use this."""
    facts = []
    iter_fn = getattr(store, "iter_visible_facts", None)
    if callable(iter_fn):
        facts = [f for f in iter_fn(owner, page_size=500) if f.status != "history"]
    else:
        facts = [f for f in store.visible_facts(owner, limit=500) if f.status != "history"]
    subjects = list(store.list_subjects(owner))
    subj_by_id = {s.id: s for s in subjects}
    kept = []
    for fact in facts:
        sub = subj_by_id.get(fact.subject_id)
        root = ((sub.path if sub else "") or "").split("/")[0].lower()
        if root in _HELD or (sub and sub.sensitive_cat):
            continue
        kept.append(fact)
    counts: dict[str, int] = {}
    recent_cut = (date.today() - timedelta(days=21)).isoformat()
    recent: dict[str, int] = {}
    for fact in kept:
        counts[fact.subject_id] = counts.get(fact.subject_id, 0) + 1
        if (fact.valid_from or "") >= recent_cut:
            recent[fact.subject_id] = recent.get(fact.subject_id, 0) + 1
    subject_rows = [
        {"id": s.id, "path": s.path, "label": s.label, "fact_count": counts.get(s.id, 0), "recent": recent.get(s.id, 0)}
        for s in subjects
        if counts.get(s.id, 0)
    ]
    fact_rows = []
    for fact in kept:
        fact_rows.append({
            "id": fact.id,
            "text": fact.text,
            "text_orig": fact.text_orig,
            "subject_id": fact.subject_id,
            "valid_from": fact.valid_from,
            "valid_to": fact.valid_to,
            "status": fact.status,
            "provenance": fact.provenance,
            "modality": getattr(fact, "modality", None),
            "event_at": getattr(fact, "event_at", None),
            "predicate": getattr(fact, "predicate", None),
        })
    evidence = {fact.id: list(fact.evidence) for fact in kept}
    entities = [e for e in store.list_entities(owner) if e.status != "merged"]
    people = []
    places = []
    for ent in entities:
        item = {
            "id": ent.id,
            "name": ent.name,
            "relation_to_user": ent.relation_to_user,
            "closeness_tier": ent.closeness_tier,
            "closeness_suggested": ent.closeness_suggested,
            "tier_confirmed_at": ent.tier_confirmed_at or ("set" if ent.closeness_tier else None),
            "aliases": list(ent.aliases),
        }
        if ent.kind == "person":
            people.append(item)
        elif ent.kind == "place":
            places.append(item)
    person_facts = []
    for fact in kept:
        sub = subj_by_id.get(fact.subject_id)
        for fe in fact.entities:
            person_facts.append({
                "entity_id": fe.entity_id,
                "id": fact.id,
                "text": fact.text,
                "text_orig": fact.text_orig,
                "subject_id": fact.subject_id,
                "subject_path": sub.path if sub else "",
                "role": fe.role,
                "valid_from": fact.valid_from,
                "valid_to": fact.valid_to,
                "status": fact.status,
                "provenance": fact.provenance,
                "modality": getattr(fact, "modality", None),
                "event_at": getattr(fact, "event_at", None),
            })
    quarantine = store.get_quarantine_counts(owner) if hasattr(store, "get_quarantine_counts") else {}
    records = getattr(store, "records", {}).get(owner, {})
    marks: dict[str, str] = {}
    for rec in records.values():
        if getattr(rec, "erased_at", None):
            continue
        marks[rec.source] = max(marks.get(rec.source, ""), rec.at)
    rising = [
        (row["path"], row["recent"])
        for row in sorted(subject_rows, key=lambda r: (-r["recent"], r["path"]))
        if row["recent"]
    ]
    return _assemble(
        owner,
        evidence_limits="voice notes not read; history before import start not seen",
        held_back=dict(quarantine or {}),
        subjects=subject_rows,
        fact_rows=fact_rows,
        people=people,
        places=places,
        person_facts=person_facts,
        evidence=evidence,
        watermarks=sorted(marks.items()),
        forget_rule_counts={},
        rising=rising[:8],
    )


def cards_for(proj: Projection, *, cluster: str | None = None, person: str | None = None) -> list[dict[str, Any]]:
    leaves = proj.leaves
    if person:
        leaves = [leaf for leaf in leaves if leaf.entity_id == person and leaf.kind == "person"]
    elif cluster:
        leaves = [leaf for leaf in leaves if leaf.cluster == cluster]
    return [leaf.as_card() for leaf in leaves]


def person_card(db: Any, owner: str, entity_id: str) -> dict[str, Any] | None:
    """One person card. Indexed lookup, capped facts, no full-table read."""
    with db.connection() as conn:
        ent = conn.execute(
            """
            SELECT id, name, relation_to_user, closeness_tier, closeness_suggested, tier_confirmed_at
            FROM entities
            WHERE owner = %s AND id = %s AND erased_at IS NULL AND kind = 'person'
            """,
            (owner, entity_id),
        ).fetchone()
        if ent is None:
            return None
        rows = conn.execute(
            """
            SELECT f.id, f.text, f.text_orig, f.subject_id, s.path AS subject_path,
                   f.valid_from, f.valid_to, f.status, f.provenance, f.modality, f.event_at,
                   (
                       SELECT fe.role FROM fact_entities fe
                       WHERE fe.owner = f.owner AND fe.fact_id = f.id AND fe.entity_id = %s
                       LIMIT 1
                   ) AS role
            FROM facts f
            JOIN subjects s ON s.owner = f.owner AND s.id = f.subject_id
            WHERE f.owner = %s
              AND f.erased_at IS NULL
              AND f.status = ANY(%s)
              AND f.provenance IN ('user_supplied', 'provider_confirmed')
              AND s.sensitive_cat IS NULL
              AND split_part(s.path, '/', 1) NOT IN ('health', 'faith', 'wellbeing')
              AND EXISTS (
                  SELECT 1 FROM fact_entities fe
                  WHERE fe.owner = f.owner AND fe.fact_id = f.id AND fe.entity_id = %s
              )
            ORDER BY f.valid_from DESC, f.id ASC
            LIMIT 24
            """,
            (entity_id, owner, ["active", "superseded", "ended", "hypothesis"], entity_id),
        ).fetchall()
        limits_row = conn.execute("SELECT evidence_limits FROM owners WHERE id = %s", (owner,)).fetchone()
    tier = ent["closeness_tier"] if ent["tier_confirmed_at"] or ent["closeness_tier"] else None
    if ent["closeness_suggested"] and not ent["tier_confirmed_at"] and not ent["closeness_tier"]:
        tier = None
    leaf = Leaf(
        key=ent["id"],
        title=ent["name"],
        cluster="people-family",
        path=f"01-people/{TIER_DIR.get(tier, 'unconfirmed')}/{slug(ent['name'])}.md" if tier else f"01-people/{slug(ent['name'])}.md",
        kind="person",
        entity_id=ent["id"],
        relation=ent["relation_to_user"],
        tier=tier if ent["closeness_tier"] else None,
        tier_suggested=ent["closeness_suggested"],
    )
    roles = []
    for row in rows:
        pair = (row["subject_path"], row["role"] or "")
        if pair not in roles:
            roles.append(pair)
    leaf.shared_subjects = roles[:12]
    limits = limits_row["evidence_limits"] if limits_row else ""
    proj = Projection(owner, limits or "", {}, [], [], {}, [], [])
    _fill_leaf(leaf, [dict(r) for r in rows], people_only_stated=True, evidence={}, today=date.today())
    if ent["closeness_suggested"] and not ent["closeness_tier"]:
        leaf.noticed.append(Bullet(
            text=f"I noticed a {ent['closeness_suggested']} tie",
            fact_ids=[],
            provenance="inferred",
            as_of="",
        ))
        leaf.tier = None
        leaf.tier_suggested = ent["closeness_suggested"]
    card = leaf.as_card()
    card["evidence_limits"] = proj.evidence_limits
    return card
