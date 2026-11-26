# Dubai Community — Facebook/Reddit Replica, Two-Tower Recommender & Context-Aware Usage Profile Plan

**Date:** 25 Nov 2026 · **Decisions:** D3, D11, D14, D19, D21, D22  
**Owned product:** Entry 2 — Best Societal AI Agent (`apps/community/`, `apps/api/app/community/`, `apps/community/mobile/`, `apps/community/desktop/`)  
**Hard boundaries unchanged:**
- **No P2P messaging in Community (D3):** Inbox stays notifications-only; any "Message" CTA hands off to Messenger.
- **Adults-only (D11):** Self-declared `adult_18_plus` / `ADULT_BANDS` enforced server-side.
- **UI rules (D14):** Light mode, zero shadows, plain AI text / tinted user box / white rounded action boxes, original branding (never Meta/Facebook/Reddit marks).
- **Rule 8 & Rule 9:** Zero background geofencing; zero inferred health/fitness/family/faith/nationality/ethnicity labels from sensors, behavior, or posts.
- **Never delete normal history (D19):** Usage-profile signals decay to weight floor $w_{\min} = 0.01$ rather than deleting; only account-level "Delete my data" purges external queries and Redis immediately.

---

## 0. Current Baseline Audit (Verified at `main` `74cbb1b`)

- **Already built (`cm_*` + E12):** Profiles (`cm_profiles`), follows (`cm_follows`), public/private groups + moderation log (`cm_groups`, `cm_group_members`, `cm_group_moderation_log`), posts + edit revisions + soft delete (`cm_posts`, `cm_post_revisions`), nested comments (`cm_comments`), reactions/likes (`cm_reactions`), bookmarks (`cm_bookmarks`), notifications (`cm_notifications`), search (`/api/community/search`), and rule-based discovery (`apps/api/app/community/agents.py` `GET /api/community/discovery`).
- **Prototype reality check (`scripts/run_two_tower_recommender.py`):** That script executes 10 hard-coded Tavily web searches for Entry 1 — it is **not** a two-tower neural/embedding recommender. Community `GET /api/community/discovery` today scores candidates with additive tag/follow rules over SQLite/Postgres without learned embeddings, two-tower retrieval, or live context coupling.

---

## 1. Part 1 — Facebook + Reddit Replica Social Core (`E14a`)

| Feature | Reddit / Facebook Mechanic | Schema & API Additions (`cm_*`) | UI Surfaces (`apps/community/src`) |
|---|---|---|---|
| **Voting & Ranking** | Reddit upvote / downvote + server-computed Hot, Top, New, Rising, Controversial | `cm_votes (owner, target_type, target_id, value ∈ {-1,+1}, created_at)`; extend `GET /api/community/feed?sort=hot\|top\|new\|rising\|controversial`; Hot score $\text{sign}(s)\log_{10}(\max(1,|s|)) + \frac{t - t_0}{45000}$ | Post cards + comment rows render upvote/downvote counters & sort pills across all lanes (`For you`, `Following`, `Communities`) |
| **Hashtags & Flairs** | Topic discovery (`#dubaimarina`, `#hiring`, `#padel`) + post flairs (`Question`, `Recommendation`, `Event`, `Warning`, `Housing`) | `cm_post_tags (post_id, tag, created_at)` + optional `flair TEXT` on `cm_posts`; `GET /api/community/tags/trending`, `/api/community/feed?tag=...` | Clickable `#tag` pills on cards, `/t/[tag]` tag feed page, tag autocomplete & flair picker in `/create` |
| **Reposts & Quote-Posts** | Facebook/Threads repost with optional commentary | Optional `repost_of_id TEXT` on `cm_posts` (blocked if original is deleted or in a private group); `POST /api/community/posts/{id}/repost` | Repost / Quote action on `RealPostCard`, quoted original preview box, attribution kept intact |
| **Thread Collapse & Deep Links** | Collapsible Reddit comment trees | Recursive tree hydration (`GET /posts/{id}/comments`) | Inline `[ - ]` collapse/expand per branch + "Continue thread" |
| **Block & Mute** | Silence abusive authors/topics server-side | `cm_user_blocks (owner, blocked_owner)`, `cm_user_mutes (owner, kind='owner'\|'group'\|'tag', target)`; enforced on feed, search, discovery, inbox | Overflow `...` menu on posts/profiles ("Mute user/community/tag", "Block user") + Settings list with Unblock/Unmute |
| **Reports & Moderation Queue** | Structured flagging with human-in-the-loop resolution | `cm_reports (id, reporter, target_type, target_id, reason, detail, priority, status, resolved_by, created_at)`; `POST /api/community/reports`, `GET /api/community/moderation/queue`, `.../resolve` | Report modal on cards & comments; Moderator tab on group pages; priority bump on safety issues |
| **Split Memory Consent** | Fix `MORNING.md` (removed 26 Nov; see git history) §E #8 | Split `remember_saved_discussions` vs `remember_public_posts` on `PUT /api/community/memory/consent` | Two independent switches in Community Profile → Memory |

---

## 2. Part 2 — Real Two-Tower Recommender (`E14b`)

Runs at **$0 API cost** using local `BAAI/bge-m3` (`1024-d`, already cached in `apps/memory`) projected to `128-d` normalized tower embeddings in Postgres 17 + `pgvector` HNSW (with deterministic linear warm-start on Day 1 so it works immediately before large organic interaction logs accumulate). Latency target: **< 150 ms p95** for candidate retrieval + ranking.

### Architecture: 4-Stage Retrieval & Ranking Funnel

1. **Stage 1 — Dual-Tower Candidate Generation (`top 200`):**
   - **Item Tower (`cm_post_embeddings`):**
     $$e_{\text{item}} = \text{norm}\!\left(W_{\text{text}} \cdot v_{\text{bge-m3}}(\text{post}+\text{tags}+\text{group}) + W_{\text{meta}} \cdot \phi(\text{flair}, \text{area}, \text{topic\_path}, \text{age}, \text{engagement\_velocity})\right) \in \mathbb{R}^{128}$$
     Topic path maps onto E10 `vocab/tree.json` (`183` nodes, `7` clusters). Indexed in `pgvector` HNSW (SQLite fallback in local unit tests computes exact cosine dot product over recent `N` posts).
   - **User + Context Tower (computed per request / cached per context bucket):**
     $$e_{\text{user},t} = \text{norm}\!\left(\alpha_{\text{long}} \cdot u_{\text{long}} + \alpha_{\text{sess}} \cdot u_{\text{session}, 30\text{m}} + \alpha_{\text{ctx}} \cdot c_{\text{context}}\right) \in \mathbb{R}^{128}$$
     - $u_{\text{long}}$: consented `temporal_note` interest topics (non-sensitive only) + `cm_usage_profile` affinities.
     - $u_{\text{session}, 30\text{m}}$: 30-minute half-life decayed weighted mean of recent organic interactions in `cm_interaction_events`.
     - $c_{\text{context}}$: normalized context embedding encoding `area_coarse`, `device_class`, `time_bucket`, and `user_state`.
   - **Multi-Channel Merge:** Top 120 ANN matches from $\langle e_{\text{user},t}, e_{\text{item}}\rangle$ + Top 40 Follow-graph recent posts + Top 40 Dubai area/time-bucket trending posts (ensures strong cold-start when a user has 0 interactions).

2. **Stage 2 — Hard Policy & Safety Filters (Fail-Closed):**
   - Private group fence (`is_member`), `cm_user_blocks`, `cm_user_mutes`, soft-deleted posts, D11 `is_minor_protected`, Rule-9 sensitive categories (`privacy/sensitive.py` pre-write check so sensitive topics never silently personalize), and expired event filter (`EVT-01`).
   - **Driving safety filter (`user_state == 'driving'`):** deprioritize or collapse long multi-paragraph text/form posts and surface short local updates / voice-friendly summaries with explicit safety notice.

3. **Stage 3 — Calibrated Multi-Task Ranker:**
   $$S(u, i \mid x_t) = w_1 P(\text{upvote/like}) + w_2 P(\text{reply}) + w_3 P(\text{save/repost}) + w_4 P(\text{dwell}>15\text{s}) - w_5 P(\text{hide/downvote}) + \beta_{\text{fit}} \cdot \text{ContextFit}(i, x_t)$$
   `ContextFit` boosts:
   - Local `area_coarse` matches during `commute` / `evening` / `walking` / `weekend`.
   - Quick bite-sized updates (`text_len <= 280` or local alert) when `user_state ∈ {walking, running, driving}` or `device_class ∈ {mobile_ios, mobile_android}`.
   - Deep discussions (`replies >= 3` or longer guides) when `user_state ∈ {sitting, stationary}` and `time_bucket ∈ {evening, late_night, weekend}` or `desktop`.

4. **Stage 4 — Re-Ranking & Transparent `Why this?`:**
   - Author & community diversity cap (max 2 posts per author / 3 per group in top 20).
   - **1-in-5 exploration slot:** preserves 20% diverse Dubai public-interest items so feeds never form a filter bubble.
   - **Deterministic `Why this?` chip:** generated strictly from top non-zero feature contributions (`Matched DIFC · Lunch`, `Because you upvoted #padel (weight 0.82)`, `Trending in Dubai Marina right now`, or `Cold start: popular public post`) — never LLM hallucination.

5. **Offline Trainer (`scripts/train_community_two_tower.py`):**
   - Consumes consented, non-deleted `cm_interaction_events` joined with D19 lowered-weight feedback (`save=1.5`, `reply=1.3`, `upvote=1.0`, `dwell_15s=0.6`, `downvote=-0.8`, `hide=-1.2`, `lower=-1.5`).
   - Optimizes PyTorch dual-encoder InfoNCE + in-batch negatives loss ($1024 \to 128$-d linear/MLP projections) + ridge/logistic multi-task weights saved cleanly as versioned local artifact (`cm_recommender_weights.json` / `.pt`), evaluated with `Recall@20`, `NDCG@10`, and calibration ECE before activation.

---

## 3. Part 3 — Context-Aware Profile Usage Understanding (`location / mobile / time of day / userState`)

### Ephemeral Context Envelope (`cm_context_envelope`)

Sent optionally on feed/discovery requests or `POST /api/community/context/heartbeat` (stored **only** in Redis with a **10-minute TTL**, never in permanent SQL history per Rule 8/9):

| Field | Allowed Values / Precision | Collection & Rules |
|---|---|---|
| `area_coarse` | Snapped ~1.5 km Dubai district (`Dubai Marina`, `JLT`, `DIFC`, `Downtown Dubai`, `Jumeirah`, `Business Bay`, `Al Quoz`, `Deira`, `Bur Dubai`, etc.) | **Foreground-only opt-in** in Expo Go / browser (`expo-location` Accuracy.Balanced → snapped server-side to district centroid, raw lat/lng discarded immediately) or explicit manual neighborhood picker. **Zero background geofencing (Rule 8).** |
| `device_class` | `mobile_ios \| mobile_android \| mobile_web \| desktop \| web` | Derived from client platform / Electron / viewport class. |
| `time_bucket` | `early_morning (05-08) \| commute_am (08-10) \| workday (10-12,14-17) \| lunch (12-14) \| commute_pm (17-20) \| evening (20-23) \| late_night (23-05)` + `is_weekend` (Sat/Sun) | Computed server-side in `Asia/Dubai` (`UTC+4`). |
| `user_state` | `stationary \| sitting \| standing \| walking \| running \| driving \| unknown` + `confidence ∈ [0,1]` + `source ∈ {expo_sensors, user_override, unavailable}` | **Foreground-only opt-in** in `apps/community/mobile/` using `expo-sensors` (`Accelerometer` variance + `Pedometer` cadence + foreground speed bucket). Web/desktop send `stationary` (on desktop) or `unknown`, or user-selectable chip (`Commuting`, `At desk`, `On the move`). **`user_state` NEVER enters `temporal_memory` as a health or fitness trait (Rule 9).** |

> **Honesty on `sitting` vs `standing`:** Phone accelerometers alone cannot always distinguish stationary `sitting` vs `standing` cleanly without wrist wearables; the mobile classifier reports `stationary` unless pitch/step-transition cadence gives `confidence >= 0.70` for `sitting` or `standing`, falling back honestly to `stationary` / `unknown`.

### Profile Usage Understanding Projector (`cm_interaction_events` → `cm_usage_profile`)

Tracks *when, where, and on which device/state* a consented adult user prefers each E10 topic — **never predicting sensitive traits (Rule 9)** and following **D19 Lower weights**:

1. **Two-visit qualification:** Behavioral usage buckets require $\ge 2$ distinct interactions across $\ge 2$ sessions separated by $\ge 6$ hours before shaping `For you` rankings.
2. **D19 Weight Formula (`w_min = 0.01`, `tau_surface = 0.10`):**
   - Positive engagement (`upvote`, `save`, `reply`, `dwell>15s`) refreshes `last_seen_at` and adds bounded evidence (`log(1 + count)`).
   - Unrefreshed usage affinity decays by age after 30 days with 30-day half-life down to natural floor `0.05`.
   - User-tapped **Lower / Less like this** drops that usage-bucket weight immediately to $w_{\min} = 0.01$ (`< 0.10`, stopping unsolicited feed influence immediately while staying inspectable under **Profile → How Community adapts to you** with **Lower** / **Restore** controls).
   - **Explicit recall & reinforcement (D19b):** If the user explicitly searches for, selects, or triggers a lowered topic/memory, it remains **100% callable** and that explicit call adds back to its weight ($w_{\text{new}} = \min(1.0, \max(0.35, w_{\text{eff}} + 0.25))$, clearing `lowered_at`).
   - **Account-level Delete my data** purges Redis context keys, `cm_usage_profile`, and `cm_interaction_events` from external queries immediately.

---

## 4. Phased Delivery

1. **`E14a` (Devin):** Facebook/Reddit social parity (`cm_votes`, Hot/Rising/Top, `#hashtags`, reposts/quote-posts, block/mute, reports/moderation queue, split consent switches) + E11b/E12 non-blocking cleanups.
2. **`E14b` (Devin, after `E14a` merges):** Real 4-stage Two-Tower Recommender (`pgvector` HNSW + `bge-m3` + E10 topics + `<150 ms` gate) + `cm_usage_profile` projector + opt-in foreground context envelope (`area_coarse`, `device_class`, `time_bucket`, `user_state`) + Expo Go sensor classifier in `apps/community/mobile/` + `scripts/train_community_two_tower.py`.
3. **`E14c` (Offline validation & 5-tester live run):** Re-train offline two-tower checkpoint on synthetic + consenting-adult logs and verify Recall@20 / NDCG@10 / latency / isolation.
