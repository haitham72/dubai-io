# Service intake guide

**Read this whenever the user adds an idea, a service or a reference image.** Any AI working in this repo files new ideas the same way. That keeps [`cases.md`](cases.md) the single menu and `PLAN.md` free of cases. `CLAUDE.md` points here.

**Default outcome is a registry row, not a case.** Filed cases are about 1% of the app; the generic engine (registry + patterns + Services surface + profiler) must cover everything else. Write a full case only when the idea needs a new pattern, a new rule, a new data source, or is a demo moment. Otherwise do steps 1–4 and 5b, then report "Covered by the engine as a registry row `<id>`".

## 1. Capture

- Note the user's words verbatim, plus any file paths.
- Never move, rename or delete the founder's files.
- If a ref was dropped loose, propose its folder and ask.

## 2. Classify

- **Group:**
  - `shops/` = the user buys an item (cloth, coffee, groceries, restaurants).
  - `service/` = someone does something for the user (maid, barber, laundry, pets, fix-it, runner).
  - Neither → propose a new group and **ask** (`companion/` and `platform/` are proposed, not yet confirmed).
- **Category:** one folder per category (`service/pets/`). Create it only when the case is picked.
- **Existing case?** Extend it (new step, new variant) rather than duplicate it.
- **Spans several categories?** It's a **bundle**: a new case that lists its component cases as lanes, with one shared deadline/route.

## 3. Clarity check

If any of these is unknown, ask before filing (≤ 3 questions in one go, with options where possible):
- the user's ask line ("I need …")
- what is sold or done
- who confirms (which merchant/provider event)
- what data leaves the phone (photo, address, household or pet facts)

If all are known or have an obvious default, file it and list the assumptions in the entry.

## 4. Rule screen

Stop and tell the user if the idea needs any of:
- a quote, bid or price negotiation
- a government submission or payment
- a status shown without a provider event (including "Verified")
- a real brand on screen
- AI advice in a safety-critical domain (medical, legal), which stays display + handoff only
- inferring a sensitive trait (health, religion, ethnicity, nationality-as-trait, gender, sexuality, politics)

Otherwise note which rules the case touches.

## 5. Compose

- Build the steps from the **pattern library** in `cases.md`. A new pattern gets a name and a one-line definition there.
- If the idea needs a new backend capability (endpoint, provider API, model), mark the case **needs plan change**. That is the only path by which an idea reaches `PLAN.md`, and only after the founder agrees.

## 5b. Registry row

If the idea is a new category or subcategory, add a row to the category registry (`demo/lab/fixtures/categories.json`; later the `registry` module). It then appears on the Services surface with no code change.

## 6. Write the entry

Add it to `cases.md` (index row + section) with the template:
- ID (next free C-number) · status `idea` · refs path · scene `?scene=<id>` · patterns
- ask · steps table · money `(demo)`
- media slots (stock source / WaveSpeed prompt)
- **profile: reads / teaches**
- checks · open questions · review-log row

## 7. Report back in one line

"Filed C14 <name> under `service/<category>/`; patterns …; N open questions."
Then offer to put it in the pick queue.
