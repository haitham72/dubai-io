# U2 — Instant triples + topic counter + per-session catch-up (R1, R2, R5, R6; D-b)

Assigned to: **Codex** (queue `Q_codex.md`, item 2). The integrator is **Claude**.
**Starts when** `memory` contains U0c (contract v2) **and** U1b (stored provenance). Check with `git merge-base --is-ancestor <commit> memory`.

```powershell
git -C G:\Haitham\VsCode\contest worktree add ..\contest-mem-wpU2 -b mem-wpU2 memory
cd G:\Haitham\VsCode\contest-mem-wpU2\apps\memory
```

## Owned files (only these)

- new `src/temporal_memory/live/triples.py`
- new `src/temporal_memory/live/topics.py`
- new `src/temporal_memory/queue/session.py`
- `src/temporal_memory/api/bridge.py`: only the `/records` hook that calls these, plus the session enqueue
- `src/temporal_memory/queue/worker.py`: route `extract.session`
- `src/temporal_memory/config.py`: new settings only
- tests: new `test_triples.py`, `test_topics.py`, `test_session_job.py`

## Deliverables

1. **Code-only triple extractor (`live/triples.py`, no LLM, p95 < 50 ms).** It runs on `/records` for records **authored by the owner** (identity from the authenticated owner and the record author, never from the text).
   - **Emit only for explicit first-person assertions** in EN / Arabic / Arabizi, from narrow templates: "I bought / ordered / got X", "اشتريت", "eshtareet", "booked Zuma for Friday", "had dinner at Zuma in DIFC".
   - **Reject lists:** negation (didn't / ما / mesh), questions (incl. no "?"), future or modal ("going to", "will", "رح") → `modality=planned` / `wanted` **only** when the template is explicit, otherwise nothing; third party ("Sara bought"); quoted or forwarded text; sarcasm cues; sensitive (`pre_write` blocks health / family / faith / credentials).
   - **Ambiguous → abstain.**
   - Write a `Fact` with the triple fields + span:
     - `provenance=user_supplied` only for an explicit first-person `done` / `affirmed` assertion;
     - everything else is `status=hypothesis` / `provenance=inferred`.
   - Places from these templates become `place` entities with `place_type` when the template names it ("dinner at …" → restaurant).
   - Dedupe against the later backfill by `(owner, span_record_id, predicate, object_text)`.
2. **Topic counter (`live/topics.py`, R6, no LLM).** For each owner-authored chat record:
   - match existing subjects (subject label / path tokens + entity → `entity_subjects`) and call `record_topic_mention(owner, subject, session_id)`;
   - when the distinct-session count reaches **2**, create **one** idempotent "I noticed you're into ⟨subject⟩" hypothesis with the evidence of both sessions;
   - **never** for `HELD_BACK_ROOTS` or People & family;
   - a topic seen in one session creates nothing.
3. **Session catch-up (`queue/session.py`, D-b: local Qwen first, Haiku fallback).**
   - A session = the client's `session_id` in record `meta`; otherwise an idle gap of `TM_SESSION_IDLE_MINUTES` (config, proposal default 30).
   - On idle or close, enqueue **one** `extract.session` job for that session's records, instead of `extract.live` per batch.
   - Pool: `owner-device` / local (`TM_LMSTUDIO_MODEL`, today `qwen/qwen3-4b-2507`), with the existing fallback to the internal cloud runner after `p1_fallback_seconds`.
   - The attempt records the model actually used.
   - The session job must not duplicate the triples from item 1.
   - It is covered by Forget (U1a / U0c already list `extract.session`).
4. **Tests (Postgres + fake), happy + failure paths:**
   - the **acceptance trap set** `G:\Haitham\lab-data\memory-bakeoff\acceptance\TRAPS.md` (84 items) as fixtures, with these hard gates:
     - **every `no_triple` item emits nothing;**
     - **every `quarantine` item emits nothing and is quarantined;**
     - report recall on the `emit_triple` items, per language;
   - latency p95 < 50 ms per record (n ≥ 100);
   - a topic over 2 sessions → 1 hypothesis; over 1 session → none; a sensitive topic → none;
   - session idle → 1 job; a Qwen worker unavailable → Haiku after the fallback delay;
   - a third-party "Sara bought an iPhone" → no `user_supplied`.

**Report** → `reports\U2.md`: branch + commit, files, the trap-set table (per language: false emissions, recall), latency, test counts, contract requests.
