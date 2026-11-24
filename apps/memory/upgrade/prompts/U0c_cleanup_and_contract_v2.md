# U0c — Cleanup + contract v2 (for U2, U3 and R6)

Assigned to: **Codex** (queue `Q_codex.md`, item 1). The integrator is **Claude**, who verifies on Postgres + the U0b harness and then merges.

```powershell
git -C G:\Haitham\VsCode\contest worktree add ..\contest-mem-wpU0c -b mem-wpU0c memory   # memory @ 267b0cf or later
cd G:\Haitham\VsCode\contest-mem-wpU0c\apps\memory
```

## Owned files (only these)

- `src/temporal_memory/models.py`
- `src/temporal_memory/db/migrations/0002_*.sql`, `0003_*.sql`
- `src/temporal_memory/privacy/forget.py`, **only** to remove `_ensure_upgrade()` and its 2 calls
- `tests/fixtures/fake_store.py`
- `tests/test_migrations.py`, `tests/test_forget.py`

## Part A — remove U1a's runtime DDL

`privacy/forget.py::_ensure_upgrade()` runs `ALTER TABLE owners …` and `CREATE TABLE IF NOT EXISTS forget_requests …` inside **every** Forget, which takes a table lock on `owners`. Migration `0001` now owns both objects.

1. Delete `_ensure_upgrade()` and both of its calls.
2. **`0002_forget_requests_owner_fk.sql`:** where `forget_requests` lacks the owner FK (databases that U1a touched before `0001`), delete orphan rows, then add `REFERENCES owners(id) ON DELETE CASCADE`. It must be idempotent and a no-op on fresh databases.

## Part B — contract v2 (additive, nullable; no behaviour change by itself)

**`0003_contract_v2.sql`** + `models.py`:

- **Triple on `Fact`** (R2), all optional:
  - `actor_entity_id`;
  - `predicate` ∈ `buys | wants | likes | dislikes | visits | moves_to | works_at | joins | leaves | birthday | other`;
  - `object_text`, `object_entity_id`;
  - `polarity` ∈ `affirmed | negated`;
  - `modality` ∈ `done | planned | wanted`;
  - `event_at`;
  - `span_record_id`, `span_start`, `span_end`.

  Mirror these on `OutFact`.
- **Reason on `Fact` / `OutFact`** (R3 "why"): `reason_text`, `reason_record_id`, `reason_start`, `reason_end`. The span must exist in the cited record. U3 enforces that.
- **`entities.place_type`** (R6): restaurant, café, gym, clinic, school, office, shop, mall, beach, park, hotel, airport, home or other. Mirror it on `Entity` and on the extractor's entity output.
- **`topic_mentions(owner, subject_id, session_id, first_at, PRIMARY KEY(owner, subject_id, session_id))`** (R6, the two-visit counter). Add `GraphStoreFull` methods:
  - `record_topic_mention(owner, subject_id, session_id) -> int` (returns the distinct-session count);
  - `topic_session_count(owner, subject_id) -> int`.
- **One taxonomy** (D-a = the engine's 7). Add these constants to `models.py`:
  - `CLUSTERS = ["career", "learning", "projects", "people-family", "events", "home-money", "travel"]`;
  - `CLUSTER_LABELS = {…: "Career", "Learning", "Projects", "People & family", "Events", "Home & money", "Travel"}`;
  - `HELD_BACK_ROOTS = ["health", "faith"]`.

  U1c (`api/vault.py`) and U3 (`core/extract.py`) import these instead of keeping their own lists.
- **Fake store parity** for every new method and field.

## Tests (Postgres, temporary schema)

- (a) a pre-U0a database + U1a's old runtime DDL + `forget_requests` rows → `migrate()` → FK present, rows kept;
- (b) a fresh database → no-op;
- (c) Forget issues **no** DDL (statement log or mock cursor);
- (d) deleting an owner cascades its `forget_requests`;
- (e) `0003` upgrades a database that has existing facts and entities; the new columns are null; the old data is intact;
- (f) `record_topic_mention` is idempotent per (owner, subject, session) and counts distinct sessions.

The full suite stays green (today 348 passed, 8 skipped).

**Report** → `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\reports\U0c.md`: branch + commit, files, test counts (fake / Postgres), and the final field and method names (U2, U3 and U1c build on them).
