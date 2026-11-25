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
2026-11-25 | E11b | devin | e11b/review-fixes | 3c0e178 | ready-for-review (B1–B6 done; memory 482p/8s, api 671p/16s, messenger test:memory 10+13, desktop 32+typecheck; report E11b.md)
