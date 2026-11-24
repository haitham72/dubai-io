"""Suite S4: CR-TM bridge on live Postgres + contest-shared HttpTemporalMemoryClient & MemoryBridge HTTP contract."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import httpx

from temporal_memory.db.db import fold_text

from common import LiveApiServer, temp_schema


def _resolve_cs_paths() -> tuple[Path | None, str]:
    repo_root = Path(__file__).resolve().parents[3]
    env_api = os.environ.get("CS_API_DIR", "").strip()
    api_candidates = [
        Path(env_api) if env_api else None,
        repo_root.parent / "contest-sub-contest-shared" / "apps" / "api",
        repo_root / "apps" / "api",
    ]
    cs_api: Path | None = None
    for cand in api_candidates:
        if cand is not None and (cand / "app" / "memory_bridge" / "client.py").is_file():
            cs_api = cand
            break

    env_py = os.environ.get("CS_PY", "").strip()
    py_candidates = [
        Path(env_py) if env_py else None,
        (cs_api / ".venv" / "Scripts" / "python.exe") if cs_api else None,
        repo_root / "apps" / "api" / ".venv" / "Scripts" / "python.exe",
        repo_root.parent / "contest" / "apps" / "api" / ".venv" / "Scripts" / "python.exe",
        repo_root.parent / "contest-sub-contest-shared" / "apps" / "api" / ".venv" / "Scripts" / "python.exe",
    ]
    cs_py = sys.executable
    for p in py_candidates:
        if p is not None and p.is_file():
            cs_py = str(p)
            break
    return cs_api, cs_py


CS_API_DIR, CS_PY = _resolve_cs_paths()


def _run_cs_http_client_probe(base_url: str, admin_token: str, owner: str, owner_tok: str) -> dict:
    """Import HttpTemporalMemoryClient from contest-shared (read-only) and run real HTTP calls."""
    sys.path.insert(0, str(CS_API_DIR))
    from app.memory_bridge.client import HttpTemporalMemoryClient  # type: ignore

    client = HttpTemporalMemoryClient(
        base_url=base_url,
        service_token=owner_tok,
        admin_token=admin_token,
        owner_token_resolver=lambda _oid: owner_tok,
    )
    results: dict[str, dict] = {}
    try:
        # 1. Admin provisioning
        try:
            ow = client.ensure_owner(owner, label=owner, display_name="Karim Bridge", kind="demo")
            tok_res = client.mint_owner_device_token(owner, label="s4-minted")
            rev_res = client.revoke_token(tok_res["id"])
            results["admin_owner_and_tokens"] = {"ok": bool(ow.get("id") == owner and rev_res.get("ok"))}
        except Exception as exc:
            results["admin_owner_and_tokens"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

        # 2. POST /records (record-only, then with direct_fact)
        try:
            up1 = client.upsert_record_and_enqueue(
                owner, record_id="mgmsg:s4-1", source="messenger:conv-a",
                at="2026-11-23T14:00:00+04:00", author=owner, text="Sprint alpha complete", enqueue="none",
            )
            results["post_records_only"] = {"ok": True, "resp": up1}
        except Exception as exc:
            results["post_records_only"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

        try:
            up2 = client.upsert_record_and_enqueue(
                owner, record_id="mgmsg:s4-2", source="messenger:conv-a",
                at="2026-11-23T14:05:00+04:00", author=owner, text="Beta testers joined", enqueue="extract.live",
                direct_fact={"text": "Beta testers joined", "subject_id": "projects/dubai-io", "valid_from": "2026-11-23", "evidence": ["mgmsg:s4-2"]},
            )
            results["post_records_with_direct_fact"] = {"ok": True, "resp": up2}
        except Exception as exc:
            results["post_records_with_direct_fact"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

        # 3. POST /facts/{id}/resolve on a Postgres-seeded hypothesis fact
        try:
            res_conf = client.resolve_fact(owner, "f_s4_hyp", action="confirm")
            results["resolve_fact_confirm"] = {"ok": True, "resp": res_conf}
        except Exception as exc:
            results["resolve_fact_confirm"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

        try:
            res_edit = client.resolve_fact(owner, "f_s4_hyp", action="edit", new_text="Karim prefers Arabic coffee", valid_from="2026-11-23")
            results["resolve_fact_edit"] = {"ok": True, "resp": res_edit}
        except Exception as exc:
            results["resolve_fact_edit"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

        # 4. GET /search with and without source_prefix on Postgres-seeded facts
        try:
            unscoped = client.search_facts(owner, "Shorebirds", limit=20)
            scoped_a = client.search_facts(owner, "Shorebirds", limit=20, source_prefix="messenger:conv-a")
            scoped_b = client.search_facts(owner, "Shorebirds", limit=20, source_prefix="messenger:conv-b")
            results["search_source_prefix"] = {
                "ok": len(unscoped) == 2 and [f["id"] for f in scoped_a] == ["f_s4_a"] and [f["id"] for f in scoped_b] == ["f_s4_b"],
                "unscoped_ids": [f["id"] for f in unscoped],
                "conv_a_ids": [f["id"] for f in scoped_a],
                "conv_b_ids": [f["id"] for f in scoped_b],
            }
        except Exception as exc:
            results["search_source_prefix"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

        # 5. Reads: context, vault/subjects, vault/people, hypotheses, timeline, why, export
        try:
            ctx = client.context_pack(owner, "Shorebirds")
            vs = client.get_vault_subjects(owner)
            vp = client.get_vault_people(owner)
            vh = client.get_hypotheses(owner)
            tl = client.get_timeline(owner)
            why = client.get_why_fact(owner, "f_s4_a")
            zbytes = client.export_markdown_zip(owner)
            results["read_surfaces"] = {
                "ok": bool(ctx.get("owner") == owner and vs.get("owner") == owner and vp.get("owner") == owner and "hypotheses" in vh and "items" in tl and why.get("fact_id") == "f_s4_a" and zbytes.startswith(b"PK")),
            }
        except Exception as exc:
            results["read_surfaces"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

        # 6. Forget via bridge (fact_id and record_ids)
        try:
            ff = client.forget_fact(owner, "f_s4_b")
            fs = client.forget_source(owner, ["r_s4_a"])
            after = client.search_facts(owner, "Shorebirds", limit=20)
            results["bridge_forget"] = {
                "ok": ff.get("facts_erased", 0) >= 1 and fs.get("facts_erased", 0) >= 1 and len(after) == 0,
                "forget_fact_resp": ff,
                "forget_source_resp": fs,
                "remaining_search_hits": len(after),
            }
        except Exception as exc:
            results["bridge_forget"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    finally:
        client.close()
    return results


def _run_contest_shared_memory_bridge_e2e(base_url: str, admin_token: str, owner: str, owner_tok: str) -> dict:
    """Run contest-shared's real MemoryBridge + HttpTemporalMemoryClient against the live Postgres API."""
    script = f"""
import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, {str(CS_API_DIR)!r})
from app import db as db_mod
from app.identity.models import VerifiedPrincipal
from app.memory_bridge.bridge import MemoryBridge
from app.memory_bridge.client import HttpTemporalMemoryClient
from app.memory_bridge.models import MemoryRecordInput

with tempfile.TemporaryDirectory() as td:
    db = db_mod.connect(Path(td) / "cs_e2e.sqlite3")
    client = HttpTemporalMemoryClient(base_url={base_url!r}, service_token={owner_tok!r}, admin_token={admin_token!r}, owner_token_resolver=lambda _o: {owner_tok!r})
    bridge = MemoryBridge(db, client)
    p = VerifiedPrincipal(user_id={owner!r}, app_id="quest", capabilities=frozenset(), auth_mode="verified_app_session", age_band="adult_18_plus")
    bridge.set_source_consent(p, "quest", enabled=True)
    bridge.set_app_consent(p, "quest", read_enabled=True, write_enabled=True)
    out = {{}}
    try:
        wr = bridge.write_consented(p, MemoryRecordInput(
            record_id="qmsg:e2e-1", source_kind="quest", source_id="quest:t1", host_app="quest",
            author_id={owner!r}, text="I am training for the Dubai 10K", valid_time="2026-11-23T10:00:00+00:00",
            subject_path="fitness/running", explicit_user_confirm=True,
        ))
        out["write_consented"] = {{"ok": True, "fact_ids": wr.fact_ids}}
    except Exception as exc:
        out["write_consented"] = {{"ok": False, "error": f"{{type(exc).__name__}}: {{exc}}"}}
    try:
        ctx = bridge.read_quest_context(p, "Dubai 10K")
        out["read_quest_context"] = {{"ok": True, "facts": len(ctx.get("facts", []))}}
    except Exception as exc:
        out["read_quest_context"] = {{"ok": False, "error": f"{{type(exc).__name__}}: {{exc}}"}}
    client.close()
    db.close()
    print(json.dumps(out))
"""
    proc = subprocess.run([CS_PY, "-c", script], capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        return {"ok": False, "error": (proc.stderr or proc.stdout).strip()[:600]}
    return json.loads(proc.stdout.strip().splitlines()[-1])


def _run_contest_shared_pytest_reference() -> dict:
    """Run contest-shared's own FakeTemporalMemoryClient bridge suite (read-only reference)."""
    proc = subprocess.run(
        [CS_PY, "-m", "pytest", "-q", *sorted(str(p) for p in (CS_API_DIR / "tests").glob("test_memory_bridge_*.py"))],
        cwd=str(CS_API_DIR),
        capture_output=True,
        text=True,
        timeout=180,
    )
    lines = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    summary = lines[-1] if lines else ""
    return {
        "returncode": proc.returncode,
        "summary": summary,
        "note": "Runs against FakeTemporalMemoryClient / SQLite in contest-shared, not live Postgres temporal_memory.",
    }


def run(out_dir: Path) -> dict:
    with temp_schema("s4") as (db, _sc):
        with LiveApiServer(db) as srv:
            owner = "karim_s4"
            srv.create_owner(owner, label=owner, kind="demo", display_name="Karim S4")
            owner_tok = srv.mint_token("owner-device", owner=owner, label="s4")
            worker_tok = srv.mint_token("worker", owner=None, label="s4-w")
            other_tok = srv.mint_token("owner-device", owner="other_owner", label="s4-other")

            # Seed Postgres records + facts directly so resolve/search/forget can be tested on real Postgres rows
            with db.transaction() as conn:
                conn.execute("INSERT INTO subjects (id, owner, path, label, kind, status) VALUES ('s1', %s, 'projects/atlas', 'Atlas', 'topic', 'active')", (owner,))
                for rid, src, txt in [
                    ("r_s4_a", "messenger:conv-a", "Shorebirds in conversation alpha"),
                    ("r_s4_b", "messenger:conv-b", "Shorebirds in conversation beta"),
                    ("r_s4_h", "gmail", "Karim likes Turkish coffee"),
                ]:
                    conn.execute(
                        "INSERT INTO records (id, owner, source, at, author, text, content_hash) VALUES (%s,%s,%s,'2026-11-23',%s,%s,%s)",
                        (rid, owner, src, owner, txt, hashlib.sha256(txt.encode()).hexdigest()),
                    )
                for fid, txt, st, rid in [
                    ("f_s4_a", "Shorebirds in conversation alpha", "active", "r_s4_a"),
                    ("f_s4_b", "Shorebirds in conversation beta", "active", "r_s4_b"),
                    ("f_s4_hyp", "Karim might like Turkish coffee", "hypothesis", "r_s4_h"),
                ]:
                    conn.execute(
                        "INSERT INTO facts (id, owner, text, text_folded, subject_id, valid_from, status, provenance, content_hash) "
                        "VALUES (%s,%s,%s,%s,'s1','2026-11-23',%s,'inferred',%s)",
                        (fid, owner, txt, fold_text(txt), st, hashlib.sha256(fid.encode()).hexdigest()),
                    )
                    conn.execute("INSERT INTO fact_evidence (owner, fact_id, record_id, record_generation) VALUES (%s,%s,%s,0)", (owner, fid, rid))
                conn.execute("UPDATE owners SET facts_version = 1 WHERE id = %s", (owner,))

            # Auth isolation checks
            with httpx.Client(base_url=srv.base_url, timeout=10.0) as hc:
                auth_checks = {
                    "worker_rejected_403_search": hc.get(f"/v1/owners/{owner}/search", headers={"Authorization": f"Bearer {worker_tok}"}, params={"q": "x"}).status_code == 403,
                    "cross_owner_rejected_403_search": hc.get(f"/v1/owners/{owner}/search", headers={"Authorization": f"Bearer {other_tok}"}, params={"q": "x"}).status_code == 403,
                }

            if CS_API_DIR is None:
                out = {
                    "suite": "S4_bridge_postgres",
                    "status": "SKIPPED",
                    "passed": False,
                    "reason": "contest-shared apps/api (with app/memory_bridge) not found; set CS_API_DIR and CS_PY to enable bridge checks",
                    "auth_checks": auth_checks,
                    "http_client_against_postgres": {},
                    "memory_bridge_http_e2e": {},
                    "contest_shared_fake_suite_reference": {},
                }
                (out_dir / "s4_bridge_pg.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
                return out

            client_probes = _run_cs_http_client_probe(srv.base_url, srv.admin_token, owner, owner_tok)
            bridge_e2e = _run_contest_shared_memory_bridge_e2e(srv.base_url, srv.admin_token, owner, owner_tok)

    cs_pytest = _run_contest_shared_pytest_reference()

    passed = (
        all(auth_checks.values())
        and all(v.get("ok") for v in client_probes.values())
        and bridge_e2e.get("write_consented", {}).get("ok", False)
    )
    out = {
        "suite": "S4_bridge_postgres",
        "status": "PASS" if passed else "FAIL",
        "passed": passed,
        "cs_api_dir": str(CS_API_DIR),
        "cs_py": CS_PY,
        "auth_checks": auth_checks,
        "http_client_against_postgres": client_probes,
        "memory_bridge_http_e2e": bridge_e2e,
        "contest_shared_fake_suite_reference": cs_pytest,
    }
    (out_dir / "s4_bridge_pg.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    return out


if __name__ == "__main__":
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "results" / "manual"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(json.dumps(run(out_dir), indent=2))
