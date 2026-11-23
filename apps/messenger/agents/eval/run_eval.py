"""Voice-command eval: streams each utterance word by word through the real intent engine and scores the result.

    python -m eval.run_eval                       # offline: rule decider, no network, no spend
    python -m eval.run_eval --decision-ms 150     # same, with an assumed model latency added to every decision
    AGENTS_LIVE=1 python -m eval.run_eval --live  # the Decisions API (spends; needs the owner's go-ahead)

Timing model (simulated clock): each word takes 0.30 s + 0.03 s per letter, a comma adds a 0.25 s pause, a partial
transcript arrives `--stt-lag` after the word ends, the engine ticks every 100 ms, and end of speech is detected after
`--silence` of quiet. Latency figures are therefore pipeline latencies under these assumptions, not field measurements.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from messenger_agents.catalog import BY_NAME  # noqa: E402
from messenger_agents.contacts import Contact  # noqa: E402
from messenger_agents.deciders import Decision, RuleDecider  # noqa: E402
from messenger_agents.engine import Conversation, Event, Policy  # noqa: E402
from messenger_agents.text import norm  # noqa: E402


class Delayed:
    """Adds a fixed latency to another decider's answers (to project a model's latency onto the offline run)."""

    def __init__(self, inner, ms: float) -> None:
        self.inner, self.ms = inner, ms

    async def decide(self, clause, utterance, contacts) -> Decision:
        d = await self.inner.decide(clause, utterance, contacts)
        return replace(d, latency_ms=d.latency_ms + self.ms)


def word_times(text: str) -> list[tuple[str, float]]:
    t, out = 0.0, []
    for w in text.split():
        t += 0.30 + 0.03 * len(re.sub(r"\W", "", w))
        out.append((w, round(t, 3)))
        if w.endswith(","):
            t += 0.25
    return out


def f1(a: str, b: str) -> float:
    x, y = Counter(norm(a).split()), Counter(norm(b).split())
    common = sum((x & y).values())
    if not common:
        return 0.0
    p, r = common / sum(x.values()), common / sum(y.values())
    return 2 * p * r / (p + r)


def arg_ok(key: str, got, want) -> bool:
    if got is None:
        return False
    if key in ("contactId", "screen"):
        return got == want
    if key in ("city", "to"):
        return norm(str(got)) == norm(str(want))
    if key == "text":
        return norm(str(got)) == norm(str(want))  # sends must keep every word, in order (case/punctuation may differ)
    return f1(got, want) >= 0.6  # topic, prompt


async def run_item(item: dict, decider, contacts: list[Contact], policy: Policy, stt_lag: float, silence: float) -> dict:
    conv = Conversation(decider, contacts, policy)
    turns = item.get("turns") or [item.get("heard") or item["said"]]
    said_last = item.get("said") or turns[-1]
    events: list[Event] = []
    decisions: list[dict] = []
    offset = 0.0
    speech_end = last_word = trigger_end = 0.0
    for n, heard in enumerate(turns):
        if n == len(turns) - 1:
            events, decisions = [], []  # a follow-up answer is scored on its own turn
        eng = conv.begin()
        heard_w = word_times(heard)
        said_w = word_times(said_last) if n == len(turns) - 1 else heard_w
        arrivals = [(offset + te + stt_lag, " ".join(w for w, _ in heard_w[: i + 1])) for i, (_, te) in enumerate(heard_w)]
        last_word = offset + heard_w[-1][1]
        speech_end = last_word + silence
        trig = item.get("trigger")
        idx = next((i for i, (w, _) in enumerate(said_w) if trig and norm(w) == norm(trig)), len(said_w) - 1)
        trigger_end = offset + said_w[idx][1]
        t, k = offset, 0
        while t < speech_end - 1e-9:
            while k < len(arrivals) and arrivals[k][0] <= t + 1e-9:
                eng.partial(arrivals[k][1], arrivals[k][0])
                k += 1
            events += await conv.tick(t)
            t = round(t + 0.1, 3)
        while k < len(arrivals):
            eng.partial(arrivals[k][1], arrivals[k][0])
            k += 1
        events += await conv.finish(speech_end)
        decisions += eng.decisions
        offset = speech_end + 1.0
    return score(item, events, decisions, speech_end, last_word, trigger_end)


def net(events: list[Event]) -> list[Event]:
    """What stands at the end: cancelled acts and anything before a "cancel all" are withdrawn."""
    out: list[Event] = []
    for e in events:
        if e.type == "cancel":
            if e.args.get("all"):
                out = [x for x in out if x.type == "act"]
            else:
                out = [x for x in out if x.id != e.ref]
            continue
        out.append(e)
    return out


def score(item: dict, events: list[Event], decisions: list[dict], speech_end: float, last_word: float, trigger_end: float) -> dict:
    final = net(events)
    expect = item["expect"]
    want_keys = Counter((x["type"], x.get("action", "")) for x in expect)

    def key(e: Event) -> tuple[str, str]:
        # An expected ask (or chat) without a named action matches any ask (or chat).
        if e.type in ("ask", "chat") and (e.type, e.action) not in want_keys:
            return e.type, ""
        return e.type, e.action

    action_ok = Counter(key(e) for e in final) == want_keys

    args_ok = action_ok
    matched: list[tuple[dict, Event]] = []
    pool = list(final)
    for x in expect:
        e = next((e for e in pool if e.type == x["type"] and (not x.get("action") or e.action == x.get("action"))), None)
        if e:
            pool.remove(e)
            matched.append((x, e))
            for key, want in (x.get("args") or {}).items():
                if not arg_ok(key, e.args.get(key), want):
                    args_ok = False
        else:
            args_ok = False

    expected_contacts = {x["args"]["contactId"] for x in expect if x.get("args", {}).get("contactId")}
    wrong_recipient = sum(1 for e in events if e.type in ("undo", "act") and e.args.get("contactId")
                          and e.args["contactId"] not in expected_contacts)
    premature = sum(1 for e in events if (e.action and BY_NAME[e.action].kind == "paid" and e.type not in ("confirm", "ask", "cancel"))
                    or (e.type == "undo" and e.t < speech_end - 1e-6))
    revised = sum(1 for e in events if e.type == "cancel" and e.label == "revised")
    first = min((e for _, e in matched if e.type in ("act", "undo", "confirm")), key=lambda e: e.t, default=None)
    lat_last = round(first.t - last_word, 3) if first else None
    lat_trigger = round(first.t - trigger_end, 3) if first else None
    return {
        "id": item["id"], "cat": item["cat"], "action_ok": action_ok, "args_ok": args_ok,
        "wrong_recipient": wrong_recipient, "premature": premature, "revised": revised,
        "first_kind": first.type if first else None, "lat_last_word": lat_last, "lat_trigger": lat_trigger,
        "events": [e.wire() for e in events], "decisions": decisions, "expect": expect,
    }


def calibration(results: list[dict], items: dict[str, dict]) -> dict:
    """Top-choice probability vs. correctness, one decision per utterance (the last one), single-action utterances only."""
    pairs = []
    for r in results:
        exp = items[r["id"]]["expect"]
        if len(exp) > 1 or not r["decisions"] or (exp and exp[0]["type"] == "ask" and not exp[0].get("action")):
            continue
        gold = exp[0].get("action", "none") if exp and exp[0]["type"] != "chat" else "none"
        d = r["decisions"][-1]
        pairs.append((d["p"], 1.0 if d["action"] == gold else 0.0))
    if not pairs:
        return {}
    bins = defaultdict(list)
    for p, ok in pairs:
        bins[min(9, int(p * 10))].append((p, ok))
    ece = sum(len(b) / len(pairs) * abs(statistics.mean(p for p, _ in b) - statistics.mean(o for _, o in b)) for b in bins.values())
    brier = statistics.mean((p - ok) ** 2 for p, ok in pairs)
    table = [{"bin": f"{k/10:.1f}-{(k+1)/10:.1f}", "n": len(b), "meanP": round(statistics.mean(p for p, _ in b), 3),
              "accuracy": round(statistics.mean(o for _, o in b), 3)} for k, b in sorted(bins.items())]
    return {"n": len(pairs), "ece": round(ece, 4), "brier": round(brier, 4), "bins": table}


def pct(xs: list[float], q: float) -> float | None:
    if not xs:
        return None
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, max(0, math.ceil(q * len(xs)) - 1))], 3)


def summarize(results: list[dict], items: dict[str, dict], meta: dict) -> dict:
    n = len(results)
    cats = sorted({r["cat"] for r in results})
    by_cat = {c: {"n": sum(r["cat"] == c for r in results),
                  "action": sum(r["action_ok"] for r in results if r["cat"] == c),
                  "args": sum(r["args_ok"] for r in results if r["cat"] == c)} for c in cats}

    def lat(key: str, kinds: tuple[str, ...]) -> dict:
        xs = [r[key] for r in results if r[key] is not None and r["first_kind"] in kinds and r["args_ok"]]
        return {"n": len(xs), "p50": pct(xs, 0.5), "p95": pct(xs, 0.95)}

    asks = [r for r in results if any(x["type"] == "ask" for x in items[r["id"]]["expect"])]
    non_asks = [r for r in results if not any(x["type"] == "ask" for x in items[r["id"]]["expect"])]
    return {
        **meta, "n": n,
        "action_accuracy": round(sum(r["action_ok"] for r in results) / n, 4),
        "args_accuracy": round(sum(r["args_ok"] for r in results) / n, 4),
        "wrong_recipient": sum(r["wrong_recipient"] for r in results),
        "premature_outward_or_paid": sum(r["premature"] for r in results),
        "revised_in_app_acts": sum(r["revised"] for r in results),
        "ask_recall": round(sum(r["action_ok"] for r in asks) / max(1, len(asks)), 4),
        "false_asks": sum(1 for r in non_asks if any(e["type"] == "ask" for e in r["events"])),
        "latency_in_app_from_last_word_s": lat("lat_last_word", ("act",)),
        "latency_in_app_from_trigger_s": lat("lat_trigger", ("act",)),
        "latency_outward_paid_from_last_word_s": lat("lat_last_word", ("undo", "confirm")),
        "decisions_per_utterance": round(sum(len(r["decisions"]) for r in results) / n, 2),
        "calibration": calibration(results, items),
        "by_category": by_cat,
        "failures": [r["id"] for r in results if not r["args_ok"]],
    }


def markdown(s: dict) -> str:
    li, lt, lo = s["latency_in_app_from_last_word_s"], s["latency_in_app_from_trigger_s"], s["latency_outward_paid_from_last_word_s"]
    cal = s["calibration"]
    rows = "\n".join(f"| {c} | {v['n']} | {v['action']}/{v['n']} | {v['args']}/{v['n']} |" for c, v in s["by_category"].items())
    return f"""## {s['name']}

Decider: **{s['decider']}** · threshold {s['threshold']} · margin {s['margin']} · stable {s['stable']} s · strict namesakes {s['strict']} · \
added decision latency {s['decision_ms']} ms · STT lag {s['stt_lag']} s · end-of-speech silence {s['silence']} s

| Metric | Value |
|---|---|
| Utterances | {s['n']} |
| Correct action (all steps) | {s['action_accuracy']:.1%} |
| Correct action **and** arguments | {s['args_accuracy']:.1%} |
| Wrong-recipient sends/opens (target 0) | **{s['wrong_recipient']}** |
| Paid run without confirm, or send before end of speech (must be 0) | **{s['premature_outward_or_paid']}** |
| In-app acts later withdrawn by a correction | {s['revised_in_app_acts']} |
| Ask recall (should ask → asked) | {s['ask_recall']:.1%} |
| Unneeded questions | {s['false_asks']} |
| In-app: last word → action, p50 / p95 | {li['p50']} s / {li['p95']} s (n={li['n']}) |
| In-app: trigger word → action, p50 / p95 | {lt['p50']} s / {lt['p95']} s (n={lt['n']}) |
| Send/paid: last word → undo or confirm card, p50 / p95 | {lo['p50']} s / {lo['p95']} s (n={lo['n']}) |
| Decisions per utterance | {s['decisions_per_utterance']} |
| Calibration (last decision, n={cal.get('n')}) | ECE {cal.get('ece')} · Brier {cal.get('brier')} |

| Category | n | Action | Action + args |
|---|---|---|---|
{rows}

Failures: {', '.join(s['failures']) or 'none'}
"""


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # the report has arrows; Windows consoles default to cp1252
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="baseline")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--threshold", type=float, default=Policy.threshold)
    ap.add_argument("--margin", type=float, default=Policy.margin)
    ap.add_argument("--lenient-namesakes", action="store_true")
    ap.add_argument("--decision-ms", type=float, default=0.0)
    ap.add_argument("--stable", type=float, default=Policy.stable_s, help="seconds a partial must be unchanged before it is decided")
    ap.add_argument("--stt-lag", type=float, default=0.35)
    ap.add_argument("--silence", type=float, default=1.4)  # the browser's end-of-speech quiet (STREAM_SILENCE_MS)
    ap.add_argument("--only", default="")
    ap.add_argument("--set", default="utterances", help="utterances (76, the development set) or holdout (24, never tuned on)")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    contacts = [Contact(**c) for c in json.loads((HERE / "contacts.json").read_text(encoding="utf-8"))]
    items = [json.loads(line) for line in (HERE / f"{args.set}.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.only:
        items = [i for i in items if i["id"].startswith(tuple(args.only.split(",")))]
    policy = Policy(threshold=args.threshold, margin=args.margin, strict_namesakes=not args.lenient_namesakes, stable_s=args.stable)

    if args.live:
        from openai import AsyncOpenAI

        from messenger_agents.config import Settings
        from messenger_agents.deciders import ModelDecider
        from messenger_agents.spend import Budget
        from messenger_agents.store import connect
        cfg = Settings()
        if not cfg.openai_live:
            sys.exit("Live run needs AGENTS_LIVE=1 and OPENAI_API_KEY (and the owner's go-ahead).")
        store = await connect(cfg.redis_url)
        decider = ModelDecider(AsyncOpenAI(api_key=cfg.openai_key, base_url="https://api.openai.com/v1"), cfg.decision_model,
                               Budget(store, cfg.prices, cfg.budget_usd, cfg.data_dir / "spend.json"))
        name = "model"
    else:
        decider, name = RuleDecider(), "rules (offline fake)"
    if args.decision_ms:
        decider = Delayed(decider, args.decision_ms)

    results = [await run_item(i, decider, contacts, policy, args.stt_lag, args.silence) for i in items]
    meta = {"name": args.name, "decider": name, "threshold": policy.threshold, "margin": policy.margin, "stable": policy.stable_s,
            "strict": policy.strict_namesakes, "decision_ms": args.decision_ms, "stt_lag": args.stt_lag, "silence": args.silence}
    s = summarize(results, {i["id"]: i for i in items}, meta)
    out = Path(args.out) if args.out else HERE / "results" / f"{args.name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"summary": s, "results": results}, indent=1, ensure_ascii=False), encoding="utf-8")
    print(markdown(s))


if __name__ == "__main__":
    asyncio.run(main())
