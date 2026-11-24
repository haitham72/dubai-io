# B-C — Muse: canonical privacy gate · Rule 9 promotion policy · Forget-by-source

Paste below the line into **Muse**.

---

Read `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\B0_common_rules.md` and follow it (worktree `..\temporal-memory-wpC`, branch `wpC`). Then build **WP-C** of `planaudit.md` v2.1 (§0 Rule 9, §1 A4/A5, §4, §6.4 step 6, §8). Your audit (`muse_planaudit.md`) found most of these gaps. Now close them. You own `src/temporal_memory/privacy/` only.

1. **`privacy/sensitive.py`: the canonical gate.** Port `g:\Haitham\VsCode\contest\apps\api\app\lab\sensitive.py` (`categories_hit`, `filter_statement`, `screen`), then:
   - add a `family_third_party` category: a fact whose subject is a person other than the user, carrying health, faith, relationship, money or legal content;
   - add a Dubai allowlist ("Sheikh <Name>", "Golden/Green Visa", "government entity", "Dubai Police" as a provider), using `G:\Haitham\lab-data\memory-bakeoff\harness\gate.py` as a reference;
   - add Arabic word boundaries (`صحي` must not fire inside `بتصحي`; `ضغط شغل` is work pressure, not health);
   - credentials (passwords, OTP codes, Wi-Fi keys) are **always** blocked;
   - export a single `CATEGORIES` list;
   - make `screen()` call a pluggable classifier (`lmstudio` local by default, from config), and **fail closed** when it's unavailable.
2. **`privacy/policy.py`:**
   - `gate_fact(fact, worker_kind)`: layer 1 always; layer 2 for `owner-hook` and `agent-cli` workers and for every `reflect` output.
   - `may_promote(entity, distinct_days, user_confirmed)`: self / user-owned → ≥ 2 distinct days or a confirm; **third-party people → `user_confirmed` only**.
   - Encode the distinction between **first-person logistics the user stated** (allowed, `user_supplied`) and **third-party private matters** (never stored without opt-in).
3. **`privacy/forget.py`:** `forget_source(owner, record_ids)`:
   - bumps `records.generation`;
   - sets `erased_at` on facts whose evidence is **only** those records (facts with other evidence keep it and drop that evidence row);
   - recomputes `entity_subjects`;
   - re-queues affected days;
   - writes a `forget_rules` row so a re-import is blocked.

   **Nothing resurrects** through a queued or late attempt (the validator's generation fence; coordinate through a contract request if you need a hook in WP-A).
4. **Tests** (`tests/test_{privacy,forget}.py`):
   - a gate matrix with ≥ 40 synthetic cases: EN / Egyptian Arabic / Arabizi, Dubai false positives, third-party health/faith/money, first-person logistics, credentials;
   - Forget cases: forget while a job is leased (the late submit is rejected); forget one of two evidence records; re-import of a forgotten source is blocked; `visible_facts` excludes forgotten facts.

   Until WP-A's schema lands, write the DB tests against `db/schema.sql` from the `memory` branch if it's there, or mark them `xfail` with a reason.
