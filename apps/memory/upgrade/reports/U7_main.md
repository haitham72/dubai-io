# U7 Report — Full Acceptance Suite on `main` (`4e2646d`, w/ U2 + U3 + U7 Harness + E3 Topic-Forget Fix)

- **Harness Branch Merged into `main`:** `4e2646d` (`a2106de` + `mem-wpAcc` + `cm/shells` + `mg/shells` + `e3/topic-forget-fix`)
- **Evaluated Commit:** `4e2646d` (`G:\Haitham\VsCode\contest`)
- **Run Folder (gitignored under `apps/memory/acceptance/results/`):** `apps/memory/acceptance/results/20261124-1548`
- **Hardware / DB:** 13th Gen i9-13900K · 24C/32T · 127.7 GB RAM · RTX 4080 · PostgreSQL 17.11 · Python 3.13.17

## Suite Summary on `main` (`4e2646d`) vs `U7_e598d43`

| Suite | `e598d43` Baseline | `main` (`4e2646d`, w/ U2+U3) | Gate / Delta |
|---|---|---|---|
| **S1 Retrieval** | PASS (`0.7934 / 0.8645`, 20k p95 `11.54 ms`) | **PASS** (`0.7934 / 0.8645`, 20k warm p95 `12.84 ms`, writer `8.49 ms`, needle `True/True/True`) | All paths `< 150 ms` |
| **S2 Extraction & Cost** | FAIL (`31/32` applied, `0/8` sup, `0/5` end, `0/4` late, `$0.1549` extract) | **FAIL** (`32/32` applied, `4/8` sup, `0/5` end, `1/4` late, `$0.198221` extract + `$0.021557` judge) | `0` rejected jobs (improved); `superseded 0->4/8`, `late 0->1/4`; mean `$0.006394`/day (`> $0.0044`); FP `3.92%` (`pre_write`); `0` sens leaks |
| **S3 Forget** | PASS | **PASS** (6/6 checks green; `facts_version` bumped, cache/counts clean) | Pass |
| **S4 Bridge on Postgres** | SKIPPED | **FAIL** (7/8 HTTP ops OK; `search_source_prefix` `ok=False`, fake suite `92 passed in 2.87s`) | Scoped `conv_a_ids=['f_s4_a']`, `conv_b_ids=['f_s4_b']` accurate; `unscoped_ids` returned 4 rows incl. earlier `f_s4_hyp`/`rf-520e903d` |
| **S5 Rule 9 Surfaces** | PASS | **PASS** (0 sensitive leaks; `inferred` never `user_supplied`) | Pass |
| **S6 Vault Graph** | PASS (`60.60 ms` / `106.96 ms`) | **PASS** (`16/16`; 20k p95 `subj=58.46 ms`, `ppl=100.69 ms`) | Pass |
| **S7 Live Triples** | NOT YET BUILT | **READY** (`temporal_memory.live.triples.extract_triples` found; 84-item EN/AR/ARZ trap set validated) | Trap scoring script (`s7_traps.py`) only probes symbol presence so far |
| **S8 R6 Places & Topics** | NOT YET BUILT | **NOT YET BUILT** (`Zuma=True, DIFC=True, restaurant=True; 2-visit hyp=0`) | Recorded engine behavior (`cost=$0.00213`) |
| **S9 Why & Story** | PASS (`13/13`) | **PASS** (`13/13`) | Pass |
| **S10 Hybrid Ablation** | PASS (`0.20->0.5333`, p95 `131.66 ms`) | **PASS** (`5/5`; paraphrase `0.20->0.5333`, Gold `0.8579`, 20k HNSW cached `/context` p95 `142.79 ms`, needle `True`) | Pass |

- **Cleanup Check:** `LEFTOVER_SCHEMAS: []`.

## S2 Breakdown (`4e2646d`, 31 Owner-Days + Late Packet, `claude-haiku-5-5`)
- **Jobs:** `32` total / `32` applied / `0` rejected (`worker_kind='internal-cloud'` workaround because LM Studio `:1234` offline).
- **Cost:** extract **`$0.198221`** (`mean=$0.006394`/day, `p95=$0.008174`/day, `max=$0.008923`/day) + judge **`$0.021557`** = **`$0.219778`** total.
- **Quality:** `102` plain gold -> recall **`76.5%`**; `200` extracted -> precision **`53.5%`** (`107T / 88N / 3W`); `20/25` people (`0` dups), `17/20` relations, `16/43` edges.
- **Changes & Privacy:** `4/8` superseded, `0/5` ended, `1/4` late; `0` sensitive leaks; `4/102` (`3.92%`) `pre_write` false positives (`El-Din`, `Egyptian passport`, `Egyptian Arabic`, `Quran`).
- **Extracted-graph retrieval (S1 on S2 output):** `/context` top-8/16 = **`0.4759 / 0.5645`**, `/search` = **`0.4627 / 0.5776`**.
