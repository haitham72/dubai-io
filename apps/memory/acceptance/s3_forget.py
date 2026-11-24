"""Suite S3: Forget completeness (bridge fact_id, bridge record_ids, direct forget_source, warm cache, in-flight job)."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

import httpx

from temporal_memory.core.graph_store import PostgresGraphStore
from temporal_memory.db.db import fold_text
from temporal_memory.live import context as live_ctx
from temporal_memory.models import Attempt, ExtractionOutput, FactEntity, OutFact, Worker
from temporal_memory.privacy.forget import forget_source
from temporal_memory.queue.jobs import PostgresJobs

from common import LiveApiServer, mcp_call, temp_schema


def _seed_forget_fixture(db, owner: str) -> dict:
    store = PostgresGraphStore(db)
    store.create_owner(owner, label=owner, kind="demo", display_name="Karim Haddad", self_aliases=["Karim"])
    with db.transaction() as conn:
        conn.execute(
            "INSERT INTO subjects (id, owner, parent_id, path, label, kind, status, fact_count) "
            "VALUES ('s_fam', %s, NULL, 'people-family/updates', 'Family Updates', 'topic', 'active', 3)",
            (owner,),
        )
        conn.execute(
            "INSERT INTO entities (id, owner, kind, name, status, relation_to_user) "
            "VALUES ('e_self', %s, 'person', 'Karim Haddad', 'active', 'self'), "
            "('e_tariq', %s, 'person', 'Uncle Tariq', 'active', 'family'), "
            "('e_careem', %s, 'org', 'Careem', 'active', NULL)",
            (owner, owner, owner),
        )
        for eid, al in [("e_tariq", "Uncle Tariq"), ("e_tariq", "Tariq"), ("e_tariq", "طارق"), ("e_careem", "Careem")]:
            conn.execute(
                "INSERT INTO entity_aliases (owner, entity_id, alias, alias_folded) VALUES (%s, %s, %s, %s)",
                (owner, eid, al, fold_text(al)),
            )
        recs = [
            ("r_forget", "whatsapp:family", "2026-11-10T10:00:00+04:00", "Tariq", "Uncle Tariq lives in Sharjah."),
            ("r_keep", "gmail", "2026-11-11T10:00:00+04:00", "hr", "Karim works at Careem in Dubai."),
            ("r_fact_only", "notes", "2026-11-12T10:00:00+04:00", "Karim", "Karim bought a desk lamp for AED 190."),
        ]
        for rid, src, at, auth, txt in recs:
            h = hashlib.sha256(f"{src}|{at}|{txt}".encode()).hexdigest()
            conn.execute(
                "INSERT INTO records (id, owner, source, at, author, text, content_hash) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (rid, owner, src, at, auth, txt, h),
            )
        facts = [
            ("f_only", "Uncle Tariq lives in Sharjah.", "s_fam", "2026-11-10", "r_forget", "e_tariq"),
            ("f_shared", "Karim and Careem scheduled a sync.", "s_fam", "2026-11-11", "r_forget", "e_careem"),
            ("f_fact_target", "Karim bought a desk lamp for AED 190.", "s_fam", "2026-11-12", "r_fact_only", "e_self"),
        ]
        for fid, txt, sid, vf, rid, eid in facts:
            h = hashlib.sha256(f"{sid}|{fold_text(txt)}".encode()).hexdigest()
            conn.execute(
                "INSERT INTO facts (id, owner, text, text_folded, subject_id, valid_from, status, provenance, content_hash) "
                "VALUES (%s,%s,%s,%s,%s,%s,'active','user_supplied',%s)",
                (fid, owner, txt, fold_text(txt), sid, vf, h),
            )
            conn.execute("INSERT INTO fact_entities (owner, fact_id, entity_id) VALUES (%s,%s,%s)", (owner, fid, eid))
            conn.execute("INSERT INTO fact_evidence (owner, fact_id, record_id, record_generation) VALUES (%s,%s,%s,0)", (owner, fid, rid))
        # f_shared also has r_keep
        conn.execute("INSERT INTO fact_evidence (owner, fact_id, record_id, record_generation) VALUES (%s,'f_shared','r_keep',0)", (owner,))
        conn.execute(
            "INSERT INTO links (id, owner, src, rel, dst, valid_from, evidence_fact_id) "
            "VALUES ('l_tariq', %s, 'e_self', 'FAMILY_OF', 'e_tariq', '2026-11-10', 'f_only')",
            (owner,),
        )
        conn.execute(
            "INSERT INTO entity_subjects (owner, entity_id, subject_id, role, weight, fact_count, first_seen, last_seen) "
            "VALUES (%s, 'e_tariq', 's_fam', '', 2.0, 2, '2026-11-10', '2026-11-11')",
            (owner,),
        )
        conn.execute("UPDATE owners SET facts_version = 1, alias_version = 1 WHERE id = %s", (owner,))
    return {"store": store}


def run(out_dir: Path) -> dict:
    # Part A & B: Bridge HTTP Forget (fact_id and record_ids) on Postgres
    bridge_fact_res = {}
    bridge_rec_res = {}
    with temp_schema("s3_bridge") as (db, _sc):
        _seed_forget_fixture(db, "karim_s3a")
        live_ctx.invalidate_alias_cache()
        with LiveApiServer(db) as srv:
            tok = srv.mint_token("owner-device", owner="karim_s3a", label="s3a")
            hdrs = {"Authorization": f"Bearer {tok}"}
            with httpx.Client(base_url=srv.base_url, timeout=10.0) as c:
                r1 = c.post("/v1/owners/karim_s3a/forget", headers=hdrs, json={"record_ids": [], "fact_id": "f_fact_target", "idempotency_key": "fk-fact"})
                ctx1 = c.post("/v1/owners/karim_s3a/context", headers=hdrs, json={"text": "desk lamp", "max_tokens": 1000}).json()
                why1 = c.get("/v1/owners/karim_s3a/why/f_fact_target", headers=hdrs)
                bridge_fact_res = {
                    "http_status": r1.status_code,
                    "response": r1.json(),
                    "fact_survived_in_context": any(f["id"] == "f_fact_target" for f in ctx1.get("facts", [])),
                    "why_status_after_forget": why1.status_code,
                }

                # Now bridge forget by record_ids
                r2 = c.post("/v1/owners/karim_s3a/forget", headers=hdrs, json={"record_ids": ["r_forget"], "idempotency_key": "fk-rec"})
                ctx2 = c.post("/v1/owners/karim_s3a/context", headers=hdrs, json={"text": "Tariq Sharjah", "max_tokens": 1000}).json()
                bridge_rec_res = {
                    "http_status": r2.status_code,
                    "response": r2.json(),
                    "f_only_survived_in_context": any(f["id"] == "f_only" for f in ctx2.get("facts", [])),
                }

    # Part C: Direct privacy.forget.forget_source with warm cache + in-flight leased job + full surface checks
    direct_res = {}
    with temp_schema("s3_direct") as (db, _sc):
        _seed_forget_fixture(db, "karim_s3c")
        live_ctx.invalidate_alias_cache()
        jobs = PostgresJobs(db)
        inflight_job = jobs.enqueue("karim_s3c", "extract.day", ["r_forget"], 1, day="2026-11-10")
        [bundle] = jobs.claim(Worker(id="w-s3", kind="internal-cloud", model="haiku", runner="anthropic"), ["internal"], owner="karim_s3c", limit=1)

        with LiveApiServer(db) as srv:
            tok = srv.mint_token("owner-device", owner="karim_s3c", label="s3c")
            hdrs = {"Authorization": f"Bearer {tok}"}
            with httpx.Client(base_url=srv.base_url, timeout=10.0) as c:
                # Warm context_pack cache BEFORE forget
                warm_before = c.post("/v1/owners/karim_s3c/context", headers=hdrs, json={"text": "Tariq", "max_tokens": 1000}).json()
                with db.connection() as conn:
                    fv_before = conn.execute("SELECT facts_version FROM owners WHERE id = 'karim_s3c'").fetchone()["facts_version"]

                # Run direct forget_source while job is in flight
                fg_out = forget_source("karim_s3c", ["r_forget"])

                # Attempt to submit the stale leased job
                att = Attempt(
                    job_id=bundle.job.id, attempt_no=bundle.job.attempt_no, fence_token=bundle.job.fence_token or "",
                    worker_id="w-s3", worker_kind="internal-cloud", model="haiku", prompt_version="extract@3",
                    output=ExtractionOutput(
                        entities=[],
                        facts=[OutFact(text="Resurrected Tariq fact", text_orig=None, subject_path="people-family/tariq", entities=[FactEntity("e_tariq")], op="new", target=None, valid_from="2026-11-10", evidence=["r_forget"], sensitive=None)],
                        links=[],
                    ),
                )
                inflight_verdict = jobs.submit(att)

                # Check every surface AFTER forget (WITHOUT calling invalidate_alias_cache!)
                warm_after = c.post("/v1/owners/karim_s3c/context", headers=hdrs, json={"text": "Tariq", "max_tokens": 1000}).json()
                srch_after = c.get("/v1/owners/karim_s3c/search", headers=hdrs, params={"q": "Sharjah", "limit": 20}).json()
                mcp_after = mcp_call(c, tok, "memory_search", {"query": "Sharjah", "owner": "karim_s3c", "limit": 20})
                why_after = c.get("/v1/owners/karim_s3c/why/f_only", headers=hdrs)
                people_after = c.get("/v1/owners/karim_s3c/vault/people", headers=hdrs).json()
                subj_after = c.get("/v1/owners/karim_s3c/vault/subjects", headers=hdrs).json()
                exp_resp = c.get("/v1/owners/karim_s3c/export/md.zip", headers=hdrs)
                with zipfile.ZipFile(io.BytesIO(exp_resp.content)) as zf:
                    exp_blob = "\n".join(zf.read(n).decode("utf-8") for n in zf.namelist())

                with db.connection() as conn:
                    fv_after = conn.execute("SELECT facts_version FROM owners WHERE id = 'karim_s3c'").fetchone()["facts_version"]
                    subj_cnt_db = conn.execute("SELECT fact_count FROM subjects WHERE owner = 'karim_s3c' AND id = 's_fam'").fetchone()["fact_count"]
                    true_vis_cnt = conn.execute("SELECT COUNT(*) AS c FROM visible_facts WHERE owner = 'karim_s3c' AND subject_id = 's_fam'").fetchone()["c"]
                    ent_row = conn.execute("SELECT erased_at FROM entities WHERE owner = 'karim_s3c' AND id = 'e_tariq'").fetchone()
                    alias_cnt = conn.execute("SELECT COUNT(*) AS c FROM entity_aliases WHERE owner = 'karim_s3c' AND entity_id = 'e_tariq'").fetchone()["c"]
                    link_row = conn.execute("SELECT erased_at FROM links WHERE owner = 'karim_s3c' AND id = 'l_tariq'").fetchone()

                direct_res = {
                    "forget_output": fg_out,
                    "facts_version_before": fv_before,
                    "facts_version_after": fv_after,
                    "facts_version_bumped": fv_after > fv_before,
                    "inflight_job_rejected": not inflight_verdict.ok,
                    "inflight_reasons": list(inflight_verdict.reasons),
                    "warm_context_had_f_only_before": any(f["id"] == "f_only" for f in warm_before.get("facts", [])),
                    "survivors_after_forget": {
                        "warm_context_f_only": any(f["id"] == "f_only" for f in warm_after.get("facts", [])),
                        "http_search_f_only": any(f["id"] == "f_only" for f in srch_after.get("facts", [])),
                        "mcp_search_f_only": any(f["id"] == "f_only" for f in mcp_after.get("facts", [])),
                        "why_f_only_status": why_after.status_code,
                        "entity_tariq_active_in_db": ent_row is not None and ent_row["erased_at"] is None,
                        "entity_tariq_in_vault_people": any(p["id"] == "e_tariq" for p in people_after.get("people", [])),
                        "aliases_tariq_count": alias_cnt,
                        "link_tariq_active_in_db": link_row is not None and link_row["erased_at"] is None,
                        "subjects_fact_count_stale": subj_cnt_db != true_vis_cnt,
                        "subjects_fact_count_db": subj_cnt_db,
                        "subjects_fact_count_true": true_vis_cnt,
                        "export_mentions_tariq_or_sharjah": ("Sharjah" in exp_blob) or ("Tariq" in exp_blob),
                        "vault_subjects_total_facts": subj_after.get("total_facts"),
                    },
                }

    surv = direct_res["survivors_after_forget"]
    passed = (
        not bridge_fact_res["fact_survived_in_context"]
        and not bridge_rec_res["f_only_survived_in_context"]
        and direct_res["facts_version_bumped"]
        and direct_res["inflight_job_rejected"]
        and not surv["warm_context_f_only"]
        and not surv["http_search_f_only"]
        and not surv["mcp_search_f_only"]
        and surv["why_f_only_status"] == 404
        and not surv["entity_tariq_in_vault_people"]
        and surv["aliases_tariq_count"] == 0
        and not surv["link_tariq_active_in_db"]
        and not surv["subjects_fact_count_stale"]
        and not surv["export_mentions_tariq_or_sharjah"]
    )
    out = {
        "suite": "S3_forget",
        "status": "PASS" if passed else "FAIL",
        "passed": passed,
        "bridge_forget_by_fact_id": bridge_fact_res,
        "bridge_forget_by_record_ids": bridge_rec_res,
        "direct_forget_source": direct_res,
    }
    (out_dir / "s3_forget.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    return out


if __name__ == "__main__":
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "results" / "manual"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(json.dumps(run(out_dir), indent=2))
