"""Suite S10: U4 Hybrid Search ablation (keyword-only vs hybrid) + 20 paraphrase probes + 20k HNSW vs exact benchmark."""
from __future__ import annotations

import json
import os
from pathlib import Path
import time

import httpx
import numpy as np

from temporal_memory.core.embed import (
    EMBED_DIM,
    EMBED_MODEL,
    clear_query_cache,
    embed_pending_facts,
    embed_query,
)
from temporal_memory.live import context as live_ctx

from common import (
    ACCEPTANCE_DIR,
    LiveApiServer,
    hardware_info,
    load_gold_graph,
    load_probes,
    score_probe_runs,
    summarize_latencies,
    temp_schema,
)
from s1_retrieval import _seed_scale_corpus

PARAPHRASE_PATH = ACCEPTANCE_DIR / "paraphrase_probes.json"


def _run_probes(
    srv: LiveApiServer, owner: str, token: str, probes: list[dict], *, uncached: bool = True
) -> dict:
    hdrs = {"Authorization": f"Bearer {token}"}
    hits_ctx: dict[str, dict] = {}
    hits_srch: dict[str, dict] = {}
    with httpx.Client(base_url=srv.base_url, timeout=15.0) as client:
        for p in probes:
            tid = p["turn_id"]
            q = p["text"]
            if uncached:
                clear_query_cache()
            t0 = time.perf_counter()
            r1 = client.post(f"/v1/owners/{owner}/context", headers=hdrs, json={"text": q, "max_tokens": 1500})
            r1.raise_for_status()
            d1 = r1.json()
            hits_ctx[tid] = {
                "ids": [f["id"] for f in d1.get("facts", [])],
                "texts": [f["text"] for f in d1.get("facts", [])],
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            }

            if uncached:
                clear_query_cache()
            t0 = time.perf_counter()
            r2 = client.get(f"/v1/owners/{owner}/search", headers=hdrs, params={"q": q, "limit": 16})
            r2.raise_for_status()
            d2 = r2.json()
            hits_srch[tid] = {
                "ids": [f["id"] for f in d2.get("facts", [])],
                "texts": [f["text"] for f in d2.get("facts", [])],
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            }
    return {
        "context_pack": score_probe_runs(probes, hits_ctx),
        "http_search": score_probe_runs(probes, hits_srch),
    }


def _seed_20k_vectors(db, owner: str, n: int = 20000) -> None:
    rng = np.random.default_rng(42)
    mat = rng.normal(size=(n, EMBED_DIM)).astype(np.float32)
    mat /= np.clip(np.linalg.norm(mat, axis=1, keepdims=True), 1e-12, None)
    vec_lits = ["[" + ",".join(f"{x:.4f}" for x in row) + "]" for row in mat]

    with db.transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS _tmp_vec")
            cur.execute("CREATE TEMP TABLE _tmp_vec (id TEXT, vec TEXT) ON COMMIT DROP")
            with cur.copy("COPY _tmp_vec (id, vec) FROM STDIN") as cp:
                for k in range(n):
                    cp.write_row((f"f{k}", vec_lits[k]))
            cur.execute(
                """
                UPDATE facts f
                SET embedding = v.vec::public.vector,
                    embedding_model = %s,
                    embedded_at = now()
                FROM _tmp_vec v
                WHERE f.owner = %s AND f.id = v.id
                """,
                (EMBED_MODEL, owner),
            )
    # Also embed the needle fact with the real model (outside bulk-update tx so row locks are released)
    cur_embed = embed_pending_facts(db, owner=owner, batch_size=64)
    with db.transaction() as conn:
        conn.execute("ANALYZE facts")
    return cur_embed


def run(out_dir: Path | None = None, *, out_file: Path | None = None) -> dict:
    gold_probes = load_probes()
    para_probes = json.loads(PARAPHRASE_PATH.read_text(encoding="utf-8"))["probes"]
    orig_sem = os.environ.get("TM_SEMANTIC")
    orig_exact = os.environ.get("TM_SEMANTIC_EXACT")

    try:
        # 1. Ablation on Karim gold ledger (keyword-only vs hybrid)
        with temp_schema("s10_gold") as (db, _):
            load_gold_graph(db, "karim_gold")
            t_bf = time.perf_counter()
            bf_stats = embed_pending_facts(db, owner="karim_gold", batch_size=64)
            bf_ms = round((time.perf_counter() - t_bf) * 1000, 1)

            with db.connection() as conn:
                embedded_cnt = conn.execute(
                    "SELECT COUNT(*)::int AS c FROM facts WHERE owner = 'karim_gold' AND embedding IS NOT NULL"
                ).fetchone()["c"]
                quar_cnt = conn.execute(
                    "SELECT COUNT(*)::int AS c FROM quarantine WHERE owner = 'karim_gold' AND status = 'held'"
                ).fetchone()["c"]
                hist_emb_cnt = conn.execute(
                    "SELECT COUNT(*)::int AS c FROM facts WHERE owner = 'karim_gold' AND status = 'history' AND embedding IS NOT NULL"
                ).fetchone()["c"]

            # Quick warmup of local ONNX session
            _ = embed_query("warmup")

            with LiveApiServer(db) as srv:
                owner_tok = srv.mint_token("owner-device", owner="karim_gold", label="s10")

                os.environ["TM_SEMANTIC"] = "0"
                live_ctx._PACK_CACHE.clear()
                kw_gold = _run_probes(srv, "karim_gold", owner_tok, gold_probes, uncached=False)
                kw_para = _run_probes(srv, "karim_gold", owner_tok, para_probes, uncached=False)

                os.environ["TM_SEMANTIC"] = "1"
                live_ctx._PACK_CACHE.clear()
                hy_gold = _run_probes(srv, "karim_gold", owner_tok, gold_probes, uncached=True)
                hy_para = _run_probes(srv, "karim_gold", owner_tok, para_probes, uncached=True)

        # 2. 20k scale benchmark (HNSW vs exact scan, uncached vs cached query embedding)
        scale_20k = {}
        with temp_schema("s10_20k") as (db2, _schema2):
            with db2.transaction() as conn:
                conn.execute(
                    "INSERT INTO owners (id, label, kind) VALUES ('scale_20k', 'scale_20k', 'simulated') ON CONFLICT DO NOTHING"
                )
            _seed_scale_corpus(db2, "scale_20k", 20000)
            t0 = time.perf_counter()
            _seed_20k_vectors(db2, "scale_20k", 20000)
            seed_s = round(time.perf_counter() - t0, 2)

            with LiveApiServer(db2) as srv2:
                tok2 = srv2.mint_token("owner-device", owner="scale_20k", label="s10-20k")
                hdrs2 = {"Authorization": f"Bearer {tok2}"}
                queries = [
                    f"When did Karim meet Careem in Business Bay round {i}?" for i in range(30)
                ]
                # Warmup HTTP + DB pool + ONNX
                with httpx.Client(base_url=srv2.base_url, timeout=15.0) as client:
                    client.post("/v1/owners/scale_20k/context", headers=hdrs2, json={"text": "warmup dentist", "max_tokens": 1500}).raise_for_status()

                    for mode_name, exact_flag, clear_cache in [
                        ("hnsw_uncached_embed", "0", True),
                        ("hnsw_cached_embed", "0", False),
                        ("exact_uncached_embed", "1", True),
                        ("exact_cached_embed", "1", False),
                    ]:
                        os.environ["TM_SEMANTIC"] = "1"
                        os.environ["TM_SEMANTIC_EXACT"] = exact_flag
                        live_ctx._PACK_CACHE.clear()
                        lats_ctx = []
                        lats_srch = []
                        for q in queries:
                            if clear_cache:
                                clear_query_cache()
                                live_ctx._PACK_CACHE.clear()
                            t_q = time.perf_counter()
                            r1 = client.post("/v1/owners/scale_20k/context", headers=hdrs2, json={"text": q, "max_tokens": 1500})
                            r1.raise_for_status()
                            lats_ctx.append((time.perf_counter() - t_q) * 1000)

                            if clear_cache:
                                clear_query_cache()
                            t_q = time.perf_counter()
                            r2 = client.get("/v1/owners/scale_20k/search", headers=hdrs2, params={"q": q, "limit": 16})
                            r2.raise_for_status()
                            lats_srch.append((time.perf_counter() - t_q) * 1000)
                        scale_20k[mode_name] = {
                            "context": summarize_latencies(lats_ctx),
                            "search": summarize_latencies(lats_srch),
                        }

                    # Check needle recall semantically with zero shared words
                    clear_query_cache()
                    r_n = client.get(
                        "/v1/owners/scale_20k/search",
                        headers=hdrs2,
                        params={"q": "What oral clinic appointment recall does Karim have from 2015?", "limit": 16},
                    )
                    r_n.raise_for_status()
                    needle_ids = [f["id"] for f in r_n.json().get("facts", [])]
    finally:
        if orig_sem is None:
            os.environ.pop("TM_SEMANTIC", None)
        else:
            os.environ["TM_SEMANTIC"] = orig_sem
        if orig_exact is None:
            os.environ.pop("TM_SEMANTIC_EXACT", None)
        else:
            os.environ["TM_SEMANTIC_EXACT"] = orig_exact

    needle_hit = "f_needle" in needle_ids
    hy_gold_ov = hy_gold["context_pack"]["overall"]
    kw_para_ov = kw_para["context_pack"]["overall"]
    hy_para_ov = hy_para["context_pack"]["overall"]
    gate_checks = {
        "gold_hybrid_top16_ge_085": hy_gold_ov["top16_macro_38"] >= 0.85,
        "gold_hybrid_zero_sens_leaks": hy_gold_ov["sensitive_leaks_top16"] == 0,
        "paraphrase_hybrid_beats_keyword": hy_para_ov["top16_macro_38"] > kw_para_ov["top16_macro_38"],
        "hnsw_cached_20k_ctx_p95_lt_150ms": scale_20k["hnsw_cached_embed"]["context"]["p95_ms"] < 150.0,
        "scale_20k_needle_semantic_hit": needle_hit,
    }
    passed = all(gate_checks.values())

    out = {
        "suite": "S10_hybrid_ablation",
        "status": "PASS" if passed else "FAIL",
        "passed": passed,
        "gate_checks": gate_checks,
        "hardware": hardware_info(),
        "model": EMBED_MODEL,
        "dim": EMBED_DIM,
        "min_sim": os.environ.get("TM_SEMANTIC_MIN_SIM", "0.40"),
        "weight": os.environ.get("TM_SEMANTIC_WEIGHT", "0.35"),
        "backfill": {"stats": bf_stats, "elapsed_ms": bf_ms, "embedded_facts": embedded_cnt, "quarantine_held": quar_cnt, "history_embedded": hist_emb_cnt},
        "gold_keyword_only": kw_gold,
        "gold_hybrid": hy_gold,
        "paraphrase_keyword_only": kw_para,
        "paraphrase_hybrid": hy_para,
        "scale_20k_seed_s": seed_s,
        "scale_20k": scale_20k,
        "scale_20k_needle_semantic_hit": needle_hit,
    }
    target_path = out_file or ((out_dir / "s10_hybrid_ablation.json") if out_dir is not None else None)
    if target_path is not None:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(json.dumps(out, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
    return out


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        arg = Path(sys.argv[1])
        if arg.suffix.lower() == ".json":
            res = run(out_file=arg)
        else:
            res = run(out_dir=arg)
    else:
        res = run(out_dir=ACCEPTANCE_DIR / "results" / "manual")
    print(json.dumps({
        "suite": res["suite"],
        "status": res["status"],
        "passed": res["passed"],
        "gate_checks": res["gate_checks"],
        "scale_20k_needle_semantic_hit": res["scale_20k_needle_semantic_hit"],
    }, indent=2))
