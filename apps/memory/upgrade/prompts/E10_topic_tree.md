# E10: One topic tree, with fixed general topics, expanded subtopics and words the LLM proposes (Gemini)

Read `E0_real_data_round.md` first. Branch `e10/topic-tree` from `main`. Do not touch `apps/web`, which is frozen.

## The founder's decision (25 Nov)

> "Fix general topics first and expand sub topics as well, but let the LLM propose to the backend that new words may be added. The world is a canvas that never ends, but everything is traced to a source and branches at some point."

The decision has three parts:

- **General topics** are fixed. Only the founder changes them.
- **Subtopics** are curated and expanded now.
- **New words** come from the LLM as *proposals*. Each one must hang under a word we already know (it branches from an existing word) and cite the record it came from (it is traced to a source). The backend checks a proposal before keeping it.

## Why (the current state on `main` 2a2e7f4)

Three word lists don't know about each other:

1. `_SYNONYM_GROUPS` / `_SYNONYM_MAP` in `apps/memory/src/temporal_memory/core/retrieval.py`.
   - These are flat, hard-coded groups.
   - They contain gold-fixture names: `fitzone`, `peakform`, `autohub`, `camry`, `testflight`, `الوكلاء`. So retrieval is partly tuned to the test set.
   - `run` sits in two groups, and the second one silently wins.
   - "surf" also pulls in "padel", "golf" and the other sports, because siblings expand to each other.
2. `SUBJECT_ALIAS_SEEDS` in `core/subject_aliases.py`, with 9 seeds.
3. Each owner's `subjects` tree, which extraction grows under the 7 clusters.

The groups exist because bge-m3 does not link "sport" to "surf school" (cosine 0.34, the same as unrelated pairs; see `reports/E9b.md`). So word expansion is still needed. It just has to come from one tree.

## Deliverables

### 1. One vocabulary, stored as data, not code

Create a new `apps/memory/src/temporal_memory/vocab/`. It holds one data file (YAML or JSON, your choice) and a loader that validates the file on load: every node's parent must exist, and paths must be unique.

- **General topics (fixed):**
  - Use the 14 roots and their first-level branches from `docs/references/residence-ontology-tree.md`, for example `lifestyle/sports`, `lifestyle/food` and `cars/…`. Ontology paths are the stable IDs.
  - Give each one a `cluster` field: one of the 7 clusters in `models.CLUSTERS`, taken from that doc's rollup table.
  - Give each one aliases in English, Arabic and Arabizi.
  - Stored fact `subject_path`s keep their cluster roots. There is **no data migration** of facts.
- **Subtopics (curated, expanded):**
  - Include the ontology leaves, with aliases.
  - Add the everyday leaves the current synonym list proves we need. Examples: a water-sports leaf (surf, surfing, kitesurf…); running (run, running, marathon, 10k, جري, ماراثون); team sports (padel, football, كورة…).
  - Use **generic words only**: no brand, venue, person or fixture names.
- **Lexicon:**
  - This section holds non-topic equivalents across English, Arabic and Arabizi. Move in today's start/begin, price/cost and mom/dad groups, keeping their Arabic and Arabizi words.
  - Lexicon entries are curated only, and they expand both ways.
- **Rule 9 marks:**
  - Mark these nodes `sensitive`: the `health` and `faith` roots, `kids_family`, family and relationship nodes, and the ontology's `⚠ user-stated only` leaves.
  - Curated words under them still expand, because the retrieval filter `_NON_SENSITIVE_CLAUSE` already governs what is returned.
  - They **never** take LLM proposals.
- **Delete** `_SYNONYM_GROUPS`, `_SYNONYM_MAP` and `SUBJECT_ALIAS_SEEDS`. Move their generic words into the file. `subject_aliases.py` then reads from the vocabulary.

### 2. Expansion follows the tree, from general to specific

- A query token that matches a node's label or alias expands to:
  - that node's own aliases;
  - then its descendants, breadth-first, including the owner's learned words (see 3);
  - cut at the existing `max_terms` cap.
- A token for a leaf expands only to that leaf's aliases and its learned children. **It does not expand to its siblings.**
- The expansion now needs the owner, because learned words belong to one owner. Cache each owner's learned words per `facts_version`.
- Keep the SQL candidate `LIMIT` and the existing **150 ms p95 gate at 20k facts**. Report p95 before and after.

### 3. The LLM proposes new words and the backend decides

- **The new output field:** extraction gets an optional output field `new_terms: [{"term": "...", "is_a": "<a word we already know>", "evidence": ["rec-…"]}]`.
  - It goes in the **same call**. There is **no extra LLM call**.
  - Keep the prompt addition short. Do **not** paste the tree into the prompt; the backend resolves `is_a`.
- **The checks:** the backend keeps a proposal only if every check passes. Otherwise it drops the proposal and counts it under the reason:
  - `no_branch`: `is_a` must resolve to exactly one node, either a curated one or one of this owner's learned words. If it matches more than one node, the reason is `ambiguous`.
  - `no_source`: every `evidence` id must be a record of this owner in this batch.
  - `rule9`: the resolved node must not be `sensitive`, or under a people, family or relationship node. The term must also pass the engine's existing privacy checks, the same ones `live/topics.py` `eligible_subject` uses: held-back roots, `_BLOCKED_ROOTS` and `quarantine_category`.
  - `curated_clash`: the term must not already be a curated word on another node. Proposals never re-parent curated words.
- **How kept words are stored:**
  - **Scope:** per owner only, with `provenance: inferred`, as a child of the resolved node. A new migration adds the learned-terms table and a link table from each term to its source records.
  - **More sightings:** a second sighting adds a source to the existing term instead of creating a duplicate.
  - **Use:** a learned word joins that owner's expansion straight away. A learned word can itself be the `is_a` of a later proposal, so the canvas grows deeper for that owner.
  - **Privacy boundary:** learned words never reach another owner, and they never enter the curated file.
- **Visibility (rule 9: nothing about the user is stored where they can't see it):**
  - Add `GET /vocab/learned`, scoped to the owner. It returns each term, its parent path and its source record ids.
  - Add **no** UI. UI work is paused.

### 4. Forget follows the source

- When Forget or a source revoke erases a learned term's **last** source record, delete the term.
- Close `MORNING.md` §E #18 the same way: after a Forget, delete the owner's `candidate` / inferred `subjects` and `subject_aliases` rows that have no live fact or source left.
- Keep user-supplied and confirmed subjects.

### 5. Tests (synthetic owners; LLM output stubbed)

Happy paths:

- "sport" finds a fact "booked a surf school for Saturday" through the curated tree. The same works with "رياضة".
- "بكام" still finds a price fact, through the lexicon.
- A stubbed proposal `{term: "FitZone", is_a: "gym", evidence: [rec]}` is kept. After that, "gym" finds this owner's "FitZone renewal" fact. A second owner's "gym" query does **not** get `fitzone`.

Failure paths:

- "surf" does **not** return a fact that only mentions padel.
- Proposals are dropped for `no_branch`, `ambiguous`, `no_source` (another owner's record), `rule9` (under a health or family node) and `curated_clash`, with the counts recorded.
- Forgetting the only source deletes the learned term. Forgetting one of two sources keeps it.
- A vocabulary file whose node has a missing parent fails to load.
- The §E #18 sweep deletes an orphaned inferred subject and keeps a confirmed one.

### 6. Honest acceptance

- Run acceptance S1 (retrieval) and S2 (change tracking) on `main` and on your branch. Report the changes for each probe.
- Probes that relied on the fixture names must now pass through learned words from the gold run (`TM_RUN_E2E`). If they don't, report them as misses.
- **Never** put fixture names back, and never edit gold probes.
- From the gold run, report these counts: proposals, kept, and dropped by reason.
- Report the extraction cost per day against E9b's $0.00517. Report the change; don't hide it.

## Owned files

- **One contract change in `models.py`, approved by Claude as integrator.** Add a `NewTerm` dataclass with `term`, `is_a` and `evidence`, and an optional `new_terms` field on `ExtractionOutput` that defaults to empty. Change nothing else in `models.py`.
- new `apps/memory/src/temporal_memory/vocab/` (data file + loader)
- `core/retrieval.py`, which drops the synonym groups and expands from the vocabulary
- `core/subject_aliases.py`
- `core/extract.py`, for the `new_terms` field in the prompt and the parser
- `core/applier.py`, but **only** the new proposal checks and storage. Codex's E11a edits `_late_superseder` in the same file, so don't reformat other functions.
- `privacy/forget.py`
- one new migration
- the API route for `GET /vocab/learned`
- tests

**Not:** `apps/web`, `apps/mobile` UI, or `live/topics.py` (topic counting stays as it is for now).

## Report

- Write `reports/E10.md` with: node, alias and lexicon counts; the S1/S2 changes for each probe; the counts of proposals kept and dropped by reason; p95 before and after; the cost change; test counts.
- **Counts only.** No real-user content.
- Add a line to `reports/STATUS.md` when the work is `ready-for-review`.

## Then (same queue, no new prompt): rerun E6 on main

1. Check: `git merge-base --is-ancestor <E10 merge commit> main`. Do the same for E11a and E11b once they are merged (see `STATUS.md`).
2. Rerun the E6 harness, all 5 lanes, on current `main`. If E10 or E11 is not merged yet, run anyway and state which commits were included.
3. Write `reports/U7_post_E11.md`, with PASS/FAIL for each check compared with `U7_final.md`, and the screenshots path.
