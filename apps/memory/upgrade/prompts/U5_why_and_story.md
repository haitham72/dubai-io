# U5 — "Why" and "tell a story" (R3, R5)

Assigned to: **Gemini** (queue `Q_gemini.md`, item 2). The integrator is **Claude**.
**Starts when** `memory` contains U1c (your item 1) and U0c (contract v2 `reason_*` fields). The reason *values* come from U3 later. Until then, `/why` returns "reason unknown", which is correct.

```powershell
git -C G:\Haitham\VsCode\contest worktree add ..\contest-mem-wpU5 -b mem-wpU5 memory
cd G:\Haitham\VsCode\contest-mem-wpU5\apps\memory
```

## Owned files

- new `src/temporal_memory/api/story.py`
- `src/temporal_memory/api/vault.py`: only the `/why` handler
- new `db/migrations/NNNN_story_cache.sql`: use the next free number when you start (U0c takes 0002 and 0003). If two branches collide, Claude renumbers at merge time.
- `api/vault.py` and `live/context.py`: replace the local `LIFE_SPINES` / `_SPINE_BY_ROOT` with `models.CLUSTERS` / `CLUSTER_LABELS` / `HELD_BACK_ROOTS` from U0c
- one `include_router` line in `api/app.py`
- tests: new `test_story.py`, `test_why.py`

## Deliverables

1. **`/why/{fact_id}`:**
   - an exact lookup (`get_facts`);
   - evidence spans, not whole raw records;
   - **provenance kept separate from the reason**;
   - `reason` = the stored cited span, or `"reason unknown"`. Never generated;
   - 404 only when the fact is truly forgotten or invisible.
2. **`GET /v1/owners/{o}/story?entity=…|subject=…&from=…&to=…`:**
   - **deterministic first:** a chronological cited timeline (dates, valid intervals, changes "was X until Y", reasons where stored). Every line carries `fact_ids`. This needs no model;
   - **optional narration** (`?narrate=1`): one call through the configured runner (local Qwen first, then the internal cloud fallback, as in D-b), with input capped at about 2k tokens of screened facts. **Accept only sentences whose cited `fact_ids` ⊆ the retrieved visible set.** Run `pre_write` and the Rule-9 screen on the output. On any failure or over budget (`governor_usd_per_month`), return the deterministic template;
   - only visible, non-hypothesis, non-sensitive facts; People & family only from `user_supplied` / confirmed facts;
   - cache in Postgres keyed by `(owner, generation, facts_version, privacy_revision, query_hash, template/prompt/model version)`, so Forget invalidates it atomically.
3. **Part C — MOVED to Cursor (`prompts\U6_quest_tree_and_persona_cards.md`, 24 Nov). Gemini: skip it; don't edit `api/export_md.py`.** The original text is kept below for reference.

   ~~Part C — the §9 Quest-like export tree.~~ Make `api/export_md.py` render the locked tree in `docs/plan/Memory/memory.md` §9 instead of the old planaudit §3.1 tree:
   - **root files:** `USER.md` (7 sections, citing leaves), `NOW.md`, `MEMORIES.md`, `SOURCES.md`, `MECHANICAL_INDEX.md`;
   - **spine folders** `01-people/` (with `inner-circle/`, `friends-and-peers/` and `professional-network/` from **confirmed** tiers only) through `07-travel-and-places/`, mapped from `models.CLUSTERS`;
   - **`_staging/hypotheses-to-confirm.md`** + `proposed-tree-splits.md`;
   - **four-block leaves** (YAML frontmatter, Current Snapshot, Open Loops & Active Signals, Timeline & Fact History + Evidence Limits).

   Health and faith never get a spine. Every bullet carries provenance + `as_of` and cites its facts. Compare against the locked references `docs/plan/Memory/_archive/quest-memory-export/` and `_archive/hindsight-kb-export/` (**read-only, never move or delete them**). Test: for the gold month the tree's file list matches §9, and no quarantined or inferred-as-stated item appears. You also own `api/export_md.py` for this part.
4. **Tests (Postgres), happy + failure paths:**
   - every sentence cites visible facts;
   - an uncited or invented sentence is dropped;
   - a forgotten fact disappears from a cached story;
   - a sensitive fact is never narrated;
   - over budget → the template;
   - a reason span that is absent → "reason unknown";
   - p95 cached < 50 ms, uncached template < 150 ms.

**Report** → `reports\U5.md`: branch + commit, test counts, a sample deterministic story and a sample narrated story (synthetic Karim), latency.
