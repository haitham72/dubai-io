"""python -m app.lab <step> --data <dir> [--chat FILE] [--me NAME]

Steps: parse | extract | index | topics | projects | person NAME | loops | search "text" | forget CHAT
Each step reads the previous step's output from <dir>, writes <step>.md + <step>.json back to it.
Real data lives in <dir> (outside the repo); nothing here writes inside the repo.
"""
from __future__ import annotations

import argparse
import re
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import extract, index
from .parse import parse_chat
from .store import Lab

OWNER = "lab-founder"  # lab runs are single-user; the owner never comes from a caller


def _write(data: Path, name: str, payload, md: str) -> None:
    (data / f"{name}.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    (data / f"{name}.md").write_text(md, encoding="utf-8")
    print(f"wrote {data / (name + '.md')}")


def _score(data: Path, step: str, payload: dict) -> None:
    folder = data / "scores"
    folder.mkdir(exist_ok=True)
    day = datetime.now().strftime("%Y-%m-%d")
    (folder / f"{day}-{step}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="app.lab")
    ap.add_argument("step")
    ap.add_argument("arg", nargs="?", default="")
    ap.add_argument("--data", required=True)
    ap.add_argument("--chat", help="parse: a WhatsApp export .txt, or an email .mbox / folder of .eml")
    ap.add_argument("--name", default="", help="parse: short chat id (default: file name as a safe slug)")
    ap.add_argument("--me", default="", help="the owner's sender name in the chat")
    ap.add_argument("--limit", type=int, default=0, help="extract: only the first N windows")
    ap.add_argument("--since", default="", help="timeline/search: from date YYYY-MM-DD")
    ap.add_argument("--until", default="", help="timeline/search: to date YYYY-MM-DD")
    ap.add_argument("--days", type=int, default=0, help="rows: only the most recent N days of each source")
    ap.add_argument("--sample", type=int, default=0, help="extract: N windows spread evenly over the timeline")
    ns = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    data = Path(ns.data)
    data.mkdir(parents=True, exist_ok=True)
    lab = Lab(data, OWNER)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if ns.step == "parse":
        path = Path(ns.chat)
        chat_id = ns.name or re.sub(r"[^\w-]+", "_", path.stem).strip("_")
        if path.is_dir() or path.suffix.lower() in (".mbox", ".eml"):  # email export -> the email skill
            from .parse_email import parse_mailbox

            records = parse_mailbox(path)
            counts = lab.ingest_messages("email", chat_id, records, now)
            stats = {"source": chat_id, "kind": "email", "messages": len(records),
                     "threads": len({r.meta["thread"] for r in records}), "bulk": sum(bool(r.meta["bulk"]) for r in records),
                     "with_attachments": sum(bool(r.meta["attachments"]) for r in records),
                     "first": records[0].ts if records else None, "last": records[-1].ts if records else None,
                     "ingest": counts}
            _write(data, f"parse-{chat_id}", stats, "# Parse report (email)\n\n" + "\n".join(f"- **{k}**: {v}" for k, v in stats.items()))
            return 0
        parsed = parse_chat(path.read_text(encoding="utf-8-sig"), chat_id)
        counts = lab.ingest_messages("whatsapp", parsed.chat, parsed.messages, now)
        stats = {**parsed.stats(), "ingest": counts}
        md = "# Parse report\n\n" + "\n".join(f"- **{k}**: {v}" for k, v in stats.items())
        _write(data, f"parse-{parsed.chat}", stats, md)
        return 0

    if ns.step == "extract":
        if not ns.me:
            ap.error("extract needs --me (the owner's name as it appears in the chat)")
        by_chat = {}
        run_stats = {}
        for chat in lab.chats("whatsapp"):
            run_stats[chat] = extract.process(lab, chat, ns.me, limit=ns.limit or None, sample=ns.sample)
            by_chat[chat] = {m.idx: m for m in lab.load_messages("whatsapp", chat)}
        leaks, unsourced = extract.leak_check(lab), extract.unsourced_facts(lab)
        total = {"chats": run_stats, "sensitive_leaks": leaks, "facts_without_source": unsourced}
        extract.report(lab, next(iter(run_stats.values()), {}), by_chat, str(data / "extract.md"))
        (data / "extract.json").write_text(json.dumps(total, indent=2), encoding="utf-8")
        _score(data, "extract", total)
        print(json.dumps(total, indent=2))
        return 0 if leaks == 0 and unsourced == 0 else 2

    if ns.step == "index":
        stats = index.build(lab)
        print(json.dumps(stats))
        return 0

    queries = {
        "topics": lambda: (index.recurring_topics(lab), ["topic", "variants", "windows", "first", "last", "weeks", "recurring", "months"]),
        "projects": lambda: (index.projects(lab), ["project", "aliases", "windows", "first", "last", "silent_days", "people", "topics", "open_loops", "tone", "facts"]),
        "loops": lambda: (index.open_loops(lab), ["loop", "who", "since", "age_days", "chat", "evidence"]),
        "timeline": lambda: (index.timeline(lab, ns.since or None, ns.until or None),
                             ["when", "kind", "topics", "names", "memory", "sentiment", "followup", "evidence"]),
        "person": lambda: ([index.person(lab, ns.arg)], ["person", "roles", "windows", "first", "last", "tone_over_time", "topics", "open_loops"]),
        "search": lambda: (index.search(lab, ns.arg, since=ns.since or None, until=ns.until or None),
                           ["text", "kind", "score", "when", "chat", "topics", "followup", "evidence", "via"]),
    }
    if ns.step in queries:
        rows, fields = queries[ns.step]()
        name = ns.step if not ns.arg else f"{ns.step}-{''.join(c for c in ns.arg if c.isalnum())[:30]}"
        _write(data, name, rows, index.render(ns.step.title(), rows, fields))
        return 0

    if ns.step == "rows":
        from . import circle, followups, rows

        cir = circle.load(data)
        me = ns.me or cir.owner
        if not me:
            ap.error("rows needs --me or an owner name in circle.json")
        from . import engine
        from .skills import Context

        run = {f"{cid}:{src}": engine.process(lab, cid, src, Context(owner=me, circle=cir, source=src,
                                                                    owner_emails=cir.owner_emails), sample=ns.sample, days=ns.days)
               for cid, src in lab.sources()}
        (data / "rows.md").write_text(rows.render(lab, followups.open_by_row(lab)), encoding="utf-8")
        (data / "rows-run.json").write_text(json.dumps(run, indent=2), encoding="utf-8")
        _score(data, "rows", run)
        print(json.dumps(run, indent=2))
        return 0

    if ns.step in ("eval-quality", "eval-queries", "eval-search"):
        from . import circle, evaluate

        cir = circle.load(data)
        if ns.step == "eval-quality":
            res = {"structural": evaluate.structural(lab, cir)}
            if ns.arg != "nojudge":
                res["judge"] = evaluate.judge(lab)
        elif ns.step == "eval-queries":
            res = evaluate.query_checks(lab)
        else:
            queries = evaluate.gen_queries(lab, data / "eval-queries.json")
            res = evaluate.search_eval(lab, queries)
        evaluate.write(data / f"{ns.step}.json", res)
        brief = {k: v for k, v in res.items() if k != "per_row"} if ns.step != "eval-quality" else {
            "structural": res["structural"], "judge": {k: v for k, v in res.get("judge", {}).items() if k != "per_row"}}
        print(json.dumps(brief, indent=2, ensure_ascii=False))
        return 0

    if ns.step == "report":
        from . import followups, rows

        (data / "rows.md").write_text(rows.render(lab, followups.open_by_row(lab)), encoding="utf-8")
        print(f"wrote {data / 'rows.md'}")
        return 0

    if ns.step == "followups":
        from . import followups, rows

        rec = followups.recurring(lab)
        res = followups.resolve(lab)
        (data / "rows.md").write_text(rows.render(lab, followups.open_by_row(lab)), encoding="utf-8")
        (data / "followups.json").write_text(json.dumps({"recurring": rec, "resolve": res,
                                                         "alias_suggestions": lab.alias_suggestions()}, indent=2,
                                                        ensure_ascii=False), encoding="utf-8")
        _score(data, "followups", {"recurring": rec, "resolve": res})
        print(json.dumps({"recurring": rec, "resolve": res, "alias_suggestions": lab.alias_suggestions()}, indent=2, ensure_ascii=False))
        return 0

    if ns.step == "audit":
        result = extract.audit(lab)
        print(json.dumps(result, indent=2))
        _score(data, "audit", result)
        return 0

    if ns.step == "tree":
        from . import tree

        built = tree.build(lab, me=ns.me)
        (data / "tree.md").write_text(tree.render_tree(built), encoding="utf-8")
        (data / "graph.md").write_text(tree.render_graph(built), encoding="utf-8")
        (data / "graph.json").write_text(json.dumps({"nodes": built["nodes"], "edges": built["edges"]}, indent=2,
                                                    ensure_ascii=False), encoding="utf-8")
        print(f"wrote {data / 'tree.md'}, graph.md, graph.json  ({built['topics']} topics, withheld {built['withheld']}, {len(built['nodes'])} nodes, {len(built['edges'])} edges)")
        return 0

    if ns.step == "forget":
        print(json.dumps(lab.forget_chat(ns.arg)))
        return 0

    ap.error(f"unknown step {ns.step}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
