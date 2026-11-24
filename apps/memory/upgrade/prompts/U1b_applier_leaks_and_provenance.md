# U1b — No leaks from quarantined facts + stored provenance (after U0a is merged)

Assigned to: **Cursor** (queue `Q_cursor.md`, item 1).

Paste below the line.

---

Read first:
- `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\B0_common_rules.md`. The integrator is **Claude** (verifies on Postgres + the U0b harness, then merges).
- `TN_UPGRADE_PLAN.md` v1: §2 rows R5 and R3 contradict, §2b **B2**, §7 **D-c**.
- Codex audit findings **01** and **05**; Gemini audit **F02**, **F05** and **F11**.
- Root `G:\Haitham\VsCode\contest\CLAUDE.md` rule 9.

**Sub-agents:** at most 2, cheap tier only: Muse → **Muse 1.3 Contributor** (never Wonder), Codex → gpt-6.2 sol, Gemini → a lower tier, Cursor → its fast model.

```powershell
git -C G:\Haitham\VsCode\contest worktree add ..\contest-mem-wpU1b -b mem-wpU1b memory   # memory must already contain U0a
cd G:\Haitham\VsCode\contest-mem-wpU1b\apps\memory
```

## The problems (reproduced by the audits)

- **Quarantine leaves leaks.** After its only fact was quarantined, a relative still appeared with a `family` label and a `RELATED_TO` link. The cause:
  - `core/applier.py:195-206` creates entities and aliases before facts survive;
  - `:399-411` anchors every link to the day's first applied fact, or to `None`;
  - `/vault/people` renders null-evidence links.
- **Auto-promotion writes the wrong provenance.** A place went from `candidate/inferred` to `active` after 2 days with no confirmation, and the API reports `active` as `user_supplied` ("You told me").
- **Privacy false positives** drop clean gold facts `f039`, `f045` and `f109` (`tests/e2e/test_gold_month.py:20-27`).
- **Multi-step late arrivals** break, because `applier.py:288` ignores non-active targets.

## Owned files (only these)

- `src/temporal_memory/core/applier.py`
- `src/temporal_memory/core/validator.py`
- `src/temporal_memory/privacy/policy.py`
- `src/temporal_memory/privacy/sensitive.py`
- `src/temporal_memory/ingest/triage.py` (false positives only)
- tests: `test_applier.py`, `test_validator.py`, `test_privacy.py`, new `test_no_orphan_leaks.py`

**Not `api/` or `live/`:** U1c renders what you store.

## Deliverables

1. **No entity, alias or link without surviving, approved evidence.**
   - Create or update them only when at least one non-quarantined fact from this attempt references them.
   - Store each link's own supporting facts in `link_evidence` (from U0a), never the day's first fact and never null.
   - Labels such as `relation_to_user = family` must come from an approved fact, never from a quarantined one.
2. **Stored provenance.** Write `entities.provenance` / `subjects.provenance` on creation:
   - `inferred` for anything extracted;
   - `user_supplied` only when the user stated it themselves (first-person, from the owner's own message) or through an explicit confirm, which also sets `user_confirmed_at`.

   Auto-promotion after 2 days may change `status` to `active`, but **never** provenance. Third-party people still need the user's tap.
3. **T1 suggestions (D-c), computed by you, written only as suggestions.** Set `closeness_suggested` (T1 / T2 / T3) + `closeness_suggested_evidence` from interaction frequency and recency across ≥ 2 separate days or sessions.
   - **Never** use family, health or faith signals as input.
   - **Never** write `closeness_tier` (only the user's confirm does that; U1c adds the endpoint).
4. **Fix `f039`, `f045` and `f109`** without losing a single true sensitive block. Report the gate's before/after false-positive and true-positive counts on the gold month.
5. **Late chains:** a late fact can update a `superseded` or `ended` target as history; older evidence never overwrites newer.
6. **Tests, happy + failure paths, on Postgres:**
   - quarantine the only fact → no entity, alias, link or label visible through `list_entities` / `list_links`;
   - mixed day → each link cites its own facts;
   - a 2-day auto-promotion keeps `provenance = inferred`;
   - a first-person statement → `user_supplied`;
   - a T1 suggestion never writes `closeness_tier`;
   - a family-only signal yields no suggestion;
   - the gold-month e2e false positives are fixed.

**Done when:** the full suite is green (Postgres DB tests included) and `TM_RUN_E2E=1` gold month passes with the false positives fixed. Commit on `mem-wpU1b`. Report: branch, files, test counts, gate FP/TP before → after, contract requests.
