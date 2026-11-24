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
