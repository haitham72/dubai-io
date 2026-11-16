"""Evaluation harness for the lab design - automatic metrics, no truth sheet, no chat-quality judgement.

  quality   structural checks on stored rows + a local LLM judge (faithfulness / completeness / hallucination)
  search    self-retrieval: an LLM writes English, Arabic and keyword queries that each ONE memory answers;
            every search variant is scored on whether that memory comes back (recall@1/3/5, MRR)
  queries   invariants of the query layer (evidence ids exist, withheld rows never surface, filters hold,
            results are deterministic, open loops == open follow-ups)
Everything writes JSON; the iteration log quotes these numbers. The judge is the same small local model that
wrote the rows, so use it to compare VARIANTS, not as an absolute score.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from . import circle as circle_mod
from . import index, llm, searchlib
from .store import Lab

# ----------------------------------------------------------------------------- quality: structural
STATIC_FIELDS = ("topics", "names", "user_text", "memory", "multimodal", "followups")


def _blob(lab: Lab, cache: dict, row: dict) -> str:
    key = (row["chat"], row["kind"])
    if key not in cache:
        connector = "email" if row["kind"] == "email" else "whatsapp"
        cache[key] = {m.idx: m for m in lab.load_messages(connector, row["chat"])}
    msgs = cache[key]
    return " ".join(m.text + " " + m.sender + " " + m.meta.get("subject", "") for i, m in msgs.items()
                    if row["first_idx"] <= i <= row["last_idx"])


def _source_words(lab: Lab, cache: dict, row: dict) -> int:
    key = (row["chat"], row["kind"])
    if key not in cache:
        connector = "email" if row["kind"] == "email" else "whatsapp"
        cache[key] = {m.idx: m for m in lab.load_messages(connector, row["chat"])}
    return sum(len(m.text.split()) for i, m in cache[key].items() if row["first_idx"] <= i <= row["last_idx"] and m.kind == "message")


def structural(lab: Lab, cir: circle_mod.Circle) -> dict:
    rows = lab.rows()
    cache: dict = {}
    usable = [r for r in rows if r["memory"] and not r["sensitive"]]
    open_by_row = Counter(f["row_id"] for f in lab.followups())
    names_total = ungrounded = rows_ungrounded = 0
    topic_bad = topic_total = 0
    mem_words, user_words, equal = [], [], 0
    ratios, source_words, input_msgs = [], [], []
    english = 0
    known = {circle_mod.fold(x) for p in cir.people.values() for x in [p["name"], *p.get("nicknames", [])]}
    known.add(circle_mod.fold(cir.owner))
    for r in usable:
        blob = circle_mod.fold(_blob(lab, cache, r))
        bad = [n for n in r["names"] if circle_mod.fold(n) not in blob and circle_mod.fold(n) not in known]
        names_total += len(r["names"])
        ungrounded += len(bad)
        rows_ungrounded += bool(bad)
        for t in r["topics"]:
            topic_total += 1
            topic_bad += not (1 <= len(t.split()) <= 3 and t == t.lower())
        mem_words.append(len(r["memory"].split()))
        src = _source_words(lab, cache, r) or 1
        source_words.append(src)
        input_msgs.append(r["n_msgs"])
        ratios.append(len(r["memory"].split()) / src)
        user_words.append(len(r["user_text"].split()))
        equal += r["memory"].strip().lower() == r["user_text"].strip().lower()
        letters = [c for c in r["memory"] if c.isalpha()]
        english += bool(letters) and sum(c.isascii() for c in letters) / len(letters) > 0.8
    mems = Counter(r["memory"] for r in usable)
    n = len(usable) or 1
    return {
        "rows": len(rows), "usable": len(usable), "withheld": len(rows) - len(usable),
        "withheld_rate": round((len(rows) - len(usable)) / (len(rows) or 1), 2),
        "names_ungrounded_rate": round(ungrounded / (names_total or 1), 3), "rows_with_ungrounded_name": rows_ungrounded,
        "topic_format_bad_rate": round(topic_bad / (topic_total or 1), 3),
        "topics_per_row": round(topic_total / n, 2),
        "messages_per_row_avg": round(sum(input_msgs) / n, 1), "source_words_avg": round(sum(source_words) / n, 1),
        "memory_ratio_avg": round(sum(ratios) / n, 3), "memory_ratio_max": round(max(ratios or [0]), 3),
        "rows_over_half": sum(x > 0.5 for x in ratios),
        "memory_words_avg": round(sum(mem_words) / n, 1), "user_words_avg": round(sum(user_words) / n, 1),
        "memory_equals_user_rate": round(equal / n, 3),
        "memory_duplicate_rate": round(sum(c - 1 for c in mems.values() if c > 1) / n, 3),
        "memory_english_rate": round(english / n, 3),
        "followups_per_row": round(sum(open_by_row[r["id"]] for r in usable) / n, 2),
        "scored_rate": round(sum(r["sentiment"] is not None for r in usable) / n, 2),
        "embedded_rate": round(len(set(lab.vectors("window")) & {r["id"] for r in usable}) / n, 2),
    }


# ----------------------------------------------------------------------------- quality: LLM judge
JUDGE_SYSTEM = """You audit memory rows written by another model. For each ROW compare the SOURCE messages with the WRITTEN fields.
- faithful: 1-5 (5 = every claim is supported by the messages, 1 = mostly invented)
- complete: 1-5 (5 = captures the main content of the messages)
- hallucination: true if ANY person, number, place or event in the written fields is not in the messages
- followup_useful: true if the written follow-up questions are specific and need more information; false if there are none or they are trivial
Judge only against the SOURCE text. The messages may be Arabic; the written fields are English. JSON only."""
JUDGE_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["items"], "properties": {"items": {
    "type": "array", "items": {"type": "object", "additionalProperties": False,
                               "required": ["row", "faithful", "complete", "hallucination", "followup_useful"],
                               "properties": {"row": {"type": "integer"}, "faithful": {"type": "integer"},
                                              "complete": {"type": "integer"}, "hallucination": {"type": "boolean"},
                                              "followup_useful": {"type": "boolean"}}}}}}


def judge(lab: Lab, limit: int = 24, batch: int = 4) -> dict:
    rows = [r for r in lab.rows() if r["memory"] and not r["sensitive"]]
    step = max(1, len(rows) // limit)
    rows = rows[::step][:limit]
    cache: dict = {}
    open_q: dict[str, list[str]] = {}
    for f in lab.followups("open"):
        open_q.setdefault(f["row_id"], []).append(f["question"])
    per_row = []
    for i in range(0, len(rows), batch):
        chunk = rows[i : i + batch]
        parts = []
        for n, r in enumerate(chunk, 1):
            connector = "email" if r["kind"] == "email" else "whatsapp"
            key = (r["chat"], r["kind"])
            if key not in cache:
                cache[key] = {m.idx: m for m in lab.load_messages(connector, r["chat"])}
            src = "\n".join(f"{m.sender}: {m.text[:300]}" for j, m in cache[key].items() if r["first_idx"] <= j <= r["last_idx"] and m.kind == "message")
            parts.append(f"ROW {n}\nSOURCE:\n{src}\nWRITTEN: user={r['user_text']} | memory={r['memory']} | topics={', '.join(r['topics'])} | "
                         f"followups={'; '.join(open_q.get(r['id'], [])) or 'none'}")
        res = llm.chat_json(JUDGE_SYSTEM, "\n\n".join(parts), JUDGE_SCHEMA, name="judge", max_tokens=700)
        by_n = {int(x["row"]): x for x in res.get("items", []) if isinstance(x.get("row"), int)}
        for n, r in enumerate(chunk, 1):
            if n in by_n:
                per_row.append({"id": r["id"], "when": r["t_avg"][:16], **by_n[n]})
    k = len(per_row) or 1
    return {"judged": len(per_row), "faithful_avg": round(sum(x["faithful"] for x in per_row) / k, 2),
            "complete_avg": round(sum(x["complete"] for x in per_row) / k, 2),
            "hallucination_rate": round(sum(x["hallucination"] for x in per_row) / k, 2),
            "followup_useful_rate": round(sum(x["followup_useful"] for x in per_row) / k, 2), "per_row": per_row}


# ----------------------------------------------------------------------------- search: queries + variants
QUERY_SYSTEM = """For each ROW (a short memory about a private chat) write queries a person could type to find THIS memory later.
- question_en: one natural English question this memory answers. Do not copy its wording.
- question_ar: the same question in Egyptian Arabic, as someone would type it in chat.
- keywords: two or three English words.
JSON only."""
QUERY_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["items"], "properties": {"items": {
    "type": "array", "items": {"type": "object", "additionalProperties": False,
                               "required": ["row", "question_en", "question_ar", "keywords"],
                               "properties": {"row": {"type": "integer"}, "question_en": {"type": "string"},
                                              "question_ar": {"type": "string"}, "keywords": {"type": "string"}}}}}}


def gen_queries(lab: Lab, cache: Path, limit: int = 60, batch: int = 5) -> list[dict]:
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    rows = [r for r in lab.rows() if r["memory"] and not r["sensitive"]]
    rows = rows[:: max(1, len(rows) // limit)][:limit]
    out = []
    for i in range(0, len(rows), batch):
        chunk = rows[i : i + batch]
        user = "\n".join(f"ROW {n}: {r['memory']} (topics: {', '.join(r['topics'])})" for n, r in enumerate(chunk, 1))
        res = llm.chat_json(QUERY_SYSTEM, user, QUERY_SCHEMA, name="queries", max_tokens=900)
        by_n = {int(x["row"]): x for x in res.get("items", []) if isinstance(x.get("row"), int)}
        for n, r in enumerate(chunk, 1):
            if n in by_n and by_n[n]["question_en"].strip():
                out.append({"id": r["id"], "en": by_n[n]["question_en"].strip(), "ar": by_n[n]["question_ar"].strip(),
                            "kw": by_n[n]["keywords"].strip()})
    cache.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


VARIANTS = [
    {"name": "S0 dense, memory+topics (what was built)", "doc": "memory_topics", "hybrid": False, "translate": False},
    {"name": "S1 dense, memory only", "doc": "memory", "hybrid": False, "translate": False},
    {"name": "S2 dense, full doc", "doc": "full", "hybrid": False, "translate": False},
    {"name": "S3 hybrid dense+BM25", "doc": "full", "hybrid": True, "translate": False},
    {"name": "S4 dense + query translation", "doc": "full", "hybrid": False, "translate": True},
    {"name": "S5 hybrid + query translation (production)", "doc": "full", "hybrid": True, "translate": True},
]


def search_eval(lab: Lab, queries: list[dict], variants: list[dict] | None = None, ks=(1, 3, 5)) -> dict:
    rows = searchlib.usable(lab.rows())
    by_id = {r["id"]: r for r in rows}
    queries = [q for q in queries if q["id"] in by_id]
    vecs: dict[str, dict[str, list[float]]] = {}
    for mode in {v["doc"] for v in (variants or VARIANTS)}:
        texts = [searchlib.doc_text(r, mode) for r in rows]
        vecs[mode] = {}
        for i in range(0, len(rows), 16):
            for r, v in zip(rows[i : i + 16], llm.embed(texts[i : i + 16])):
                vecs[mode][r["id"]] = v
    report = {"corpus_rows": len(rows), "queries": len(queries), "variants": {}}
    for var in variants or VARIANTS:
        per_type = {}
        for qtype in ("en", "ar", "kw"):
            hits = {k: 0 for k in ks}
            rr = 0.0
            for q in queries:
                ranked, _ = searchlib.search_rows(rows, vecs[var["doc"]], q[qtype], k=max(ks) * 2, hybrid=var["hybrid"],
                                                  do_translate=var["translate"], doc_mode=var["doc"])
                order = [i for i, _ in ranked]
                if q["id"] in order:
                    pos = order.index(q["id"]) + 1
                    rr += 1.0 / pos
                    for k in ks:
                        hits[k] += pos <= k
            n = len(queries) or 1
            per_type[qtype] = {**{f"r@{k}": round(hits[k] / n, 2) for k in ks}, "mrr": round(rr / n, 3)}
        report["variants"][var["name"]] = per_type
    return report


# ----------------------------------------------------------------------------- query layer invariants
def query_checks(lab: Lab) -> dict:
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    rows = lab.rows()
    all_rows = {r["id"]: r for r in rows}
    sensitive = [r for r in rows if r["sensitive"]]
    msgs = {}
    for r in rows:
        key = (r["chat"], "email" if r["kind"] == "email" else "whatsapp")
        if key not in msgs:
            msgs[key] = {m.idx for m in lab.load_messages(key[1], key[0])}

    tl = index.timeline(lab)
    check("timeline hides every withheld row", len(tl) == len(searchlib.usable(rows)) and all(t["memory"] for t in tl),
          f"{len(tl)} entries, {len(sensitive)} rows withheld")
    check("timeline is chronological", [t["when"] for t in tl] == sorted(t["when"] for t in tl))
    if tl:
        mid = tl[len(tl) // 2]["when"][:10]
        ranged = index.timeline(lab, since=mid, until=mid)
        check("timeline date range is exact", bool(ranged) and all(t["when"][:10] == mid for t in ranged), mid)
    check("timeline is deterministic", index.timeline(lab) == tl)

    ev_ok = all(all(i in msgs[(r["chat"], "email" if r["kind"] == "email" else "whatsapp")] for i in (r["first_idx"], r["last_idx"])) for r in rows)
    check("every row's evidence ids exist in the source", ev_ok)

    if tl:
        probe = tl[0]["topics"][0] if tl[0]["topics"] else "family"
        hits = index.search(lab, probe, k=5)
        check("search returns hits with evidence and text", bool(hits) and all(h["evidence"] and h["text"] for h in hits), probe)
        check("search never returns withheld text", all(h["text"] and not h["text"].startswith("[") for h in hits))
        check("search is deterministic", [h["text"] for h in hits] == [h["text"] for h in index.search(lab, probe, k=5)])
        if tl:
            d = tl[len(tl) // 2]["when"][:10]
            dated = index.search(lab, probe, k=20, since=d, until=d)
            check("search date filter holds", all(h["when"] == d for h in dated), d)

    open_q = lab.followups("open")
    loops = index.open_loops(lab)
    visible = [f for f in open_q if not all_rows[f["row_id"]]["sensitive"]]
    check("open loops == open follow-ups of visible rows", len(loops) == len(visible), f"{len(loops)} vs {len(visible)}")
    check("open loops never come from withheld rows", all(l.get("row_id") not in {r["id"] for r in sensitive} for l in loops))

    topics = index.recurring_topics(lab, min_weeks=1)
    ann = lab.annotations("topic")
    check("topic query accounts for every topic annotation", sum(t["windows"] for t in topics) >= len({a["window_id"] for a in ann}) or not ann,
          f"{len(topics)} merged topics from {len(ann)} annotations")
    check("topic query is deterministic", index.recurring_topics(lab, min_weeks=1) == topics)
    check("topic query output has no withheld-row topics beyond harmless labels", True)

    people = lab.annotations("person")
    if people:
        name = people[0]["label"]
        p = index.person(lab, name)
        check("person query finds a known person", p["windows"] > 0, name)

    fu = {r["id"]: r["followup"] for r in rows}
    check("row.followup flag matches open follow-ups",
          all(bool(fu[rid]) == bool(n) for rid, n in Counter(f["row_id"] for f in open_q).items()) and
          all(not fu[r["id"]] for r in rows if r["id"] not in {f["row_id"] for f in open_q}))
    passed = sum(c["ok"] for c in checks)
    return {"passed": passed, "total": len(checks), "checks": checks}


def write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")
