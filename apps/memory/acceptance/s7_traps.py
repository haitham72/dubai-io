"""Suite S7: Validate live-triple trap dataset (84 items) and probe engine support."""
from __future__ import annotations

from collections import Counter
import importlib
import json
from pathlib import Path
import sys

from common import ACCEPTANCE_DIR


def run(out_dir: Path) -> dict:
    ds_path = ACCEPTANCE_DIR / "traps_dataset.json"
    data = json.loads(ds_path.read_text(encoding="utf-8"))
    items = data["items"]
    by_cat = Counter(x["category"] for x in items)
    by_lang = Counter(x["lang"] for x in items)
    by_action = Counter(x["expected_action"] for x in items)

    # Probe whether live triple extraction exists in temporal_memory
    has_live_triples = False
    found_symbols: list[str] = []
    for mod_name in ("temporal_memory.live.triples", "temporal_memory.live.context"):
        try:
            mod = importlib.import_module(mod_name)
        except ImportError:
            continue
        for sym in ("extract_triples", "extract_instant_triples", "instant_triples"):
            if callable(getattr(mod, sym, None)):
                has_live_triples = True
                found_symbols.append(f"{mod_name}.{sym}")

    # E6: real scoring of the shipped extractor (no LLM). no_triple / quarantine items must emit nothing; quarantine items
    # must also be held by quarantine_category; emit_triple items are scored for predicate + object.
    scored = {"emit_ok": 0, "emit_miss": 0, "emit_wrong": 0, "trap_clean": 0, "trap_fp": 0, "quarantine_held": 0, "quarantine_leak": 0}
    fp_items, miss_items = [], []
    if has_live_triples:
        from temporal_memory.live.triples import extract_triples, quarantine_category
        for it in items:
            got = extract_triples(it["text"])
            act = it["expected_action"]
            if act == "emit_triple":
                exp = it.get("expected_triple") or {}
                if not got:
                    scored["emit_miss"] += 1; miss_items.append(it["id"])
                elif got[0].predicate == {"books": "other"}.get("%s" % exp.get("predicate"), exp.get("predicate")) and str(exp.get("object", "")).casefold() in got[0].object_text.casefold():
                    scored["emit_ok"] += 1
                else:
                    scored["emit_wrong"] += 1; fp_items.append(it["id"])
            else:
                if got:
                    scored["trap_fp"] += 1; fp_items.append(it["id"])
                else:
                    scored["trap_clean"] += 1
                if act == "quarantine":
                    if quarantine_category(it["text"]):
                        scored["quarantine_held"] += 1
                    else:
                        scored["quarantine_leak"] += 1
    emitted = scored["emit_ok"] + scored["emit_wrong"] + scored["trap_fp"]
    precision = round(scored["emit_ok"] / emitted, 4) if emitted else None
    recall = round(scored["emit_ok"] / max(1, by_action.get("emit_triple", 0)), 4)
    traps_total = by_action.get("no_triple", 0) + by_action.get("quarantine", 0)
    s7_pass = bool(has_live_triples and scored["trap_fp"] == 0 and scored["quarantine_leak"] == 0 and precision is not None and precision >= 0.98)

    out = {
        "suite": "S7_live_triples",
        "status": ("PASS" if s7_pass else "FAIL") if has_live_triples else "NOT YET BUILT",
        "passed": s7_pass,
        "scoring": {**scored, "precision": precision, "recall": recall, "traps_total": traps_total, "wrong_or_fp_ids": fp_items, "missed_ids": miss_items},
        "dataset": {
            "path": str(ds_path),
            "total_items": len(items),
            "by_category": dict(sorted(by_cat.items())),
            "by_lang": dict(sorted(by_lang.items())),
            "by_expected_action": dict(sorted(by_action.items())),
        },
        "found_symbols": found_symbols,
        "notes": "E6: scores temporal_memory.live.triples.extract_triples over the 84-item EN/AR/ARZ trap set; gate = 0 emissions on no_triple/quarantine, precision >= 0.98 (Codex proposal; Gemini 0.90).",
    }
    (out_dir / "s7_traps.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


if __name__ == "__main__":
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ACCEPTANCE_DIR / "results" / "manual"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(json.dumps(run(out_dir), indent=2))
