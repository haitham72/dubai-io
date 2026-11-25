# U7 Post-E11 — Full 5-Lane E6 Acceptance Rerun on `main` (`74cbb1b`)

**Tested commit:** `74cbb1b0f3b56e7e06a21dd7201809042d9135a8` (`main`, clean detached worktree `G:\Haitham\VsCode\contest-e6-post`)  
**`apps/web` baseline check:** `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web` → **clean (exit `0`)**  
**Screenshots path:** `G:\Haitham\VsCode\contest\apps\memory\acceptance\results\screens\` (`22` PNGs)

## 1. Included Merges (`git merge-base --is-ancestor` vs `main` `74cbb1b`)

| Work Package | Source Branch / Commit | Merged into `main` | Ancestor of `main` |
|---|---|---|---|
| **E11a** (A1 end-cue negation/ownership + A2 late supersession) | `e11a/temporal-fixes` (`722aa37`) | `7bcc898` | **True** |
| **E11b** (PR #7: B1–B6 review fixes) | `origin/e11b/review-fixes` (`61f230d`) | `83d498a` | **True** |
| **E10** (D17 topic tree + D18 weight-floor retention + independent review) | `origin/e10/topic-tree` (`f33242c`) | `e577ba3` | **True** |
| **E12** (PR #8: Community web wired to real `/api/community/*`) | `origin/e12/community-wiring` (`bee0aa0`) | `74cbb1b` | **True** |

---

## 2. E6 5-Lane Overview & Comparison vs E6 Baseline (`4e8d531`)

| Lane | E6 Baseline (`4e8d531`) | Post-E11 `main` (`74cbb1b`) | Delta / Notes |
|---|---|---|---|
| **Lane 1: Engine S1–S10** | Pre-E9a/E9b/E10/E11 | **9 PASS / 1 FAIL** | S1, S3, S4, S5, S6, S7, S8, S9, **S10 all PASS**; S2 FAIL on `$0.00514`/day cost (`<=$0.0044`) & `6/8` sup / `1/4` late |
| **Lane 2: App & Shell Suites** | Older test baselines | **10/10 projects PASS** | `memory` `540p/8s`, `api` `671p/16s`, `mobile` `50p`, `desktop` `32+7p`, `community` `40+8+11p` (+4 E2E), `messenger` `4+10+13+8+8+6p` |
| **Lane 3: Stack Health + 2-Account E2E** | `26/27 GREEN`; E2E `86 PASS / 3 FAIL` (FAIL 1, 3, 4, 6, 7) | Health **28/29 GREEN**; E2E **89 PASS / 0 FAIL** | FAIL 2/3/4 (Forget sweep & stale image) & FAIL 7A (Chat citation) FIXED; desktop shell stopped in daemon due to inherited `ELECTRON_RUN_AS_NODE=1`; Today `0` cards & B Chat `cited=0` remain |
| **Lane 4: Playwright Web Smoke** | **12 PASS / 10 FAIL** (FAIL 5 CORS, FAIL 8 `/profile` 404) | **20 PASS / 2 FAIL** (`0 serverErrors`) | FAIL 5 CORS & FAIL 8 `/profile` 404 FIXED; `dubaiio /memory` mobile+desktop emit React Native Web responder `console.error` warnings (`onStartShouldSetResponder`) |
| **Lane 5: Electron 3 Desktop Shells** | **2 PASS / 1 FAIL** (`dubaiio-desktop` timed out — FAIL 9) | **3 PASS / 0 FAIL** (when `ELECTRON_RUN_AS_NODE` unset) | FAIL 9 (`dubaiio-desktop`) FIXED: loads `http://localhost:8081/`, off-origin & `window.open` blocked |

### E6 Baseline FAIL 1–9 Resolution Map

| Baseline FAIL | Item | Status on `74cbb1b` |
|---|---|---|
| FAIL 1 | Extraction cost `$0.00531/day` vs `$0.0044` | Still open (`$0.00514/day` in S2) |
| FAIL 2 | Owner provisioning / `TM_ADMIN_TOKEN` | **FIXED** (`owner-provisioning-ready` GREEN; `e6:gmail` + `/api/ingest/*` 200) |
| FAIL 3 | Stale Docker `api` image kept forgotten text | **FIXED** (`memory-image-current` GREEN; Forget raw SQL `{}`) |
| FAIL 4 | Forget sweep left text in `job_attempts` | **FIXED** (`sweep` raw SQL `{}`) |
| FAIL 5 | `dubaiio` `:8081` → `:8000` CORS errors | **FIXED** (`0` CORS errors across all 10 `dubaiio` Playwright checks) |
| FAIL 6 | Today live cards = `0` on synthetic data | Open (`cards=0`, `empty_reason=no_confirmed_interests`; awaits real data) |
| FAIL 7 | Live chat recall / citations | **Partial**: Account A Chat `cited=8` (PASS), Account B Chat `cited=0` (HTTP 200, non-empty reply) |
| FAIL 8 | Community `/profile` 404 on first visit | **FIXED** (mobile & desktop `/profile` `200`, `0 consoleErrors`, `0 serverErrors`) |
| FAIL 9 | `dubaiio-desktop` Electron shell | **FIXED** (`started=true`, `http://localhost:8081/`, navigation/popup guards active) |

---

## 3. Lane 1 — Engine S1–S10 (`apps/memory/acceptance/results/e6-post-e11-merged/REPORT.md`)

| Suite | Gate | Measured Result on `74cbb1b` | Status |
|---|---|---|---|
| **S1** Retrieval | Gold ctx top-8 ≥ 0.78, top-16 ≥ 0.85, AR ≥ 0.80, 0 leaks; 20k p95 < 150 ms | Gold ctx `0.7816 / 0.8645`, AR `0.9028`, `0` sens leaks; 20k p95 `113.01 ms` (writer `146.1 ms`, `12` commits), `/search` `67.48 ms`, MCP `62.19 ms`, needle `True/True/True`; Extracted `/context` `0.5461 / 0.6702` | **PASS** |
| **S2** Extraction & Cost | mean ≤ $0.0044/day; 8/8+4/4+4/4; 0 leaks; FP ≤ 2% | `32/32` applied (`0` rejected); mean **`$0.00514`/day** (p95 `$0.00715`, max `$0.00807`, total `$0.1594` + judge `$0.0223`); recall `90.2%`, prec `90.0%`; changes `6/8` sup, `5/5` end, `1/4` late; `0` leaks, FP `1.96%` (`f049`, `f084`); E10 proposals `11` (`8` kept, `2 no_branch`, `1 rule9`) | **FAIL** |
| **S3** Forget | 0 survivors; fenced in-flight jobs | `facts_erased=1`, `warm_ctx_leak=False`, `facts_version 1->2`, `generation_stale` fenced, `stale_subj_cnt=False` | **PASS** |
| **S4** Bridge Postgres | HTTP contract + fake reference suite | `8/8` `HttpTemporalMemoryClient` ops OK on Postgres; fake suite `92 passed in 2.66s` | **PASS** |
| **S5** Rule 9 Surfaces | 0 sensitive leaks; inferred provenance | 5A leaks (`people=False`, `links=0`); 5B `Alserkal Cafe` `provenance=inferred`; 5C `health`/`faith` `False` | **PASS** |
| **S6** Vault Graph | 20k p95 < 150 ms; true counts | `16/16` checks OK; 20k p95 subjects `60.52 ms`, people `102.09 ms` | **PASS** |
| **S7** Live Triples | prec ≥ 0.98 on 84-item EN/AR/ARZ trap set | `precision=1.0`, `recall=0.9286`, `trap_fp=0` (`56/56`), `quarantine_leak=0` (`5/5`) | **PASS** |
| **S8** Places & Topics | restaurant by name/area/category; 2-visit hyp | `Zuma=True`, `DIFC=True`, `restaurant=True`, `2-visit hyp=1` | **PASS** |
| **S9** Why & Story | cited span/unknown; cache invalidation | `13/13` checks OK (`reason_span=True`, `story_cache=False->True`, `forget_inv=True`, `why_after=404`) | **PASS** |
| **S10** Hybrid Ablation | hybrid beats kw on para; gold top-16 ≥ 0.85; 20k HNSW p95 < 150 ms | Gold hyb `0.7838 / 0.8645` (`0` sens leaks); paraphrase kw→hyb `0.25 → 0.4833`; 20k HNSW cached `/context` p95 **`128.63 ms`** (`/search` `96.41 ms`), needle `True` | **PASS** |

---

## 4. Lane 2 — Every App & Shell Test Suite (`contest-e6-post` @ `74cbb1b`)

| Package | Command | Result |
|---|---|---|
| `apps/memory` | `pytest -q` (full memory venv + Postgres `:5442`, verified on `e577ba3` prior to docs/community-only E12 merge) | **540 passed, 8 skipped, 0 failed** (`76.01s`) |
| `apps/api` | `pytest -q tests` (`DATABASE_URL` unset, `PYTHONPATH` on `contest-e6-post`) | **671 passed, 16 skipped, 0 failed** (`212.35s`) |
| `apps/mobile` | `npm test` + `npx tsc --noEmit` | **10 suites / 50 passed**, `tsc` exit `0` |
| `apps/desktop` (main) | `npm test` + `npm run typecheck:main` | **6 files / 32 passed**, `tsc` exit `0` |
| `apps/desktop/renderer` | `npm test` + `npx tsc` + `npm run build` | **4 files / 7 passed**, `tsc` + `vite build` exit `0` |
| `apps/community` | `npm test` + `npx tsc --noEmit` + `npm run build` | **7 files / 40 passed**, `tsc` clean, `next build` (9/9 static pages across 10 routes) |
| `apps/community/mobile` | `npm test` + `npx tsc --noEmit` | **2 files / 8 passed**, `tsc` exit `0` |
| `apps/community/desktop` | `npm test` + `npm run typecheck` + `npm run build` | **2 files / 11 passed**, `tsc` + build exit `0` |
| `apps/messenger` | `npm run typecheck`, `test:photo-window`, `test:memory`, `test:store`, `npm run build` | `typecheck` `0`, photo-window `4/4`, memory `10` + **`MEMDOM 13/13`**, store `8/8`, `vite build` exit `0` |
| `apps/messenger/mobile` | `npm test` + `npx tsc --noEmit` | **1 file / 8 passed**, `tsc` exit `0` |
| `apps/messenger/desktop` | `npm test` + `npm run typecheck` + `npm run build:ts` | **1 file / 6 passed**, `tsc` + `build:ts` exit `0` |
| `apps/community/tests/e2e` | `test_community_web_e2e.py` (verified in E12 PR #8 gate on `bee0aa0`) | **4 passed** (`12.65s`), `8` PNG screenshots |

*(Environment note from prior Lane 2 bootstrap: `community/{mobile,desktop}` and `messenger/{mobile,desktop}` lack `package-lock.json` so `npm install --no-package-lock` was used in `contest-e6-post` without altering tracked files.)*

---

## 5. Lane 3 — Live Stack Health & 2-Account E2E (`results/e6-post-e11/e2e.json`)

- **`health.ps1`:** **28/29 GREEN**. Every infrastructure container (`postgres`, `rabbitmq`, `redis`, `api`), host workers (`p0@w`, `p1@w`, `1 beat`), semantic model (`bge-m3 loaded`), `memory-image-current`, `owner-provisioning-ready`, `apps/api:8000`, `website/expo-lan:8081`, `community-api:8060`/`website:3060` (`backend=http identity_shared=True bridge=True`), `messenger-api:8070`/`website:5173` (`backend=http identity_shared=True bridge=True`), queue depths (`0`), and `claude -p (Haiku, medium effort)` passed GREEN. `[RED] desktop stopped` in the agent-launched daemon occurred because the VSCode/Antigravity host shell exported `ELECTRON_RUN_AS_NODE=1` (fixed by unsetting that env var in Lane 5).
- **`e2e_stack.py` (`ingest → verify → forget A → forget B → sweep A → isolation`):** **89 PASS / 0 FAIL** (`0` leaks, `0` cross-account bleed):
  - `ingest` (**10/10 PASS**): consent + Takeout/WhatsApp upload + mocked Gmail boundary for accounts A and B.
  - `verify` (**24/24 PASS** + `2` INFO rows):
    - Account A: `applied=7, rejected=1`, `facts=12`, `cost=$0.0091` (8 attempts), `Today`: `http=200 cards=0 interests=7 empty_reason=no_confirmed_interests`, `Chat`: `http=200 cited=8 memory_used=True`, `graph(subjects)` `8n/7e/0 orphans`, `graph(people)` `6n/6e/0 orphans`, `why`/`story`/`md.zip` (`14` files)/`quests` `200`.
    - Account B: `applied=8`, `facts=12`, `cost=$0.0085` (8 attempts), `Today`: `http=200 cards=0 interests=8 empty_reason=no_confirmed_interests`, `Chat`: `http=200 cited=0`, `graph(subjects)` `9n/8e/0 orphans`, `graph(people)` `8n/13e/0 orphans`, `why`/`story`/`md.zip` (`14` files)/`quests` `200`.
  - `forget A` (**10/10 PASS**): Takeout forgotten, raw SQL `{}` for `Zephyrcrest`, search/context/graph/story/export clean, WhatsApp retained.
  - `forget B` (**10/10 PASS**): Takeout forgotten, raw SQL `{}` for `Halcyonford`, search/context/graph/story/export clean, WhatsApp retained.
  - `sweep A` (**3/3 PASS**): Engine Forget on `e6:gmail:A:*` cleared `Zinnwald` (`{}`) and kept earlier erased `Zephyrcrest` clean (`{}`).
  - `isolation` (**32/32 PASS**): Community & Messenger sessions valid; zero cross-account hits on search/context/graph/today/chat/export/community/messenger; `403` on cross-app session reuse and cross-owner engine requests; raw SQL scans `{}` both ways.

---

## 6. Lane 4 — Playwright Web Smoke (`22` checks across `3` sites × `2` viewports)

Raw output: `G:\Haitham\VsCode\contest\apps\memory\acceptance\results\e6-post-e11\web-smoke.json`  
Screenshots (`22` PNGs): `G:\Haitham\VsCode\contest\apps\memory\acceptance\results\screens\`

| Site | Viewport | Route | HTTP | `textLen` | `consoleErrors` | `serverErrors` | Result |
|---|---|---|---:|---:|---:|---:|---|
| `dubaiio` | mobile / desktop | `/`, `/chat`, `/quests`, `/connect` (8 checks) | `200` | `55`–`125` | `0` | `0` | **8/8 PASS** |
| `dubaiio` | mobile & desktop | `/memory` (2 checks) | `200` | `1489` | `6` (`Unknown event handler property '%s'... onStartShouldSetResponder`) | `0` | **2/2 FAIL** (RN-web SVG responder warnings; 0 HTTP/CORS errors) |
| `community` | mobile / desktop | `/`, `/communities`, `/inbox`, `/profile`, `/create` (10 checks) | `200` | `221`–`1162` | `0` | `0` | **10/10 PASS** |
| `messenger` | mobile / desktop | `/` (2 checks) | `200` | `160` / `368` | `0` | `0` | **2/2 PASS** |

---

## 7. Lane 5 — Electron Desktop Shells (`results/e6-post-e11/electron.json`)

*(Executed with `ELECTRON_RUN_AS_NODE` unset; prior attempt with inherited `ELECTRON_RUN_AS_NODE=1` failed to launch Electron as Chromium.)*

| Shell | Started | Loaded URL | `urlOk` | `offOriginBlocked` | `windowOpenBlocked` | `externalHandoffs` | Notes |
|---|---|---|---|---|---|---|---|
| `community-desktop` | `True` | `http://localhost:3060/` | `True` | `True` | `True` | `2` | `[]` |
| `messenger-desktop` | `True` | `http://localhost:5173/` | `True` | `True` | `True` | `2` | `[]` |
| `dubaiio-desktop` | `True` | `http://localhost:8081/` | `True` | `True` | `True` | `2` | `[]` |

**Lane 5 total:** **3 PASS / 0 FAIL**.
