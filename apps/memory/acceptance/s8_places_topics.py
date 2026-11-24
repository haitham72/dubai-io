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
            os.environ["TM_AGENT_CLI_CMD"] = shlex.join([
                Path(CLAUDE_EXE).as_posix(), "-p", "--model", "{model}", "--effort", "medium", "--output-format", "json",
                "--system-prompt-file", sys_file.as_posix(), "--strict-mcp-config", "--mcp-config", EMPTY_MCP.as_posix(),
                "--tools", "", "--disable-slash-commands", "--no-session-persistence", "--max-turns", "1",
            ])
            os.environ["CLAUDE_CODE_DISABLE_ATTACHMENTS"] = "1"
            os.environ["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
            extract.build_system_prompt = lambda _: ""
            bundle.system_prompt = ""
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

                    # 8B: Topic asked in 2 separate sessions -> check /hypotheses
                    c.post(f"/v1/owners/{owner}/context", headers=hdrs, json={"text": "Tell me about AI agents", "max_tokens": 1000})
                    h_after_1 = len(c.get(f"/v1/owners/{owner}/hypotheses", headers=hdrs).json().get("hypotheses", []))
                    c.post(f"/v1/owners/{owner}/context", headers=hdrs, json={"text": "How do AI agents do tool calling?", "max_tokens": 1000})
                    h_after_2 = len(c.get(f"/v1/owners/{owner}/hypotheses", headers=hdrs).json().get("hypotheses", []))

            zuma_ok = hits_place["Zuma"]["context_hits"] > 0 or hits_place["Zuma"]["search_hits"] > 0
            difc_ok = hits_place["DIFC"]["context_hits"] > 0 or hits_place["DIFC"]["search_hits"] > 0
            rest_ok = hits_place["restaurant"]["context_hits"] > 0 or hits_place["restaurant"]["search_hits"] > 0
            topic_ok = (h_after_1 == 0 and h_after_2 == 1)

            out = {
                "suite": "S8_r6_places_topics",
                "status": "NOT YET BUILT",
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
                    "two_visit_ok": topic_ok,
                },
                "notes": "R6 keep-list expansion, place type ('restaurant'), and 2-session topic counter are U2/U3 work; recorded today's actual engine behaviour.",
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
