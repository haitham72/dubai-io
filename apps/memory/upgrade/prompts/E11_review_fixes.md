# E11: Fixes from the overnight reviews (Part A: Codex · Part B: Devin)

Read `E0_real_data_round.md` first. Every item comes from `reports/MORNING.md` §E and the review file named next to it. Each fix ships with a happy-path test and a failure-path test. Do not touch `apps/web`, which is frozen.

- **Concurrent work:** Gemini is building E10 (the topic tree) at the same time. It owns `core/retrieval.py`, `core/subject_aliases.py`, `core/extract.py`, and the new-terms code in `core/applier.py`. Don't edit those, except where an item below names them.
- **Before ready-for-review:** rebase on `main` if E10 has already merged.
- **Status:** add a line to `reports/STATUS.md` when the work is `ready-for-review`.

---

## Part A: Codex (branch `e11a/temporal-fixes` from `main`)

### A1. The end-cue fallback ends facts it shouldn't (§E #5; `E9b.review.md` (b))

- **The bug:** the `_END_CUE` fallback in `core/validator.py` turns "Omar quit" and "not cancelled" into an `ended` fact.
- **The fix:**
  - The fallback may end only the user's own events.
  - Skip it when the cue's subject is a named other person.
  - Skip it when the cue is negated. Cover English (not, never, wasn't, didn't), Egyptian and Gulf Arabic (مش, ما, لم, لن) and Arabizi (msh, mesh).
- **Tests:**
  - "my gym membership got cancelled" → ended;
  - "Omar quit his job" → not ended;
  - "the class was not cancelled" → not ended;
  - "الكلاس ما اتلغاش" → not ended.

### A2. The late superseder can demote a separate event (§E #20; `E9b.review.md` (b))

- **The bug:** the condition in `core/applier.py` `_late_superseder` is "both texts carry a number and share 2 words". So two separate trips on one subject, ingested out of order, can demote the older one.
- **The fix:** demote only when the two facts describe **the same thing changing value**, for example the same booking's time or the same item's price. Separate events stay current. Edit only `_late_superseder` and its helpers in `applier.py`; E10 adds code to the same file.
- **Tests:**
  - Dubai→Cairo in March and Dubai→Cairo in June, ingested June first → both stay current;
  - "class moved to 7pm", ingested after "class at 6pm" → the 6pm fact is demoted.
- **Acceptance:** rerun S2. Today's numbers are superseded 7/8, ended 5/5 and late 3/4, and none may drop. Report each one.

**Report** → `reports/E11a.md`

---

## Part B: Devin (branch `e11b/review-fixes` from `main`; open a PR into `main`)

### B1. Lazy embedding of older facts (§E #7; `E9b.review.md` (e))

In `ensure_embeddings` (the embeddings module of `apps/memory`; not `retrieval.py`):

1. **Keep going until done:**
   - Continue across calls until every live fact is embedded.
   - Mark a `facts_version` done only when nothing is left.
   - Use a time budget for each call instead of the fixed 64 newest facts.
2. **Load the model off the request path:**
   - Never load or download the model inside a user request. Use E9d's warmup.
   - Until the model is ready, the query honestly returns `embedder_unavailable`.
3. **Cache a failed load with a backoff**, so offline queries don't retry the 570 MB download on every call.

**Tests:**

- 150 unembedded facts → all are embedded after N calls, and the version is marked done only at the end;
- a failed model load → one attempt per backoff window, and queries still answer through the word channel.

### B2. Pairing issues the session before consuming the code (§E #22; `E5.review.md`)

- **The fix:** in `apps/api` identity pairing, consume the code and issue the session in one transaction, with the consume first.
- **Test:** a failed consume leaves no session row.

### B3. The agent-CLI classifier treats an item with a number but no category as "none" (§E #21; `E1b.review.md`)

- **The fix:** such an item goes to screening; it is not treated as clear.
- **Tests:** one test for each path.

### B4. The Messenger memory UI has no click-through test (§E #9; `E5b.md`)

- **The test:** add a browser click-through test for the approval card.
  - It renders with the exact fields that would be shared.
  - Approve sends; Cancel sends nothing.
- **Use:** `apps/messenger`'s existing test runner.

### B5. Desktop `DUBAI_APP_URL` accepts any URL without a warning (§E #10; `E9a.review.md`)

- **The fix:** when the URL is not localhost, a LAN address or https, the desktop app shows a visible warning and logs one line.
- **Tests:** one test for each path.

### B6. `stop-all` can't tell if a recorded PID was reused (§E #11; `E1.review.md`)

- **The fix:** before stopping a recorded PID, check that its process name, and its start time where available, still match what `start-all` recorded. If they don't match, skip it and say so.

**Report** → `reports/E11b.md`, with test counts for `apps/memory`, `apps/api`, `apps/messenger` and `apps/desktop`.

---

## Not in E11 (waiting for founder decisions)

- §E #6 (forgetting a fact keeps the source email's text) no longer applies under D18: the founder allows only lower weights, not forget. Whether to remove the existing Forget feature is a separate founder decision and is not in E11.
- §E #8: Community saved discussions and public posts share one consent flag.
