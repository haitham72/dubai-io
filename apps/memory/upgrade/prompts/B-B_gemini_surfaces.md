# B-B — Gemini: instant context · Vault/Quests APIs · md export · weekly reflect · ops

Paste below the line into **Gemini**.

---

Read `G:\Haitham\VsCode\contest-memory\apps\memory\upgrade\prompts\B0_common_rules.md` and follow it (worktree `..\temporal-memory-wpB`, branch `wpB`). Then build **WP-B** of `planaudit.md` v2.1 (§3.1, §3.3, §5, §8, §12). WP-A (the store) is being built in parallel. Code against the `GraphStore` protocol in `models.py`, and test with an in-memory fake store seeded from a gold slice. You own `live/`, `api/vault.py`, `api/export_md.py`, `api/ops.py` and `reflect.py`.

1. **`live/context.py`:** `context_pack(owner, text)` with **no LLM**.
   - Port `fold` from `contest/apps/api/app/lab/circle.py:22-31`.
   - A whole-word alias index for EN/AR/Arabizi, cached per owner and invalidated on alias change. Port from `C:\Users\h.ibrahim\Documents\Claude\Projects\temporal_note\mcp_server\memory_tools.py:67,120`.
   - Colliding aliases resolve by co-occurring entities and recency.
   - Dates + AED regex (port `_extract_date:464`).
   - FTS over `text` + `text_orig` scoped to the matched entities/subjects, then global, with RRF (port from `contest/apps/api/app/lab/searchlib.py:73`; tokens use `fold`).
   - Pack ≤ 1.5k tokens: entity cards with roles per subject, top dated facts, open changes. Return the matched entities and candidate names.
   - **Test p95 < 150 ms on 5k synthetic facts.**
2. **`api/vault.py`:** FastAPI router under `/v1/owners/{owner}/`: `vault/subjects` (tree + counts per theme), `vault/people` (people/places + relations + closeness tier), `quests` (goal subjects + milestones), `timeline`, `why/{fact_id}` (evidence records, date, job, model or "your Claude"). Auth via the WP-A token dependency: an owner-device token can only read its own owner. Every value carries `provenance` + `as_of`. Demo/fixture data carries `"demo_data": true`.
3. **`api/export_md.py`:** `render(owner)` → the exact tree in planaudit §3.1 (port `G:\Haitham\lab-data\memory-bakeoff\weekbench\export.py`). People files include role per subject, closeness tier, aliases and evidence limits. Changes render as "was … until <date>". `held-back.md` holds counts only. Add a zip endpoint.
4. **`reflect.py`:** `reflect_week` (port `G:\Haitham\lab-data\memory-bakeoff\weekbench\reflect.py`), using the WP-A extract runner interface.
   - Writes USER.md claims and goal/milestone **hypotheses only** (`facts.status='hypothesis'`, surfaced via the `hypotheses` view with Confirm / Not true).
   - Claims need ≥ 2 distinct days of evidence. Trivia (sign-ups, OTP, subscriptions, deliveries) never becomes a milestone. Rule 9 categories are never inferred.
5. **`api/ops.py`:** `GET /v1/ops/memory` (admin token): queue depth by priority, oldest job age, workers online by model, attempts by verdict **per model**, cost per owner per week, **demo cost saved** (owner-hook + agent-cli tokens × the cloud rate).

**Tests** (`tests/test_{live,vault,export,reflect}.py`), happy path plus failures:
- Arabizi alias, two "Omar"s, an Arabic query with no Latin entity;
- a forgotten fact is absent from every surface;
- a single-day claim is rejected; a trivia item is not a milestone; a sensitive subject is never inferred;
- an owner token reading another owner is a 403.
