"""Suite S8: R6 Places & Topics baseline (restaurant retrieval + two-session topic counter)."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shlex
import sys

import httpx

from temporal_memory.core import extract
from temporal_memory.core.graph_store import PostgresGraphStore
from temporal_memory.models import Worker
from temporal_memory.queue.jobs import PostgresJobs

from common import CLAUDE_EXE, EMPTY_MCP, LiveApiServer, temp_schema


def run(out_dir: Path) -> dict:
    orig_cmd = os.environ.get("TM_AGENT_CLI_CMD")
    orig_build = extract.build_system_prompt
    sys_file = out_dir / "_s8_sys.txt"

    try:
        with temp_schema("s8") as (db, _sc):
            store = PostgresGraphStore(db)
            owner = "karim_s8"
            store.create_owner(owner, label=owner, kind="demo", display_name="Karim Haddad", self_aliases=["Karim"])
            rec_text = "Had dinner at Zuma in DIFC last night, loved the black cod"
            with db.transaction() as conn:
                conn.execute(
                    "INSERT INTO records (id, owner, source, at, author, text, content_hash) "
                    "VALUES ('r_zuma', %s, 'live', '2026-11-23T21:00:00+04:00', 'Karim', %s, %s)",
                    (owner, rec_text, hashlib.sha256(rec_text.encode()).hexdigest()),
                )

            jobs = PostgresJobs(db, store)
            job = jobs.enqueue(owner, "extract.day", ["r_zuma"], 1, pool="owner-device", day="2026-11-23")
            [bundle] = jobs.claim(Worker(id="w-s8", kind="agent-cli", model="haiku", runner="agent-cli", owner=owner), ["owner-device"], owner=owner, limit=1)

            sys_file.write_text(orig_build(store.get_owner(owner)), encoding="utf-8")
            os.environ["CLAUDE_CODE_DISABLE_ATTACHMENTS"] = "1"
            os.environ["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
            bundle.system_prompt = orig_build(store.get_owner(owner))  # E6: product runner (E8) ignores custom claude cmd
            attempt = extract.run(bundle, "agent-cli", "haiku")
            attempt.worker_kind = "internal-cloud"
            verdict = jobs.submit(attempt)

            extracted_entities = [{"ref": e.ref, "kind": e.kind} for e in (attempt.output.entities if attempt.output else [])]
            extracted_facts = [{"text": f.text, "subject_path": f.subject_path} for f in (attempt.output.facts if attempt.output else [])]

            with LiveApiServer(db) as srv:
                tok = srv.mint_token("owner-device", owner=owner, label="s8")
                hdrs = {"Authorization": f"Bearer {tok}"}
                with httpx.Client(base_url=srv.base_url, timeout=10.0) as c:
                    hits_place = {}
                    for q in ("Zuma", "DIFC", "restaurant"):
                        ctx_r = c.post(f"/v1/owners/{owner}/context", headers=hdrs, json={"text": q, "max_tokens": 1000}).json()
                        srch_r = c.get(f"/v1/owners/{owner}/search", headers=hdrs, params={"q": q, "limit": 10}).json()
                        hits_place[q] = {
                            "context_hits": len(ctx_r.get("facts", [])),
                            "search_hits": len(srch_r.get("facts", [])),
                            "texts": [f["text"] for f in ctx_r.get("facts", [])],
                        }

                    # 8B (E6 rewrite): the real topic path is POST /records source=live, author=owner, meta.session_id.
                    # A topic named in >= 2 separate sessions yields ONE "I noticed" hypothesis; a topic asked once yields none.
                    with db.transaction() as conn:
                        sid_agents = store._ensure_subject_path(conn, owner, "learning/ai-agents", "topic", "AI agents")
                        sid_once = store._ensure_subject_path(conn, owner, "learning/quantum-gardening", "topic", "Quantum gardening")

                    def post_live(rid, session, text):
                        r = c.post(f"/v1/owners/{owner}/records", headers=hdrs, json={"records": [{
                            "id": rid, "source": "live", "at": "2026-11-24T12:00:00+04:00", "author": owner,
                            "text": text, "meta": {"session_id": session}}]})
                        return r.status_code

                    def hyps():
                        return c.get(f"/v1/owners/{owner}/hypotheses", headers=hdrs).json().get("hypotheses", [])

                    codes = [post_live("t1", "sess-1", "How do AI agents work?"),
                             post_live("t2", "sess-1", "Quantum gardening sounds fun"),
                             post_live("t3", "sess-1", "Tell me about AI agents again")]  # same session: still one visit
                    h_after_1 = len(hyps())
                    codes.append(post_live("t4", "sess-2", "How do AI agents do tool calling?"))
                    hs = hyps()
                    h_after_2 = len([h for h in hs if "AI agents" in str(h)])
                    h_once = len([h for h in hs if "Quantum gardening" in str(h)])
                    h_total_2 = len(hs)

                    # 8C (E6): Forget the evidence records of the topic hypothesis -> hypothesis gone, and a raw SQL scan of every
                    # owner table (current schema) finds no forgotten token (E8 scrubs text everywhere, tombstone only).
                    fr = c.post(f"/v1/owners/{owner}/forget", headers=hdrs, json={"record_ids": ["t1", "t3", "t4"], "idempotency_key": "e6-s8-topic"})
                    h_after_forget = len([h for h in hyps() if "AI agents" in str(h)])
                    token_sql = "tool calling"
                    scan_hits = {}
                    with db.connection() as conn_:
                        tabs = conn_.execute("SELECT table_name FROM information_schema.columns WHERE table_schema=current_schema() AND column_name='owner'").fetchall()
                        for t_ in tabs:
                            tn = t_["table_name"] if isinstance(t_, dict) else t_[0]
                            cols = conn_.execute("SELECT column_name FROM information_schema.columns WHERE table_schema=current_schema() AND table_name=%s AND data_type IN ('text','character varying','json','jsonb','ARRAY')", (tn,)).fetchall()
                            cn = [(c_["column_name"] if isinstance(c_, dict) else c_[0]) for c_ in cols]
                            if not cn:
                                continue
                            cond = " OR ".join(f'"{x}"::text ILIKE %s' for x in cn)
                            n_ = conn_.execute(f'SELECT count(*) AS n FROM "{tn}" WHERE owner=%s AND ({cond})', (owner, *[f"%{token_sql}%"] * len(cn))).fetchone()
                            n_ = n_["n"] if isinstance(n_, dict) else n_[0]
                            if n_:
                                scan_hits[tn] = n_

            zuma_ok = hits_place["Zuma"]["context_hits"] > 0 or hits_place["Zuma"]["search_hits"] > 0
            difc_ok = hits_place["DIFC"]["context_hits"] > 0 or hits_place["DIFC"]["search_hits"] > 0
            rest_ok = hits_place["restaurant"]["context_hits"] > 0 or hits_place["restaurant"]["search_hits"] > 0
            topic_ok = (h_after_1 == 0 and h_after_2 == 1 and h_once == 0 and all(c_ == 200 for c_ in codes) and fr.status_code == 200 and h_after_forget == 0 and not scan_hits)

            out = {
                "suite": "S8_r6_places_topics",
                "status": "PASS" if (zuma_ok and difc_ok and rest_ok and topic_ok) else "FAIL",
                "passed": bool(zuma_ok and difc_ok and rest_ok and topic_ok),
                "part_8a_restaurant": {
                    "input": rec_text,
                    "cost_usd": attempt.cost_usd,
                    "verdict_ok": verdict.ok,
                    "extracted_entities": extracted_entities,
                    "extracted_facts": extracted_facts,
                    "retrieval": hits_place,
                    "by_name": zuma_ok,
                    "by_area": difc_ok,
                    "by_word_restaurant": rest_ok,
                },
                "part_8b_topic_counter": {
                    "hypotheses_after_session_1": h_after_1,
                    "hypotheses_after_session_2": h_after_2,
                    "topic_asked_once_hypotheses": h_once, "forget_status": fr.status_code, "hypotheses_after_forget": h_after_forget, "raw_sql_scan_hits_for_forgotten_token": scan_hits, "total_hypotheses_after_2": h_total_2, "post_codes": codes,
                    "two_visit_ok": topic_ok,
                },
                "notes": "E6: 8B drives the shipped topic path (POST /records live + session_id).",
            }
            (out_dir / "s8_places_topics.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
            return out
    finally:
        extract.build_system_prompt = orig_build
        if orig_cmd is None:
            os.environ.pop("TM_AGENT_CLI_CMD", None)
        else:
            os.environ["TM_AGENT_CLI_CMD"] = orig_cmd
        sys_file.unlink(missing_ok=True)


if __name__ == "__main__":
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "results" / "manual"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(json.dumps(run(out_dir), indent=2))
