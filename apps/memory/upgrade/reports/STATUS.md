# temporal_note upgrade: status board

One line per event, newest last: `<date time> | <WP> | <agent> | <branch> | <commit> | <state>`
States: in-progress · ready-for-review · fixes-requested (see `<WP>.review.md`) · merged.

2026-11-24 | U1a | codex | mem-wpU1a | afcec62 | merged → memory 9ac5875 (Claude: 343 passed; 21 Postgres)
2026-11-24 | U0a | ? | mem-wpU0a | 3923366 | merged → memory 267b0cf (Claude: 348 passed; 26 Postgres)
2026-11-24 | U0b | gemini | (acceptance/) | e05371f-20261124-1059 | baseline done
2026-11-24 | U1b | (previous agent, quota out) | mem-wpU1b | 267b0cf (ff by Claude; no commits) | paused → continues in Q_cursor item 1; see U1b.handoff.md
2026-11-24 | U7_267b0cf | gemini | (acceptance/) | 267b0cf-20261124-1144 | done (S4 PASS 8/8; S3 U1a fixed, fixture overlap noted; S1/S5 await U1c/U1b)
2026-11-24 11:42 | U0c | codex | mem-wpU0c | af78e62 | ready-for-review
2026-11-24 11:45 | U1b | cursor | mem-wpU1b | 2ed3c7c | ready-for-review
2026-11-24 11:50 | U3 | cursor | (no branch) | — | Part A in reports/U3_diagnosis.md; Part B waiting on U0c (af78e62) to be merged into memory
2026-11-24 13:12 | U1c | gemini | mem-wpU1c | c86db4e | ready-for-review (367 passed; acceptance S1/S3/S4/S5/S6 all PASS on c86db4e)
2026-11-24 12:05 | U0c | codex | mem-wpU0c | af78e62 | merged → memory 01b5183 (Claude: 364 passed + gold e2e; see U0c.review.md)
2026-11-24 12:05 | U1b | cursor | mem-wpU1b | 2ed3c7c | merged → memory 573ff79, pushed (Claude: 364 passed + gold e2e; note for U3 in U1b.review.md)
2026-11-24 13:40 | U3 | cursor | mem-wpU3 | 5218ee5 | ready-for-review
2026-11-24 13:55 | UI | cursor | ios-graph | e3125bb | ready-for-review
2026-11-24 13:52 | U4 | gemini | mem-wpU4 | d9259c7 | ready-for-review (BAAI/bge-m3 1024-d HNSW; 371 passed; paraphrase top16 0.20->0.533; 20k uncached p95 149.64ms ctx / 116.40ms srch; 0 leaks)
2026-11-24 14:00 | U5 | gemini | mem-wpU5 | f1f2161 | ready-for-review (base c86db4e; 371 passed; /why spans + /story atomic cache; cached p95 12.99ms, uncached template p95 18.66ms; Part C skipped)
2026-11-24 14:40 | U1c | gemini | mem-wpU1c | c86db4e | merged → memory 8ba3aa7 (U1c.review.md)
2026-11-24 14:40 | U4 | gemini | mem-wpU4 | d9259c7 | merged → memory 7625d90 (U4.review.md)
2026-11-24 14:40 | U5 | gemini | mem-wpU5 | f1f2161 | merged → memory 932de06; migration renamed 0005 in fb96253; pushed (U5.review.md)
2026-11-24 14:40 | U3 | cursor | mem-wpU3 | 5218ee5 | fixes-requested (alias channel: Rule-9 leak + full scan 304 ms) — see U3.review.md
2026-11-24 14:55 | UI | cursor | ios-graph | e3125bb | merged → ios, pushed (UI.review.md)
2026-11-24 15:20 | (all) | claude | memory | e598d43 | tracker/prompts/reports moved into repo apps/memory/upgrade/; next round: Cursor U3-fix→U6, Codex U2, Gemini harness-move+rerun→SH-1/SH-2; Claude: CS-1 merge
2026-11-24 16:45 | U3 | cursor | mem-wpU3 | 1ab1cee | ready-for-review
2026-11-24 15:50 | CS-1 | gemini (+claude) | cs/live-bridge-tests | f4922b9 | merged → contest-shared dd40257 → societal aad53cc, business 2d15989; pushed (API suites green except known test_ops/redis; societal test_identity_jwt flaky in full run, passes alone 3/3)
2026-11-24 14:52 | U2 | codex | mem-wpU2 | 6476a83 | ready-for-review (396 passed; 13.98 ms HTTP p95; 0/51 trap emissions; 5/5 quarantined)
2026-11-24 17:30 | U3 | cursor | mem-wpU3 | 1ab1cee | merged → memory 7ecbbd4 (U3.review.md)
2026-11-24 17:30 | U2 | codex | mem-wpU2 | 6476a83 | merged → memory cbd20c8 (U2.review.md)
2026-11-24 17:30 | E-round | claude | — | — | prompts E0–E4 written (real-data round: E1 run stack, E2 sign-in+QR pairing, E3 ingest, E4 chat+Today feed)
2026-11-24 18:10 | U6 | cursor | mem-wpU6 | e23d8e8 | paused (Cursor quota out) — unverified WIP commit; see U6.handoff.md. E2 reassigned Cursor → Gemini
2026-11-24 15:32 | U7 | gemini | mem-wpAcc | f8b404a | ready-for-review (harness+gold moved, 0 leaks; e598d43 full run incl S2: S1/S3/S5/S6/S9/S10 PASS, S4 skipped, S7/S8 pre-U2/U3, S2 $0.1549 extract + $0.0210 judge, mean $0.0050/day — U7_e598d43.md)
2026-11-24 15:32 | SH-1 | gemini | cm/shells | d93d6f7 | ready-for-review (unmerged; mobile 8/8, desktop 11/11, unsigned exe 93.87MB, Community tests 9/9 + next build OK, Gate1 585p/15s/1f pre-existing redis, Gate2/3/5 clean — SH-1.md)
2026-11-24 15:32 | SH-2 | gemini | mg/shells | fb3eed4 | ready-for-review (unmerged; mobile 8/8, desktop 6/6, unsigned exe 93.96MB, Messenger gates OK, old-name grep 0 matches, Gate1 545p/16s/1f pre-existing redis, Gate2/3/4/5 clean — SH-2.md)
2026-11-24 15:25 | E3 item 0 | codex | e3/topic-forget-fix | b116f31 | ready-for-review (407 passed, 8 skipped; Postgres topic retraction)
2026-11-24 16:11 | U7_main | gemini | main | 4e2646d | done (32/32 jobs applied, sup 4/8, late 1/4, end 0/5; extract $0.1982 + judge $0.0216 = $0.2198, mean $0.0064/day; S1/S3/S5/S6/S9/S10 PASS; S4 7/8 HTTP + 92 fake passed — U7_main.md)
2026-11-24 16:11 | E4 | gemini | e4/chat-today | 275757e | ready-for-review (unmerged; /api/chat/turn + /api/today + Rule 9/isolation tests; 620 passed, 17 skipped, 1 pre-existing test_ops/redis — E4.md)
2026-11-24 15:45 | E3 | codex | e3/ingest | 0decd30 | ready-for-review (623 API passed; 8/8 E3 Postgres; item 0 b116f31)
2026-11-24 19:30 | Acc | gemini | mem-wpAcc | f8b404a | merged → main (acceptance + synthetic gold now in apps/memory/acceptance/; validate.py PASS)
2026-11-24 19:30 | SH-1 | gemini | cm/shells | d93d6f7 | merged → main (Community Expo Go + Electron; tests green). Fix owed: apps/community/tsconfig.json must exclude mobile/ + desktop/ (fresh-checkout build fails) → Devin task 3
2026-11-24 19:30 | SH-2 | gemini | mg/shells | fb3eed4 | merged → main (Messenger Expo Go + Electron; tests green; old-name gate clean)
2026-11-24 19:30 | E3-fix | codex | e3/topic-forget-fix | b116f31 | merged → main (407 passed); main pushed
2026-11-24 16:00 | E3 | codex | e3/ingest | 0decd30 | merged → main 68e2147, pushed (E3.review.md)
2026-11-24 16:15 | U6 | devin | mem-wpU6 | b31a649 | merged → main (413 memory passed; U6.review.md)
2026-11-24 16:15 | community-next-security + npm-lockfiles | devin | 721d0f8 / 7c1892c | merged → main fc8417b, pushed (tsc/9 tests/build; mobile 30, desktop 10)
2026-11-24 16:45 | E4 | gemini | e4/chat-today | 275757e | merged → main 36eb356, pushed (api 623 passed; E3 8; E4 7; scope ok; no secrets; E4.review.md). Founder-PC live-cards check still owed
2026-11-24 18:45 | E1/E2 | gemini | e1/run-stack, e2/signin | eea494f / 9f114c4 | STALLED (no commits since 15:46, no report, last file edit 16:16) — wip UNVERIFIED snapshots pushed; not merged, no gates run
- 2026-11-24 DOCS-AUDIT merged into main d4a127a (31 md files; rules 1-10 + Gates byte-identical; apps/web untouched) — Claude
2026-11-24 18:53 | E2 | gemini→claude/sonnet | e2/signin | 4964993 | ready-for-review
- 2026-11-24 E2 merged into main 8c5b547 (+lockfile fix d485571) (api 631/637 + 5 env-only proven 16/16, mobile 44, desktop 17) — Claude verifier
2026-11-24 19:07 | E2b | claude/sonnet builder | e2b/pairing-polish | 4fbb019 | ready-for-review (api 637/643, mobile 50, desktop main 18 + renderer 7)
2026-11-24 19:10 | E7 | claude/sonnet builder | e7/receipts | deeadb7 | ready-for-review (memory 428 passed/8 skipped, +15 tests; S2 gold cost unchanged ~$0.0064/day: 0 gold slots pre-filled, ~-$0.0007 per receipt estimated) - E7.md
- 2026-11-24 E7 merged into main 4202a33 (e7/receipts deeadb7; memory 428 passed/8 skipped vs baseline 413; gold e2e Docker test not run, prepass on gold = 0 prefilled) — Claude verifier
2026-11-24 19:35 | E1 | claude/sonnet builder (continues gemini WIP) | e1/run-stack | d707653 | ready-for-review (health 15/15 green x3, api 644 passed 0 failed w/ memory engine in venv)
2026-11-24 20:50 | E1b | claude/sonnet builder | e1b/host-workers | e92c872 | ready-for-review (host celery workers+beat run real claude -p extraction: job applied, 3 facts, 0.083 USD; fixes claude envelope parse + opt-in agent-cli layer-2 screen; memory 432p/8s, api 644p; renderer lockfile) - E1b.md
2026-11-24 20:55 | E5 | claude/sonnet builder | e5/shared-layer | 6887f23 | ready-for-review (branched from e1b; shared identity + http memory for Community/Messenger, app_id on exchange/pair, CS-1 live 86p/6s/0f vs fake 92p, 9 new tests, flaky fix; start-all/health rows) - E5.md
- 2026-11-24 E1b merged into main 7fc38fb (memory 432, api 644, renderer 7; stack 20/20 green) — Claude verifier
- 2026-11-24 E5 merged into main 9233daf (api 653, community 11 + build, messenger typecheck/build ok, shells 11/8/6/8; stack 27/27 green) — Claude verifier
2026-11-24 23:59 | E5b | claude/sonnet builder | e5b/memory-ui | d61eee5 | ready-for-review (api 664p/16s, community 16, messenger memory-ui 10 + store + build; Community consent/Forget + Messenger Save-to-memory approval card + Settings memory wired to server; pair store bounded; cross-app redeem tests) - E5b.md
- E8 engine-fixes: branch e8/engine-fixes pushed, not merged. CLI trim (46k->~1k overhead; note 23.5k/12.8k/$0.083/156s -> 2.8k/2.3k/$0.002/12s), user Forget scrubs text (tombstone only), resolve returns old_fact/new_fact. memory 443/8, api 653/16.
- 2026-11-24 E8 merged into main 4e8d531 (memory 443, api 653; stack 26/27 green, desktop allowed-stopped; proof 2.8k in/3.4k out/$0.0025) — Claude verifier
- 2026-11-25 E6 full test: 37 PASS / 9 FAIL — Claude
- 2026-11-25 E6 harness merged into main 50f8f4a — Claude verifier
- E9a 01:18: branch e9a/stack-fixes (630ea72) pushed, not merged: FAILs 2,3,5,7,8,9 fixed; api 670, desktop 28+7, community 19; live check green. See reports/E9a.md
- E9a revised: chat fallback removed (memory_used=false on empty pack); branch e9a/stack-fixes tip f077a72, api 670 passed
- 2026-11-25 E9a merged into main a17f5b5 — Claude verifier
- 2026-11-25 E9c admin token not needed: start-all.ps1 (since 630ea72) already generates a 32-byte URL-safe TM_ADMIN_TOKEN into git-ignored apps/memory/.env when missing/empty, never printed; compose env_file (.env, required:false) + `up -d --build api` picks it up; README already documents it — Claude
E9b: branch e9b/s2-quality 37f0d1f pushed (not merged); pytest 475/8 skip; S2 sup 7/8 ended 5/5 late 3/4 FP 1.96%; S3/S5/S7 PASS; live context semantic fix (embeddings were never written; Docker lacked [semantic]). See E9b.md
- 2026-11-25 E9b merged into main 9d7b9e5 — Claude verifier
2026-11-25 07:46 | E10 | gemini | e10/topic-tree | — | queued (prompts/E10_topic_tree.md; founder decision on _SYNONYM_GROUPS)
2026-11-25 07:46 | E11a | codex | e11a/temporal-fixes | — | queued (prompts/E11_review_fixes.md Part A)
2026-11-25 07:46 | E11b | devin | e11b/review-fixes | — | queued (prompts/E11_review_fixes.md Part B)
2026-11-25 08:24 | E10 | claude | e10/topic-tree | — | prompt amended per D18 (no deletion; weights to floor) — agents read latest main
2026-11-25 08:28 | E12 | devin | e12/community-wiring | — | queued after E11b (prompts/E12_community_wiring.md)
2026-11-25 08:24 | E11a | codex | e11a/temporal-fixes | 2d6af51 | A1/A2 implemented; pytest 524 passed, 8 skipped; S2 6/8 superseded, 5/5 ended, 3/4 late on repeat; historical supersession gate open (paired score unchanged). See E11a.md.
2026-11-25 | E11a | gemini-integrator | e11a/temporal-fixes | 722aa37 | merged → main (A1/A2; memory 524p/8s/0f; historical S2 7/8 superseded gate open; handoff committed)
2026-11-25 | E11b | devin | e11b/review-fixes | 3c0e178 | ready-for-review (B1–B6 done; memory 482p/8s, api 671p/16s, messenger test:memory 10+13, desktop 32+typecheck; report E11b.md)
2026-11-25 | E11b | gemini-integrator | e11b/review-fixes | 61f230d | merged → main (PR #7; B1–B6; full-venv memory 530p/8s/0f, api 671p/16s, messenger 10+13, desktop 32p; follow-ups queued for E12)
2026-11-25 09:03 | E10 | gemini | e10/topic-tree | HEAD | ready-for-review (D18 weight floor 0.05 applied, 0 delete paths, privacy/forget.py untouched; 183 nodes/463 aliases/32 lexicon; 486 passed/0 failed; S2 proposals 10: 5 kept / 5 dropped; mean $0.004956/day; 20k p95 12.71ms ctx / 111.11ms srch / 102.07ms mcp; see E10.md)
2026-11-25 | E10 | gemini-integrator | e10/topic-tree | f33242c | merged → main (independent sub-agent review in E10.review.md; D17+D18; combined memory 540p/8s/0f)
2026-11-25 | E12 | devin | e12/community-wiring | bee0aa0 | ready-for-review (Community wired to real /api/community/*: feed+lanes+sort, post actions, follows/profiles, groups, search, discovery Why-this, real-first inbox; vitest 40, mobile 8, desktop 11, api community 65, Playwright two-user e2e 4/4 + screenshots) - E12.md
2026-11-25 | E12 | gemini-integrator | e12/community-wiring | bee0aa0 | merged → main (PR #8; vitest 40p + build 9 routes, community/mobile 8p, community/desktop 11p, api community 65p, Playwright 2-user e2e 4p; apps/api/app/community untouched)
2026-11-25 | U7_post_E11 | gemini-integrator | main | 74cbb1b | done (E6 5-lane rerun: Lane1 9/10 PASS [S1/S10 PASS, S2 $0.00514/d]; Lane2 10/10 green; Lane3 28/29 green + 89/89 E2E PASS; Lane4 20/22 [0 CORS/404, 2 /memory RN-web warnings]; Lane5 3/3 Electron PASS; see U7_post_E11.md)
2026-11-25 | D19–D22 + canon | gemini-integrator | main | 5a5f6bd | done (recorded D19–D22 in founder-decisions.md; finalized & archived canon-patches to docs/archive/canon-patches-2026-11-25/; Community Facebook/Reddit + Two-Tower + context plan written)
2026-11-25 | E13a | codex | e13a/lower-and-delete | — | queued (prompts/E13a_lower_weights_delete_my_data.md — D19 Lower to 0.01 + account Delete my data + FAQ)
2026-11-25 | E13b | gemini | e13b/shared-vocab-agent | — | queued (prompts/E13b_similar_queries_vocab_agent.md — D21 similar-query logical agent + E10 review cleanups)
2026-11-25 | E14a | devin | e14a/community-social-parity | — | queued (prompts/E14a_community_social_parity.md — D22 Facebook/Reddit social core + E11b/E12 cleanups)
2026-11-25 | E14b | devin | e14b/community-two-tower | — | queued after E14a (prompts/E14b_community_two_tower_context.md — D22 real Two-Tower + foreground context + usage profile)
2026-11-25 | E14 | gemini-integrator (4 sub-agents) | e14/community-replica-recommender | 1275b25 | in-progress, UNVERIFIED WIP pushed (2 of 4 agents hit quota; two-tower not wired into server.py/agents.py; 2 failing tests; web UI gates not run) - see prompts/HANDOFF_integrator_2026-11-25b.md
2026-11-25 | HANDOFF | gemini-integrator | main | 55878ab | handoff 2 written (prompts/HANDOFF_integrator_2026-11-25b.md); PR #9 (chore/e11b-e12-cleanups) open, E13a uncommitted in contest-e13a
2026-11-25 | E14c | devin | e14c-1..7 | - | queued piece by piece (prompts/E14c_devin_piecewise.md): 1 start shells, 2 LAN api base, 3 backend verify, 4 mobile verify, 5 web social, 6 two-tower fix, 7 wire
2026-11-25 | E14c piece 1 | devin | e14c-1/start-shells | - | ready-for-review (start-all -Shells starts community/messenger Expo :8082/:8083 + Electron desktops; health rows SKIP without -Shells; stop-all unchanged; verified live: start/health/stop all green for shells; report E14c.md)
2026-11-25 | PR #9 (cleanups) | gemini-integrator | chore/e11b-e12-cleanups | ab6ca8c | merged -> main (Postgres memory tests 8p/0f: test_embed_lazy_backfill + test_semantic_hybrid; stop-all.ps1 parse OK; apps/community vitest 40p/0f, tsc clean, next build 9 routes; apps/web frozen)
2026-11-25 | PR #10 (E14c piece 1) | gemini-integrator | e14c-1/start-shells | f41494f | merged -> main (start-all.ps1 -Shells + health.ps1 + stop-all.ps1 + README; all 3 scripts parse clean; apps/web frozen)
2026-11-25 | E13a | gemini-integrator | e13a/lower-and-delete | b0785c3 | UNVERIFIED WIP committed & pushed from contest-e13a (57 files: D19 lower-weights + account Delete my data + FAQ; missing D19b explicit-recall weight boost; not gated, not merged)
2026-11-25 | EOD WRAP-UP | gemini-integrator | main | - | day wrapped cleanly; 0 open PRs; resume from prompts/HANDOFF_integrator_2026-11-25c_EOD.md
2026-11-26 | Wave Cleanup + LAN Fix | hydrogen-subagents | main | - | cleaned 22 stale folders (14 worktrees + 8 non-git dirs; 4 kept: contest, contest-e13a, contest-e14-community, contest-memory); Community/Messenger LAN API URL fallback (community 44p/tsc/build, messenger typecheck/store/photo/memory pass, apps/web frozen); wave prompts committed at prompts/wave_2026-11-26/
2026-11-26 | Phase A Fixes + Pairing UI | claude-audit + hydrogen | main | - | Claude Phase A complete (A1/A2/A3); start-all.ps1 drops localhost env overrides + 8-port firewall check; loopback-on-LAN rewrite + 6-char PC pairing-code sign-in added to Community & Messenger (community 45p/tsc/build, messenger typecheck/store 10/photo 4/memory 10+13, ps1 parse OK, apps/web frozen); wave prompts patched for A1/A2/A3
2026-11-26 10:01 | HANDOFF | gemini/hydrogen -> claude | main | b3f9e76 | lead integrator handoff to Claude (strict merge order: PR #11 E14 -> E13a -> E13b; sandbox .env ready) — see prompts/HANDOFF_integrator_2026-11-26_to_claude.md
2026-11-26 | E14 | cursor | e14/community-replica-recommender | a9f0d71 | ready-for-review (PR #11; rebased on main b3f9e76; Phase A D22 DEFAULT 0 + ephemeral user_state/area_coarse + purge_owner_community_data + Google Limited Use; LAN+Pair PC kept; api 84p; web 58p; mobile 18p; desktop 11p; Playwright 4p; bench 19.73ms; apps/web frozen; STOP for E14.review.md PASS + founder visual preview) - E14.md
2026-11-26 | E14 | cursor | e14/community-replica-recommender | ea9a93a | ready-for-review (PR #11 re-review1: B3 real Lower + B4 exact recall/no evidence inflate + S1/S3/S4/S5; api 85p/1s; smoke ok; web 58p; mobile 18p; desktop 11p; Playwright 4p; apps/web frozen; STOP for Claude re-check) - E14.md
2026-11-26 | E13a | codex | e13a/lower-and-delete | - | D19b and Phase A2 E1-E7 implemented; memory 559p/8sk, API 674p/16sk, client gates and apps/web freeze pass; awaiting Claude review (E13a.md)
2026-11-26 | E13b | cursor (Muse WIP finish) | e13b/shared-vocab-agent | 480c28d | ready-for-review (0009 shared vocab + similarity/proposer/admin; HMAC fail-closed; E10 cleanups 461/35; memory 551p/8s; apps/web frozen; wait for E13a PR#12 before merge) - E13b.md

2026-11-26 | E13b | cursor | e13b/shared-vocab-agent | (pending) | ready-for-review (PR #13 re-review: F1-F5; merged main+E13a; memory 572p/8s; apps/web frozen) - E13b.md
