# E14b: Community Two-Tower Recommender & Context-Aware Usage Profile (Devin, after E14a)

Read `apps/memory/upgrade/prompts/E0_real_data_round.md`, `docs/submissions/community/FACEBOOK_REDDIT_RECOMMENDER_PLAN.md` (§2–§3), and `docs/submissions/shared/founder-decisions.md` (D11, D19, D22). Branch **`e14b/community-two-tower`** from **`main`** after `E14a` merges. Open one PR into `main`. Do NOT touch `apps/web`.

## Deliverables

1. **Real 4-Stage Two-Tower Recommender (`apps/api/app/community/recommender.py` + `app/community/agents.py`):**
   - Replace rule-only `GET /api/community/discovery` scoring with a real 4-stage pipeline (`$0` API cost, `< 150 ms` p95 on 5k posts):
     - **Stage 1 (Dual-Tower Candidates):**
       - `cm_post_embeddings`: precompute normalized `128-d` item tower vector from local `BAAI/bge-m3` (`1024-d` via `temporal_memory.core.embed` when loaded or fast warm-start TF/hash projection fallback in SQLite/offline tests) + topic path (`vocab/tree.json`) + flair + coarse area. On Postgres use `pgvector` HNSW index; on SQLite use exact cosine matrix scan.
       - User+Context Tower: blend long-term consented `temporal_note` interests + `cm_usage_profile` affinities + 30-min half-life decayed `cm_interaction_events` session vector + normalized context vector ($e_{\text{user},t}$).
       - Merge top ANN candidates + follow-graph recent posts + Dubai area/time-bucket trending fallback (cold-start safe).
     - **Stage 2 (Hard Policy Filters):** private group fence, `cm_user_blocks`, `cm_user_mutes`, soft-deleted, D11 `is_minor_protected`, Rule-9 sensitive guard, and **Driving mode filter** (when `user_state == 'driving'`, suppress long multi-paragraph reading posts & tag driving-safe mode cleanly).
     - **Stage 3 (Multi-Task Scorer + ContextFit):** combine calibrated engagement/save/reply/downvote weights with `ContextFit` (`area_coarse`, `device_class`, `time_bucket`, `user_state`).
     - **Stage 4 (Diversity + Exploration + `Why this?`):** author/group cap, 1-in-5 exploration slot, deterministic `Why this?` reason chip naming only real contributing non-sensitive features (`Matched DIFC · Lunch`, `Because you upvoted #padel`, `Trending in Dubai Marina`, or `Cold start: public post`).

2. **Profile Usage Understanding + Context Envelope (`apps/api/app/community/context_profile.py`):**
   - Ephemeral context endpoint `POST /api/community/context/heartbeat` + optional request context payload/headers stored **only in Redis (10-min TTL)** — never raw lat/lng in SQL, zero background geofencing (Rule 8).
     - Fields: `area_coarse` (~1.5 km Dubai neighborhood grid, foreground opt-in or manual selector), `device_class` (`mobile_ios|mobile_android|mobile_web|desktop|web`), `time_bucket` (`Asia/Dubai` server-derived + `is_weekend`), `user_state` (`stationary|sitting|standing|walking|running|driving|unknown`, `confidence`, `source`).
     - **`user_state` NEVER writes a health/fitness fact to `temporal_memory` (Rule 9).**
   - Append-only `cm_interaction_events` (`upvote|downvote|reply|bookmark|repost|dwell|hide|lower`, deduped) + `cm_usage_profile` projector (`(owner, topic_key, time_bucket, area_coarse, format_bucket)`):
     - **Two-visit qualification** ($\ge 2$ distinct visits $\ge 6$h apart before long-term feed impact).
     - **D19 weight formula:** age decay to `0.05` floor, explicit user **Lower** sets weight to `w_min = 0.01` (`< 0.10` active surface cutoff while staying visible + restorable under **Profile → How Community adapts to you**).
     - Endpoints: `GET /api/community/profile/usage`, `POST /api/community/profile/usage/lower`, `POST /api/community/profile/usage/restore`, pause switch `context_aware_enabled`.

3. **Foreground Context Collector (`apps/community/mobile/` + `apps/community/src/`):**
   - `apps/community/mobile/`: opt-in foreground-only sensor hook using `expo-sensors` (`Accelerometer` + `Pedometer` cadence + foreground `expo-location` snapped server-side to `area_coarse`) classifying `walking | running | driving | sitting | standing | stationary | unknown` (honest `stationary`/`unknown` fallback when sensors unavailable/denied).
   - `apps/community/src/`: subtle header/profile context & "How Community adapts to you" panel showing active context pill (editable/pausable), usage buckets with **Lower** / **Restore**, and driving-safe banner when `user_state === 'driving'`.

4. **Offline Two-Tower Trainer (`scripts/train_community_two_tower.py`):**
   - Trains PyTorch dual-encoder (`InfoNCE` / BPR over consented `cm_interaction_events` + D19 feedback) + calibrated multi-task weights into local versioned checkpoint loaded automatically when present, printing `Recall@20` / `NDCG@10` evaluation metrics on held-out synthetic split.

## Tests & Gates

- `apps/api`: `test_community_two_tower.py` + `test_community_context_profile.py` covering:
  - Item + User+Context towers match synthetic user interests (`NDCG@10` beats recency-only baseline), `< 150 ms` latency check at 2k–5k synthetic posts.
  - Hard filters: blocks/mutes, private group fence, under-18 fail-closed zero personalisation, driving mode suppresses long reading posts.
  - Context privacy: raw lat/lng discarded immediately (only `area_coarse`), Redis TTL set (`<= 600s`), `user_state` produces zero Rule-9 health facts.
  - Usage profile D19: two-visit qualification enforced, explicit **Lower** drops weight to `0.01` (stops influencing feed immediately, stays listed + restorable).
- `apps/community`, `apps/community/mobile`, `apps/community/desktop`: unit + tsc + build green; offline trainer unit test on tiny synthetic fixture passes.
- `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web` exits `0`.
- Report → `apps/memory/upgrade/reports/E14b.md` + line in `STATUS.md`.
