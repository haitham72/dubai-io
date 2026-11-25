# E13a: Never Forget (Lower Weights to Formula Minimum) + Account "Delete My Data" (Codex)

Read `apps/memory/upgrade/prompts/E0_real_data_round.md`, `CLAUDE.md` Rule 9, and `docs/submissions/shared/founder-decisions.md` **D18–D19** first. Branch **`e13a/lower-and-delete`** from **`main` (`5a5f6bd` or latest)**. Do NOT touch `apps/web`, `apps/community/**`, `vocab/proposals.py` (shared-vocab agent territory), or `core/retrieval.py` semantic clustering (E13b territory). Keep changes focused and clean (~half volume).

## Goal (Founder Decision D19)

1. **Never forget on items/sources — lower weights to the formula floor instead:**
   - Canonical weight formula across `temporal_memory` (`core/retrieval.py`, `vocab/proposals.py`, `core/graph_store.py`, `api/vault.py`):
     $$w_{\text{eff}}(t, k, c) = \max\Big(w_{\min},\; w_{\text{base}} \cdot c \cdot 2^{-\frac{\max(0,\, t - 30)}{30}} \cdot 0.5^{k}\Big)$$
     - `WEIGHT_FLOOR = 0.01` ($w_{\min}$), natural age-decay floor `AGE_DECAY_FLOOR = 0.05`, and active surface visibility threshold `SURFACE_WEIGHT_THRESHOLD = 0.10` ($\tau_{\text{surface}}$).
     - Confirmed `user_supplied` / `provider_confirmed` items do not time-decay ($t$ decay factor $= 1.0$) unless explicitly lowered or rejected.
     - Explicit user **"Lower"** (for a fact, inferred subject, or source) sets the item's weight directly to `0.01` (`lowered_at` / weight override `0.01`) **without deleting text, rows, evidence, or records**. Items below `0.10` immediately stop appearing in Chat context packs, `/search` default results, Today cards, and recommendations, while remaining visible in Memory Vault under a filterable `"Lowered"` state and restorable via **"Restore"** (`lower = false` / `restore`).
   - Replace/alias existing item-level & source-level UI/API `"Forget"` controls across `apps/memory`, `apps/api/app/memory_bridge/`, `apps/api/app/ingest/`, `apps/mobile`, `apps/desktop`, and `apps/messenger` memory settings so normal controls trigger **Lower** (not tombstone/erase). Keep backward-compatible internal migration safety on existing tests by updating tests to assert D19 non-deletion + `<= 0.01` exclusion behavior (and adding explicit Lower/Restore tests).
2. **Account-level `"Delete my data"` (`POST /v1/owners/{owner}/delete-my-data` + `/api/identity/delete-my-data`):**
   - Immediately and synchronously inside one request:
     1. Purges **every Redis key** scoped to this owner (`redis.scan_iter(f"*{owner}*")` / explicit key prefixes on `TM_REDIS_URL`, failing closed cleanly only if Redis is unconfigured while logging/returning `redis_purged`).
     2. Clears **every in-process cache** for this owner (`_LEARNED_CACHE`, context cache, story cache, embed pending/backfill state).
     3. Bumps owner generation / `facts_version`, revokes all `cs_app_sessions`, `cs_memory_tokens`, and owner device tokens, and marks the owner `deleted_from_external = true` (`deleted_at = now()`) so **zero external queries, `/search`, `/context`, `/vault/*`, MCP tools, Today, or Chat can return any row for that owner immediately** (HTTP 403/404 or empty excluded state).
     4. Copies an **isolated, externally unreachable, de-identified training backup** into an internal backup table (`training_backups` — owner UUID replaced by one-way salted hash / random surrogate ID, email/name/phone/tokens/credentials scrubbed, **excluding any rows with Google Workspace / YouTube sources** `gmail`, `calendar`, `youtube`, `takeout_youtube` to honor Google API Limited Use policy). Zero public or bridge API endpoint may ever read `training_backups`.
3. **FAQs disclosure:** Add a concise user-facing Privacy & Memory FAQ entry (`docs/PRIVACY_AND_MEMORY_FAQ.md` + link/text in `apps/mobile` Settings / Memory screen) stating plainly that lowering dims weights without deleting, and "Delete my data" removes all data from Redis and external queries immediately while keeping a de-identified training backup (excluding Google Workspace/YouTube data).

## Tests & Gates (Run All)

- `apps/memory` (`G:\Haitham\VsCode\contest-memory\apps\memory\.venv\Scripts\python.exe -m pytest -q` against Postgres `:5442`):
  - Weight formula unit test (age decay, `k` step halving, `0.05` age floor, `0.01` lowered floor, `0.10` visibility cutoff, `user_supplied` no-decay, Restore).
  - Item/source Lower keeps DB row intact (`erased_at IS NULL`, text intact), drops weight to `0.01`, hides from `/context`, `/search`, MCP, Today, and stays visible in Vault `"Lowered"`.
  - Account `"Delete my data"` purges owner keys from Redis + in-process caches + revokes tokens + excludes all external queries immediately (`0` results) while writing one de-identified `training_backups` row (and omitting Gmail/YouTube rows from the backup).
- `apps/api`: `pytest -q tests` (`DATABASE_URL` unset).
- `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web` must exit `0`.
- Report → `apps/memory/upgrade/reports/E13a.md` + line in `apps/memory/upgrade/reports/STATUS.md`. Do NOT merge into `main`.
