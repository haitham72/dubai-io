#!/usr/bin/env python3
"""Seed the real Community store with the 10-user / 7-group demo cohort.

Guards (fail closed):
  - DEMO_SEED_ENABLED=true required for --apply / --reset-demo
  - Default mode is --dry-run (writes nothing)
  - Namespace-scoped only: community-demo-10-v1

Usage:
  python scripts/seed_community_10_users.py
  python scripts/seed_community_10_users.py --dry-run
  DEMO_SEED_ENABLED=true python scripts/seed_community_10_users.py --apply
  DEMO_SEED_ENABLED=true python scripts/seed_community_10_users.py --reset-demo
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps" / "api"
if str(API) not in sys.path:
    sys.path.insert(0, str(API))


def _store_target() -> str | Path:
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if url:
        return url
    data = API / "data" / "actions.sqlite3"
    data.parent.mkdir(parents=True, exist_ok=True)
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=False, help="Plan only (default if no other mode)")
    mode.add_argument("--apply", action="store_true", help="Write demo rows (requires DEMO_SEED_ENABLED=true)")
    mode.add_argument("--reset-demo", action="store_true", help="Delete namespace-scoped demo rows only")
    parser.add_argument("--verify", action="store_true", help="Print verify_counts after action")
    parser.add_argument("--json", action="store_true", help="Emit JSON result")
    args = parser.parse_args(argv)

    if not args.apply and not args.reset_demo:
        args.dry_run = True

    enabled = (os.environ.get("DEMO_SEED_ENABLED") or "").strip().lower() in ("1", "true", "yes")
    if (args.apply or args.reset_demo) and not enabled:
        print("Refusing: set DEMO_SEED_ENABLED=true for --apply / --reset-demo", file=sys.stderr)
        return 2

    from app.actions import ActionStore
    from app.community.demo_10_users import NAMESPACE, apply_seed, reset_demo, verify_counts

    store = ActionStore(_store_target())
    try:
        if args.reset_demo:
            result = {"action": "reset-demo", "namespace": NAMESPACE, "deleted": reset_demo(store)}
            if args.verify:
                result["verify"] = verify_counts(store)
        elif args.apply:
            result = apply_seed(store, dry_run=False)
            result["action"] = "apply"
        else:
            result = apply_seed(store, dry_run=True)
            result["action"] = "dry-run"
            if args.verify:
                result["verify"] = verify_counts(store)

        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"action={result.get('action')} namespace={NAMESPACE}")
            if "deleted" in result:
                print("deleted:", result["deleted"])
            v = result.get("verify")
            if v:
                print("verify.ok=", v.get("ok"), "measured=", v.get("measured"))
            if result.get("dry_run"):
                print("dry-run: no writes")
        if result.get("action") in ("dry-run", "reset-demo"):
            return 0
        v = result.get("verify") or {}
        return 0 if v.get("ok") else 1
    finally:
        store.db.close()


if __name__ == "__main__":
    raise SystemExit(main())
