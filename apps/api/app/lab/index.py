"""Embeddings + queries over the annotation layer.

Three vector spaces, one model: window summaries (what happened), annotation labels (topics,
projects, facts, loops - to merge near-duplicates and to search), and queries. Structured
questions (recurring topics, projects, people, open loops) are GROUP BYs over `lab_annotations`
with label clustering on top; free questions are cosine search. No numpy: pure Python is fine at
chat scale (thousands of rows).
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime

from app.config import settings

from . import llm, searchlib
from .store import Lab

CLUSTER_FACETS = {"topic": 0.80, "project": 0.78}
NEAR = 6  # messages either side of a project mention that still count as "about it"


# --------------------------------------------------------------------------- build vectors
def build_windows(lab: Lab) -> dict:
    """Embed the memory of every row / window that has no vector yet (memory text + its topics)."""
    model = settings.lab_embed_model
    stats = {"windows": 0}
    have_w = lab.vectors("window")
    todo = [w for w in lab.windows() if w["id"] not in have_w and not w["summary"].startswith("[summary withheld")]
    topics_by_win: dict[str, list[str]] = defaultdict(list)
    for a in lab.annotations("topic"):
        topics_by_win[a["window_id"]].append(a["label"])
    for i in range(0, len(todo), 32):
        chunk = todo[i : i + 32]
        texts = [f"{w['summary']} Topics: {', '.join(sorted(set(topics_by_win[w['id']])))}" for w in chunk]
        for w, v in zip(chunk, llm.embed(texts)):
            lab.put_vector("window", w["id"], model, v)
            stats["windows"] += 1
    lab.db.commit()
    return stats


def build(lab: Lab) -> dict:
    """Embed every window and every distinct annotation label that has no vector yet."""
    model = settings.lab_embed_model
    stats = {**build_windows(lab), "labels": 0}
    have_a = lab.vectors("annotation")
    by_norm: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for a in lab.annotations():
        if a["facet"] in ("topic", "project", "fact", "loop") and a["id"] not in have_a:
            by_norm[(a["facet"], a["norm"])].append(a)
    keys = list(by_norm)
    for i in range(0, len(keys), 32):
        chunk = keys[i : i + 32]
        for key, v in zip(chunk, llm.embed([by_norm[k][0]["label"] for k in chunk])):
            for a in by_norm[key]:
                lab.put_vector("annotation", a["id"], model, v)
            stats["labels"] += 1
    lab.db.commit()
    return stats


# --------------------------------------------------------------------------- helpers
def _week(ts: str) -> str:
    y, w, _ = datetime.fromisoformat(ts).isocalendar()
    return f"{y}-W{w:02d}"


def _mean(vs: list[list[float]]) -> list[float]:
    return [sum(c) / len(vs) for c in zip(*vs)]


def cluster_annotations(rows: list[dict], vecs: dict[str, list[float]], threshold: float) -> list[list[dict]]:
    """Greedy centroid clustering; most frequent labels seed clusters. Exact-norm grouping when no vectors."""
    freq = Counter(r["norm"] for r in rows)
    reps: dict[str, dict] = {}
    for r in rows:
        reps.setdefault(r["norm"], r)
    clusters: list[dict] = []  # {"norms": [...], "centroid": vec|None}
    for norm_label, _ in freq.most_common():
        rep = reps[norm_label]
        v = vecs.get(rep["id"])
        placed = False
        if v is not None:
            best, best_sim = None, threshold
            for c in clusters:
                if c["centroid"] is not None:
                    sim = llm.cosine(v, c["centroid"])
                    if sim >= best_sim:
                        best, best_sim = c, sim
            if best is not None:
                best["norms"].append(norm_label)
                best["vecs"].append(v)
                best["centroid"] = _mean(best["vecs"])
                placed = True
        if not placed:
            clusters.append({"norms": [norm_label], "vecs": [v] if v is not None else [], "centroid": v})
    member = {n: i for i, c in enumerate(clusters) for n in c["norms"]}
    grouped: list[list[dict]] = [[] for _ in clusters]
    for r in rows:
        grouped[member[r["norm"]]].append(r)
    return grouped


def _span(rows: list[dict]) -> dict:
    times = sorted(r["valid_from"] for r in rows)
    return {"first": times[0][:10], "last": times[-1][:10], "weeks": len({_week(t) for t in times}),
            "months": dict(sorted(Counter(t[:7] for t in times).items()))}


def _corpus_end(lab: Lab) -> datetime:
    ends = [w["t_end"] for w in lab.windows()]
    return datetime.fromisoformat(max(ends)) if ends else datetime.now()


# --------------------------------------------------------------------------- structured queries
def recurring_topics(lab: Lab, min_weeks: int = 3) -> list[dict]:
    rows = lab.annotations("topic")
    vecs = lab.vectors("annotation")
    out = []
    for group in cluster_annotations(rows, vecs, CLUSTER_FACETS["topic"]):
        labels = Counter(r["label"].lower() for r in group)
        span = _span(group)
        out.append({
            "topic": labels.most_common(1)[0][0],
            "variants": sorted(labels),
            "windows": len({r["window_id"] for r in group}),
            "chats": sorted({r["chat"] for r in group}),
            **span,
            "recurring": span["weeks"] >= min_weeks,
        })
    return sorted(out, key=lambda t: (-t["weeks"], -t["windows"]))


def projects(lab: Lab) -> list[dict]:
    rows = lab.annotations("project")
    vecs = lab.vectors("annotation")
    all_ann = lab.annotations()
    wins = {w["id"]: w for w in lab.windows()}
    end = _corpus_end(lab)
    out = []
    for group in cluster_annotations(rows, vecs, CLUSTER_FACETS["project"]):
        wids = {r["window_id"] for r in group}
        near = {(r["chat"], i) for r in group for e in r["evidence"] for i in range(e - NEAR, e + NEAR + 1)}
        # Related = another annotation citing a message within NEAR messages of this project's evidence.
        related = [a for a in all_ann if a["facet"] != "project" and any((a["chat"], e) in near for e in a["evidence"])]
        names = Counter(r["label"] for r in group)
        span = _span(group)
        loops = Counter(a["label"] for a in related if a["facet"] == "loop")
        out.append({
            "project": names.most_common(1)[0][0],
            "aliases": sorted(set(names) - {names.most_common(1)[0][0]}),
            "windows": len(wids),
            **span,
            "silent_days": (end - datetime.fromisoformat(span["last"])).days,
            "people": [n for n, _ in Counter(a["label"] for a in related if a["facet"] == "person").most_common(5)],
            "topics": [n for n, _ in Counter(a["label"].lower() for a in related if a["facet"] == "topic").most_common(5)],
            "open_loops": list(loops)[:5],
            "tone": dict(Counter(wins[w]["tone"] for w in wids)),
            "facts": [a["label"] for a in related if a["facet"] == "fact"][:5],
        })
    return sorted(out, key=lambda p: -p["windows"])


def person(lab: Lab, name: str) -> dict:
    needle = name.lower()
    hits = [a for a in lab.annotations("person") if needle in a["norm"]]
    wids = {a["window_id"] for a in hits}
    wins = {w["id"]: w for w in lab.windows()}
    related = [a for a in lab.annotations() if a["window_id"] in wids]
    return {
        "person": name,
        "roles": dict(Counter(a["detail"] for a in hits if a["detail"])),
        "windows": len(wids),
        **(_span(hits) if hits else {}),
        "tone_over_time": {w["t_start"][:7]: w["tone"] for w in sorted((wins[i] for i in wids), key=lambda w: w["t_start"])},
        "topics": [n for n, _ in Counter(a["label"].lower() for a in related if a["facet"] == "topic").most_common(8)],
        "open_loops": [a["label"] for a in related if a["facet"] == "loop"],
    }


def open_loops(lab: Lab) -> list[dict]:
    """Things still waiting: open follow-up questions (rows design) plus legacy 'loop' annotations."""
    end = _corpus_end(lab)
    rows = {r["id"]: r for r in lab.rows()}
    out = []
    for f in lab.followups("open"):
        r = rows.get(f["row_id"])
        if r and not r["sensitive"]:
            out.append({"loop": f["question"], "who": "unknown", "since": r["t_avg"][:10],
                        "age_days": (end - datetime.fromisoformat(r["t_avg"])).days, "chat": r["chat"],
                        "evidence": [r["first_idx"], r["last_idx"]], "row_id": r["id"], "attempts": f["attempts"]})
    for a in lab.annotations("loop"):
        out.append({"loop": a["label"], "who": a["detail"], "since": a["valid_from"][:10],
                    "age_days": (end - datetime.fromisoformat(a["valid_from"])).days, "chat": a["chat"],
                    "evidence": a["evidence"]})
    return sorted(out, key=lambda x: -x["age_days"])


def timeline(lab: Lab, since: str | None = None, until: str | None = None, limit: int | None = None) -> list[dict]:
    """Memory entries in a date range (YYYY-MM-DD), oldest first. Withheld rows never appear."""
    out = []
    for r in searchlib.usable(lab.rows(), since, until)[:limit]:
        out.append({"when": r["t_avg"][:16].replace("T", " "), "kind": r["kind"], "topics": r["topics"], "names": r["names"],
                    "memory": r["memory"], "sentiment": r["sentiment"], "followup": bool(r["followup"]),
                    "evidence": [r["first_idx"], r["last_idx"]]})
    return out


# --------------------------------------------------------------------------- free-text search
def search_annotations(lab: Lab, query: str, k: int = 8) -> list[dict]:
    """Pre-rows path (v1 windows / facts): cosine over window summaries and facts; lexical fallback."""
    wins = {w["id"]: w for w in lab.windows()}
    wv, av = lab.vectors("window"), lab.vectors("annotation")
    hits: list[dict] = []
    if wv or av:
        q = llm.embed([query], kind="query")[0]
        for wid, v in wv.items():
            hits.append({"kind": "window", "score": llm.cosine(q, v), "text": wins[wid]["summary"],
                         "when": wins[wid]["t_start"][:10], "chat": wins[wid]["chat"],
                         "evidence": [wins[wid]["first_idx"], wins[wid]["last_idx"]]})
        ann = {a["id"]: a for a in lab.annotations() if a["facet"] in ("fact", "loop", "project")}
        for aid, v in av.items():
            if aid in ann:
                a = ann[aid]
                hits.append({"kind": a["facet"], "score": llm.cosine(q, v), "text": a["label"],
                             "when": a["valid_from"][:10], "chat": a["chat"], "evidence": a["evidence"]})
    else:
        needle = query.lower()
        for a in lab.annotations():
            if needle in a["label"].lower():
                hits.append({"kind": a["facet"], "score": 1.0, "text": a["label"], "when": a["valid_from"][:10],
                             "chat": a["chat"], "evidence": a["evidence"]})
    return sorted(hits, key=lambda h: -h["score"])[:k]


# --------------------------------------------------------------------------- markdown
def render(title: str, rows: list[dict], fields: list[str]) -> str:
    lines = [f"# {title}", ""]
    for r in rows:
        head = r.get(fields[0])
        lines.append(f"## {head}")
        for f in fields[1:]:
            if r.get(f) not in (None, [], {}, ""):
                lines.append(f"- **{f}**: {r[f]}")
        lines.append("")
    return "\n".join(lines)


def search(lab: Lab, query: str, k: int = 8, since: str | None = None, until: str | None = None) -> list[dict]:
    """Semantic + lexical memory search over rows (hybrid, non-English queries translated). Date filters are
    YYYY-MM-DD. Falls back to the annotation search for databases that have no rows."""
    rows = searchlib.usable(lab.rows(), since, until)
    if not rows:
        return search_annotations(lab, query, k) if not (since or until) else []
    ranked, mode = searchlib.search_rows(rows, lab.vectors("window"), query, k=k)
    by_id = {r["id"]: r for r in rows}
    return [{"kind": by_id[i]["kind"], "score": round(score, 3), "text": by_id[i]["memory"], "when": by_id[i]["t_avg"][:10],
             "chat": by_id[i]["chat"], "topics": by_id[i]["topics"], "followup": bool(by_id[i]["followup"]),
             "evidence": [by_id[i]["first_idx"], by_id[i]["last_idx"]], "via": mode} for i, score in ranked]
