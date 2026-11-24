"""Suite S6: /vault/graph?view=subjects|people, 7 clusters, Rule 9, T1 tier confirmation, and 20k latency."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import time

import httpx

from common import LiveApiServer, load_gold_graph, summarize_latencies, temp_schema
from s1_retrieval import _seed_scale_corpus
from temporal_memory.db.db import fold_text

_ALLOWED_CLUSTERS = frozenset({
    "career",
    "learning",
    "projects",
    "people-family",
    "events",
    "home-money",
    "travel",
})


def run(out_dir: Path) -> dict:
    checks: dict[str, bool] = {}
    details: dict[str, object] = {}

    with temp_schema("s6") as (db, _sc):
        load_gold_graph(db, "karim_s6")
        # Add an inferred sensitive health fact + unconfirmed family entity + project + evidence link
        # to verify Rule 9 gating, zero orphan edges, and true counts before capping.
        with db.transaction() as conn:
            conn.execute(
                "INSERT INTO entities (id, owner, kind, name, status, relation_to_user, provenance) VALUES "
                "('e_proj_s6', 'karim_s6', 'project', 'Raseef App', 'active', NULL, 'user_supplied'), "
                "('e_inf_fam_s6', 'karim_s6', 'person', 'Inferred Uncle', 'candidate', 'family', 'inferred'), "
                "('e_orphan_s6', 'karim_s6', 'person', 'Hidden Ghost', 'candidate', 'friend', 'inferred') "
                "ON CONFLICT DO NOTHING"
            )
            conn.execute(
                "INSERT INTO subjects (id, owner, parent_id, path, label, kind, status, provenance, sensitive_cat) VALUES "
                "('s_health_s6', 'karim_s6', NULL, 'health/sleep', 'Sleep', 'topic', 'active', 'inferred', 'health'), "
                "('s_faith_s6', 'karim_s6', NULL, 'faith/prayer', 'Prayer', 'topic', 'active', 'inferred', 'religion') "
                "ON CONFLICT DO NOTHING"
            )
            conn.execute(
                "INSERT INTO records (id, owner, source, at, author, text, content_hash) VALUES "
                "('r_s6_1', 'karim_s6', 'notes', '2026-11-18', 'Karim', 'Raseef App sprint review with Omar', 'hs6_1'), "
                "('r_s6_sens', 'karim_s6', 'notes', '2026-11-18', 'Karim', 'Karim slept 5 hours', 'hs6_sens') "
                "ON CONFLICT DO NOTHING"
            )
            conn.execute(
                "INSERT INTO facts (id, owner, text, text_folded, subject_id, valid_from, status, provenance, content_hash) VALUES "
                "('f_s6_proj', 'karim_s6', 'Omar reviewed Raseef App.', 'omar reviewed raseef app', 's_health_s6', '2026-11-18', 'active', 'user_supplied', 'fs6_proj'), "
                "('f_s6_sens', 'karim_s6', 'Karim slept 5 hours.', 'karim slept 5 hours', 's_health_s6', '2026-11-18', 'active', 'inferred', 'fs6_sens'), "
                "('f_s6_faith', 'karim_s6', 'Karim prayed Dhuhr.', 'karim prayed dhuhr', 's_faith_s6', '2026-11-18', 'active', 'inferred', 'fs6_faith') "
                "ON CONFLICT DO NOTHING"
            )
            conn.execute(
                "INSERT INTO fact_entities (owner, fact_id, entity_id) VALUES "
                "('karim_s6', 'f_s6_proj', 'p02'), ('karim_s6', 'f_s6_proj', 'e_proj_s6'), "
                "('karim_s6', 'f_s6_sens', 'e_orphan_s6') ON CONFLICT DO NOTHING"
            )
            conn.execute(
                "INSERT INTO links (id, owner, src, rel, dst, valid_from, evidence_fact_id) VALUES "
                "('l_s6_proj', 'karim_s6', 'p02', 'WORKS_ON', 'e_proj_s6', '2026-11-18', 'f_s6_proj'), "
                "('l_s6_orphan', 'karim_s6', 'p01', 'KNOWS', 'e_orphan_s6', '2026-11-18', 'f_s6_sens') "
                "ON CONFLICT DO NOTHING"
            )

        with LiveApiServer(db) as srv:
            srv.create_owner("layla_s6", label="layla_s6", kind="demo", display_name="Layla")
            tok_owner = srv.mint_token("owner-device", owner="karim_s6", label="s6")
            tok_other = srv.mint_token("owner-device", owner="layla_s6", label="s6_other")
            tok_worker = srv.mint_token("worker", label="s6_w")
            hdrs = {"Authorization": f"Bearer {tok_owner}"}
            hdr_other = {"Authorization": f"Bearer {tok_other}"}
            hdr_worker = {"Authorization": f"Bearer {tok_worker}"}
            hdr_admin = srv.admin_headers

            with httpx.Client(base_url=srv.base_url, timeout=15.0) as c:
                r_subj = c.get("/v1/owners/karim_s6/vault/graph", headers=hdrs, params={"view": "subjects", "max_per_group": 2})
                r_ppl_cap = c.get("/v1/owners/karim_s6/vault/graph", headers=hdrs, params={"view": "people", "max_per_group": 2})
                r_ppl_full = c.get("/v1/owners/karim_s6/vault/graph", headers=hdrs, params={"view": "people", "max_per_group": 100})
                r_xowner = c.get("/v1/owners/karim_s6/vault/graph", headers=hdr_other, params={"view": "subjects"})
                r_worker = c.get("/v1/owners/karim_s6/vault/graph", headers=hdr_worker, params={"view": "subjects"})

                checks["subjects_200"] = r_subj.status_code == 200
                checks["people_200"] = r_ppl_cap.status_code == 200 and r_ppl_full.status_code == 200
                checks["cross_owner_403"] = r_xowner.status_code == 403
                checks["worker_403"] = r_worker.status_code == 403

                gs = r_subj.json()
                gp_cap = r_ppl_cap.json()
                gp_full = r_ppl_full.json()

                clusters = {n["group"] for n in gs.get("nodes", []) if n.get("kind") == "cluster"}
                checks["subjects_only_7_clusters"] = bool(clusters) and clusters.issubset(_ALLOWED_CLUSTERS)
                checks["subjects_no_health_or_faith"] = (
                    "health" not in clusters
                    and "faith" not in clusters
                    and all(n.get("id") not in ("s_health_s6", "s_faith_s6") for n in gs.get("nodes", []))
                )
                checks["subjects_centered_on_karim"] = gs.get("center_id") == "p01" and gs.get("version") == "1"

                full_labels = {n["label"] for n in gp_full.get("nodes", [])}
                full_groups = {n["group"] for n in gp_full.get("nodes", [])}
                cap_node_ids = {n["id"] for n in gp_cap.get("nodes", [])}
                checks["people_includes_projects_orgs_places"] = (
                    "people" in full_groups and "places" in full_groups and "orgs" in full_groups and "projects" in full_groups
                )
                checks["sensitive_inferred_and_unconfirmed_family_hidden"] = (
                    "Hidden Ghost" not in full_labels and "Inferred Uncle" not in full_labels
                )
                checks["counts_computed_before_capping"] = (
                    all(
                        gp_cap.get("counts", {}).get(k) == gp_full.get("counts", {}).get(k)
                        for k in ("total_nodes", "people", "places", "projects", "relations")
                    )
                    and gp_cap.get("counts", {}).get("shown_nodes", 0) < gp_full.get("counts", {}).get("total_nodes", 0)
                    and bool(gp_cap.get("counts", {}).get("hidden_by_group"))
                )
                checks["no_orphan_edges"] = all(
                    e["src"] in cap_node_ids and e["dst"] in cap_node_ids for e in gp_cap.get("edges", [])
                )

                p02_before = next((n for n in gp_full.get("nodes", []) if n["id"] == "p02"), {})
                checks["tier_null_until_confirmed"] = p02_before.get("tier") is None

                # Confirm tier strictly owner-device only
                r_t_adm = c.post("/v1/owners/karim_s6/vault/people/p02/tier", headers=hdr_admin, json={"tier": "T1"})
                r_t_wrk = c.post("/v1/owners/karim_s6/vault/people/p02/tier", headers=hdr_worker, json={"tier": "T1"})
                r_t_oth = c.post("/v1/owners/karim_s6/vault/people/p02/tier", headers=hdr_other, json={"tier": "T1"})
                r_t_ok = c.post("/v1/owners/karim_s6/vault/people/p02/tier", headers=hdrs, json={"tier": "T1"})

                checks["tier_strict_owner_auth"] = (
                    r_t_adm.status_code == 403
                    and r_t_wrk.status_code == 403
                    and r_t_oth.status_code == 403
                    and r_t_ok.status_code == 200
                    and r_t_ok.json().get("closeness_tier") == "T1"
                )
                gp_after = c.get("/v1/owners/karim_s6/vault/graph", headers=hdrs, params={"view": "people", "max_per_group": 100}).json()
                p02_after = next((n for n in gp_after.get("nodes", []) if n["id"] == "p02"), {})
                checks["tier_persisted_in_graph"] = p02_after.get("tier") == "T1"

                details["counts_full"] = gp_full.get("counts")
                details["clusters"] = sorted(clusters)

    # 20k HTTP /vault/graph latency check
    with temp_schema("s6_20k") as (db20, _sc20):
        with LiveApiServer(db20) as srv20:
            srv20.create_owner("karim_s6_20k", label="karim_s6_20k", kind="demo", display_name="Karim")
            tok20 = srv20.mint_token("owner-device", owner="karim_s6_20k", label="s6_20k")
            _seed_scale_corpus(db20, "karim_s6_20k", 20_000)
            hdr20 = {"Authorization": f"Bearer {tok20}"}
            lat_s, lat_p = [], []
            with httpx.Client(base_url=srv20.base_url, timeout=15.0) as c20:
                # Warm connection pool on Windows (avoids cold IPv6 localhost connect outlier)
                for _v in ("subjects", "people"):
                    assert c20.get("/v1/owners/karim_s6_20k/vault/graph", headers=hdr20, params={"view": _v}).status_code == 200
                for _ in range(100):
                    t0 = time.perf_counter()
                    assert c20.get("/v1/owners/karim_s6_20k/vault/graph", headers=hdr20, params={"view": "subjects"}).status_code == 200
                    lat_s.append((time.perf_counter() - t0) * 1000.0)
                    t0 = time.perf_counter()
                    assert c20.get("/v1/owners/karim_s6_20k/vault/graph", headers=hdr20, params={"view": "people"}).status_code == 200
                    lat_p.append((time.perf_counter() - t0) * 1000.0)
            sum_s = summarize_latencies(lat_s)
            sum_p = summarize_latencies(lat_p)
            details["latency_20k"] = {"graph_subjects": sum_s, "graph_people": sum_p}
            checks["graph_20k_subjects_p95_lt_150ms"] = sum_s["p95_ms"] < 150.0
            checks["graph_20k_people_p95_lt_150ms"] = sum_p["p95_ms"] < 150.0

    passed = all(checks.values())
    out = {
        "suite": "S6_vault_graph",
        "status": "PASS" if passed else "FAIL",
        "passed": passed,
        "checks": checks,
        "details": details,
    }
    (out_dir / "s6_graph.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


if __name__ == "__main__":
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "results" / "manual"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(json.dumps(run(out_dir), indent=2))
