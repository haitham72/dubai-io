# U3 Part A — why the shipped extractor scores 66.7% / 59% / 1 of 8

Evidence is the saved S2 run `acceptance/results/e05371f-20261124-1059` (`claude-haiku-5-5`, 31 owner-days) compared with `weekbench/configs/tn_update.py` and the month run `runs/20261123-140525_tn_update-day_month` (also `haiku` via `claude -p`, 92% of 102, 6/8). S2 was not re-run: one owner-month is about $0.15 and is not a cheap one-change experiment. The effects below are counted from the saved job log and the gold ledger.

## The two scores are not the same test

| | Shipped worker (S2) | Weekbench `tn_update` day/month |
|---|---|---|
| Model | `claude-haiku-5-5` | `haiku` (`claude -p`), effort medium |
| Recall | 66.7% (102 plain) | 92% of 102 |
| Precision | 59% (85 true / 57 noise / 2 wrong) | 118 true / 3 noise / 1 wrong |
| Changes | 1/8 superseded, 0/5 ended, 0/4 late | 6/8 |
| What 6/8 allows | S2 requires the old fact and the new fact both present, old not active, new active | `weekbench/score.py:99-102` passes when the new fact is active and the old fact is **missing or** not active. It also ignores the 4 standalone `ended` facts |

The one S2 pair marked ok is `f039 → f040`: `old_statuses` is empty and `new_statuses` is `active`. That is the weak condition. `f039` was quarantined as religion (`Sara Eid`). It is not a real supersede. Strict linked updates in this run: **0/8**.

## Causes, with the effect that can be counted without a new model call

1. **A whole day is thrown away for one bad fact.** `validator.py` appends `duplicate_fact`, `evidence_span_mismatch`, or `credential_in_fact` and `ok` is false for the attempt, so nothing from that day is applied. Five jobs applied 0 facts: 20 Oct (`evidence_span_mismatch`), 23 Oct (`credential_in_fact`), 11 Nov, 17 Nov, 19 Nov (`duplicate_fact`). **18 of 102** plain gold facts have `valid_from` on those five days, including the change pairs `f033/f034` and `f044`. Weekbench applies the rest of the JSON and records one bad object as an error. `model_mismatch` is on every job (`haiku` vs `claude-haiku-5-5`) and is not itself a failure.

2. **The model is not shown the fact it should update.** `graph_store.scoped_context` adds at most 80 facts for matched entities and 50 more recent facts (`graph_store.py` around the `visible_facts(..., limit=80)` and `limit=50` calls). Weekbench sends **every** active fact (`tn_update.py` `facts_block`). Four superseded pairs (`f003/f004`, `f009/f010`, `f027/f028`, `f046/f006`) and all four late pairs were stored as two **active** facts: the model emitted a second `new` fact instead of `update`/`end`. That is what happens when the target id is not under `ACTIVE FACTS`. The prompt on both sides says "only target ids listed under ACTIVE FACTS".

3. **Late history only happens when the model uses `update`.** The applier (before U1b) ignored a target whose status was not `active`, and it stores an older `update` as `history` only when `op` is `update`. The four late facts are `active` next to the newer fact, so the model did not send `update` against the newer id. U1b now keeps a late `update` of an already superseded target as history. It cannot invent the `op` the model did not send.

4. **Two change facts never entered the queue.** `f045` and `f109` (2 of 5 ended) have empty status lists because triage dropped `noreply@` / `news@` mail. U1b keeps those two receipts. `f046`, `f047`, `f048` are present and still `active`: the model did not emit `end`.

5. **The output schema is heavier, so the call is more expensive and noisier.** Weekbench facts are `category` + `topic` and entity ids. The shipped prompt (`extract.py` `build_system_prompt`, `PROMPT_VERSION = extract@3`) asks for `subject_path`, `text_orig`, per-fact `{entity_id, role}`, and `links`. S2 output tokens are often 5.5k–11k. Mean cost is **$0.00492** / day (p95 $0.00748, max $0.00816) against a gate of $0.0044. 57 of 144 extracted facts were judged noise. The same keep-list is in both prompts; the extra fields give the model more ways to emit a near-duplicate.

6. **Privacy false positives remove gold text before the judge sees a change.** `f039` (the only pair S2 called ok) was held as religion because the pattern treats the surname Eid as the holiday. U1b stops that. The other four clean false positives (`f017`, `f049`, `f061`, `f084`) are still held, on purpose for U1b.

## What is real, and what is the scorer

The gap from 92% / 6 of 8 down to 66.7% / 1 of 8 is mostly real, not just a stricter judge:

- About 18 gold facts sit on days that saved zero facts (cause 1).
- The pairs that do exist are two active copies, not a supersede (cause 2). The weekbench 6/8 can count a pair whose old fact is simply absent.
- Two ended facts were deleted by triage (cause 4), now fixed in U1b but not re-measured on S2.
- Cost is over the gate because output tokens are large (cause 5). A cheaper model was not the difference: both runs used Haiku.

## Part B is blocked

`mem-wpU0c` (`af78e62`, v2 contract) is **not** an ancestor of `memory`. Reason spans, `place_type`, and `extract@4` are Part B and need that contract. No extractor code was changed for U3.
