# U1b review — Claude, 24 Nov 2026

**Approved and merged:** `mem-wpU1b` `2ed3c7c` → `memory` `573ff79` (pushed).

Verified on the merged result (U0c + U1b): **364 passed, 8 skipped**; gold-month e2e **1 passed** (1012 records); `apps/web` untouched. False positives went from 5 gate + 2 triage to 4 + 0, and sensitive true positives stay at 8/8. The `tests/e2e/test_gold_month.py` edit (removing the masks) is accepted.

**No fixes on this branch.** One rule-9 point carries into **U3 Part B** (also yours):
- Today a fact is `user_supplied` whenever every cited record is owner-authored. So an *interpretation* the extractor draws from the owner's own message (e.g. "seems stressed about work" from "ugh work again") is labelled "You told me".
- In U3, have the extractor mark each fact as `stated` (the owner literally said it) or `inferred` (an interpretation), via an `OutFact` flag in the output schema.
- `provenance_for_statement` then returns `user_supplied` only for **owner-authored AND stated**. Add a test with one stated and one inferred fact from the same owner message.

**Cursor: continue with U3 Part B** (U0c ✅ and U1b ✅ are in `memory` @ `573ff79`).
