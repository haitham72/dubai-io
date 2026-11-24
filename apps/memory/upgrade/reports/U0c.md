# U0c — Forget cleanup and shared contract v2

**Ready for Claude review.** Branch `mem-wpU0c`, commit `af78e62`, based on `memory@267b0cf`. Worktree `G:\Haitham\VsCode\contest-mem-wpU0c`.

## Changes

| File under `apps/memory/` | Change |
|---|---|
| `src/temporal_memory/models.py` | Added the shared v2 fields, taxonomy, and topic-session methods. |
| `src/temporal_memory/db/migrations/0002_forget_requests_owner_fk.sql` | Cleans up orphan receipts from the temporary U1a table and adds the cascading owner FK. Keeps valid receipts and existing privacy revisions. Fresh schemas already have the FK. |
| `src/temporal_memory/db/migrations/0003_contract_v2.sql` | Adds nullable fact and entity fields and owner-scoped `topic_mentions`. |
| `src/temporal_memory/privacy/forget.py` | Removes the runtime DDL helper, both calls, and the bootstrap connection used by the receipt path. |
| `tests/fixtures/fake_store.py` | Implements the per-owner, per-subject distinct-session counter. |
| `tests/test_migrations.py`, `tests/test_forget.py` | Test legacy and fresh upgrades, owner and subject isolation, distinct sessions, and legacy Forget behavior without DDL. |

## Contract for U2, U3, U5, and U1c

- Optional fields on `Fact` and `OutFact`: `actor_entity_id`, `predicate`, `object_text`, `object_entity_id`, `polarity`, `modality`, `event_at`, `span_record_id`, `span_start`, `span_end`, `reason_text`, `reason_record_id`, `reason_start`, `reason_end`. Span offsets are zero-based character indexes, inclusive at the start and exclusive at the end. Backfill and read-side consumers must validate the cited record before exposing a reason.
- `Entity.place_type` and `OutEntity.place_type` use the optional `PlaceType` literal, including `restaurant` and `café`. Existing facts and entities have NULL in the added columns.
- `GraphStoreFull.record_topic_mention(owner: str, subject_id: str, session_id: str) -> int` and `topic_session_count(owner: str, subject_id: str) -> int`. `topic_mentions` stores `owner, subject_id, session_id, first_at`. Its composite key deduplicates sessions and its subject FK cascades. U2 owns the Postgres implementation and must attach surviving evidence when promoting a topic hypothesis.
- Import `CLUSTERS`, `CLUSTER_LABELS`, and `HELD_BACK_ROOTS` from `models.py`. The held-back roots are `health` and `faith`. U2's topic policy also excludes `people-family`.
- No new contract request for U0c. U2 may stack on this commit per the Codex queue. The stored-provenance dependency is still open: at verification, `memory` and `mem-wpU1b` both pointed to `267b0cf`, and U1b's handoff documented no implementation commit.

## Verification

- Full suite against compose Postgres on port 5442: **354 passed, 8 skipped**. Skips are the opt-in Docker/gold/queue integration tests and live-model test.
- Focused migration and Forget suite: **11 passed**, split **9 Postgres and 2 fake**. Six tests were added, five Postgres and one fake. The migration fixtures dropped their schemas in autocommit.
- Legacy FK upgrade kept the valid receipt and revision and removed only the orphan. Fresh FK repair preserved the existing constraint. A v1 fact and entity survived migration 0003 with nullable fields. Statement tracing saw receipt writes and revision updates with zero Forget DDL.
