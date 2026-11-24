# B-C2 — Muse: two privacy-gate fixes found in integration

Paste below the line into **Muse**.

---

Your WP-C is merged into the `temporal-memory` integration branch `memory`. Thank you. Integration found two gate errors. Fix them on a new branch from `memory` in your worktree:

```powershell
cd G:\Haitham\VsCode\temporal-memory-wpC
git fetch; git switch -c wpC2 memory
```

Rules as before (`prompts/B0_common_rules.md`); only `src/temporal_memory/privacy/` and `tests/test_privacy.py`.

1. **Credentials leak unless the literal word "password" appears.** All of these currently return `None` from `filter_statement` and must return `credential`:
   - `wifi: BarshaL0bby!2026`
   - `Wi-Fi key for the flat is BarshaL0bby!2026`
   - `Your verification code is 482913`
   - `الباسورد بتاع الواي فاي BarshaL0bby!2026`

   Cover Wi-Fi/wifi/WLAN + key/pass/password, `verification|security|one-time|login|OTP code` + 4–8 digits, Arabic `باسورد|الباسورد|رمز التحقق|كود التفعيل|كلمة السر`, and a guarded heuristic for a secret-looking token (≥ 8 chars mixing upper, lower, digit and symbol) right after `:` / `is` / `هو`. Add all of these to the matrix, plus 3 negatives (e.g. "the Wi-Fi was slow", "code review on Thursday", "flight code EK 384").
2. **"wedding" is wrongly in `gender_sexuality`.** The founder's ruling (23 Nov):
   - **weddings and engagements are social events**, so they're allowed: "best man at Omar's wedding", "Omar is getting engaged", `خطوبة`, `فرح`;
   - **still blocked:** sexuality and gender terms, and a **third party's** dating, divorce or affair (`divorce`, `طلاق` about another person, "X is dating Y", "X cheated");
   - the user's own first-person relationship logistics they stated themselves follow the existing first-person rule.

   Remove `wedding`, `marriage`, `جواز` and `خطوبة` from the hard `gender_sexuality` regex, and route third-party relationship cases through `family_third_party`.

**Done when** `python -m pytest -q` passes on your branch, **including `tests/test_reflect.py::test_reflect_week_enforces_two_days_trivia_and_rule9`** (it currently fails on `main` only because of fix 2). Commit, then report the branch name and test counts.
