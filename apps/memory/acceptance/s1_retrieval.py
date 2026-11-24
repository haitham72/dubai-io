"""Suite S1: Retrieval quality (gold + extracted, 3 HTTP paths, per-bucket, leaks & noise) + HTTP latency at 1k/5k/20k + concurrent writer."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import random
import sys
import threading
import time

import httpx

from temporal_memory.core import applier
from temporal_memory.db.db import fold_text
from temporal_memory.live import context as live_ctx
from temporal_memory.models import Attempt, ExtractionOutput, FactEntity, Job, OutEntity, OutFact

from common import (
    LiveApiServer,
    hardware_info,
    load_gold,
    load_gold_graph,
    load_graph_snapshot,
    load_probes,
    mcp_call,
    score_probe_runs,
    summarize_latencies,
    temp_schema,
)


def _run_40_probes(srv: LiveApiServer, owner: str, token: str, probes: list[dict], extracted_to_gold: dict[str, list[str]] | None = None) -> dict:
    hdrs = {"Authorization": f"Bearer {token}"}
    hits_ctx: dict[str, dict] = {}
    hits_srch: dict[str, dict] = {}
    hits_mcp: dict[str, dict] = {}

    with httpx.Client(base_url=srv.base_url, timeout=15.0) as client:
        for p in probes:
            tid = p["turn_id"]
            q = p["text"]

            t0 = time.perf_counter()
            r1 = client.post(f"/v1/owners/{owner}/context", headers=hdrs, json={"text": q, "max_tokens": 1500})
            r1.raise_for_status()
            d1 = r1.json()
            hits_ctx[tid] = {
                "ids": [f["id"] for f in d1.get("facts", [])],
                "texts": [f["text"] for f in d1.get("facts", [])],
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            }

            t0 = time.perf_counter()
            r2 = client.get(f"/v1/owners/{owner}/search", headers=hdrs, params={"q": q, "limit": 16})
            r2.raise_for_status()
            d2 = r2.json()
            hits_srch[tid] = {
                "ids": [f["id"] for f in d2.get("facts", [])],
                "texts": [f["text"] for f in d2.get("facts", [])],
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            }

            t0 = time.perf_counter()
            d3 = mcp_call(client, token, "memory_search", {"query": q, "owner": owner, "limit": 16})
            hits_mcp[tid] = {
                "ids": [f["id"] for f in d3.get("facts", [])],
                "texts": [f["text"] for f in d3.get("facts", [])],
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            }

    return {
        "context_pack": score_probe_runs(probes, hits_ctx, extracted_to_gold=extracted_to_gold),
        "http_search": score_probe_runs(probes, hits_srch, extracted_to_gold=extracted_to_gold),
        "mcp_memory_search": score_probe_runs(probes, hits_mcp, extracted_to_gold=extracted_to_gold),
    }


def _seed_scale_corpus(db, owner: str, n: int) -> None:
    rng = random.Random(7)
    names = ["Omar", "Layla", "Karim", "Sara", "Yousef", "Huda", "Rami", "Noor", "Tariq", "Mina"] + [f"Person{i}" for i in range(190)]
    places = ["Business Bay", "JLT", "Marina", "Deira", "Jumeirah", "Al Barsha", "DIFC", "Karama"]
    orgs = ["Emirates NBD", "Careem", "Noon", "DEWA", "Talabat", "Etisalat", "du", "Majid Al Futtaim"]
    verbs = ["works at", "met with", "moved to", "visited", "called about", "paid AED 450 to", "joined", "left"]
    topics = ["work", "family", "housing", "travel", "fitness", "finance", "car", "food"]

    with db.transaction() as conn:
        cur = conn.cursor()
        with cur.copy("COPY entities (id, owner, kind, name, status) FROM STDIN") as cp:
            for i, nm in enumerate(names):
                cp.write_row((f"e{i}", owner, "person", nm, "active"))
        with cur.copy("COPY entity_aliases (owner, entity_id, alias, alias_folded) FROM STDIN") as cp:
            for i, nm in enumerate(names):
                cp.write_row((owner, f"e{i}", nm, fold_text(nm)))
        with cur.copy("COPY subjects (id, owner, path, label, kind, status) FROM STDIN") as cp:
            for j, t in enumerate(topics):
                cp.write_row((f"s{j}", owner, f"life/{t}", t, "topic", "active"))
        with cur.copy("COPY records (id, owner, source, at, author, text, content_hash) FROM STDIN") as cp:
            for k in range(n):
                ei = k % len(names)
                day = f"20{20 + k * 6 // max(n, 1):02d}-{1 + k % 12:02d}-{1 + k % 28:02d}"
                text = f"{names[ei]} {verbs[k % len(verbs)]} {orgs[k % len(orgs)]} in {places[k % len(places)]} (note {k})"
                cp.write_row((f"r{k}", owner, "whatsapp", day, names[ei], text, f"h_{owner}_{k}"))
            cp.write_row(("r_needle", owner, "gmail", "2015-01-01", "clinic", "zanzibarite dentist recall", f"needle_{owner}"))
        with cur.copy("COPY facts (id, owner, text, text_folded, subject_id, valid_from, status, provenance, content_hash) FROM STDIN") as cp:
            for k in range(n):
                ei = k % len(names)
                day = f"20{20 + k * 6 // max(n, 1):02d}-{1 + k % 12:02d}-{1 + k % 28:02d}"
                text = f"{names[ei]} {verbs[k % len(verbs)]} {orgs[k % len(orgs)]} in {places[k % len(places)]} (note {k})"
                cp.write_row((f"f{k}", owner, text, fold_text(text), f"s{rng.randrange(len(topics))}", day, "active", "user_supplied", f"h_{owner}_{k}"))
            cp.write_row(("f_needle", owner, "Karim has a zanzibarite dentist recall", "karim has a zanzibarite dentist recall", "s4", "2015-01-01", "active", "user_supplied", f"needle_{owner}"))
        with cur.copy("COPY fact_entities (owner, fact_id, entity_id) FROM STDIN") as cp:
            for k in range(n):
                cp.write_row((owner, f"f{k}", f"e{k % len(names)}"))
            cp.write_row((owner, "f_needle", "e2"))
        with cur.copy("COPY fact_evidence (owner, fact_id, record_id) FROM STDIN") as cp:
            for k in range(n):
                cp.write_row((owner, f"f{k}", f"r{k}"))
            cp.write_row((owner, "f_needle", "r_needle"))
        conn.execute("UPDATE owners SET facts_version = 1, alias_version = 1 WHERE id = %s", (owner,))
    with db.connection() as conn:
        conn.execute("ANALYZE")


def _run_http_latency(n_facts: int, *, with_writer: bool = False) -> dict:
    with temp_schema(f"lat_{n_facts}") as (db, _sc):
        with LiveApiServer(db) as srv:
            owner = f"bench_{n_facts}"
            srv.create_owner(owner, label=owner, kind="demo", display_name="Karim")
            token = srv.mint_token("owner-device", owner=owner, label="lat")
            _seed_scale_corpus(db, owner, n_facts)
            live_ctx.invalidate_alias_cache()

            hdrs = {"Authorization": f"Bearer {token}"}
            queries = [
                "Where does Omar work now?",
                "What did Layla say about Careem?",
                "Who works in DIFC?",
                "Tell me about Karim at Etisalat",
                "Where did Sara move to?",
            ]

            with httpx.Client(base_url=srv.base_url, timeout=30.0) as client:
                # Cold request
                t0 = time.perf_counter()
                rc = client.post(f"/v1/owners/{owner}/context", headers=hdrs, json={"text": queries[0], "max_tokens": 1500})
                rc.raise_for_status()
                cold_ms = round((time.perf_counter() - t0) * 1000, 2)

                # Warm n=100 for context, search, mcp_search
                ctx_lat, srch_lat, mcp_lat = [], [], []
                for i in range(100):
                    q = queries[i % len(queries)]
                    t0 = time.perf_counter()
                    r = client.post(f"/v1/owners/{owner}/context", headers=hdrs, json={"text": q, "max_tokens": 1500})
                    r.raise_for_status()
                    ctx_lat.append((time.perf_counter() - t0) * 1000)

                    t0 = time.perf_counter()
                    r2 = client.get(f"/v1/owners/{owner}/search", headers=hdrs, params={"q": "Careem", "limit": 20})
                    r2.raise_for_status()
                    srch_lat.append((time.perf_counter() - t0) * 1000)

                    t0 = time.perf_counter()
                    mcp_call(client, token, "memory_search", {"query": "Careem", "owner": owner, "limit": 20})
                    mcp_lat.append((time.perf_counter() - t0) * 1000)

                out = {
                    "n_facts": n_facts,
                    "context_cold_ms": cold_ms,
                    "context_warm": summarize_latencies(ctx_lat),
                    "http_search_warm": summarize_latencies(srch_lat),
                    "mcp_search_warm": summarize_latencies(mcp_lat),
                }

                # 20k old needle test across all 3 paths
                if n_facts == 20000:
                    rc_n = client.post(f"/v1/owners/{owner}/context", headers=hdrs, json={"text": "zanzibarite dentist", "max_tokens": 1500}).json()
                    rs_n = client.get(f"/v1/owners/{owner}/search", headers=hdrs, params={"q": "zanzibarite", "limit": 20}).json()
                    rm_n = mcp_call(client, token, "memory_search", {"query": "zanzibarite", "owner": owner, "limit": 20})
                    out["needle_2015"] = {
                        "context_pack": any(f["id"] == "f_needle" for f in rc_n.get("facts", [])),
                        "http_search": any(f["id"] == "f_needle" for f in rs_n.get("facts", [])),
                        "mcp_memory_search": any(f["id"] == "f_needle" for f in rm_n.get("facts", [])),
                    }

                if with_writer:
                    stop_ev = threading.Event()
                    writer_stats = {"applied": 0, "errors": 0}

                    def _writer_loop():
                        idx = 0
                        while not stop_ev.is_set():
                            rid = f"rw_{idx}"
                            txt = f"Omar met Sara at DIFC coffee shop batch {idx}"
                            h = hashlib.sha256(f"{owner}_{rid}".encode()).hexdigest()
                            try:
                                with db.transaction() as conn:
                                    conn.execute(
                                        "INSERT INTO records (id, owner, source, at, author, text, content_hash) "
                                        "VALUES (%s, %s, 'live', '2026-11-24', 'Karim', %s, %s) ON CONFLICT DO NOTHING",
                                        (rid, owner, txt, h),
                                    )
                                job = Job(
                                    id=f"j_w_{idx}", owner=owner, kind="extract.day", priority=1,
                                    pool="internal", input_ref=[rid], input_version=0,
                                    context_hash="", prompt_version="extract@3", day="2026-11-24", state="leased",
                                )
                                att = Attempt(
                                    job_id=job.id, attempt_no=1, fence_token="f", worker_id="w-bench",
                                    worker_kind="internal-cloud", model="haiku", prompt_version="extract@3",
                                    output=ExtractionOutput(
                                        entities=[OutEntity(ref="e0", kind="person", aliases=[], relation_to_user="friend")],
                                        facts=[OutFact(
                                            text=txt, text_orig=None, subject_path="life/work",
                                            entities=[FactEntity(entity_id="e0", role=None)],
                                            op="new", target=None, valid_from="2026-11-24",
                                            evidence=[rid], sensitive=None,
                                        )],
                                        links=[],
                                    ),
                                )
                                v = applier.apply(owner, job, att, db=db)
                                if v.ok:
                                    writer_stats["applied"] += 1
                            except Exception:
                                writer_stats["errors"] += 1
                            idx += 1
                            time.sleep(0.15)

                    wt = threading.Thread(target=_writer_loop, daemon=True)
                    wt.start()
                    cw_lat = []
                    cw_errs = 0
                    try:
                        for i in range(100):
                            t0 = time.perf_counter()
                            try:
                                r = client.post(f"/v1/owners/{owner}/context", headers=hdrs, json={"text": queries[i % len(queries)], "max_tokens": 1500})
                                r.raise_for_status()
                                cw_lat.append((time.perf_counter() - t0) * 1000)
                            except Exception:
                                cw_errs += 1
                    finally:
                        stop_ev.set()
                        wt.join(timeout=5.0)
                    out["context_during_writer"] = {
                        **summarize_latencies(cw_lat),
                        "http_errors": cw_errs,
                        "writer_commits": writer_stats["applied"],
                        "writer_errors": writer_stats["errors"],
                    }
                return out


def run(out_dir: Path) -> dict:
    probes = load_probes()
    hw = hardware_info()
    (out_dir / "hardware.json").write_text(json.dumps(hw, indent=2), encoding="utf-8")

    # 1. Gold graph mode
    with temp_schema("s1_gold") as (db, _sc):
        gold_load = load_gold_graph(db, "karim_gold")
        live_ctx.invalidate_alias_cache()
        with LiveApiServer(db) as srv:
            tok = srv.mint_token("owner-device", owner="karim_gold", label="s1_gold")
            gold_res = _run_40_probes(srv, "karim_gold", tok, probes)

    # 2. Extracted graph mode (from S2 snapshot + judge)
    snap_path = out_dir / "s2_extracted_graph.json"
    judge_path = out_dir / "s2_judge.json"
    ext_res = None
    if snap_path.exists() and judge_path.exists():
        judge = json.loads(judge_path.read_text(encoding="utf-8"))
        e2g: dict[str, list[str]] = {}
        for gfid, ext_ids in (judge.get("facts") or {}).items():
            for eid in ext_ids:
                e2g.setdefault(eid, []).append(gfid)
        with temp_schema("s1_ext") as (db, _sc):
            owner_ext = load_graph_snapshot(db, snap_path)
            live_ctx.invalidate_alias_cache()
            with LiveApiServer(db) as srv:
                tok = srv.mint_token("owner-device", owner=owner_ext, label="s1_ext")
                ext_res = _run_40_probes(srv, owner_ext, tok, probes, extracted_to_gold=e2g)

    # 3. Authenticated HTTP latency (1k, 5k, 20k + concurrent writer)
    lat_1k = _run_http_latency(1000, with_writer=False)
    lat_5k = _run_http_latency(5000, with_writer=False)
    lat_20k = _run_http_latency(20000, with_writer=True)
    latency = {"hardware": hw, "sizes": {"1000": lat_1k, "5000": lat_5k, "20000": lat_20k}}
    (out_dir / "s1_latency_http.json").write_text(json.dumps(latency, indent=2), encoding="utf-8")

    # Evaluate against §6 gates
    needle = lat_20k.get("needle_2015", {})
    lat_ok = (
        lat_20k["context_warm"]["p95_ms"] < 150.0
        and lat_20k["http_search_warm"]["p95_ms"] < 150.0
        and lat_20k["mcp_search_warm"]["p95_ms"] < 150.0
        and lat_20k["context_during_writer"]["p95_ms"] < 150.0
        and all(needle.values())
    )
    gold_ctx = gold_res["context_pack"]["overall"]
    qual_ok = (
        gold_ctx["top8_macro_38"] >= 0.78
        and gold_ctx["top16_macro_38"] >= 0.85
        and (gold_res["context_pack"]["by_bucket"].get("arabic", {}).get("top16_raw") or 0.0) >= 0.80
        and gold_ctx["sensitive_leaks_top16"] == 0
    )
    if ext_res is not None:
        ext_ctx = ext_res["context_pack"]["overall"]
        qual_ok = qual_ok and ext_ctx["sensitive_leaks_top16"] == 0

    passed = bool(lat_ok and qual_ok)
    out = {
        "suite": "S1_retrieval",
        "status": "PASS" if passed else "FAIL",
        "passed": passed,
        "gold_load_stats": gold_load,
        "gold_mode": gold_res,
        "extracted_mode": ext_res,
        "latency_summary": {
            "1k_ctx_p95_ms": lat_1k["context_warm"]["p95_ms"],
            "5k_ctx_p95_ms": lat_5k["context_warm"]["p95_ms"],
            "20k_ctx_p95_ms": lat_20k["context_warm"]["p95_ms"],
            "20k_ctx_during_writer_p95_ms": lat_20k["context_during_writer"]["p95_ms"],
            "20k_search_p95_ms": lat_20k["http_search_warm"]["p95_ms"],
            "20k_mcp_p95_ms": lat_20k["mcp_search_warm"]["p95_ms"],
            "needle_2015": needle,
        },
        "gate_checks": {
            "latency_20k_p95_lt_150ms_all_paths": lat_ok,
            "needle_2015_all_paths": all(needle.values()),
            "gold_quality_and_zero_sens_leaks": qual_ok,
        },
    }
    (out_dir / "s1_retrieval.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


if __name__ == "__main__":
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "results" / "manual"
    out_dir.mkdir(parents=True, exist_ok=True)
    res = run(out_dir)
    print(json.dumps({"status": res["status"], "latency_summary": res["latency_summary"], "gate_checks": res["gate_checks"]}, indent=2))
