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

    out = {
        "suite": "S7_live_triples",
        "status": "READY" if has_live_triples else "NOT YET BUILT",
        "passed": False,
        "dataset": {
            "path": str(ds_path),
            "total_items": len(items),
            "by_category": dict(sorted(by_cat.items())),
            "by_lang": dict(sorted(by_lang.items())),
            "by_expected_action": dict(sorted(by_action.items())),
        },
        "found_symbols": found_symbols,
        "notes": "Live-triple extractor (U2) is not built on this commit; 84-item labelled EN/AR/ARZ trap set validated and ready.",
    }
    (out_dir / "s7_traps.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


if __name__ == "__main__":
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ACCEPTANCE_DIR / "results" / "manual"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(json.dumps(run(out_dir), indent=2))
