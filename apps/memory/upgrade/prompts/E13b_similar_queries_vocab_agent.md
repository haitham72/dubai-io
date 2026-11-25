# E13b: Similar-Query Clustering & Logical Agent for Shared Vocabulary Proposals (D21)

Read `apps/memory/upgrade/prompts/E0_real_data_round.md`, `apps/memory/CLAUDE.md`, `apps/memory/upgrade/reports/E10.review.md`, and `docs/submissions/shared/founder-decisions.md` **D17, D19, D21**. Branch **`e13b/shared-vocab-agent`** from **`main`** (coordinate with or rebase after `e13a` only on migration numbers — use next free migration number). Do NOT touch `apps/web` or `privacy/forget.py`.

## Goal (Founder Decision D21 + E10 Review Cleanups)

1. **Similar-query retrieval & clustering function (`apps/memory/src/temporal_memory/vocab/similarity.py`):**
   - Record privacy-safe anonymised unknown/low-hit search & context query tokens (`query_logs` or `vocab_query_signals` table: hashed owner key, folded query/term, 1024-d `BAAI/bge-m3` embedding vector, hit count, resolved branch if any, timestamps — **never** store raw PII or full user sentences containing phone/email/names; apply `privacy/sensitive.py` pre-write screen before logging).
   - Implement **`find_similar_queries_and_terms(conn, query_text, *, top_k=15, min_sim=0.68)`** combining:
     - `pgvector` cosine similarity over `bge-m3` query embeddings + existing curated `vocab/tree.json` node/alias embeddings; and
     - folded/Arabic-normalized lexical overlap (`fold_text`, `_arabic_variants`).
     - Returns ranked similar queries/terms with distinct-owner count (aggregate only, zero owner IDs exposed), nearest curated `parent_path`, and similarity score.

2. **Logical agent to propose shared vocabulary additions (`apps/memory/src/temporal_memory/vocab/shared_proposer.py`):**
   - Implement **`propose_shared_vocab_promotions(conn, *, min_owners=3, min_sim=0.72, runner=None)`**:
     - Clusters anonymised multi-owner query terms and recurring per-owner `learned_terms` crossing `>= min_owners` distinct owners (aggregate counts only — Rule 9 & cross-user privacy preserved).
     - Filters every candidate strictly through `privacy/sensitive.py` + `eligible_subject` + `VocabTree.blocks_proposals` so sensitive/personal/entity-name terms are rejected fail-closed.
     - Calls the configured LLM runner via `core/extract.py` (**logical verification step**: given only the anonymized term cluster, distinct owner count, and candidate parent branches from `vocab/tree.json` — zero raw user data!) to judge whether the cluster is a genuine generalizable Dubai/everyday term, assign `{canonical_term, aliases_en_ar, parent_path, rationale}`, or reject noise.
     - Writes approved candidates to **`shared_vocab_proposals`** table (`status = 'pending'`), never auto-editing `vocab/tree.json`.
   - Admin endpoints (`apps/memory/src/temporal_memory/api/vault.py`, admin-token gated only — `403` for owner/worker tokens):
     - `POST /v1/admin/vocab/propose` (runs `propose_shared_vocab_promotions`)
     - `GET /v1/admin/vocab/proposals` (lists pending/approved/rejected proposals + similar query cluster metadata)
     - `POST /v1/admin/vocab/proposals/{id}/decide` (`approve` / `reject`; approved terms are loaded cleanly into `VocabTree` overlay alongside `tree.json`).

3. **E10 Non-Blocking Review Follow-ups (`E10.review.md`):**
   - Remove the shadowed `_arabic_variants` duplicate in `core/retrieval.py` (use the imported helper from `vocab/loader.py`).
   - Include `had_fact` in `acceptance/common.py` `load_graph_snapshot`.
   - Correct the alias/lexicon count note in `E10.md` (`461` aliases / `35` lexicon words verified from `vocab/tree.json`).

## Tests & Gates

- New `apps/memory/tests/test_shared_vocab_agent.py`:
  - Happy path: `>= 3` distinct owners querying/learning semantically similar EN/AR/Arabizi terms cluster via `find_similar_queries_and_terms`, pass logical agent (`mocked` + structured runner check), and land in `shared_vocab_proposals` with `distinct_owners >= 3` and zero owner IDs leaked.
  - Failure paths: `< min_owners` rejected, sensitive/Rule-9 term blocked fail-closed, cross-owner/non-admin caller gets `403` on `/v1/admin/vocab/proposals*`.
- Full `apps/memory` suite in `contest-memory\apps\memory\.venv` against Postgres `:5442`: all pass, 0 failed.
- `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web` exits `0`.
- Report → `apps/memory/upgrade/reports/E13b.md` + line in `STATUS.md`.
