# Task — Muse: E13b Similar-Query Clustering + Shared Vocab Agent + E10 Cleanups

- **Agent:** Muse
- **NEW Branch:** `e13b/shared-vocab-agent`
- **NEW Worktree:** `G:\Haitham\VsCode\contest-e13b`
- **Creation Command (run from any terminal first):**
  ```powershell
  git -C G:\Haitham\VsCode\contest fetch origin
  git -C G:\Haitham\VsCode\contest worktree add G:\Haitham\VsCode\contest-e13b -b e13b/shared-vocab-agent origin/main
  ```
- **Mandatory Reads First:**
  - `apps/memory/upgrade/prompts/E13b_similar_queries_vocab_agent.md`
  - `apps/memory/upgrade/reports/E10.review.md`
  - `docs/submissions/shared/founder-decisions.md` (D17, D19, D21)
  - `apps/memory/CLAUDE.md` and root `CLAUDE.md` (Rule 9, `apps/web` frozen)

---

## Deliverables

### 1. Migration `0009_shared_vocab_proposals.sql` (Explicitly `0009`)
- Path: `apps/memory/src/temporal_memory/db/migrations/0009_shared_vocab_proposals.sql`
- **Do NOT use `0008`** — `0008_memory_controls.sql` is reserved exclusively for E13a.
- Define:
  - Privacy-safe anonymised query signal storage (e.g., `vocab_query_signals`: hashed owner key, folded query/term, 1024-d `BAAI/bge-m3` `vector(1024)` embedding, hit count, resolved branch if any, timestamps — **never** store raw owner IDs or raw PII sentences).
  - `shared_vocab_proposals` table (`id`, `canonical_term`, `aliases_en_ar`, `parent_path`, `rationale`, `distinct_owners`, `cluster_metadata`, `status` `'pending' | 'approved' | 'rejected'`, `decided_at`, `decided_by`, `created_at`).

### 2. Similar-Query Retrieval & Clustering (`vocab/similarity.py`)
- Path: `apps/memory/src/temporal_memory/vocab/similarity.py`
- Screen any recorded unknown/low-hit search or context query token through `privacy/sensitive.py` **before** writing to `vocab_query_signals` (never store phone/email/names/Rule 9 sensitive terms).
- Implement **`find_similar_queries_and_terms(conn, query_text, *, top_k=15, min_sim=0.68)`**:
  - Combines `pgvector` cosine similarity over `bge-m3` query embeddings + existing curated `vocab/tree.json` node/alias embeddings with folded/Arabic-normalized lexical overlap (`fold_text`, `_arabic_variants` from `vocab/loader.py`).
  - Returns ranked similar queries/terms with **aggregate `distinct_owners` count only** (zero owner IDs exposed), nearest curated `parent_path`, and similarity score.

### 3. Logical Agent for Shared Vocabulary Proposals (`vocab/shared_proposer.py`)
- Path: `apps/memory/src/temporal_memory/vocab/shared_proposer.py`
- Implement **`propose_shared_vocab_promotions(conn, *, min_owners=3, min_sim=0.72, runner=None)`**:
  - Clusters anonymised multi-owner query terms and recurring per-owner `learned_terms` crossing `>= min_owners` distinct owners (aggregate counts only — zero cross-owner data leaks).
  - Filters every candidate strictly through `privacy/sensitive.py` + `eligible_subject` + `VocabTree.blocks_proposals` fail-closed.
  - Runs logical verification via `core/extract.py` LLM runner (receiving **only** anonymized term cluster, distinct owner count, and candidate parent branches from `vocab/tree.json` — zero raw user data) to judge genuine generalizable Dubai/everyday terms, assign `{canonical_term, aliases_en_ar, parent_path, rationale}`, or reject noise.
  - Inserts approved candidates into `shared_vocab_proposals` with `status = 'pending'`; **never** auto-edits `vocab/tree.json`.

### 4. Admin-Only Router (`api/vocab_admin.py` + 2-Line Mount in `api/vault.py`)
- Path: `apps/memory/src/temporal_memory/api/vocab_admin.py`
- Put the endpoint implementations in `api/vocab_admin.py` and mount with a **minimal 2-line `include_router`** in `apps/memory/src/temporal_memory/api/vault.py` (to avoid merge conflicts with E13a in `vault.py`):
  - `POST /v1/admin/vocab/propose` (runs `propose_shared_vocab_promotions`)
  - `GET /v1/admin/vocab/proposals` (lists pending/approved/rejected proposals + cluster metadata)
  - `POST /v1/admin/vocab/proposals/{id}/decide` (`approve` / `reject`; approved terms load cleanly into `VocabTree` overlay alongside `tree.json`)
- **Admin-token gated ONLY:** owner/worker/cross-owner tokens MUST receive `403`.

### 5. E10 Non-Blocking Review Follow-Ups (`E10.review.md`)
1. `apps/memory/src/temporal_memory/core/retrieval.py`: Remove ONLY the shadowed local `_arabic_variants` duplicate and use the imported helper from `vocab/loader.py` (do NOT alter E13a weight/recall logic).
2. `apps/memory/acceptance/common.py`: Include `had_fact` in `load_graph_snapshot` when restoring `learned_term_sources`.
3. `apps/memory/upgrade/reports/E10.md`: Correct the alias/lexicon count note to `461` aliases / `35` lexicon words (verified from `vocab/tree.json`).

### 6. Tests, Gates & Report
- New `apps/memory/tests/test_shared_vocab_agent.py`:
  - Happy path: `>= 3` distinct owners querying/learning semantically similar EN/AR/Arabizi terms cluster via `find_similar_queries_and_terms`, pass logical agent (`mocked` + structured runner check), and land in `shared_vocab_proposals` with `distinct_owners >= 3` and zero owner IDs leaked.
  - Failure paths: `< min_owners` rejected, sensitive/Rule-9 term blocked fail-closed, non-admin/owner/worker caller gets `403` on `/v1/admin/vocab/proposals*`.
- Run full `apps/memory` Postgres suite in `contest-memory` venv against `:5442`:
  - `$env:TM_TEST_DATABASE_URL="postgresql://tm:tm@localhost:5442/tm"`
  - `G:\Haitham\VsCode\contest-memory\apps\memory\.venv\Scripts\python.exe -m pytest -q` (all pass, 0 failed).
- Run `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web` (MUST exit `0`).
- Write `apps/memory/upgrade/reports/E13b.md` + append 1 row to `apps/memory/upgrade/reports/STATUS.md`.
- Never stage the 3 founder untracked files or build artifacts.
- Commit, `git push origin e13b/shared-vocab-agent`, open PR into `main`, and **STOP** (do NOT merge; note that E13b merges after E13a and will rebase cleanly onto `main` post-E13a).

---

## File Ownership Boundaries

- **ALLOWED:**
  - `apps/memory/src/temporal_memory/db/migrations/0009_shared_vocab_proposals.sql`
  - `apps/memory/src/temporal_memory/vocab/similarity.py`
  - `apps/memory/src/temporal_memory/vocab/shared_proposer.py`
  - `apps/memory/src/temporal_memory/vocab/loader.py` (overlay load for approved `shared_vocab_proposals`, minimal)
  - `apps/memory/src/temporal_memory/api/vocab_admin.py`
  - `apps/memory/src/temporal_memory/api/vault.py` (minimal 2-line `include_router` mount ONLY)
  - `apps/memory/src/temporal_memory/core/retrieval.py` (`_arabic_variants` dedup ONLY)
  - `apps/memory/acceptance/common.py` (`had_fact` restore ONLY)
  - `apps/memory/upgrade/reports/E10.md` (alias/lexicon count fix ONLY)
  - `apps/memory/tests/test_shared_vocab_agent.py`
  - `apps/memory/upgrade/reports/E13b.md` + `STATUS.md` (append row only)
- **FORBIDDEN (Do NOT touch):**
  - `apps/memory/src/temporal_memory/db/migrations/0008_*` (E13a ONLY)
  - `apps/memory/src/temporal_memory/privacy/forget.py`, `privacy/controls.py` (E13a ONLY)
  - `apps/community/**`, `apps/api/app/community/**` (E14 ONLY)
  - `apps/web/**` (frozen)
