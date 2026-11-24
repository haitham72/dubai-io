# U3 — Backfill quality: why the shipped extractor is weak, then reason / places / one taxonomy (R3, R6; D-a)

Assigned to: **Cursor** (queue `Q_cursor.md`, item 2). The integrator is **Claude**.
**Starts when** `memory` contains U1b (your own item 1) **and** U0c (contract v2, Codex). Until U0c lands you can already do Part A (diagnosis only; no contract needed).

```powershell
git -C G:\Haitham\VsCode\contest worktree add ..\contest-mem-wpU3 -b mem-wpU3 memory
cd G:\Haitham\VsCode\contest-mem-wpU3\apps\memory
```

## Owned files (only these)

- `src/temporal_memory/core/extract.py`, `core/validator.py`
- `core/applier.py`: reason, `place_type` and op handling only
- `queue/jobs.py`: day bucketing and chunking only
- `ingest/triage.py`: the timezone function
- new `src/temporal_memory/core/daytime.py`
- new `src/temporal_memory/db/proposals/` (never applied automatically)
- tests: `test_extract*.py`, `test_validator.py`, `test_applier.py`, `test_jobs.py`, new `test_chunking.py`

## Part A — diagnose first (evidence before changes)

The U0b baseline (`acceptance/results/e05371f-20261124-1059/BASELINE.md`, S2) measured `apps/memory`'s own worker (`claude-haiku-5-5`) on the gold month:
- **recall 66.7 %, precision 59 %**;
- **changes: 1/8 superseded, 0/5 ended, 0/4 late**;
- mean **$0.00492 / day**.

The weekbench adapter (`weekbench/configs/tn_update.py`, LEADERBOARD month run) scored 92 % and 6 of 8 with a weaker scorer. Find out, with evidence, how much is real: diff the prompt, the output schema, the context passed (`scoped_context`), the applier rules and the model between the two. Write `reports\U3_diagnosis.md` **before** changing code, with each cause and its measured effect (re-run S2 with one change at a time where cheap).

## Part B — fixes

1. **Parity fixes** from Part A. Targets on S2: **8/8 superseded, every ended, 4/4 late** (gold counts per the harness), with recall and precision up and **mean cost ≤ $0.0044 per owner-day** (report p95 and max too). If the cost gate can't be met with the current model's price, say so with numbers.
2. **Reason span** (contract v2 `reason_*`): extract the stated "because …" only when the source says it. The validator checks that the span exists in the cited record; otherwise the reason is dropped (never invented).
3. **R6 places and preferences:** the keep-list adds *places visited, likes, dislikes, preferences*. Places get `place_type`. Food and outings go under `events`.
4. **One taxonomy (D-a):** the extractor's `subject_path` roots = `models.CLUSTERS` + `HELD_BACK_ROOTS` (health and faith are never clusters). Write `db/proposals/cluster_roots.sql` (**not** in `db/migrations/`: `migrate()` applies every `.sql` file there) **only as a reviewed proposal** mapping the old roots (`background, devices, family, health, identity, interests, learning, lifestyle, money, projects, wellbeing, work`) → new ones, and list the mapping in your report. **Don't run it on any real database**; the founder confirms the mapping.
5. **Days and chunks:**
   - one `daytime.local_day(at, tz)` used by `ingest/triage.py`, `queue/jobs.py::split_import` and the bridge;
   - split a day packet by a token budget (`TM_PACKET_TOKEN_BUDGET`, config; proposal 4000) into ordered chunks, with chunk-aware idempotency keys;
   - later chunks get the earlier chunks' new facts in their context, so updates still work;
   - `split_import` uses the same owner-device / internal pool routing as `ingest_records`.
6. **`PROMPT_VERSION = "extract@4"`,** with dedupe-safe re-runs: no `duplicate_fact` storm, and the existing valid intervals are kept.
7. **Stated vs inferred** (from `reports\U1b.review.md`): add an `OutFact` flag. `provenance_for_statement` returns `user_supplied` only when the record is owner-authored **and** the fact is `stated`.
8. **Topic aliases (founder: "phone" must find iPhone facts):**
   - the backfill writes subject aliases (EN / AR / Arabizi, e.g. phone = mobile = iphone = samsung = موبايل = تليفون), stored with the subject;
   - `search_candidates`' subject channel matches query tokens against subject labels **and** those aliases;
   - seed a small alias list for the common Dubai-life subjects from `docs/references/residence-ontology-tree.md` (read-only).
   - Test: "phone" retrieves an "iPhone 13 Pro Max" fact that has no token "phone".
9. **Validator per fact, not per job** (diagnosis cause 1): a bad fact is dropped or quarantined alone; the rest of the day applies. **Show the model the active facts it may update** (cause 2).

## Tests

Happy + failure paths:
- a heavy day → several chunks, and the later chunk updates the earlier fact;
- 20:30Z in Dubai → the next local day, on every path;
- an invented reason (span not in the record) → dropped;
- a restaurant with "loved it" → a place with `place_type=restaurant` and a preference fact;
- old roots map per the proposal;
- the full suite plus `TM_RUN_E2E=1` gold month green.

**Report** → `reports\U3.md`: branch + commit, the Part A causes table, the S2 before → after (recall, precision, changes, cost mean / p95 / max), the mapping proposal, test counts.
