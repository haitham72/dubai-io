"""P1A+P2 gold-set self-check. Asserts ledger/probe/source integrity. Prints counts only."""
import json
import re
import subprocess
from datetime import date
from pathlib import Path

GOLD = Path(__file__).resolve().parent
LEDGER = GOLD / "ledger.json"
PROBES = GOLD / "probes.json"
INGEST = GOLD / "ingest_order.json"
SOURCES = GOLD / "sources"


def fail(msg):
    raise AssertionError(f"VALIDATE FAIL: {msg}")


def week_of(day: str) -> int:
    d = date.fromisoformat(day)
    if date(2026, 10, 20) <= d <= date(2026, 10, 26):
        return 1
    if date(2026, 10, 27) <= d <= date(2026, 11, 2):
        return 2
    if date(2026, 11, 3) <= d <= date(2026, 11, 9):
        return 3
    if date(2026, 11, 10) <= d <= date(2026, 11, 16):
        return 4
    if date(2026, 11, 17) <= d <= date(2026, 11, 19):
        return 5
    fail(f"date {day} outside corpus window")


def _git_repo_info() -> tuple[Path | None, str | None]:
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, cwd=str(GOLD))
    if r.returncode != 0:
        return None, None
    top = Path(r.stdout.decode("utf-8").strip()).resolve()
    try:
        rel = GOLD.resolve().relative_to(top).as_posix()
    except ValueError:
        return top, None
    return top, rel


def git_head_exists(top: Path, rel_path: str) -> bool:
    r = subprocess.run(["git", "cat-file", "-e", f"HEAD:{rel_path}"], capture_output=True, cwd=str(top))
    return r.returncode == 0


def git_head(top: Path, rel_path: str) -> str:
    r = subprocess.run(["git", "show", f"HEAD:{rel_path}"], capture_output=True, cwd=str(top))
    if r.returncode != 0:
        fail(f"git show HEAD:{rel_path} failed: {r.stderr.decode('utf-8', 'replace').strip()[:200]}")
    return r.stdout.decode("utf-8")


def main():
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    probes = json.loads(PROBES.read_text(encoding="utf-8"))["probes"]
    ingest = json.loads(INGEST.read_text(encoding="utf-8"))
    people = {p["id"]: p for p in ledger["people"]}
    subjects = {s["id"]: s for s in ledger["subjects"]}
    orgs = {o["id"]: o for o in ledger["orgs"]}
    places = {l["id"]: l for l in ledger["places"]}
    facts = {f["id"]: f for f in ledger["facts"]}
    ent_ids = set(people) | set(subjects) | set(orgs) | set(places)

    # ---- 1. every fact has resolvable evidence ----
    wa_lines = {}
    for chat, fn in [("wab", "whatsapp_best.txt"), ("wag", "whatsapp_work.txt"), ("waf", "whatsapp_family.txt")]:
        wa_lines.update({f"{chat}-{i:04d}": ln for i, ln in
                         enumerate((SOURCES / fn).read_text(encoding="utf-8").splitlines(), 1)})
    gmails = {json.loads(ln)["id"]: json.loads(ln)
              for ln in (SOURCES / "gmail.jsonl").read_text(encoding="utf-8").splitlines()}
    notes = {}
    for ln in (SOURCES / "notes.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\[(n\d+)\]", ln)
        if m:
            notes[m.group(1)] = ln
    all_records = set(wa_lines) | set(gmails) | set(notes)
    for fid, f in facts.items():
        if not f["evidence"]:
            fail(f"{fid} has no evidence")
        for rid in f["evidence"]:
            if rid not in all_records:
                fail(f"{fid} evidence {rid} not found in sources")
    # WA line-number integrity: spot-check first evidence id matches its line number
    for fid, f in facts.items():
        for rid in f["evidence"]:
            m = re.match(r"(wa[bgf])-(\d+)", rid)
            if m and int(m.group(2)) > len([k for k in wa_lines if k.startswith(m.group(1))]):
                fail(f"{rid} line number out of range")

    # ---- 2. probe gold IDs exist ----
    if len(probes) != 40:
        fail(f"expected 40 probes, got {len(probes)}")
    buckets = {}
    for p in probes:
        buckets[p["bucket"]] = buckets.get(p["bucket"], 0) + 1
        g = p["gold"]
        for fid in g["context_memory_ids"] + p["gold_context_fact_ids"]:
            if fid not in facts:
                fail(f"{p['turn_id']} unknown fact {fid}")
        for c in g["contradictions"]:
            if c["memory_id"] not in facts:
                fail(f"{p['turn_id']} unknown contradiction target {c['memory_id']}")
            if c["verdict"] not in ("changes", "ends", "repeats"):
                fail(f"{p['turn_id']} bad verdict {c['verdict']}")
        for m in g["mentions"]:
            if m["resolved_id"] not in ent_ids:
                fail(f"{p['turn_id']} unknown entity {m['resolved_id']}")
        for s in g["subjects"]:
            if s["subject_id"] not in ent_ids:
                fail(f"{p['turn_id']} unknown subject {s['subject_id']}")
        if p["bucket"] == "sensitive":
            if not g["gated"]:
                fail(f"{p['turn_id']} sensitive probe has empty gated")
            low = g["finding"].lower()
            for s in p["must_not_contain"]:
                if s.lower() in low:
                    fail(f"{p['turn_id']} finding leaks must_not string")
    expect = {"person": 7, "person_alias": 3, "contradiction": 10, "twohop": 8,
              "arabic": 6, "sensitive": 4, "noise": 2}
    if buckets != expect:
        fail(f"bucket mix {buckets} != {expect}")

    # ---- 3. alias counts as specified ----
    if len(ledger["people"]) != 25:
        fail("people != 25")
    for pid, p in people.items():
        if not (2 <= len(p["aliases"]) <= 3):
            fail(f"{pid} has {len(p['aliases'])} aliases")
    traps = ledger["alias_traps"]
    if len(traps) != 4:
        fail("alias_traps != 4")
    kinds = sorted(t["kind"] for t in traps)
    if kinds != ["multi_spelling", "multi_spelling", "shared_first_name", "shared_first_name"]:
        fail(f"trap kinds {kinds}")

    # ---- 4. synthetic persona & record count check ----
    if ledger.get("persona", {}).get("name") != "Karim Haddad":
        fail("unexpected persona name")
    if len(all_records) != 1172:
        fail(f"expected 1172 records, got {len(all_records)}")

    # ---- 5. ingest order: complete + late records trail their newer facts ----
    if set(ingest["order"]) != all_records or len(ingest["order"]) != len(all_records):
        fail("ingest order != record set")
    pos = {rid: i for i, rid in enumerate(ingest["order"])}
    for rid, info in ingest["late_records"].items():
        new_pos = min(pos[r] for r in facts[info["after_fact_id"]]["evidence"])
        if pos[rid] < new_pos:
            fail(f"late {rid} ingests before {info['after_fact_id']}")

    # ---- 6. P2: milestones / trivia / profile ----
    ms = ledger.get("milestones", [])
    if len(ms) != 6 or [m["id"] for m in ms] != [f"ms{i:02d}" for i in range(1, 7)]:
        fail("milestones != ms01..ms06")
    for m in ms:
        if set(m["status_by_week"]) != {"1", "2", "3", "4", "5"}:
            fail(f"{m['id']} status_by_week keys")
        if any(v not in ("done", "in_progress", "planned", None) for v in m["status_by_week"].values()):
            fail(f"{m['id']} bad status value")
        if len(m["fact_ids"]) < 2 or any(fid not in facts for fid in m["fact_ids"]):
            fail(f"{m['id']} fact_ids")
        days = {facts[fid]["occurred"] for fid in m["fact_ids"]}
        if len(days) < 2:
            fail(f"{m['id']} needs facts from >= 2 days")
        if min(week_of(facts[fid]["occurred"]) for fid in m["fact_ids"]) != m["first_week"]:
            fail(f"{m['id']} first_week != week of first supporting fact")
        for w in range(1, m["first_week"]):
            if m["status_by_week"][str(w)] is not None:
                fail(f"{m['id']} has status before first_week")
        for w in range(m["first_week"], 6):
            if m["status_by_week"][str(w)] is None:
                fail(f"{m['id']} missing status for week {w}")
    tr = ledger.get("trivia", [])
    if len(tr) != 12 or [t["id"] for t in tr] != [f"tr{i:02d}" for i in range(1, 13)]:
        fail("trivia != tr01..tr12")
    for t in tr:
        if not t["record_ids"] or any(r not in all_records for r in t["record_ids"]):
            fail(f"{t['id']} record_ids")
    prof = ledger.get("profile", {})
    if set(prof) != {"Identity", "Personality", "Values", "Strengths & Tensions",
                     "Interests", "Drive", "Relationships"}:
        fail("profile sections")
    n_claims = 0
    for sec, claims in prof.items():
        if not (2 <= len(claims) <= 4):
            fail(f"profile {sec} claim count")
        for c in claims:
            if not c["fact_ids"] or any(fid not in facts for fid in c["fact_ids"]):
                fail(f"profile {sec} bad fact_ids")
            if any(week_of(facts[fid]["occurred"]) > c["first_week"] for fid in c["fact_ids"]):
                fail(f"profile {sec} claim predates its evidence")
            n_claims += 1
    if len(ledger.get("must_not_claim", [])) != 3:
        fail("must_not_claim != 3")

    # ---- 7. P2: frozen base unchanged vs git HEAD (when committed) ----
    if len(ledger["facts"]) != 110 or len(probes) != 40:
        fail("fact/probe count changed")
    repo_top, gold_rel = _git_repo_info()
    head_checked = False
    if repo_top and gold_rel and git_head_exists(repo_top, f"{gold_rel}/ledger.json"):
        head_ledger = json.loads(git_head(repo_top, f"{gold_rel}/ledger.json"))
        for key in ("persona", "people", "subjects", "orgs", "places", "facts",
                    "edges", "alias_traps"):
            if ledger[key] != head_ledger[key]:
                fail(f"ledger.{key} changed vs HEAD")
        if set(ledger) - set(head_ledger) - {"milestones", "trivia", "profile", "must_not_claim"}:
            fail("unexpected ledger top-level keys")
        if git_head(repo_top, f"{gold_rel}/probes.json") != (GOLD / "probes.json").read_text(encoding="utf-8"):
            fail("probes.json changed vs HEAD")
        if git_head(repo_top, f"{gold_rel}/ingest_order.json") != (GOLD / "ingest_order.json").read_text(encoding="utf-8"):
            fail("ingest_order.json changed vs HEAD")
        for fn in ("sources/whatsapp_best.txt", "sources/whatsapp_work.txt",
                   "sources/whatsapp_family.txt", "sources/gmail.jsonl", "sources/notes.md"):
            if git_head(repo_top, f"{gold_rel}/{fn}") != (GOLD / fn).read_text(encoding="utf-8"):
                fail(f"{fn} changed vs HEAD")
        head_checked = True

    # ---- counts only ----
    n_wa = len(wa_lines)
    print(f"people=25 subjects={len(subjects)} facts={len(facts)} edges={len(ledger['edges'])} "
          f"traps=4 changed={sum(1 for f in facts.values() if f['status'] == 'changed')} "
          f"ended={sum(1 for f in facts.values() if f['status'] == 'ended')} "
          f"sensitive={sum(1 for f in facts.values() if f['sensitive'])}")
    print(f"records: whatsapp={n_wa} gmail={len(gmails)} notes={len(notes)} "
          f"total={len(all_records)} late={len(ingest['late_records'])}")
    print(f"probes=40 person=10(3 alias) contradiction=10 twohop=8 arabic=6 sensitive=4 noise=2")
    head_note = "base frozen vs HEAD" if head_checked else "local integrity (not yet in HEAD)"
    print(f"milestones=6 trivia=12 profile_claims={n_claims} must_not_claim=3; "
          f"{head_note} (110 facts, 1172 records, 40 probes). PASS")


if __name__ == "__main__":
    main()
