# P1A — Muse: synthetic 30-day corpus + gold probe set

Paste everything below the line into Muse.

---

You are building the **gold evaluation set** for a memory-library bake-off for Dubai-io, a personal AI agent for people in Dubai. Read `G:\Haitham\lab-data\memory-bakeoff\PLAN.md` first, especially §1 (the goal chain) and §4 (the MemoryInsight contract). Your own earlier audit is at `G:\Haitham\lab-data\bench-4tools-30d\muse_spark_auditRview.md`. This set must fix the flaws you found there: vacuous supersession, keyword grading, and untested graph hops.

## Method: truth ledger first, then render

Write the truth ledger first and render the messages from it, never the other way round. That way the gold answers are correct by construction.

1. **Persona.** "Karim Haddad", 31, AI engineer living in Dubai. Speaks English, Egyptian Arabic and Arabizi. Fully fictional. Don't use any real person from the founder's data.
2. **Truth ledger** `gold/ledger.json`, covering 30 days (2026-10-20 → 2026-11-19):
   - **25 people**, each with `id`, canonical name, **2–3 aliases** (e.g. `Omar`, `عمر`, `3omar`, `O.`), relation to Karim (friend / colleague / manager / recruiter / family / neighbour), and their facts over time.
   - **12 subjects/projects** (e.g. a side-project app, a job search, a marathon plan, a car purchase, a course).
   - **Typed edges** between people, subjects, orgs and places, each with `valid_from` / `valid_to`.
   - **15 changes over time:**
     - 6 `changes` (job switch, date moved, price changed);
     - 5 `ends` (plan cancelled, subscription stopped);
     - 4 **late-arriving older facts** (an email from day 3 ingested after a day-20 update; it must NOT overwrite the newer fact).
   - **8 sensitive third-party facts** (a relative's illness, a friend's divorce, someone's religion practice, a credential in an email). These must be gated, never surfaced.
   - **4 alias traps:** two different people sharing a first name, and one person under three spellings.
   - **Milestones gold:** 6 real milestones Karim never labels as milestones (e.g. shipped a beta, passed a certification, signed a car lease, finished a half-marathon), each with `status` (done / in_progress / planned) and evidence across ≥ 2 days. Also 12 **trivia events** that must NOT become milestones (app sign-ups, OTP logins, subscription renewals, newsletter joins, account linking).
3. **Render sources** from the ledger:
   - `gold/sources/whatsapp_*.txt` in real WhatsApp export format: 3 chats (best friend, work group, family). About 900 messages total, mixed EN/AR/Arabizi, with realistic noise ("ok", stickers, `<Media omitted>`).
   - `gold/sources/gmail.jsonl`: about 200 emails as `{id, thread_id, ts, from, subject, body}`. About 60% noise: promos, OTPs, newsletters, job-alert spam.
   - `gold/sources/notes.md`: about 40 dated personal notes and dev-log lines.
   - Every planted fact must appear in **at least one** source record. Record which ones in the ledger (`evidence: [record_ids]`).
4. **Backfill order file** `gold/ingest_order.json`: the record IDs in the order the harness ingests them, with the 4 late-arriving older facts placed after their newer versions.
5. **40 live probe turns** `gold/probes.json`. Each one is a message Karim types *after* backfill, with its gold MemoryInsight (§4 of `PLAN.md`, all fields). Mix:
   - 10 person + relation (including 3 alias resolutions);
   - 10 contradiction / change (exact `memory_id` = ledger fact ID, plus verdict);
   - 8 two-hop links (person → org → subject);
   - 6 Arabic or Arabizi turns;
   - 4 that touch a sensitive fact (gold: `gated` count > 0, the fact text appears nowhere in `finding`);
   - 2 pure-noise turns (gold: no contradiction, no new subject).

   Each probe also lists `must_not_contain` (stale or ended facts, sensitive text) and `gold_context_fact_ids` (3–8 IDs).
6. **Self-check script** `gold/validate.py`. Assert:
   - every ledger fact has evidence in a source;
   - every probe's gold IDs exist;
   - alias counts are as specified;
   - no real names from `G:\Haitham\lab-data\mamty*` folders appear (grep them).

   Print counts only.

## Constraints

- Write only under `G:\Haitham\lab-data\memory-bakeoff\gold\`.
- Don't read or copy real family chats. Keep it synthetic.
- Fact IDs in `probes.json` are **ledger fact IDs**. The harness maps each library's stored memories back to ledger IDs through the evidence record IDs, so keep `record_id` on every source line (WhatsApp: line number; email: `id`).

## Done when

`python gold/validate.py` passes. Then finish with a 10-line summary: counts per category and anything you couldn't make realistic.
