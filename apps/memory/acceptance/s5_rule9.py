"""Suite S5: Rule 9 surfaces (quarantined entity/link leak, auto-promoted place -> user_supplied, sensitive exports)."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

import httpx

from temporal_memory.core import applier
from temporal_memory.core.graph_store import PostgresGraphStore
from temporal_memory.db.db import fold_text
from temporal_memory.live import context as live_ctx
from temporal_memory.models import Attempt, ExtractionOutput, FactEntity, Job, OutEntity, OutFact, OutLink

from common import LiveApiServer, mcp_call, temp_schema


def run(out_dir: Path) -> dict:
    with temp_schema("s5") as (db, _sc):
        store = PostgresGraphStore(db)
        owner = "karim_s5"
        store.create_owner(owner, label=owner, kind="demo", display_name="Karim Haddad", self_aliases=["Karim"])
        with db.transaction() as conn:
            conn.execute(
                "INSERT INTO entities (id, owner, kind, name, status, relation_to_user) "
                "VALUES ('e_self', %s, 'person', 'Karim Haddad', 'active', 'self')",
                (owner,),
            )
            for rid, src, at, auth, txt in [
                ("r_q1", "notes", "2026-11-01", "Karim", "Zeta Relative was diagnosed with diabetes at Rashidiya Clinic."),
                ("r_p1", "whatsapp:work", "2026-11-02", "Omar", "Karim had coffee at Alserkal Cafe."),
                ("r_p2", "whatsapp:work", "2026-11-05", "Omar", "Karim worked from Alserkal Cafe."),
                ("r_h1", "notes", "2026-11-06", "Karim", "Karim went for a sleep and gym checkup."),
                ("r_f1", "notes", "2026-11-07", "Karim", "Karim prayed Fajr at Jumeirah Mosque."),
            ]:
                conn.execute(
                    "INSERT INTO records (id, owner, source, at, author, text, content_hash) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (rid, owner, src, at, auth, txt, hashlib.sha256(txt.encode()).hexdigest()),
                )

        # 5A: Apply extraction output whose ONLY fact is sensitive (Codex F01)
        j1 = Job(id="j_s5_1", owner=owner, kind="extract.day", priority=1, pool="internal", input_ref=["r_q1"], input_version=0, context_hash="c1", prompt_version="extract@3", day="2026-11-01", state="leased")
        a1 = Attempt(
            job_id=j1.id, attempt_no=1, fence_token="f1", worker_id="w1", worker_kind="internal-cloud", model="haiku", prompt_version="extract@3",
            output=ExtractionOutput(
                entities=[
                    OutEntity(ref="new:Zeta Relative", kind="person", aliases=["Zeta"], relation_to_user="family"),
                    OutEntity(ref="new:Rashidiya Clinic", kind="place", aliases=[], relation_to_user=None),
                ],
                facts=[
                    OutFact(
                        text="Zeta Relative was diagnosed with diabetes at Rashidiya Clinic.",
                        text_orig=None, subject_path="family/health",
                        entities=[FactEntity("new:Zeta Relative", "patient"), FactEntity("new:Rashidiya Clinic", None)],
                        op="new", target=None, valid_from="2026-11-01", evidence=["r_q1"], sensitive=None,
                    )
                ],
                links=[OutLink(src="e_self", rel="RELATED_TO", dst="new:Zeta Relative", valid_from="2026-11-01", evidence=["r_q1"])],
            ),
        )
        v1 = applier.apply(owner, j1, a1, db=db)

        # 5B: Apply 2 clean facts on 2 distinct days mentioning place 'Alserkal Cafe' (Codex F05)
        for idx, (rid, day, txt) in enumerate([
            ("r_p1", "2026-11-02", "Karim had coffee at Alserkal Cafe."),
            ("r_p2", "2026-11-05", "Karim worked from Alserkal Cafe."),
        ], 2):
            j = Job(id=f"j_s5_{idx}", owner=owner, kind="extract.day", priority=1, pool="internal", input_ref=[rid], input_version=0, context_hash=f"c{idx}", prompt_version="extract@3", day=day, state="leased")
            a = Attempt(
                job_id=j.id, attempt_no=1, fence_token=f"f{idx}", worker_id="w1", worker_kind="internal-cloud", model="haiku", prompt_version="extract@3",
                output=ExtractionOutput(
                    entities=[OutEntity(ref="new:Alserkal Cafe", kind="place", aliases=[], relation_to_user=None)],
                    facts=[OutFact(text=txt, text_orig=None, subject_path="projects/remote-work", entities=[FactEntity("new:Alserkal Cafe")], op="new", target=None, valid_from=day, evidence=[rid], sensitive=None)],
                    links=[],
                ),
            )
            applier.apply(owner, j, a, db=db)

        # 5C: Seed inferred health/family/faith facts directly to check surface gating
        with db.transaction() as conn:
            conn.execute(
                "INSERT INTO subjects (id, owner, parent_id, path, label, kind, status, sensitive_cat) "
                "VALUES ('s_health', %s, NULL, 'health/sleep', 'Sleep', 'topic', 'active', 'health'), "
                "('s_faith', %s, NULL, 'faith/prayer', 'Prayer', 'topic', 'active', 'religion')",
                (owner, owner),
            )
            for fid, txt, sid, rid, at in [
                ("f_inferred_health", "Karim sleeps 6 hours a night.", "s_health", "r_h1", "2026-11-06"),
                ("f_inferred_faith", "Karim prays Fajr regularly.", "s_faith", "r_f1", "2026-11-07"),
            ]:
                conn.execute(
                    "INSERT INTO facts (id, owner, text, text_folded, subject_id, valid_from, status, provenance, content_hash) "
                    "VALUES (%s,%s,%s,%s,%s,%s,'active','inferred',%s)",
                    (fid, owner, txt, fold_text(txt), sid, at, hashlib.sha256(txt.encode()).hexdigest()),
                )
                conn.execute("INSERT INTO fact_evidence (owner, fact_id, record_id, record_generation) VALUES (%s,%s,%s,0)", (owner, fid, rid))

        live_ctx.invalidate_alias_cache()
        with LiveApiServer(db) as srv:
            tok = srv.mint_token("owner-device", owner=owner, label="s5")
            hdrs = {"Authorization": f"Bearer {tok}"}
            with httpx.Client(base_url=srv.base_url, timeout=10.0) as c:
                v_people = c.get(f"/v1/owners/{owner}/vault/people", headers=hdrs).json()
                v_subj = c.get(f"/v1/owners/{owner}/vault/subjects", headers=hdrs).json()
                v_quests = c.get(f"/v1/owners/{owner}/quests", headers=hdrs).json()
                v_hyps = c.get(f"/v1/owners/{owner}/hypotheses", headers=hdrs).json()
                v_tl = c.get(f"/v1/owners/{owner}/timeline", headers=hdrs).json()
                ctx_zeta = c.post(f"/v1/owners/{owner}/context", headers=hdrs, json={"text": "Zeta Alserkal", "max_tokens": 1500}).json()
                srch_zeta = c.get(f"/v1/owners/{owner}/search", headers=hdrs, params={"q": "Zeta", "limit": 10}).json()
                mcp_srch = mcp_call(c, tok, "memory_search", {"query": "sleeps", "owner": owner, "limit": 10})
                mcp_vault = mcp_call(c, tok, "memory_vault", {"owner": owner})

                # Get one Alserkal fact id for /why check
                alserkal_fid = next((it["id"] for it in v_tl.get("items", []) if "Alserkal" in it["text"]), None)
                why_res = c.get(f"/v1/owners/{owner}/why/{alserkal_fid}", headers=hdrs).json() if alserkal_fid else {}

                exp = c.get(f"/v1/owners/{owner}/export/md.zip", headers=hdrs)
                with zipfile.ZipFile(io.BytesIO(exp.content)) as zf:
                    exp_files = {n: zf.read(n).decode("utf-8") for n in zf.namelist()}

        # Evaluate 5A leaks
        zeta_in_people = any("Zeta" in p["name"] for p in v_people.get("people", []))
        rashidiya_in_places = any("Rashidiya" in p["name"] for p in v_people.get("places", []))
        orphan_zeta_links = [ln for ln in v_people.get("links", []) if "Zeta" in str(ln) or any(p["id"] == ln["dst"] and "Zeta" in p["name"] for p in v_people.get("people", []))]
        zeta_in_mcp_vault = any("Zeta" in str(p) for p in mcp_vault.get("people", []))
        zeta_in_export = any("Zeta" in txt or "Rashidiya" in txt for txt in exp_files.values())

        # Evaluate 5B auto-promoted place -> user_supplied
        alserkal_vault = next((p for p in v_people.get("places", []) if "Alserkal" in p["name"]), None)
        alserkal_ctx = next((e for e in ctx_zeta.get("entities", []) if "Alserkal" in e["name"]), None)
        hardcoded_envelopes = {
            "vault_subjects_top": v_subj.get("provenance"),
            "vault_people_top": v_people.get("provenance"),
            "timeline_top": v_tl.get("provenance"),
            "context_top": ctx_zeta.get("provenance"),
            "why_evidence_0": (why_res.get("evidence") or [{}])[0].get("provenance"),
        }

        # Evaluate 5C sensitive cluster/export leaks
        faith_in_export = any("Fajr" in txt for path, txt in exp_files.items() if path != "memory/held-back.md")
        health_in_vault_subj = any("sleep" in json.dumps(t).lower() for t in v_subj.get("themes", []))
        faith_in_vault_subj = any("faith" in json.dumps(t).lower() or "prayer" in json.dumps(t).lower() for t in v_subj.get("themes", []))
        vault_subj_missing_sens_cat = all("sensitive_cat" not in t for t in v_subj.get("themes", []))

        zero_leaks = not (
            zeta_in_people
            or rashidiya_in_places
            or orphan_zeta_links
            or zeta_in_mcp_vault
            or zeta_in_export
            or faith_in_export
            or health_in_vault_subj
            or faith_in_vault_subj
        )
        zero_mislabelled_inferred = (
            (alserkal_vault is None or alserkal_vault.get("provenance") != "user_supplied")
            and (alserkal_ctx is None or alserkal_ctx.get("provenance") != "user_supplied")
        )
        passed = zero_leaks and zero_mislabelled_inferred and not vault_subj_missing_sens_cat

        out = {
            "suite": "S5_rule9_surfaces",
            "status": "PASS" if passed else "FAIL",
            "passed": passed,
            "case_5a_quarantined_fact_leaks": {
                "quarantined_by_applier": dict(v1.quarantined),
                "zeta_in_vault_people": zeta_in_people,
                "rashidiya_in_vault_places": rashidiya_in_places,
                "orphan_links_count": len(orphan_zeta_links),
                "zeta_in_mcp_vault": zeta_in_mcp_vault,
                "zeta_in_export_md": zeta_in_export,
            },
            "case_5b_autopromoted_place_provenance": {
                "alserkal_vault_status": alserkal_vault.get("status") if alserkal_vault else None,
                "alserkal_vault_provenance": alserkal_vault.get("provenance") if alserkal_vault else None,
                "alserkal_context_provenance": alserkal_ctx.get("provenance") if alserkal_ctx else None,
                "hardcoded_envelopes": hardcoded_envelopes,
            },
            "case_5c_sensitive_surfaces": {
                "health_in_vault_subjects": health_in_vault_subj,
                "faith_in_vault_subjects": faith_in_vault_subj,
                "faith_in_export_md": faith_in_export,
                "vault_subjects_omits_sensitive_cat": vault_subj_missing_sens_cat,
                "inferred_health_in_mcp_search": any("sleeps" in f["text"] for f in mcp_srch.get("facts", [])),
            },
            "gate_checks": {
                "zero_sensitive_leaks": zero_leaks,
                "zero_inferred_as_user_supplied": zero_mislabelled_inferred,
                "vault_subjects_exposes_sensitive_cat": not vault_subj_missing_sens_cat,
            },
        }
        (out_dir / "s5_rule9.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
        return out


if __name__ == "__main__":
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "results" / "manual"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(json.dumps(run(out_dir), indent=2))
