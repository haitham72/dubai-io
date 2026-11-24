# P2 — Muse: add milestone + profile gold to the Karim ledger

Paste everything below the line into Muse. Working directory: `G:\Haitham\lab-data\memory-bakeoff\` (a git repo; commit when done).

---

Your gold set (`gold/`) is now the frozen benchmark for the memory bake-off (see `LEADERBOARD.md`). One part of the original spec didn't land: `gold/ledger.json` has no milestones. We need it to score the **reflection layer** (Honcho vs our own build), which writes a Quest-style `USER.md` and a milestones list.

Add, **without changing any existing fact, record or probe ID**:

1. **`ledger.milestones`:** 6 real milestones Karim never labels as milestones (e.g. shipped the Raseef beta, half-marathon done, car bought, offer accepted). Each gets `id` (`ms01`…), `title`, `status` (done / in_progress / planned) **as of the end of each week** (`status_by_week: {"1": ..., "5": ...}`), `fact_ids` (≥ 2 ledger facts from ≥ 2 different days) and `first_week`.
2. **`ledger.trivia`:** 12 events present in the sources that must **not** become milestones (app sign-ups, OTP logins, subscription renewals, newsletter joins, account linking, a one-off delivery). Each gets `id`, `text`, `record_ids`.
3. **`ledger.profile`:** the answer key for `USER.md`. For each Quest section (Identity, Personality, Values, Strengths & Tensions, Interests, Drive, Relationships), 2–4 true claims, each with supporting `fact_ids` and `first_week`, plus 3 **tempting-but-unsupported** claims a model might invent (`must_not_claim`).
4. If milestone or trivia evidence isn't in the sources yet, add the **minimum** new records at the **end** of the relevant files, with new IDs that don't shift existing line numbers. Insert them into `gold/ingest_order.json` at their chronological position. List any new record IDs.
5. Extend `gold/validate.py`: every milestone and profile claim resolves to facts with evidence, trivia record IDs exist, and the existing 110 facts, 1,172+ records and 40 probes are unchanged (compare against `git show HEAD:gold/ledger.json`).

**Done when** `python gold/validate.py` passes and you've committed. Reply with counts and any records you added.
