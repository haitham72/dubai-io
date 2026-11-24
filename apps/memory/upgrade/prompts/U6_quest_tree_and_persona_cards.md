# U6 — The Quest-like memory tree + persona cards (one builder, two outputs)

Assigned to: **Cursor**. The integrator is **Claude**.
**Starts when** `memory` contains U1c (Gemini) and U3 (yours). Check `reports\STATUS.md`.

```powershell
git -C G:\Haitham\VsCode\contest worktree add ..\contest-mem-wpU6 -b mem-wpU6 memory
cd G:\Haitham\VsCode\contest-mem-wpU6\apps\memory
```

## Why

The founder: "backfill mainly is used for persona cards". The locked design is `docs/plan/Memory/memory.md` (branch `memory`):
- **§9:** the Quest-like tree;
- **§17:** the Vault;
- **§18:** the current engine.

A **card** is the rendered form of a §9 **leaf**, so build one projection and render it twice: as md files and as JSON cards.

## Owned files

- `src/temporal_memory/api/export_md.py`
- new `src/temporal_memory/core/persona.py` (the shared leaf / card builder)
- new `src/temporal_memory/api/cards.py` (+ one `include_router` line in `api/app.py`)
- tests: `test_export.py`, new `test_persona_cards.py`

## Deliverables

1. **`core/persona.py`.** It builds the §9 projection from Postgres through bounded SQL (never load-all):
   - the **7 spines** from `models.CLUSTERS` (`01-people` … `07-travel-and-places`). `01-people` is split into `inner-circle/`, `friends-and-peers/` and `professional-network/` from **confirmed** tiers only;
   - **leaves** per subject / topic and per person / place;
   - each leaf has 4 blocks:
     - **Current Snapshot**: active facts;
     - **Open Loops & Active Signals**: planned / wanted triples, upcoming dates, unconfirmed "I noticed";
     - **Timeline & Fact History**: including "was X until Y" from superseded / ended facts;
     - **Evidence Limits**: from `owners.evidence_limits` and the held-back counts.
   - Every bullet has `fact_ids`, `provenance` ("You told me" only for `user_supplied`), `as_of`. Health and faith are never a spine. People & family uses only stated or confirmed facts.
2. **Export** (`api/export_md.py`): the §9 tree:
   - root files: `USER.md` (7 sections, citing leaves), `NOW.md` (open loops, the next-30-day dates, rising topics, pending confirmations), `MEMORIES.md` (the index with counts), `SOURCES.md` (watermarks, evidence limits, Never-Remember rules), `MECHANICAL_INDEX.md` (no LLM: subject → evidence record ids);
   - `_staging/hypotheses-to-confirm.md` + `proposed-tree-splits.md`: propose a split when a leaf has ≥ 12 facts (memory.md §6.2), proposal only.

   Compare against the locked references `docs/plan/Memory/_archive/quest-memory-export/` and `_archive/hindsight-kb-export/` (**read-only: never move or delete them**).
3. **Cards API** (`api/cards.py`):
   - `GET /v1/owners/{o}/cards?cluster=…|person=…` → the same leaves as JSON cards: title, cluster, snapshot, open loops, recent changes, "I noticed" items with Confirm / Not true actions, `fact_ids`, provenance, `as_of`;
   - `GET /v1/owners/{o}/people/{entity_id}/card`: the **person card** ("what I know about Omar"): relation, confirmed tier, snapshot, shared subjects, recent changes.
   - p95 < 150 ms at 20k facts.
4. **Tests (Postgres), happy + failure paths:**
   - for the gold month the tree's file list matches §9;
   - no quarantined, sensitive or inferred-as-stated bullet appears;
   - a superseded fact shows as "was … until …";
   - a forgotten fact disappears from the tree and the cards (privacy revision);
   - person card for a T1-confirmed person vs a suggested one;
   - the split proposal fires at 12 facts and never auto-applies.

**Report** → `reports\U6.md`: branch + commit, test counts, a sample tree listing + one sample leaf + one sample card (synthetic Karim), latency.
