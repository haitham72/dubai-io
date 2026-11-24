"""Suite S9: U5 Why (evidence/reason spans) & Story endpoint + Postgres cache + Forget invalidation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import httpx

from temporal_memory.api import story as story_api
from temporal_memory.core.graph_store import PostgresGraphStore
from temporal_memory.db.db import fold_text
from temporal_memory.privacy import forget as forget_mod

from common import ACCEPTANCE_DIR, LiveApiServer, temp_schema


def run(out_dir: Path) -> dict:
    checks: dict[str, bool] = {}

    with temp_schema("s9") as (db, _sc):
        store = PostgresGraphStore(db)
        owner = "karim_s9"
        other_owner = "layla_s9"
        store.create_owner(owner, label=owner, kind="simulated", display_name="Karim Haddad", self_aliases=["Karim"])
        store.create_owner(other_owner, label=other_owner, kind="simulated", display_name="Layla Haddad")

        long_raw = (
            ("Header banner filler text. " * 22)
            + "Karim withdrew from the Dubai Marathon because his flight schedule clashed with race morning."
            + (" Footer trailing filler text." * 22)
        )
        span_phrase = "Karim withdrew from the Dubai Marathon"
        reason_phrase = "his flight schedule clashed with race morning"
        span_start = long_raw.index(span_phrase)
        span_end = span_start + len(span_phrase)
        reason_start = long_raw.index(reason_phrase)
        reason_end = reason_start + len(reason_phrase)

        with db.transaction() as conn:
            conn.execute(
                "INSERT INTO entities (id, owner, kind, name, status, relation_to_user) VALUES "
                "('e_self', %s, 'person', 'Karim Haddad', 'active', 'self'), "
                "('e_omar', %s, 'person', 'Omar Farouk', 'active', 'friend')",
                (owner, owner),
            )
            conn.execute(
                "INSERT INTO entity_aliases (owner, entity_id, alias, alias_folded) VALUES "
                "(%s, 'e_omar', 'Omar', 'omar')",
                (owner,),
            )
            conn.execute(
                "INSERT INTO subjects (id, owner, path, label, kind, status, sensitive_cat) VALUES "
                "('s_ev', %s, 'events/marathon', 'Marathon', 'event', 'active', NULL), "
                "('s_fam', %s, 'people-family/updates', 'Family Updates', 'topic', 'active', NULL), "
                "('s_hl', %s, 'health/meds', 'Health', 'topic', 'active', 'health')",
                (owner, owner, owner),
            )
            for rid, txt in [
                ("r_why_long", long_raw),
                ("r_why_2", "Karim prefers flat white coffee at QamarTech."),
                ("r_sup", "Karim registered for the Dubai Marathon."),
                ("r_fam", "Mom arrives in Dubai on December 1."),
                ("r_sens", "Doctor prescribed daily tablets at the clinic."),
            ]:
                conn.execute(
                    "INSERT INTO records (id, owner, source, at, author, text, content_hash) "
                    "VALUES (%s, %s, 'notes', '2026-11-15', 'Karim', %s, %s)",
                    (rid, owner, txt, hashlib.sha256(txt.encode()).hexdigest()),
                )

            conn.execute(
                "INSERT INTO facts (id, owner, text, text_folded, subject_id, valid_from, valid_to, status, provenance, "
                "content_hash, span_record_id, span_start, span_end, reason_text, reason_record_id, reason_start, reason_end) "
                "VALUES ('f_with_reason', %s, %s, %s, 's_ev', '2026-11-15', NULL, 'active', 'inferred', %s, "
                "'r_why_long', %s, %s, %s, 'r_why_long', %s, %s)",
                (
                    owner,
                    span_phrase,
                    fold_text(span_phrase),
                    hashlib.sha256(b"f_with_reason").hexdigest(),
                    span_start,
                    span_end,
                    reason_phrase,
                    reason_start,
                    reason_end,
                ),
            )
            extra_facts = [
                ("f_superseded", "Karim registered for the Dubai Marathon.", "s_ev", "2026-10-22", "2026-11-15", "superseded", "user_supplied", "r_sup"),
                ("f_no_reason", "Karim prefers flat white coffee.", "s_ev", "2026-11-10", None, "active", "user_supplied", "r_why_2"),
                ("f_hyp", "I noticed Karim runs morning laps.", "s_ev", "2026-11-12", None, "hypothesis", "inferred", "r_sup"),
                ("f_fam_inf", "Omar mentioned a surprise party.", "s_fam", "2026-11-13", None, "active", "inferred", "r_fam"),
                ("f_fam_conf", "Mom arrives in Dubai on Dec 1.", "s_fam", "2026-11-14", None, "active", "user_supplied", "r_fam"),
                ("f_sens_inf", "Doctor prescribed daily tablets.", "s_hl", "2026-11-16", None, "active", "inferred", "r_sens"),
                ("f_sens_usr", "Confirmed knee physiotherapy visit.", "s_hl", "2026-11-16", None, "active", "user_supplied", "r_sens"),
            ]
            for fid, txt, sid, vf, vt, st, prov, rid in extra_facts:
                conn.execute(
                    "INSERT INTO facts (id, owner, text, text_folded, subject_id, valid_from, valid_to, status, provenance, content_hash) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (fid, owner, txt, fold_text(txt), sid, vf, vt, st, prov, hashlib.sha256(fid.encode()).hexdigest()),
                )
                conn.execute(
                    "INSERT INTO fact_evidence (owner, fact_id, record_id, record_generation) VALUES (%s, %s, %s, 0)",
                    (owner, fid, rid),
                )
            conn.execute(
                "INSERT INTO fact_evidence (owner, fact_id, record_id, record_generation) VALUES (%s, 'f_with_reason', 'r_why_long', 0)",
                (owner,),
            )
            conn.execute(
                "INSERT INTO fact_entities (owner, fact_id, entity_id) VALUES (%s, 'f_with_reason', 'e_self'), (%s, 'f_superseded', 'e_self')",
                (owner, owner),
            )
            conn.execute("UPDATE owners SET facts_version = 1 WHERE id = %s", (owner,))

        with LiveApiServer(db) as srv:
            tok = srv.mint_token("owner-device", owner=owner, label="s9")
            tok_other = srv.mint_token("owner-device", owner=other_owner, label="s9-other")
            tok_worker = srv.mint_token("worker", owner=None, label="s9-worker")
            hdrs = {"Authorization": f"Bearer {tok}"}
            hdrs_other = {"Authorization": f"Bearer {tok_other}"}
            hdrs_worker = {"Authorization": f"Bearer {tok_worker}"}

            with httpx.Client(base_url=srv.base_url, timeout=10.0) as c:
                # 1. /why checks
                r_w1 = c.get(f"/v1/owners/{owner}/why/f_with_reason", headers=hdrs)
                r_w2 = c.get(f"/v1/owners/{owner}/why/f_no_reason", headers=hdrs)
                r_ws = c.get(f"/v1/owners/{owner}/why/f_sens_inf", headers=hdrs)

                w1 = r_w1.json()
                w2 = r_w2.json()

                checks["why_with_reason_200"] = r_w1.status_code == 200
                checks["why_reason_matches_cited_span"] = (
                    w1.get("reason") == reason_phrase
                    and isinstance(w1.get("reason_span"), dict)
                    and w1["reason_span"].get("record_id") == "r_why_long"
                    and w1["reason_span"].get("text") == reason_phrase
                )
                checks["why_evidence_bounded_span"] = (
                    len(w1.get("evidence") or []) == 1
                    and w1["evidence"][0].get("span") == span_phrase
                    and len(w1["evidence"][0].get("text") or "") < 250
                )
                checks["why_provenance_separate_from_reason"] = (
                    w1.get("provenance") == "inferred"
                    and w2.get("provenance") == "user_supplied"
                )
                checks["why_without_reason_is_unknown"] = (
                    r_w2.status_code == 200
                    and w2.get("reason") == "reason unknown"
                    and w2.get("reason_span") is None
                )
                checks["why_unconfirmed_sensitive_404"] = r_ws.status_code == 404

                # 2. /story deterministic template + filtering + cache hit
                r_st1 = c.get(f"/v1/owners/{owner}/story", headers=hdrs, params={"subject": "events/marathon"})
                r_st2 = c.get(f"/v1/owners/{owner}/story", headers=hdrs, params={"subject": "events/marathon"})
                r_st_all = c.get(f"/v1/owners/{owner}/story", headers=hdrs)

                st1 = r_st1.json()
                st2 = r_st2.json()
                st_all = r_st_all.json()

                checks["story_200"] = r_st1.status_code == 200 and r_st_all.status_code == 200
                checks["story_template_mode_and_citations"] = (
                    st1.get("mode") == "template"
                    and set(st1.get("fact_ids") or []) == {"f_superseded", "f_with_reason", "f_no_reason"}
                    and all(bool(s.get("fact_ids")) for s in st1.get("sentences") or [])
                    and reason_phrase in st1.get("story", "")
                    and "superseded" in st1.get("story", "")
                )
                checks["story_filters_sensitive_hypothesis_unconfirmed_family"] = (
                    set(st_all.get("fact_ids") or []) == {"f_superseded", "f_with_reason", "f_no_reason", "f_fam_conf"}
                    and "tablets" not in st_all.get("story", "").lower()
                    and "physiotherapy" not in st_all.get("story", "").lower()
                    and "surprise party" not in st_all.get("story", "").lower()
                    and "morning laps" not in st_all.get("story", "").lower()
                )
                checks["story_cache_miss_then_hit"] = (
                    st1.get("cached") is False
                    and st2.get("cached") is True
                    and st2.get("story") == st1.get("story")
                )

                # 3. /story narrated grounding + Rule 9 screening
                def _fake_narrator(_prompt: str, fact_items: list[dict]):
                    assert all(it["id"] not in ("f_sens_inf", "f_sens_usr") for it in fact_items)
                    payload = {
                        "sentences": [
                            {"text": "Karim registered for the marathon and later withdrew due to a flight schedule clash [f_superseded, f_with_reason].", "fact_ids": ["f_superseded", "f_with_reason"]},
                            {"text": "Uncited hallucinated claim.", "fact_ids": []},
                            {"text": "Bad cited unknown fact [f_999].", "fact_ids": ["f_999"]},
                            {"text": "He visited a private diabetes clinic [f_with_reason].", "fact_ids": ["f_with_reason"]},
                        ]
                    }
                    return json.dumps(payload), 0.0, "test-narrator"

                story_api.set_narrator(_fake_narrator)
                story_api.set_screen_classifier(
                    lambda labels: {lbl: ("health" if "clinic" in lbl.lower() or "diabetes" in lbl.lower() else "none") for lbl in labels}
                )
                try:
                    r_nar = c.get(f"/v1/owners/{owner}/story", headers=hdrs, params={"subject": "events/marathon", "narrate": "1"})
                    nar = r_nar.json()
                finally:
                    story_api.set_narrator(None)
                    story_api.set_screen_classifier(None)

                checks["story_narrate_grounding_and_rule9"] = (
                    r_nar.status_code == 200
                    and nar.get("mode") == "narrated"
                    and nar.get("dropped_sentences") == 3
                    and len(nar.get("sentences") or []) == 1
                )

                # 4. Forget invalidates /why and Postgres story_cache atomically
                forget_mod.forget_fact(owner, "f_with_reason")
                r_w_after = c.get(f"/v1/owners/{owner}/why/f_with_reason", headers=hdrs)
                r_st_after = c.get(f"/v1/owners/{owner}/story", headers=hdrs, params={"subject": "events/marathon"})
                st_after = r_st_after.json()

                checks["forget_invalidates_why_and_story_cache"] = (
                    r_w_after.status_code == 404
                    and r_st_after.status_code == 200
                    and st_after.get("cached") is False
                    and "f_with_reason" not in (st_after.get("fact_ids") or [])
                    and "withdrew" not in st_after.get("story", "")
                )

                # 5. Auth isolation (worker and cross-owner rejected with 403)
                checks["auth_isolation_403"] = (
                    c.get(f"/v1/owners/{owner}/why/f_no_reason", headers=hdrs_other).status_code == 403
                    and c.get(f"/v1/owners/{owner}/why/f_no_reason", headers=hdrs_worker).status_code == 403
                    and c.get(f"/v1/owners/{owner}/story", headers=hdrs_other).status_code == 403
                    and c.get(f"/v1/owners/{owner}/story", headers=hdrs_worker).status_code == 403
                )

    passed = all(checks.values())
    out = {
        "suite": "S9_why_story",
        "status": "PASS" if passed else "FAIL",
        "passed": passed,
        "checks": checks,
        "why_with_reason": {
            "status": r_w1.status_code,
            "reason": w1.get("reason"),
            "reason_span": w1.get("reason_span"),
            "provenance": w1.get("provenance"),
            "evidence_span_len": len((w1.get("evidence") or [{}])[0].get("span") or ""),
        },
        "why_without_reason": {
            "status": r_w2.status_code,
            "reason": w2.get("reason"),
            "reason_span": w2.get("reason_span"),
            "provenance": w2.get("provenance"),
        },
        "story_template": {
            "status": r_st1.status_code,
            "mode": st1.get("mode"),
            "first_cached": st1.get("cached"),
            "second_cached": st2.get("cached"),
            "subject_fact_ids": st1.get("fact_ids"),
            "unfiltered_fact_ids": st_all.get("fact_ids"),
        },
        "story_narrated": {
            "status": r_nar.status_code,
            "mode": nar.get("mode"),
            "dropped_sentences": nar.get("dropped_sentences"),
            "kept_sentences": len(nar.get("sentences") or []),
        },
        "story_forget_invalidation": {
            "why_after_status": r_w_after.status_code,
            "story_after_cached": st_after.get("cached"),
            "story_after_fact_ids": st_after.get("fact_ids"),
        },
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "s9_why_story.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


if __name__ == "__main__":
    target_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ACCEPTANCE_DIR / "results" / "manual"
    target_dir.mkdir(parents=True, exist_ok=True)
    res = run(target_dir)
    print(json.dumps({"suite": res["suite"], "status": res["status"], "passed": res["passed"], "checks": res["checks"]}, indent=2))
