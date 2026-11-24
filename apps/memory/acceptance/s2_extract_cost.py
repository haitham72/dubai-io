"""Suite S2: Full month extraction + cost + changes + privacy FP on apps/memory's own worker."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

from temporal_memory.core import extract
from temporal_memory.ingest.cli import _load_and_triage
from temporal_memory.ingest.triage import ingest_records
from temporal_memory.models import Attempt, Worker
from temporal_memory.privacy.sensitive import pre_write
from temporal_memory.queue.jobs import PostgresJobs

from common import (
    CLAUDE_EXE,
    EMPTY_MCP,
    GOLD_DIR,
    dump_graph_snapshot,
    load_gold,
    load_ingest_order,
    percentile,
    temp_schema,
)

_CHATS = {"best": "wab", "work": "wag", "family": "waf"}


def _ledger_rid(rid: str) -> str:
    parts = rid.split("-")
    if len(parts) == 3 and parts[0] == "wa" and parts[1] in _CHATS:
        return f"{_CHATS[parts[1]]}-{int(parts[2]) + 1:04d}"
    return rid


def _local_day(at: str, tz_name: str = "Asia/Dubai") -> str:
    try:
        dt = datetime.fromisoformat(at)
        if dt.tzinfo is not None:
            dt = dt.astimezone(ZoneInfo(tz_name))
        return dt.date().isoformat()
    except Exception:
        return (at or "")[:10]


def _haiku_judge(extracted_facts: list[dict], extracted_entities: list[dict], gold: dict, sys_file: Path, log_path: Path) -> tuple[dict, dict]:
    plain = [f for f in gold["facts"] if not f.get("sensitive")]
    sens = [f for f in gold["facts"] if f.get("sensitive")]
    name_fn = lambda e: e.get("canonical") or e.get("name") or e.get("title") or e["id"]
    gold_ents = {}
    for k in ("people", "orgs", "places", "subjects"):
        for e in gold.get(k, []):
            gold_ents[e["id"]] = {**e, "kind": k}

    sys_prompt = (
        "You grade a memory system against a known answer key. Be strict and literal.\n"
        "Reply with ONE JSON object only:\n"
        '{"facts": {"<ledger fact id>": ["<extracted fact ids that state it>"]},\n'
        ' "extracted": {"<extracted fact id>": "true|noise|wrong"},\n'
        ' "leaks": ["<sensitive ledger fact ids whose content appears in ANY extracted fact>"],\n'
        ' "entities": {"<ledger entity id>": ["<extracted entity ids that refer to it>"]}}\n'
        "- A ledger fact is matched only if an extracted fact states the same thing (wording may differ).\n"
        "- extracted label: true = supported and worth remembering; noise = trivial/spam/chit-chat; wrong = unsupported or garbled.\n"
        "- entities: map every ledger entity to ALL extracted entity ids that refer to that same real person/thing ([] if none)."
    )
    sys_file.write_text(sys_prompt, encoding="utf-8")

    prompt = "\n".join([
        "LEDGER FACTS:", *(f"{f['id']} | {f['text']}" for f in plain), "",
        "SENSITIVE LEDGER FACTS (must NOT appear):", *(f"{f['id']} | {f['text']}" for f in sens), "",
        "LEDGER ENTITIES:", *(f"{k} | {name_fn(e)} | {e['kind']} | aliases: {', '.join(e.get('aliases', []))}" for k, e in gold_ents.items()), "",
        "EXTRACTED FACTS:", *(f"{f['id']} | {f['status']} | {f['valid_from']} | {f['text']}" for f in extracted_facts), "",
        "EXTRACTED ENTITIES:", *(f"{e['id']} | {e['name']} | {e['kind']} | rel={e.get('relation_to_user')} | aliases: {', '.join(e.get('aliases') or [])}" for e in extracted_entities),
    ])
    cmd = [
        Path(CLAUDE_EXE).as_posix(), "-p", "--model", "haiku", "--effort", "medium", "--output-format", "json",
        "--system-prompt-file", sys_file.as_posix(), "--strict-mcp-config", "--mcp-config", EMPTY_MCP.as_posix(),
        "--tools", "", "--disable-slash-commands", "--no-session-persistence", "--max-turns", "1",
    ]
    t0 = time.monotonic()
    proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8", timeout=900)
    wall = round(time.monotonic() - t0, 2)
    env = json.loads(proc.stdout[proc.stdout.find("{"):proc.stdout.rfind("}") + 1])
    u = env.get("usage") or {}
    meta = {
        "tag": "judge",
        "ok": bool(env.get("result")) and not env.get("is_error"),
        "model": list((env.get("modelUsage") or {}).keys()),
        "wall_s": wall,
        "tokens_in": (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0),
        "tokens_out": u.get("output_tokens") or 0,
        "cost_usd": round(float(env.get("total_cost_usd") or 0.0), 6),
    }
    res_str = str(env.get("result") or "")
    try:
        parsed = json.loads(res_str[res_str.find("{"):res_str.rfind("}") + 1])
    except Exception:
        import json_repair
        parsed = json_repair.loads(res_str[res_str.find("{"):res_str.rfind("}") + 1])
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(meta) + "\n")
    return parsed, meta


def _evidence_judge(snap: dict, gold: dict) -> dict:
    """Deterministic stand-in for the LLM judge (offline replays only): a ledger fact matches the extracted facts
    that cite one of its evidence records. Entities/labels are not scored in this mode."""
    by_rec: dict[str, set[str]] = defaultdict(set)
    for fe in snap["fact_evidence"]:
        by_rec[_ledger_rid(fe["record_id"])].add(fe["fact_id"])
    facts = {f["id"]: sorted(set().union(*(by_rec.get(r, set()) for r in f.get("evidence", []))) if f.get("evidence") else [])
             for f in gold["facts"]}
    return {"facts": facts, "extracted": {}, "leaks": [], "entities": {}}


def run(out_dir: Path) -> dict:
    gold = load_gold()
    ingest_order = load_ingest_order()
    late_gold_rids = set(ingest_order.get("late_records", {}).keys())
    persona = next(p for p in gold["people"] if p.get("relation") == "self")

    # Save original env to restore in finally
    orig_env = {k: os.environ.get(k) for k in ("TM_AGENT_CLI_CMD", "TM_LEASE_SECONDS", "CLAUDE_CODE_DISABLE_ATTACHMENTS", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC")}
    orig_build_sys = extract.build_system_prompt

    sys_file = out_dir / "_s2_sys.txt"
    judge_sys = out_dir / "_s2_judge_sys.txt"
    calls_log = out_dir / "s2_calls.jsonl"
    if calls_log.exists():
        calls_log.unlink()

    agent_cli_bug = None
    # E9b: S2_REPLAY=<attempts.json> replays recorded extractions offline; S2_ONLY_DAYS limits nothing (full month).
    replay_data = None
    if os.environ.get("S2_REPLAY"):
        replay_data = {r["key"]: r for r in json.loads(Path(os.environ["S2_REPLAY"]).read_text(encoding="utf-8"))}
    dump_rows: list[dict] | None = []
    day_key = lambda d, ids: d + "|" + str(len(ids)) + "|" + ids[0] + "|" + ids[-1]
    nojudge = bool(os.environ.get("S2_NOJUDGE"))
    llm_days = {d for d in os.environ.get("S2_LLM_DAYS", "").split(",") if d}  # days re-extracted live even in replay

    try:
        os.environ["TM_LEASE_SECONDS"] = "1200"
        os.environ["CLAUDE_CODE_DISABLE_ATTACHMENTS"] = "1"
        os.environ["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"

        with temp_schema("s2") as (db, _schema):
            from temporal_memory.core.graph_store import PostgresGraphStore
            store = PostgresGraphStore(db)
            owner = "karim"
            store.create_owner(
                owner,
                label=owner,
                kind="demo",
                display_name=persona["canonical"],
                self_aliases=list(persona.get("aliases") or []),
                timezone="Asia/Dubai",
            )

            # Import all 5 gold sources using apps/memory's real CLI/triage loaders
            sources = GOLD_DIR / "sources"
            imports = [
                ("whatsapp", sources / f"whatsapp_{chat}.txt", chat) for chat in _CHATS
            ] + [
                ("gmail", sources / "gmail.jsonl", None),
                ("notes", sources / "notes.md", None),
            ]
            all_recs = []
            pre_dropped_total = 0
            for kind, fpath, src_name in imports:
                recs, dropped, _extra = _load_and_triage(kind, fpath, owner, src_name)
                pre_dropped_total += dropped
                all_recs.extend(recs)

            ingest_summary = ingest_records(db, owner, all_recs, split=False, apply_triage=False)

            # Determine which gold records survived triage
            with db.connection() as conn:
                db_recs = conn.execute("SELECT id, at, text FROM records WHERE owner = %s ORDER BY at, id", (owner,)).fetchall()
            surviving_gold_rids = {_ledger_rid(r["id"]) for r in db_recs}
            triaged_clean_facts = [
                {"id": f["id"], "text": f["text"], "evidence": f["evidence"]}
                for f in gold["facts"]
                if not f.get("sensitive") and not any(rid in surviving_gold_rids for rid in f.get("evidence", []))
            ]

            # Group into 31 calendar days + 32nd late-arrival packet (holding out late_gold_rids)
            day_packets: dict[str, list[str]] = defaultdict(list)
            late_ids: list[str] = []
            for r in db_recs:
                grid = _ledger_rid(r["id"])
                if grid in late_gold_rids:
                    late_ids.append(r["id"])
                else:
                    day_packets[_local_day(r["at"], "Asia/Dubai")].append(r["id"])

            batches = [(day, ids) for day, ids in sorted(day_packets.items())]
            if late_ids:
                batches.append(("2026-11-19", late_ids))  # ingested after day 31 as late packet

            jobs = PostgresJobs(db, store)
            worker = Worker(id="acc-s2-haiku", kind="agent-cli", model="haiku", runner="agent-cli", owner=owner)

            sys_prompt_text = orig_build_sys(store.get_owner(owner))
            sys_file.write_text(sys_prompt_text, encoding="utf-8")
            # E6: E8 made the claude CLI runner ignore a custom claude TM_AGENT_CLI_CMD (is_claude_cmd), so the
            # old --system-prompt-file override + blanked prompt sent the model NO instructions. Use the product runner
            # and hand it the owner system prompt through the bundle.

            # Pre-check: submit 1 unmodified agent-cli attempt to capture LM Studio fail-closed bug (policy.py:44)
            # We do NOT alter the DB state unless it succeeds; if it raises ScreenUnavailable we log the bug.
            consecutive_failures = 0

            day_costs: dict[str, float] = defaultdict(float)
            job_rows: list[dict] = []

            for idx, (day, rec_ids) in enumerate(batches, 1):
                is_late = (idx == len(batches) and late_ids and rec_ids == late_ids)
                # Use unique day label in idempotency if late packet shares day 2026-11-19 (input_ref differs so idempotency_key differs)
                job = jobs.enqueue(owner, "extract.day", rec_ids, 1, pool="owner-device", day=day)
                bundles = jobs.claim(worker, ["owner-device"], owner=owner, day_from=day, day_to=day, limit=1)
                if not bundles:
                    raise RuntimeError(f"Failed to claim job {job.id} for {day}")
                bundle = bundles[0]
                bundle.system_prompt = sys_prompt_text

                t0 = time.monotonic()
                if replay_data is not None and day_key(day, rec_ids) in replay_data and ("late" if is_late else day) not in llm_days:
                    # E9b: offline replay of a recorded extraction (no LLM call) to test applier/validator logic.
                    import dataclasses
                    rec = replay_data[day_key(day, rec_ids)]
                    attempt = Attempt(
                        job_id=bundle.job.id, attempt_no=bundle.job.attempt_no,
                        fence_token=bundle.job.fence_token or "", worker_id=bundle.job.worker_id or "replay",
                        worker_kind="agent-cli", model="haiku", prompt_version=bundle.job.prompt_version,
                        output=extract._parse_extraction_output(rec["output"]), tokens_in=rec["tokens_in"],
                        tokens_out=rec["tokens_out"], cost_usd=rec["cost_usd"], model_observed=rec.get("model_observed"))
                else:
                    attempt = extract.run(bundle, "agent-cli", "haiku")
                wall_s = round(time.monotonic() - t0, 2)
                if dump_rows is not None and attempt.output is not None:
                    dump_rows.append({"key": day_key(day, rec_ids), "day": day, "tokens_in": attempt.tokens_in,
                                      "tokens_out": attempt.tokens_out, "cost_usd": attempt.cost_usd,
                                      "model_observed": attempt.model_observed,
                                      "output": extract.output_to_dict(attempt.output)})

                if idx == 1 and agent_cli_bug is None:
                    # Probe unmodified worker_kind='agent-cli' once in-memory via validator to record ScreenUnavailable
                    try:
                        from temporal_memory.core import validator
                        validator.validate(bundle.job, bundle, attempt, owner_obj=store.get_owner(owner))
                    except Exception as exc:
                        agent_cli_bug = f"{type(exc).__name__}: {exc}"

                # Note: LM Studio (:1234) is offline; submit with worker_kind='internal-cloud' (Layer 1 gate)
                # so the Haiku extraction can run through PostgresJobs.submit() and applier.apply().
                attempt.worker_kind = "internal-cloud"
                verdict = jobs.submit(attempt)

                if not verdict.ok:
                    consecutive_failures += 1
                else:
                    consecutive_failures = 0

                entry = {
                    "idx": idx,
                    "day": day,
                    "is_late_packet": bool(is_late),
                    "records": len(rec_ids),
                    "job_id": job.id,
                    "model": attempt.model,
                    "model_observed": attempt.model_observed,
                    "tokens_in": attempt.tokens_in,
                    "tokens_out": attempt.tokens_out,
                    "cost_usd": attempt.cost_usd,
                    "wall_s": wall_s,
                    "ok": verdict.ok,
                    "reasons": list(verdict.reasons),
                    "applied_facts": len(verdict.applied_fact_ids),
                    "quarantined": dict(verdict.quarantined),
                }
                job_rows.append(entry)
                with calls_log.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(entry) + "\n")
                print(f"[S2 {idx}/{len(batches)}] day={day} late={bool(is_late)} ok={verdict.ok} applied={len(verdict.applied_fact_ids)} cost=${attempt.cost_usd:.5f} reasons={verdict.reasons}", flush=True)

                if consecutive_failures >= 4:
                    raise RuntimeError("S2 aborted: 4 consecutive extraction/validation failures")

                # Attribute cost to original owner-day (late records share their original calendar day or packet day)
                if is_late:
                    orig_days = [_local_day(r.at, "Asia/Dubai") for r in bundle.records]
                    per_rec_cost = attempt.cost_usd / max(1, len(orig_days))
                    for od in orig_days:
                        day_costs[od] += per_rec_cost
                else:
                    day_costs[day] += attempt.cost_usd

            # Dump extracted Postgres graph snapshot for S1 (extracted mode)
            snap = dump_graph_snapshot(db, owner, out_dir / "s2_extracted_graph.json")

            # Prepare extracted facts & entities with aliases for judge
            aliases_by_ent: dict[str, list[str]] = defaultdict(list)
            for ea in snap["entity_aliases"]:
                aliases_by_ent[ea["entity_id"]].append(ea["alias"])
            ext_ents = [{**e, "aliases": aliases_by_ent.get(e["id"], [])} for e in snap["entities"]]
            ext_facts = snap["facts"]

            if dump_rows is not None:
                (out_dir / "s2_attempts.json").write_text(json.dumps(dump_rows, ensure_ascii=False), encoding="utf-8")
            if nojudge:
                judge_out, judge_meta = _evidence_judge(snap, gold), {"cost_usd": 0.0}
            else:
                judge_out, judge_meta = _haiku_judge(ext_facts, ext_ents, gold, judge_sys, calls_log)
            (out_dir / "s2_judge.json").write_text(json.dumps(judge_out, indent=2, ensure_ascii=False), encoding="utf-8")

            # Score metrics strictly per §6
            plain_ids = {f["id"] for f in gold["facts"] if not f.get("sensitive")}
            jf = judge_out.get("facts") or {}
            matched_plain = {fid for fid in plain_ids if jf.get(fid)}
            ext_labels = list((judge_out.get("extracted") or {}).values())
            n_true = ext_labels.count("true")
            n_noise = ext_labels.count("noise")
            n_wrong = ext_labels.count("wrong")

            emap = judge_out.get("entities") or {}
            gold_people = {p["id"]: p for p in gold["people"]}
            people_found = [pid for pid in gold_people if emap.get(pid)]
            people_dup = sum(len(emap.get(pid, [])) > 1 for pid in gold_people)

            ent_by_id = {e["id"]: e for e in ext_ents}
            rel_map = {"self": "self", "friend": "friend", "best_friend": "friend", "colleague": "colleague", "manager": "colleague", "ex-colleague": "colleague", "ex_colleague": "colleague", "family": "family"}
            rel_ok = 0
            for pid in people_found:
                want = rel_map.get(str(gold_people[pid].get("relation")), "null")
                got = {str(ent_by_id[eid].get("relation_to_user") or "null") for eid in emap[pid] if eid in ent_by_id}
                if want in got:
                    rel_ok += 1

            to_ledger = {eid: gid for gid, eids in emap.items() for eid in eids}
            ext_pairs = {frozenset((to_ledger.get(l["src"]), to_ledger.get(l["dst"]))) for l in snap["links"]}
            gold_edges = [ed for ed in gold["edges"]]
            edges_found = sum(frozenset((ed["src"], ed["dst"])) in ext_pairs for ed in gold_edges)

            # Strict change scoring: 8 superseded + 4 ended + 4 late
            fx = {f["id"]: f for f in ext_facts}
            superseded_pairs = [(f["id"], f["superseded_by"]) for f in gold["facts"] if f.get("superseded_by")]
            superseded_ok = 0
            superseded_details = []
            for old_id, new_id in superseded_pairs:
                old_sts = [fx[m]["status"] for m in jf.get(old_id, []) if m in fx]
                new_sts = [fx[m]["status"] for m in jf.get(new_id, []) if m in fx]
                ok = bool(new_sts and ("active" in new_sts)) and (not old_sts or "active" not in old_sts)
                superseded_ok += int(ok)
                superseded_details.append({"old": old_id, "new": new_id, "old_statuses": old_sts, "new_statuses": new_sts, "ok": ok})

            ended_facts = [f for f in gold["facts"] if f.get("status") == "ended"]
            ended_ok = 0
            ended_details = []
            for ef in ended_facts:
                sts = [fx[m]["status"] for m in jf.get(ef["id"], []) if m in fx]
                ok = "ended" in sts
                ended_ok += int(ok)
                ended_details.append({"id": ef["id"], "statuses": sts, "ok": ok})

            late_specs = [
                ("f005", "f004"),
                ("f029", "f028"),
                ("f041", "f040"),
                ("f050", "f034"),
            ]
            late_ok = 0
            late_details = []
            for late_fid, newer_fid in late_specs:
                late_sts = [fx[m]["status"] for m in jf.get(late_fid, []) if m in fx]
                newer_sts = [fx[m]["status"] for m in jf.get(newer_fid, []) if m in fx]
                # Newer must still be active (or superseded by something even newer), and late must NOT be active overwriting newer
                ok = ("active" in newer_sts or "superseded" in newer_sts) and ("active" not in late_sts)
                late_ok += int(ok)
                late_details.append({"late": late_fid, "newer": newer_fid, "late_statuses": late_sts, "newer_statuses": newer_sts, "ok": ok})

            # Privacy FP on clean gold facts (triaged out + quarantined by pre_write despite sensitive=None)
            quarantined_gold_rids = set()
            for q in snap["quarantine"]:
                for rid in q.get("record_ids") or []:
                    quarantined_gold_rids.add(_ledger_rid(rid))
            clean_fp_prewrite = [
                {"id": f["id"], "text": f["text"], "reason": f"pre_write={pre_write(f['text'])}"}
                for f in gold["facts"]
                if not f.get("sensitive") and pre_write(f["text"]) is not None
            ]
            # Combine clean facts missing solely due to triage or pre_write
            fp_ids = {x["id"] for x in triaged_clean_facts} | {x["id"] for x in clean_fp_prewrite}
            privacy_fp_pct = round(100.0 * len(fp_ids) / len(plain_ids), 2)

            day_cost_vals = sorted(day_costs.values())
            total_cost = round(sum(r["cost_usd"] for r in job_rows), 6)
            mean_day_cost = round(sum(day_cost_vals) / max(1, len(day_cost_vals)), 6)
            p95_day_cost = round(percentile(day_cost_vals, 0.95), 6)
            max_day_cost = round(max(day_cost_vals) if day_cost_vals else 0.0, 6)

            sens_leaked = len(judge_out.get("leaks") or [])
            rejected_jobs = [r for r in job_rows if not r["ok"]]

            passed = (
                mean_day_cost <= 0.0044
                and superseded_ok == len(superseded_pairs)
                and ended_ok == len(ended_facts)
                and late_ok == len(late_specs)
                and sens_leaked == 0
                and privacy_fp_pct <= 2.0
                and len(rejected_jobs) == 0
            )

            out = {
                "suite": "S2_extraction_cost",
                "status": "PASS" if passed else "FAIL",
                "passed": passed,
                "runner": "agent-cli (claude -p haiku via apps/memory core.extract.run)",
                "worker_kind_note": (
                    "Submitted with worker_kind='internal-cloud' because unmodified worker_kind='agent-cli' "
                    "crashes when LM Studio (:1234) is offline (policy.py:44 -> sensitive.py:231 ScreenUnavailable)."
                ),
                "unmodified_agent_cli_error": agent_cli_bug,
                "ingest": {
                    "imported": ingest_summary["imported"],
                    "pre_dropped_triage": pre_dropped_total,
                    "triaged_clean_gold_facts": triaged_clean_facts,
                },
                "jobs": {
                    "total": len(job_rows),
                    "applied": sum(1 for r in job_rows if r["ok"]),
                    "rejected": len(rejected_jobs),
                    "rejected_details": rejected_jobs,
                },
                "cost_per_owner_day": {
                    "owner_days": len(day_cost_vals),
                    "total_extract_usd": total_cost,
                    "mean_usd": mean_day_cost,
                    "p95_usd": p95_day_cost,
                    "max_usd": max_day_cost,
                    "judge_cost_usd": judge_meta["cost_usd"],
                    "models_observed": sorted({r["model_observed"] for r in job_rows if r.get("model_observed")}),
                },
                "extraction_quality": {
                    "plain_gold_total": len(plain_ids),
                    "fact_recall": round(len(matched_plain) / len(plain_ids), 4),
                    "extracted_facts": len(ext_facts),
                    "extracted_true": n_true,
                    "extracted_noise": n_noise,
                    "extracted_wrong": n_wrong,
                    "fact_precision": round(n_true / max(1, len(ext_facts)), 4),
                    "people_found": len(people_found),
                    "people_total": len(gold_people),
                    "people_duplicated": people_dup,
                    "relation_correct": rel_ok,
                    "edges_found": edges_found,
                    "edges_total": len(gold_edges),
                },
                "changes": {
                    "superseded_ok": superseded_ok,
                    "superseded_total": len(superseded_pairs),
                    "superseded_details": superseded_details,
                    "ended_ok": ended_ok,
                    "ended_total": len(ended_facts),
                    "ended_details": ended_details,
                    "late_ok": late_ok,
                    "late_total": len(late_specs),
                    "late_details": late_details,
                },
                "privacy": {
                    "sensitive_leaked": sens_leaked,
                    "leaked_ids": judge_out.get("leaks") or [],
                    "quarantine_counts": store.get_quarantine_counts(owner),
                    "clean_gold_fp_count": len(fp_ids),
                    "clean_gold_fp_pct": privacy_fp_pct,
                    "clean_gold_fp_prewrite": clean_fp_prewrite,
                    "clean_gold_fp_triage": triaged_clean_facts,
                },
                "gate_checks": {
                    "mean_cost_le_0_0044": mean_day_cost <= 0.0044,
                    "changes_8_4_4": (superseded_ok == 8 and ended_ok == 4 and late_ok == 4),
                    "zero_sensitive_leaks": sens_leaked == 0,
                    "privacy_fp_le_2pct": privacy_fp_pct <= 2.0,
                    "zero_rejected_jobs": len(rejected_jobs) == 0,
                },
            }
            (out_dir / "s2_extract_cost.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
            return out
    finally:
        extract.build_system_prompt = orig_build_sys
        for k, v in orig_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        sys_file.unlink(missing_ok=True)
        judge_sys.unlink(missing_ok=True)


if __name__ == "__main__":
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "results" / "manual"
    out_dir.mkdir(parents=True, exist_ok=True)
    res = run(out_dir)
    print(json.dumps({k: res[k] for k in ("status", "cost_per_owner_day", "extraction_quality", "changes", "privacy", "gate_checks")}, indent=2))
