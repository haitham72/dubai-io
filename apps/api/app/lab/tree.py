"""Topic tree + relationship graph, rendered as markdown (Mermaid) and graph.json for a later bubble UI.

Built only from stored annotations - no re-read of the chat. The model is used once more, on
*labels only* (never message text): it files each merged topic under one of the life themes and a
short group name, giving Theme -> Group -> Topic. Edges come from co-occurrence: two nodes that
cite messages in the same 10-message bucket are linked, weight = number of shared buckets.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from itertools import combinations

from . import llm, tree_assign
from .index import CLUSTER_FACETS, _span, cluster_annotations
from .sensitive import screen
from .store import Lab

BUCKET = 10
BATCH = 40
THEMES = tree_assign.THEMES


def topic_clusters(lab: Lab) -> list[dict]:
    rows = lab.annotations("topic")
    out = []
    for group in cluster_annotations(rows, lab.vectors("annotation"), CLUSTER_FACETS["topic"]):
        labels = Counter(r["label"].lower() for r in group)
        out.append({
            "id": "t:" + labels.most_common(1)[0][0],
            "label": labels.most_common(1)[0][0],
            "variants": sorted(labels),
            "mentions": len(group),
            "buckets": {(r["chat"], e // BUCKET) for r in group for e in r["evidence"]},
            **_span(group),
        })
    return sorted(out, key=lambda c: (-c["mentions"], c["label"]))


def build(lab: Lab, me: str = "", max_topics: int = 120, min_edge: int = 2) -> dict:
    """Raises LabLLMError when the privacy screen cannot run: no unscreened tree is ever produced."""
    from .extract import norm

    clusters = topic_clusters(lab)[:max_topics]
    project_rows = lab.annotations("project")
    blocked = screen([v for c in clusters for v in c["variants"]] + [r["label"] for r in project_rows])
    withheld: Counter = Counter()
    kept_clusters = []
    for c in clusters:
        cat = next((blocked[v] for v in c["variants"] if v in blocked), None)
        if cat:
            withheld[cat] += 1
        else:
            kept_clusters.append(c)
    clusters = kept_clusters
    themes = tree_assign.assign([c["label"] for c in clusters])
    tree: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for c in clusters:
        theme, group = themes[c["label"]]
        c["theme"], c["group"] = theme, group
        tree[theme][group].append(c)

    # Graph nodes: topics, people, projects. Weight = mentions. The owner is the centre, never a node;
    # people carry no model-guessed role (it was wrong for a mother: "partner or close friend").
    nodes: dict[str, dict] = {}
    buckets: dict[tuple, set] = defaultdict(set)

    def put(node_id: str, kind: str, label: str, weight: int, **extra):
        nodes[node_id] = {"id": node_id, "kind": kind, "label": label, "weight": weight, **extra}

    for c in clusters[:40]:
        put(c["id"], "topic", c["label"], c["mentions"], theme=c["theme"], group=c["group"])
        for b in c["buckets"]:
            buckets[b].add(c["id"])
    me_n = norm(me)
    for facet, cap in (("person", 15), ("project", 10)):
        rows = [r for r in lab.annotations(facet)
                if r["label"] not in blocked and not (facet == "person" and me_n and norm(r["label"]) in {me_n, "self", "owner"})]
        count = Counter(r["norm"] for r in rows)
        evid = defaultdict(set)
        for r in rows:
            evid[r["norm"]] |= {(r["chat"], e // BUCKET) for e in r["evidence"]}
        labels = {r["norm"]: r["label"] for r in rows}
        for n, w in count.most_common(cap):
            nid = f"{facet[0]}:{n}"
            put(nid, facet, labels[n], w)
            for b in evid[n]:
                buckets[b].add(nid)
    edges: Counter = Counter()
    for members in buckets.values():
        for a, b in combinations(sorted(members), 2):
            edges[(a, b)] += 1
    kept = [{"a": a, "b": b, "weight": w} for (a, b), w in edges.most_common(80) if w >= min_edge and a in nodes and b in nodes]
    return {"tree": {t: dict(g) for t, g in tree.items()}, "nodes": list(nodes.values()), "edges": kept,
            "topics": len(clusters), "withheld": dict(withheld)}


# ----------------------------------------------------------------------------- markdown
def _txt(s: str) -> str:
    return re.sub(r"[\"()\[\]{}<>#;:`]", "", s).strip() or "-"


def render_tree(data: dict) -> str:
    tree = data["tree"]
    order = sorted(tree, key=lambda t: -sum(c["mentions"] for g in tree[t].values() for c in g))
    lines = ["# Topic tree", "",
             "Theme → group → topic. Counts are mentions; every topic is a hypothesis with evidence in the database "
             "(`Confirm / Edit / Not true / Forget`).", ""]
    for theme in order:
        groups = tree[theme]
        total = sum(c["mentions"] for g in groups.values() for c in g)
        lines += [f"## {theme} · {total}", ""]
        for group, topics in sorted(groups.items(), key=lambda kv: -sum(c["mentions"] for c in kv[1])):
            lines.append(f"### {group} · {sum(c['mentions'] for c in topics)}")
            for c in topics:
                tag = " · recurring" if c["weeks"] >= 3 else ""
                lines.append(f"- **{c['label']}** ×{c['mentions']} · {c['first']} → {c['last']} · {c['weeks']} wk{tag}")
            lines.append("")
    lines += ["## Mindmap", "", "```mermaid", "mindmap", "  root((You))"]
    for theme in order:
        lines.append(f"    {_txt(theme)}")
        for group, topics in sorted(tree[theme].items(), key=lambda kv: -sum(c["mentions"] for c in kv[1]))[:6]:
            lines.append(f"      {_txt(group)}")
            for c in topics[:5]:
                lines.append(f"        {_txt(c['label'])}")
    lines += ["```", ""]
    return "\n".join(lines)


def render_graph(data: dict) -> str:
    nodes, edges = data["nodes"], data["edges"]
    ids = {n["id"]: f"n{i}" for i, n in enumerate(nodes)}
    lines = ["# Graph", "",
             "Nodes sized by mentions (shown as ×count); a line means two things were discussed in the same stretch of "
             "messages (weight = shared stretches).", "", "```mermaid", "graph LR"]
    shape = {"topic": ('(["', '"])'), "person": ('(("', '"))'), "project": ('[["', '"]]')}
    for n in nodes:
        o, c = shape[n["kind"]]
        lines.append(f"  {ids[n['id']]}{o}{_txt(n['label'])} ×{n['weight']}{c}")
    for e in edges:
        lines.append(f"  {ids[e['a']]} ---|{e['weight']}| {ids[e['b']]}")
    lines += ["```", "", "## People", ""]
    for n in sorted((n for n in nodes if n["kind"] == "person"), key=lambda n: -n["weight"]):
        lines.append(f"- **{n['label']}** ×{n['weight']}")
    lines += ["", "## Projects", ""]
    for n in sorted((n for n in nodes if n["kind"] == "project"), key=lambda n: -n["weight"]):
        lines.append(f"- **{n['label']}** ×{n['weight']}")
    return "\n".join(lines) + "\n"
