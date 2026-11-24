# U1b — no leaks, stored provenance, T1 suggestions

- Branch: `mem-wpU1b`
- Commit: `2ed3c7c`
- Base: `memory` @ `267b0cf` (U0a + U1a already merged). No review file was waiting.
- `api/app.py` and `api/` / `live/` were not edited. `validator.py` needed no change: it already accepts an update whose target is in context. The late-chain bug was the applier ignoring non-active targets.

## Files

- `apps/memory/src/temporal_memory/core/applier.py`
- `apps/memory/src/temporal_memory/privacy/policy.py`
- `apps/memory/src/temporal_memory/privacy/sensitive.py`
- `apps/memory/src/temporal_memory/ingest/triage.py`
- `apps/memory/tests/test_no_orphan_leaks.py` (new)
- `apps/memory/tests/test_privacy.py`
- `apps/memory/tests/e2e/test_gold_month.py` (assertion update so the fixed false positives are expected)

## What changed

- An entity, alias, family label, or link is written only when an approved fact in the same attempt references it. `link_evidence` stores that link's own facts. A link is not anchored to the day's first fact and is not stored with null evidence.
- `entities.provenance` and `subjects.provenance` are `user_supplied` only when every cited record was written by the owner. Otherwise `inferred`. Auto-promotion changes `status` only.
- `closeness_suggested` is T1 (5+ facts), T2 (3–4), or T3 (2) across at least two days. Family, health, and faith text is ignored. `closeness_tier` is never written.
- A late update of a `superseded` or `ended` target is stored as history. Older evidence still does not overwrite a newer fact.
- `Sara Eid` is no longer a faith hit. `Eid Mubarak` still is. A subscription-cancelled mail and an "you are unsubscribed" receipt are kept. OTP mail and digests still drop.

## Gate, gold month, before → after

Counted with `pre_write` on `gold/ledger.json` fact text. Sensitive true positives are the 8 facts whose ledger `sensitive` is set.

| | before | after |
|---|---|---|
| Gate false positives on clean facts | 5 (`f017`, `f039`, `f049`, `f061`, `f084`) | 4 (`f039` fixed; the other four stay, out of scope) |
| Triage false positives | 2 (`f045`, `f109`) | 0 |
| Sensitive true positives | 8 / 8 | 8 / 8 |

## Tests

- Non-e2e suite: **358 passed** (Postgres tests included; the new leak tests run on Postgres).
- `TM_RUN_E2E=1` gold month: **1 passed** in 99s. Record count is 1012 (the two receipts are imported).

## Contract requests

- U1c should render `entities.provenance`, not `user_supplied` merely because `status == active`. This WP stores the column. It does not change `api/vault.py`.
- `closeness_tier` is still only for a confirm endpoint, which this WP does not add.
