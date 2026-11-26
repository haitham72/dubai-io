# Community 10-user demo — cohort, acceptance, runbook

**Branch:** `dev/community`  
**Namespace:** `community-demo-10-v1`  
**Seed:** `20261126` · **Provenance:** `demo_fixture` (UI: Demo data pill)  
**Plan:** `docs/submissions/community/02A_COMMUNITY_10_USER_AGENT_ORCHESTRATION.md`  
**Store:** local ActionStore (`actions.sqlite3` / `DATABASE_URL`) — no Supabase

## Cohort

| Actor | Handle | Groups |
|---|---|---|
| sim-01 Nour | nour_fe_demo | dubai-developers, learning-circle |
| sim-02 Omar | omar_design_demo | design-creators, dubai-developers |
| sim-03 Leila | leila_walks_demo | dubai-weekends, design-creators |
| sim-04 Adam | adam_new_demo | new-in-dubai, dubai-weekends |
| sim-05 Mariam | mariam_study_demo | learning-circle, dubai-developers |
| sim-06 Rami | rami_games_demo | dubai-gamers, design-creators |
| sim-07 Sara | sara_biz_demo | small-business-uae, dubai-developers |
| sim-08 Youssef | youssef_photo_demo | design-creators, dubai-weekends |
| sim-09 Dana | dana_vol_demo | new-in-dubai, dubai-weekends |
| sim-10 Kareem | kareem_pm_demo | small-business-uae, learning-circle |

**7 groups:** Dubai Developers, Design & Creators, Dubai Weekends, New in Dubai, Learning Circle, Dubai Gamers, Small Business UAE (handles prefixed `demo-`).

Owners / entity IDs: `{namespace}:sim-NN`, `{namespace}:grp-…`, `{namespace}:post-NNN`.

## Target counts (§2)

| Entity | Target | Notes |
|---|---|---|
| Users | 10 | exact |
| Groups | 7 | exact |
| Posts | ≥40 | ≥3 / user; ≥10 image media |
| Comments | ≥90 | ≥15 nested reply chains |
| Reactions | ≥120 | |
| Follows | ≥20 | no self-follows |
| Memberships | ≥20 | ≥2 groups / user |
| Notifications | ≥20 | from replies + follows |
| Bookmarks | ≥10 | |
| Moderation | 2 | FP candidate + spam; flag-only, no auto-ban |

Excluded from two-tower training (`scripts/train_community_two_tower.py`), usage-profile (`record_interaction_event` skip), and `temporal_memory` (`community.memory.remember` skip).

## Gate results (this PR)

| Gate | Result |
|---|---|
| §7 `tests/test_community_10_users_demo.py` | 10 passed |
| `apps/api` full pytest | 704 passed, 16 skipped |
| `apps/community` npm test | 58 passed |
| `apps/community` `tsc --noEmit` | exit 0 |
| `apps/community` npm run build | exit 0 |
| `apps/web` frozen (`mobile-pwa-baseline-2026-10-23`) | clean |

## Acceptance (§7)

Covered by `apps/api/tests/test_community_10_users_demo.py`:

- Exact 10 users / 7 groups + §2 count gates (`verify_counts`)
- Provenance `demo_fixture`, stable namespaced IDs, timestamps
- FK integrity for comments / reactions / bookmarks / notifications
- Persist across ActionStore reopen
- Cross-owner bookmarks isolation
- Demo skipped for usage profile + memory bridge
- Public group feed returns demo posts with provenance
- `--dry-run` writes nothing; re-apply idempotent; `--reset-demo` namespace-scoped only
- Moderation fixtures flagged, never banned
- CLI refuses `--apply` / `--reset-demo` without `DEMO_SEED_ENABLED=true`

## Runbook

```bash
# Dry-run (default — no writes)
python scripts/seed_community_10_users.py
python scripts/seed_community_10_users.py --dry-run --verify

# Apply (local / demo env only)
DEMO_SEED_ENABLED=true python scripts/seed_community_10_users.py --apply --verify

# Reset namespace only (organic rows kept)
DEMO_SEED_ENABLED=true python scripts/seed_community_10_users.py --reset-demo --verify
```

Optional: set `DATABASE_URL` for Postgres; otherwise seeds `apps/api/data/actions.sqlite3`.

View: join or open a demo group (e.g. `GET /api/community/groups/community-demo-10-v1:grp-dubai-developers/posts`) — posts show `provenance=demo_fixture`. Community UI renders the Demo data pill for that provenance.

Implementation: `apps/api/app/community/demo_10_users.py` · CLI: `scripts/seed_community_10_users.py`.
