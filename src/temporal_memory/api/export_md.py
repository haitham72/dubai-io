"""Quest-style Markdown tree export & ZIP endpoint (WP-B).

Ported from: G:\\Haitham\\lab-data\\memory-bakeoff\\weekbench\\export.py
Produces the exact tree in planaudit.md v2.1 §3.1 generated from DB / GraphStore.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import io
import re
from typing import Any
import zipfile

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from temporal_memory.api.vault import AuthContext, call_opt, get_store, require_owner_access
from temporal_memory.models import Entity, EntitySubject, Fact, GraphStore, Link, Milestone, Subject

_DEFAULT_STORE: GraphStore | None = None


def set_default_store(store: GraphStore | None) -> None:
    """Register fallback GraphStore when render(owner) is called without store arg."""
    global _DEFAULT_STORE
    _DEFAULT_STORE = store


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:60] or "item"


def _fmt_bullet(f: Fact, entities_by_id: dict[str, Entity]) -> str:
    change = ""
    if f.status in ("superseded", "ended"):
        change = f"  _(was true until {f.valid_to or '?'}; {f.status})_"
    orig = f'  ["{f.text_orig}"]' if f.text_orig else ""
    src = ", ".join(f.evidence[:3]) or f.id
    return f"- {f.valid_from or '?'} · {f.text}{orig}{change}  `src: {src}`"


def render(owner: str, *, store: GraphStore | None = None) -> dict[str, str]:
    """Render the full Quest-style markdown tree (`relative/path.md -> content`)."""
    st: Any = store or _DEFAULT_STORE
    if st is None:
        raise RuntimeError("No GraphStore configured for api.export_md.render")

    out: dict[str, str] = {}
    facts = [f for f in st.visible_facts(owner, limit=10_000) if f.status != "history"]
    entities: list[Entity] = [e for e in call_opt(st, "list_entities", owner, default=[]) if e.status != "merged"]
    subjects: list[Subject] = call_opt(st, "list_subjects", owner, default=[])
    ent_subjs: list[EntitySubject] = call_opt(st, "list_entity_subjects", owner, default=[])
    links: list[Link] = call_opt(st, "list_links", owner, default=[])
    milestones: list[Milestone] = call_opt(st, "list_milestones", owner, default=[])
    quarantine: dict[str, int] = call_opt(st, "get_quarantine_counts", owner, default={}) or {}
    user_md: str = call_opt(st, "get_user_md", owner, default="") or ""
    evidence_limits: str = call_opt(
        st,
        "get_evidence_limits",
        owner,
        default="voice notes not read; records prior to import start not seen",
    )

    by_id: dict[str, Entity] = {e.id: e for e in entities}
    subj_by_id: dict[str, Subject] = {s.id: s for s in subjects}
    visible_ids = {f.id for f in facts}

    # Group regular facts (non-hypothesis) vs open hypotheses
    regular = [f for f in facts if f.status != "hypothesis"]
    hypotheses = [f for f in facts if f.status == "hypothesis"]

    # 1. USER.md
    if user_md.strip():
        out["USER.md"] = user_md.rstrip() + "\n"
    else:
        sections = [
            "Identity", "Personality", "Values", "Strengths & Tensions",
            "Interests", "Drive", "Relationships",
        ]
        u_lines = [f"# USER Profile ({owner})", ""]
        for sec in sections:
            u_lines.append(f"## {sec}")
            if sec == "Relationships":
                people_rel = [e for e in entities if e.kind == "person" and e.relation_to_user not in (None, "self")]
                if people_rel:
                    for p in people_rel[:6]:
                        u_lines.append(f"- {p.name} ({p.relation_to_user}) `[people/{slug(p.name)}.md]`")
                else:
                    u_lines.append("- _(unconfirmed)_")
            else:
                u_lines.append("- _(pending weekly reflect)_")
            u_lines.append("")
        out["USER.md"] = "\n".join(u_lines)

    # 2. subjects/<theme>/... (_subject.md + <topic>.md)
    facts_by_subject: dict[str, list[Fact]] = defaultdict(list)
    for f in regular:
        facts_by_subject[f.subject_id].append(f)

    es_by_subject: dict[str, list[EntitySubject]] = defaultdict(list)
    es_by_entity: dict[str, list[EntitySubject]] = defaultdict(list)
    for es in ent_subjs:
        es_by_subject[es.subject_id].append(es)
        es_by_entity[es.entity_id].append(es)

    children_by_parent: dict[str | None, list[Subject]] = defaultdict(list)
    for s in subjects:
        children_by_parent[s.parent_id].append(s)

    index_groups: dict[str, list[str]] = defaultdict(list)
    theme_docs: dict[str, dict[str, Any]] = defaultdict(lambda: {"topics": [], "people": [], "count": 0, "updated": ""})

    for sid, s_facts in sorted(facts_by_subject.items()):
        subj = subj_by_id.get(sid)
        raw_path = (subj.path if subj else "background/general").strip("/")
        parts = [slug(p) for p in raw_path.split("/") if p] or ["general"]
        theme = parts[0]
        # Canon Rule 9: health/ appears only when user_supplied facts exist
        if theme == "health":
            s_facts = [f for f in s_facts if f.provenance == "user_supplied"]
            if not s_facts:
                continue
        topic_rel = "/".join(parts[1:]) if len(parts) > 1 else parts[0]
        md_path = f"subjects/{theme}/{topic_rel}.md"
        label = subj.label if subj else topic_rel.replace("-", " ").title()
        bullets = [_fmt_bullet(f, by_id) for f in sorted(s_facts, key=lambda x: (x.valid_from or "", x.id))]
        latest = max((f.valid_from or "" for f in s_facts), default="")
        front = (
            f"---\nname: {label}\npath: {raw_path}\nfacts: {len(s_facts)}\nupdated: {latest or '?'}\n---\n"
        )
        out[md_path] = front + "\n".join(bullets) + "\n"
        index_groups[theme].append(f"- [{label}]({md_path}) — {len(s_facts)} facts · updated {latest or '?'}")
        theme_docs[theme]["topics"].append((label, md_path, len(s_facts)))
        theme_docs[theme]["count"] += len(s_facts)
        theme_docs[theme]["updated"] = max(theme_docs[theme]["updated"], latest)
        for es in es_by_subject.get(sid, []):
            ent = by_id.get(es.entity_id)
            if ent:
                theme_docs[theme]["people"].append(f"{ent.name} ({es.role or ent.kind})")

    for theme, info in sorted(theme_docs.items()):
        t_lines = [
            f"# {theme.replace('-', ' ').title()}", "",
            f"- **Facts:** {info['count']} · **Last updated:** {info['updated'] or '?'}",
            f"- **People involved:** {', '.join(sorted(set(info['people']))) or 'none'}", "",
            "## Topics",
            *(f"- [{lbl}]({p}) ({cnt})" for lbl, p, cnt in sorted(info["topics"])),
            "",
        ]
        out[f"subjects/{theme}/_subject.md"] = "\n".join(t_lines)

    # 3. people/, places/, orgs/
    facts_by_entity: dict[str, list[Fact]] = defaultdict(list)
    for f in regular:
        for fe in f.entities:
            facts_by_entity[fe.entity_id].append(f)

    for ent in sorted(entities, key=lambda x: x.name):
        e_facts = sorted(facts_by_entity.get(ent.id, []), key=lambda x: (x.valid_from or "", x.id))
        e_slug = slug(ent.name)
        subj_roles = []
        for es in es_by_entity.get(ent.id, []):
            s_lbl = subj_by_id[es.subject_id].label if es.subject_id in subj_by_id else es.subject_id
            subj_roles.append(f"- {s_lbl}: {es.role or 'mentioned'} ({es.fact_count} facts)")

        if ent.kind == "person":
            if ent.relation_to_user == "self":
                continue
            md_path = f"people/{e_slug}.md"
            head = [
                "---",
                f"name: {ent.name}",
                f"relationship: {ent.relation_to_user}",
                f"closeness: {ent.closeness_tier or 'T3'}",
                f"aliases: {', '.join(ent.aliases)}",
                f"last_contact: {ent.last_seen or '?'}",
                "---",
                f"# {ent.name}",
                "",
                "## Subjects & Roles",
                *(subj_roles or ["- _(none yet)_"]),
                "",
                "## Timeline",
                *([_fmt_bullet(f, by_id) for f in e_facts] or ["- _(no facts yet)_"]),
                "",
                "## Open Loops",
                *([f"- [?] {h.text}" for h in hypotheses if any(fe.entity_id == ent.id for fe in h.entities)] or ["- _(none)_"]),
                "",
                f"_Evidence limits: {evidence_limits}_",
                "",
            ]
            out[md_path] = "\n".join(head)
            index_groups["people"].append(f"- [{ent.name}]({md_path}) — {ent.relation_to_user or 'contact'} · {len(e_facts)} facts")
        elif ent.kind == "place":
            md_path = f"places/{e_slug}.md"
            lines = [
                f"# {ent.name}", "",
                f"- **Visits / mentions:** {len(e_facts)} · **Last seen:** {ent.last_seen or '?'}",
                "", "## Linked Subjects", *(subj_roles or ["- _(none)_"]),
                "", "## Notes", *([_fmt_bullet(f, by_id) for f in e_facts] or ["- _(none)_"]), "",
            ]
            out[md_path] = "\n".join(lines)
            index_groups["places"].append(f"- [{ent.name}]({md_path}) — {len(e_facts)} facts")
        elif ent.kind == "org":
            md_path = f"orgs/{e_slug}.md"
            people_there = [
                by_id[ln.src].name if ln.dst == ent.id and ln.src in by_id else by_id[ln.dst].name
                for ln in links
                if (ln.dst == ent.id and ln.src in by_id) or (ln.src == ent.id and ln.dst in by_id)
            ]
            lines = [
                f"# {ent.name}", "",
                f"- **Relation:** {ent.relation_to_user or 'org'}",
                f"- **People there:** {', '.join(sorted(set(people_there))) or 'none'}",
                "", "## Linked Subjects", *(subj_roles or ["- _(none)_"]),
                "", "## Notes", *([_fmt_bullet(f, by_id) for f in e_facts] or ["- _(none)_"]), "",
            ]
            out[md_path] = "\n".join(lines)
            index_groups["orgs"].append(f"- [{ent.name}]({md_path}) — {len(e_facts)} facts")

    # 4. quests/<slug>.md
    ms_by_subj: dict[str, list[Milestone]] = defaultdict(list)
    for m in milestones:
        kept_ev = [fid for fid in m.evidence_fact_ids if fid in visible_ids]
        if m.evidence_fact_ids and not kept_ev:
            continue
        ms_by_subj[m.subject_id].append(m)

    for s in subjects:
        if s.kind != "goal":
            continue
        q_slug = slug(s.label)
        md_path = f"quests/{q_slug}.md"
        q_ms = ms_by_subj.get(s.id, [])
        done = [m for m in q_ms if m.state == "done"]
        prog = [m for m in q_ms if m.state == "in_progress"]
        plan = [m for m in q_ms if m.state == "planned"]
        lines = [
            f"# Quest: {s.label}", "",
            f"- **Status:** {s.status} ({'hypothesis — I noticed…' if s.status == 'candidate' else 'active'})",
            f"- **Momentum:** {len(done)} done · {len(prog)} in progress · {len(plan)} planned", "",
            "## Milestones",
            *([f"- [x] {m.title} `ev: {', '.join(m.evidence_fact_ids)}`" for m in done]),
            *([f"- [~] {m.title} `ev: {', '.join(m.evidence_fact_ids)}`" for m in prog]),
            *([f"- [ ] {m.title} `ev: {', '.join(m.evidence_fact_ids)}`" for m in plan]),
            "",
        ]
        if not q_ms:
            lines.append("- _(no milestones yet)_")
        out[md_path] = "\n".join(lines)
        index_groups["quests"].append(f"- [{s.label}]({md_path}) — {len(q_ms)} milestones")

    # 5. timeline/<YYYY-MM>.md
    by_month: dict[str, list[Fact]] = defaultdict(list)
    for f in regular:
        ym = (f.valid_from or "0000-00")[:7]
        by_month[ym].append(f)
    for ym, m_facts in sorted(by_month.items()):
        m_lines = [f"# Timeline — {ym}", "", *[_fmt_bullet(f, by_id) for f in sorted(m_facts, key=lambda x: (x.valid_from or "", x.id))], ""]
        out[f"timeline/{ym}.md"] = "\n".join(m_lines)

    # 6. noticed.md (open hypotheses awaiting Confirm / Not true)
    n_lines = ["# Noticed (hypotheses awaiting your confirmation)", ""]
    if hypotheses:
        for h in sorted(hypotheses, key=lambda x: (x.valid_from or "", x.id)):
            txt = h.text if h.text.startswith("I noticed") else f"I noticed {h.text}"
            n_lines.append(f"- {txt} `[Confirm / Edit / Not true / Forget]`  `src: {', '.join(h.evidence[:3]) or h.id}`")
    else:
        n_lines.append("- _(no open hypotheses)_")
    n_lines.append("")
    out["noticed.md"] = "\n".join(n_lines)

    # 7. held-back.md (sensitive category + count ONLY, never text)
    h_lines = ["# Held Back (sensitive categories — counts only, Rule 9)", ""]
    if quarantine:
        for cat, cnt in sorted(quarantine.items()):
            h_lines.append(f"- **{cat}:** {cnt} item(s) held back `[Review in app]`")
    else:
        h_lines.append("- _(0 items held back)_")
    h_lines.append("")
    out["held-back.md"] = "\n".join(h_lines)

    # 8. MEMORIES.md index
    idx_lines = [f"# Memories ({owner})", ""]
    for sec in sorted(index_groups):
        idx_lines.append(f"## {sec.replace('-', ' ').title()}")
        idx_lines.extend(sorted(index_groups[sec]))
        idx_lines.append("")
    idx_lines.extend(["## Review & Safety", "- [Noticed Hypotheses](noticed.md)", "- [Held Back Counts](held-back.md)", ""])
    out["MEMORIES.md"] = "\n".join(idx_lines)
    return out


router = APIRouter(prefix="/v1/owners/{owner}", tags=["export"])


@router.get("/export/md.zip")
def export_md_zip(
    owner: str,
    _: AuthContext = Depends(require_owner_access),
    store: GraphStore = Depends(get_store),
) -> StreamingResponse:
    try:
        files = render(owner, store=store)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Export failed: {exc}") from exc

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel_path, content in sorted(files.items()):
            zf.writestr(f"memory/{rel_path}", content.encode("utf-8"))
    buf.seek(0)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    headers = {"Content-Disposition": f'attachment; filename="{slug(owner)}-memory-{ts}.zip"'}
    return StreamingResponse(buf, media_type="application/zip", headers=headers)
