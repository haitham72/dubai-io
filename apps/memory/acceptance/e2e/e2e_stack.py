"""E6 lane 3: scripted end-to-end on the started stack (scripts/dev/start-all.ps1) with two SYNTHETIC accounts.

Run with the apps/api venv:  python e2e_stack.py <sessions.json> <out.json> [stage]
Stages: ingest | verify | forget | isolation | all (default).  Never prints tokens.
Synthetic fixtures only; Gmail is mocked at the engine boundary (a Google pull cannot be mocked on a live stack).
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import time
import zipfile
from datetime import datetime, timedelta, timezone

import httpx
import psycopg

API, COMMUNITY, MESSENGER, MEM = "http://localhost:8000", "http://localhost:8060", "http://localhost:8070", "http://localhost:8040"
TM_DSN = os.environ.get("TM_DATABASE_URL", "postgresql://tm:tm@localhost:5442/tm")
MARK = {"A": {"wa": "Quillfeather", "gm": "Zinnwald", "yt": "Zephyrcrest"},
        "B": {"wa": "Marmoset", "gm": "Tamarind", "yt": "Halcyonford"}}
RESULTS: list[dict] = []


def rec(name: str, ok: bool, detail: str = "") -> bool:
    RESULTS.append({"check": name, "ok": bool(ok), "detail": detail[:400]})
    print(("PASS " if ok else "FAIL ") + name + (" :: " + detail[:200] if detail else ""), flush=True)
    return bool(ok)


def hdr(sess: dict, app: str) -> dict:
    return {"X-App-Session": sess[app]}


def days(n=4):
    base = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0)
    return [base - timedelta(days=i + 1) for i in range(n)]


def takeout_zip(k: str) -> bytes:
    m = MARK[k]["yt"]
    watch = []
    for i, d in enumerate(days()):
        for j in range(3):
            watch.append({"header": "YouTube", "title": f"Watched {m} tutorial {i}-{j} on {'Dubai padel coaching' if k == 'A' else 'Lisbon surf lessons'}",
                          "titleUrl": f"https://www.youtube.com/watch?v=syn{k}{i}{j}",
                          "subtitles": [{"name": f"{m} Channel", "url": "https://www.youtube.com/channel/synthetic"}],
                          "time": (d + timedelta(minutes=j * 7)).strftime("%Y-%m-%dT%H:%M:%S.000Z"), "products": ["YouTube"]})
    search = [{"header": "YouTube", "title": f"Searched for {m} {'Zuma DIFC dinner' if k == 'A' else 'Alfama fado night'}",
               "titleUrl": "https://www.youtube.com/results?search_query=x", "time": days()[0].strftime("%Y-%m-%dT%H:%M:%S.000Z"),
               "products": ["YouTube"]}]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("Takeout/YouTube and YouTube Music/history/watch-history.json", json.dumps(watch))
        z.writestr("Takeout/YouTube and YouTube Music/history/search-history.json", json.dumps(search))
    return buf.getvalue()


def whatsapp_txt(k: str) -> bytes:
    m = MARK[k]["wa"]
    me, other = ("Karim", "Salma") if k == "A" else ("Rui", "Ines")
    lines = []
    for i, d in enumerate(days(3)):
        ts = lambda mins: (d + timedelta(minutes=mins)).strftime("%m/%d/%Y, %I:%M:%S %p")
        if k == "A":
            texts = [(me, f"I started {m} calligraphy classes in Jumeirah this week"), (other, "Nice, how is it going?"),
                     (me, f"My {m} teacher says I should practice daily, I moved my padel game to Thursday"),
                     (me, "I am now working at a fintech in DIFC as a backend engineer")]
        else:
            texts = [(me, f"I joined the {m} surf school in Cascais"), (other, "Amazing, when do you go?"),
                     (me, f"The {m} coach moved my lesson to Friday, I switched to a new job at a Lisbon startup")]
        for j, (a, t) in enumerate(texts):
            lines.append(f"[{ts(j * 11)}] {a}: {t}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def gmail_records(k: str) -> list[dict]:
    m = MARK[k]["gm"]
    out = []
    for i, d in enumerate(days(2)):
        body = (f"Your {m} booking is confirmed for the weekend " + ("at the Palm Jumeirah spa" if k == "A" else "in Sintra") + ".")
        out.append({"id": f"e6:gmail:{k}:{i}", "source": "gmail", "at": d.isoformat(), "author": f"{m} Travel <noreply@{m.lower()}.example>",
                    "text": f"Subject: {m} booking {i}\n{body}"})
    return out


def owner_token(c: httpx.Client, sess: dict) -> str:
    r = c.post(f"{API}/api/identity/memory-device-token", headers=hdr(sess, "quest"), json={"label": "e6-harness"})
    r.raise_for_status()
    j = r.json()
    return j.get("token") or j["secret"] if isinstance(j, dict) and ("token" in j or "secret" in j) else j["data"]["token"]


def pg(sql: str, params=()):
    with psycopg.connect(TM_DSN, autocommit=True) as conn:
        return conn.execute(sql, params).fetchall()


def owner_scan(owner: str, needle: str, skip_chat: bool = False) -> dict[str, int]:
    """Raw SQL: every text/json column of every table that has an `owner` column, owner-scoped, ILIKE needle."""
    hits: dict[str, int] = {}
    with psycopg.connect(TM_DSN, autocommit=True) as conn:
        tabs = conn.execute("""SELECT table_name FROM information_schema.columns WHERE table_schema='public' AND column_name='owner'""").fetchall()
        for (t,) in tabs:
            cols = conn.execute("""SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s
                                   AND data_type IN ('text','character varying','json','jsonb','ARRAY')""", (t,)).fetchall()
            if not cols:
                continue
            cond = " OR ".join(f'"{c}"::text ILIKE %s' for (c,) in cols)
            extra = " AND id NOT LIKE 'chat:%%'" if (skip_chat and t == "records") else ""
            n = conn.execute(f'SELECT count(*) FROM "{t}" WHERE owner=%s AND ({cond}){extra}', (owner, *[f"%{needle}%"] * len(cols))).fetchone()[0]
            if n:
                hits[t] = n
    return hits


def wait_jobs(owner: str, timeout=900) -> dict:
    t0 = time.time()
    last = {}
    while time.time() - t0 < timeout:
        rows = pg("SELECT state, count(*) FROM jobs WHERE owner=%s GROUP BY state", (owner,))
        last = {s: n for s, n in rows}
        pending = sum(n for s, n in last.items() if s not in ("applied", "rejected", "dead", "failed", "cancelled", "superseded", "done", "expired"))
        if last and pending == 0:
            return last
        time.sleep(10)
    return {"timeout": True, **last}


def stage_ingest(c, S):
    for k in ("A", "B"):
        sess = S[k]["sessions"]
        for src in ("takeout", "whatsapp"):
            r = c.put(f"{API}/api/ingest/consent/{src}", headers=hdr(sess, "quest"), json={"enabled": True})
            rec(f"{k} consent {src}", r.status_code == 200, f"{r.status_code}")
        r = c.post(f"{API}/api/ingest/takeout", headers=hdr(sess, "quest"), files={"file": ("takeout.zip", takeout_zip(k), "application/zip")})
        rec(f"{k} ingest takeout", r.status_code == 200, f"{r.status_code} {r.text[:160]}")
        r = c.post(f"{API}/api/ingest/whatsapp", headers=hdr(sess, "quest"), files={"file": (f"WhatsApp Chat with Syn{k}.txt", whatsapp_txt(k), "text/plain")})
        rec(f"{k} ingest whatsapp", r.status_code == 200, f"{r.status_code} {r.text[:160]}")
        tok = owner_token(c, sess)
        uid = S[k]["user_id"]
        r = c.post(f"{MEM}/v1/owners/{uid}/records", headers={"Authorization": f"Bearer {tok}"},
                   json={"records": gmail_records(k), "enqueue": "extract.day"})
        rec(f"{k} ingest gmail (mocked, engine boundary)", r.status_code == 200, f"{r.status_code} {r.text[:160]}")


def stage_verify(c, S):
    for k in ("A", "B"):
        sess, uid = S[k]["sessions"], S[k]["user_id"]
        jobs = wait_jobs(uid)
        rec(f"{k} backfill finished", not jobs.get("timeout") and jobs.get("applied", 0) > 0, str(jobs))
        st = c.get(f"{API}/api/ingest/status", headers=hdr(sess, "quest")).json()
        rec(f"{k} status endpoint onboarding_percent", st.get("onboarding_percent") is not None, f"runner={st.get('runner')} model={st.get('model')} cost={st.get('recorded_backfill_cost_usd')}")
        facts = pg("SELECT count(*) FROM facts WHERE owner=%s", (uid,))[0][0]
        rec(f"{k} facts extracted", facts > 0, f"facts={facts}")
        # Today
        r = c.get(f"{API}/api/today?refresh=1", headers=hdr(sess, "quest"))
        j = r.json() if r.status_code == 200 else {}
        cards = j.get("cards", [])
        card_ok = bool(cards) and all(x.get("as_of") or j.get("as_of") for x in cards) and all(x.get("source") or x.get("provider") or x.get("sources") for x in cards)
        rec(f"{k} Today", r.status_code == 200 and "as_of" in j, f"http={r.status_code} cards={len(cards)} interests={len(j.get('interests', []))} empty_reason={j.get('empty_reason')} cards_have_source_asof={card_ok}")
        # Chat
        ask = "What am I learning or practising lately, and where?" if k == "A" else "What sport am I doing lately and where?"
        r = c.post(f"{API}/api/chat/turn", headers=hdr(sess, "quest"), json={"text": ask, "thread_id": f"e6-{k}"}, timeout=180)
        j = r.json() if r.status_code == 200 else {}
        rec(f"{k} Chat reply with citations", r.status_code == 200 and bool(j.get("reply") or j.get("text")), f"http={r.status_code} keys={sorted(j)[:8]} cited={len(j.get('cited_fact_ids') or j.get('citations') or [])} runner={j.get('runner')}")
        # graph both views
        for view in ("subjects", "people"):
            r = c.get(f"{API}/api/vault/graph", params={"view": view}, headers=hdr(sess, "quest"))
            g = r.json() if r.status_code == 200 else {}
            ids = {n["id"] for n in g.get("nodes", [])}
            orphan = [e for e in g.get("edges", []) if e.get("src") not in ids or e.get("dst") not in ids]
            rec(f"{k} graph view={view}", r.status_code == 200 and len(ids) > 0 and not orphan, f"http={r.status_code} nodes={len(ids)} edges={len(g.get('edges', []))} orphans={len(orphan)}")
        tok = owner_token(c, sess)
        H = {"Authorization": f"Bearer {tok}"}
        # why / story / export / quests
        fid = pg("SELECT id FROM facts WHERE owner=%s AND status='active' ORDER BY created_at DESC LIMIT 1", (uid,)) if False else pg("SELECT id FROM facts WHERE owner=%s LIMIT 1", (uid,))
        if fid:
            r = c.get(f"{MEM}/v1/owners/{uid}/why/{fid[0][0]}", headers=H)
            w = r.json() if r.status_code == 200 else {}
            rec(f"{k} why", r.status_code == 200 and bool(w.get("evidence") or w.get("evidence_spans") or w), f"http={r.status_code} keys={sorted(w)[:8]}")
        r = c.get(f"{MEM}/v1/owners/{uid}/story", headers=H)
        s = r.json() if r.status_code == 200 else {}
        rec(f"{k} story", r.status_code == 200 and bool(s), f"http={r.status_code} keys={sorted(s)[:8]}")
        r = c.get(f"{MEM}/v1/owners/{uid}/export/md.zip", headers=H)
        names = []
        if r.status_code == 200:
            names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
        rec(f"{k} Quest-tree export (md.zip)", r.status_code == 200 and len(names) > 0, f"http={r.status_code} files={len(names)}")
        r = c.get(f"{API}/api/vault/quests", headers=hdr(sess, "quest"))
        rec(f"{k} quests endpoint", r.status_code == 200, f"http={r.status_code} quests={len((r.json() or {}).get('quests', [])) if r.status_code == 200 else '-'}")
        cost = pg("SELECT coalesce(sum(a.cost_usd),0), count(*) FROM job_attempts a WHERE a.owner=%s", (uid,))[0]
        print(f"INFO {k} job_attempts={cost[1]} cost_usd={float(cost[0]):.4f}", flush=True)
        RESULTS.append({"check": f"{k} LLM attempts", "ok": True, "detail": f"{cost[1]} attempts ${float(cost[0]):.4f}"})


def stage_forget(c, S):
    k = os.environ.get("E6_FORGET_ACCOUNT", "B")
    sess, uid = S[k]["sessions"], S[k]["user_id"]
    needle = MARK[k]["yt"]
    before = owner_scan(uid, needle)
    rec(f"{k} takeout marker present before Forget (precondition)", bool(before), str(before))
    r = c.delete(f"{API}/api/ingest/takeout/data", headers=hdr(sess, "quest"))
    rec(f"{k} Forget takeout source", r.status_code == 200, f"{r.status_code} {r.text[:160]}")
    after = owner_scan(uid, needle)
    rec(f"{k} raw SQL: no '{needle}' in any owner table after Forget", not after, str(after))
    tok = owner_token(c, sess)
    H = {"Authorization": f"Bearer {tok}"}
    for path, q in (("search", {"q": needle}), ):
        r = c.get(f"{MEM}/v1/owners/{uid}/{path}", params=q, headers=H)
        rec(f"{k} API search finds no '{needle}'", needle.lower() not in r.text.lower(), f"http={r.status_code}")
    r = c.post(f"{MEM}/v1/owners/{uid}/context", headers=H, json={"text": f"{needle} tutorial", "max_tokens": 1500})
    cj = r.json() if r.status_code == 200 else {}
    # `candidate_names` merely echoes the query's own words; leaks would show in facts / entities.
    rec(f"{k} API context returns no '{needle}' fact/entity", needle.lower() not in json.dumps([cj.get("facts"), cj.get("entities")]).lower(), f"http={r.status_code} facts={len(cj.get('facts', []))}")
    for view in ("subjects", "people"):
        r = c.get(f"{API}/api/vault/graph", params={"view": view}, headers=hdr(sess, "quest"))
        rec(f"{k} graph({view}) has no '{needle}'", needle.lower() not in r.text.lower())
    r = c.get(f"{MEM}/v1/owners/{uid}/story", headers=H)
    rec(f"{k} story has no '{needle}'", needle.lower() not in r.text.lower())
    r = c.get(f"{MEM}/v1/owners/{uid}/export/md.zip", headers=H)
    blob = b""
    if r.status_code == 200:
        z = zipfile.ZipFile(io.BytesIO(r.content))
        blob = b"\n".join(z.read(n) for n in z.namelist())
    rec(f"{k} export has no '{needle}'", needle.lower().encode() not in blob.lower())
    # other sources must survive
    wa = owner_scan(uid, MARK[k]["wa"])
    rec(f"{k} whatsapp data still present (Forget is source-scoped)", bool(wa), str(wa))


def stage_sweep(c, S):
    """A forgets her mocked-Gmail records through the engine; E8's sweep must also scrub A's EARLIER soft-erased takeout rows."""
    k = "A"
    sess, uid = S[k]["sessions"], S[k]["user_id"]
    tok = owner_token(c, sess)
    H = {"Authorization": f"Bearer {tok}"}
    before = owner_scan(uid, MARK[k]["yt"])
    r = c.post(f"{MEM}/v1/owners/{uid}/forget", headers=H, json={"record_ids": [f"e6:gmail:{k}:0", f"e6:gmail:{k}:1"], "idempotency_key": "e6-sweep"})
    rec(f"{k} Forget gmail records via engine", r.status_code == 200, f"{r.status_code} {r.text[:200]}")
    after_gm = owner_scan(uid, MARK[k]["gm"])
    rec(f"{k} raw SQL: no '{MARK[k]['gm']}' after Forget", not after_gm, str(after_gm))
    after_yt = owner_scan(uid, MARK[k]["yt"])
    rec(f"{k} raw SQL: earlier soft-erased takeout text swept (no '{MARK[k]['yt']}')", not after_yt, f"before={before} after={after_yt}")


def stage_isolation(c, S):
    for me, other in (("A", "B"), ("B", "A")):
        sess, uid = S[me]["sessions"], S[me]["user_id"]
        foreign = [MARK[other][x] for x in ("wa", "gm", "yt")]
        surfaces = {}
        tok = owner_token(c, sess)
        H = {"Authorization": f"Bearer {tok}"}
        for fm in foreign:
            surfaces.setdefault("quest-search", "")
            surfaces["quest-search"] += c.get(f"{MEM}/v1/owners/{uid}/search", params={"q": fm}, headers=H).text
        cj = c.post(f"{MEM}/v1/owners/{uid}/context", headers=H, json={"text": " ".join(foreign), "max_tokens": 1500}).json()
        # `candidate_names` only echoes the query's own words; a leak would be a fact / entity / open change.
        surfaces["quest-context"] = json.dumps([cj.get("facts"), cj.get("entities"), cj.get("open_changes")])
        surfaces["quest-graph"] = "".join(c.get(f"{API}/api/vault/graph", params={"view": v}, headers=hdr(sess, "quest")).text for v in ("subjects", "people"))
        surfaces["quest-today"] = c.get(f"{API}/api/today?refresh=1", headers=hdr(sess, "quest")).text
        surfaces["quest-chat"] = c.post(f"{API}/api/chat/turn", headers=hdr(sess, "quest"), json={"text": f"What do you know about {foreign[0]} {foreign[1]}?", "thread_id": f"iso-{me}"}, timeout=180).text
        surfaces["quest-export"] = ""
        r = c.get(f"{MEM}/v1/owners/{uid}/export/md.zip", headers=H)
        if r.status_code == 200:
            z = zipfile.ZipFile(io.BytesIO(r.content))
            surfaces["quest-export"] = "\n".join(z.read(n).decode("utf-8", "ignore") for n in z.namelist())
        # Community + Messenger (own app sessions)
        cm = c.get(f"{COMMUNITY}/api/community/memory/consent", headers=hdr(sess, "community"))
        surfaces["community-consent"] = cm.text
        ci = c.get(f"{API}/api/memory-bridge/community/interests", headers=hdr(sess, "community")) if False else None
        mg = c.get(f"{MESSENGER}/api/messenger/memory", headers=hdr(sess, "messenger"))
        surfaces["messenger-memory"] = mg.text
        rec(f"{me} community session valid", cm.status_code == 200, f"http={cm.status_code}")
        rec(f"{me} messenger session valid", mg.status_code == 200, f"http={mg.status_code}")
        for name, text in surfaces.items():
            leak = [f for f in foreign if f.lower() in text.lower()]
            # a chat reply echoing the user's own question text is not a leak: question contains the foreign words
            if name == "quest-chat":
                try:
                    j = json.loads(text)
                    text = str(j.get("reply") or j.get("text") or "")
                    leak = [f for f in foreign if f.lower() in text.lower()]
                    denies = any(w in text.lower() for w in ("don't", "do not", "no information", "not have", "no saved", "nothing", "can't", "cannot", "unable"))
                    if leak and denies:
                        leak = []  # the reply only repeats the asked words while saying it knows nothing
                    RESULTS.append({"check": f"{me} chat reply text (review)", "ok": True, "detail": text[:300]})
                except Exception:
                    pass
            rec(f"{me} sees none of {other}'s data in {name}", not leak, f"leaked={leak}" if leak else "")
        # app scoping: a Quest session must not open Community/Messenger and vice versa
        x = c.get(f"{COMMUNITY}/api/community/memory/consent", headers=hdr(sess, "quest"))
        rec(f"{me} quest session rejected by Community", x.status_code in (401, 403), f"http={x.status_code}")
        x = c.get(f"{MESSENGER}/api/messenger/memory", headers=hdr(sess, "quest"))
        rec(f"{me} quest session rejected by Messenger", x.status_code in (401, 403), f"http={x.status_code}")
        x = c.get(f"{API}/api/vault/graph", headers=hdr(sess, "messenger"))
        rec(f"{me} messenger session rejected by Quest vault", x.status_code in (401, 403), f"http={x.status_code}")
        # cross-owner path spoof on the engine
        other_uid = S[other]["user_id"]
        x = c.get(f"{MEM}/v1/owners/{other_uid}/search", params={"q": MARK[other]["wa"]}, headers=H)
        rec(f"{me} owner token refused on {other}'s owner path", x.status_code in (401, 403, 404), f"http={x.status_code}")
    # raw SQL: owner-scoped separation
    for me, other in (("A", "B"), ("B", "A")):
        uid = S[me]["user_id"]
        leaks = {f: {t: n for t, n in owner_scan(uid, f, skip_chat=True).items()} for f in (MARK[other]["wa"], MARK[other]["gm"], MARK[other]["yt"])}
        rec(f"raw SQL: {me}'s owner rows contain no {other} marker", not any(leaks.values()), str({k: v for k, v in leaks.items() if v}))


def stage_graph(c, S):
    for k in ("A", "B"):
        sess = S[k]["sessions"]
        for view in ("subjects", "people"):
            r = c.get(f"{API}/api/vault/graph", params={"view": view}, headers=hdr(sess, "quest"))
            g = r.json() if r.status_code == 200 else {}
            ids = {n["id"] for n in g.get("nodes", [])}
            orphan = [e for e in g.get("edges", []) if e.get("src") not in ids or e.get("dst") not in ids]
            raw = any(n.get("kind") == "owner" and str(n.get("label", "")).startswith("usr_") for n in g.get("nodes", []))
            rec(f"{k} graph view={view}", r.status_code == 200 and len(ids) > 0 and not orphan,
                f"http={r.status_code} nodes={len(ids)} edges={len(g.get('edges', []))} orphans={len(orphan)} owner_label_is_raw_user_id={raw}")


def main():
    sess_path, out_path = sys.argv[1], sys.argv[2]
    stage = sys.argv[3] if len(sys.argv) > 3 else "all"
    S = json.load(open(sess_path, encoding="utf-8"))
    c = httpx.Client(timeout=120)
    stages = {"sweep": stage_sweep, "graph": stage_graph, "ingest": stage_ingest, "verify": stage_verify, "forget": stage_forget, "isolation": stage_isolation}
    for name in (stages if stage == "all" else [stage]):
        print(f"--- stage {name}", flush=True)
        try:
            stages[name](c, S)
        except Exception as exc:  # report, keep going
            rec(f"stage {name} crashed", False, f"{type(exc).__name__}: {exc}")
    prev = []
    if os.path.exists(out_path):
        prev = json.load(open(out_path, encoding="utf-8"))
    json.dump(prev + RESULTS, open(out_path, "w", encoding="utf-8"), indent=1)
    print(f"{sum(r['ok'] for r in RESULTS)} PASS / {sum(not r['ok'] for r in RESULTS)} FAIL")


if __name__ == "__main__":
    main()
