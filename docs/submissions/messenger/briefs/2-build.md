# Brief B — Build · the Messenger (Entry 3) · branch `business`

Suggested lead: **Cursor** (it planned this entry). Paste everything below the line **only after**:
1. the founder has approved `docs/submissions/messenger/DELIVERY_ROADMAP.md`, and
2. the founder has confirmed the M0 keep/exclude table in `ip-and-baseline.md`.

Slices that need shared identity or memory also wait for Gate S (B0 merged into `business`).

---

You are the **build lead** for *the Messenger*, our **Best Business AI Agent** entry: the WhatsApp-like AI messenger whose business agents turn team chat into approved, tracked work. It lives on branch **`business`** of `github.com/haitham72/dubai-io` (private). You build the approved roadmap with subagents and merge every slice yourself after its gates pass. "Messenger" is a working name until the founder picks one (O2).

## 0. Preconditions and setup

- Local: `D:\Vscode\dubai-io-business`. Cloud: `git fetch origin && git switch business && git pull --ff-only`.
- **Stop** unless `DELIVERY_ROADMAP.md` reads `approved — <date>` and `ip-and-baseline.md` records the founder's confirmation of the M0 table. Also stop if `open-questions.md` still has an unanswered question marked as blocking your next slice.
- **The first slice is the rebranded snapshot import:**
  ```
  git subtree add --prefix=apps/messenger https://github.com/haitham72/Mirsal-redesign master --squash
  ```
  1. Commit it as `messenger: import founder-authored redesign snapshot @<sha> (M0, <date>)`.
  2. In the same slice, **remove every item the M0 table marks `exclude`**.
  3. Then run the **rebrand** slice: identifiers, packages, routes, `@`-skills, strings and assets.
  4. Gate: `git grep -n -i -e "m[i]rsal" -- apps/messenger apps/api/app/messenger` prints nothing.
- **Never** commit to or push `main`; never force-push; never push to the redesign repo. Lane branches are `mg/<slice-id>`, cut from the latest `business`.
- Record two baselines in `messenger/log.md`: the Dubai-io API suite pass count before any change, and the imported app's own test count after the import.

## 1. Read

1. `docs/submissions/shared/founder-decisions.md` (D1–D15) · root `CLAUDE.md` · `docs/submissions/CLAUDE.md` (zero-conflict rule, paths §2, gates §4 incl. gate 5, rules §5)
2. The spec since D15: `messenger/DELIVERY_ROADMAP.md` and `IMPLEMENTATION_GAP_MATRIX.md`, read through D1–D15 (the founder's starting plan was removed)
3. `ip-and-baseline.md`, `open-questions.md`, `demo-script.md`
4. `shared/SHARED_MEMORY_CROSS_APP_CONTRACT.md` · `ARCHITECTURE.md` §2, §3, §7, §9, §11 · `apps/api/CLAUDE.md`

## 2. Hard rules (paste this block into every subagent prompt)

```
- Work only on your lane branch mg/<slice-id>, cut from business. Never touch main. Never push to the redesign repo.
- ADD files only, inside: apps/messenger/**, apps/api/app/messenger/**, apps/api/tests/test_messenger_*.py,
  apps/api/tests/fixtures/messenger/**, docs/submissions/messenger/**. Never edit an existing file anywhere else:
  Dubai-io's iOS, desktop and memory work (branches memory, ios, desktop) edits the same repo, and any edit risks a merge conflict. Read-only
  includes apps/web/**, apps/site/**, apps/memory/**, every existing module in apps/api/app/, PLAN.md,
  ARCHITECTURE.md, supabase/**, packages/**, docs/submissions/shared/**, apps/api/app/identity/**, apps/api/app/memory_bridge/**.
  Settings come from env, read inside your own package.
- The product's old name is retired: never in UI, identifiers, packages, routes, skills, strings, deck or video.
  No office-origin asset (anything marked exclude in the M0 table). Never run, call, copy or integrate the sticker
  Builder service: built-in emoji and sticker packs are finished files the founder supplies. User stickers are
  image + background removal only. No AI image or sticker generation.
- Messages are chat records, not memories. Memory only through apps/api/app/memory_bridge (a client of the
  temporal_note engine; never Hindsight, Honcho or the Redis /agents/memory store as long-term memory), with
  per-conversation consent (Off / Session only / Save approved memories), default private. Other people's
  messages are never facts about the user; no group content goes to a model or to memory without group policy and consent.
- Every external effect (a send on the user's behalf, a task or calendar event, a post, a shared file) is a registered
  capability with an approval card listing the exact recipient and payload, plus an idempotency key. The LLM
  proposes; it never sends.
- Seeded chats only in an explicit demo mode, labelled Demo data; never presented as the two-user test passing.
- No E2EE claim. WhatsApp only by manual Export chat. No Gemini API. Background removal runs on a licence-checked
  model, locally where possible, with honest failures. No Meta or WhatsApp branding.
- Synthetic fixtures only. Every workflow: a happy-path AND a failure-path test. Keys from env only.
- Report back: files changed, the exact test commands you ran WITH their output, anything left open.
```

## 3. Use subagents

At most 4 lanes in parallel, following `DELIVERY_ROADMAP.md`; parallel slices never share a file. Typical lanes:
- **Import and rebrand** (first, alone)
- **Chat core:** two real authenticated users, persistent 1:1 and group messages, receipts, realtime transport (per the P2 decision), attachments with signed access, reconnect, offline retry, idempotent sends, block and report
- **Stickers, media and voice on real chats:** the founder-supplied packs; user stickers from an image + background removal (D7, no AI generation); the voice engine; contextual skills; stickers and media travel between two accounts end to end
- **Memory** via the bridge: consent, cited recall, Forget
- **Business agents:** Decision Keeper, Action Tracker, Project Brief, Knowledge Assistant, and approval cards, registered from `apps/api/app/messenger/`
- **Demo and packaging:** the Stage 2 pilot chain (Summarise → Decision Keeper → draft task → approval → task created → evidence-backed brief, plus the access-denied case), deck, video

You merge each lane into `business` after **re-running** gates 1–5 (`docs/submissions/CLAUDE.md` §4; gate 4 is the Messenger app's own test and build commands) plus the old-name grep yourself. A subagent's report is not evidence. If something truly needs an existing file changed, stop and put it in `open-questions.md`; only the founder can allow it.

## 4. Done means

- The spec's §8 acceptance criteria pass in tests, as far as the roadmap reaches. The first is two **real authenticated** users sending, receiving, editing and deleting messages across devices, with the state surviving a restart.
- Gates 1–5 and the old-name grep are green in your own run.
- UI slices have a recorded founder visual review of a staged preview.
- The demo script runs end to end three times without a manual fix.
- Packaging for **Fri 18 Dec 2026** is done: deck (10 slides, English, new name), video (≤ 4 min), hosting or tunnel, and the Stage 2 team pilot with consenting participants written up in `messenger/log.md`, with observed measures only.

A partial slice is never "done".

## 5. Final report (to the founder, ≤ 20 lines)

Slices merged with commit hashes · test counts (API vs baseline, Messenger app) · which spec §8 criteria are green (test names) · the old-name grep result · what is `Demo data` on stage · open risks · what is needed from the founder (the name, keys, provider budget, pilot participants, visual review).
