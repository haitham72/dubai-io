# Brief B — Build · Mirsal AI Messenger (Entry 3) · branch `business`

Suggested lead: **Muse** (any of Cursor / Muse / Codex / Antigravity works). Paste everything below the line into the lead agent **only after** (1) the founder has approved `docs/submissions/mirsal/DELIVERY_ROADMAP.md`, (2) **M0** is decided in `mirsal/open-questions.md`, and (3) Gate S has passed and `contest-shared` is merged into `business`.

---

You are the **build lead** for *Mirsal*, our **Best Business AI Agent** entry, on branch **`business`** of `github.com/haitham72/dubai-io` (private). You turn the approved roadmap into a real two-user messenger whose business agents turn chat into approved, tracked work. You use subagents for the slices and merge every slice yourself after its gates pass.

## 0. Preconditions and setup

- Local: `D:\Vscode\dubai-io-business`. Cloud: `git fetch origin && git switch business && git pull --ff-only`.
- **Stop** unless all three conditions above hold. Read the M0 decision and follow only its path:
  - **M0 = reuse** (written rights confirmed): your first slice imports the POC with history: `git subtree add --prefix=apps/mirsal https://github.com/haitham72/Mirsal-redesign master`. Do this once, as its own commit (`mirsal: import POC from Mirsal-redesign@<sha> (M0 reuse, <date>)`). Preserve its approved visuals and working modules; never replace them with a generic WhatsApp skin.
  - **M0 = clean-room:** build a new `apps/mirsal/` with an original design and brand. Agents writing it **must not open** the office-owned parts that `ip-and-baseline.md` lists. Use only the spec and the evidence-cleared material.
  - **M0 = no-go:** stop and report.
- **Never** commit to or push `main`; never force-push; never push to `Mirsal-redesign`. Lane branches are `ms/<slice-id>`, cut from the latest `business`.
- Run the `dubai-io` API suite once before any change and record the pass count in `mirsal/log.md` as your baseline. After an import, also record the POC's own test count.

## 1. Read

Root `CLAUDE.md` · `docs/submissions/CLAUDE.md` (paths §2, gates §4, rules §5) · `shared/founder-inputs/03_MIRSAL_AI_MESSENGER_PLAN.md` (the spec) · `mirsal/DELIVERY_ROADMAP.md`, `IMPLEMENTATION_GAP_MATRIX.md`, `ip-and-baseline.md`, `open-questions.md` (with the founder's answers), `demo-script.md` · `shared/SHARED_MEMORY_CROSS_APP_CONTRACT.md` · `ARCHITECTURE.md` §2, §3, §7, §9, §11 · `apps/api/CLAUDE.md`.

## 2. Hard rules (paste this block into every subagent prompt)

```
- Work only on your lane branch ms/<slice-id>, cut from business. Never touch main. Never push to Mirsal-redesign.
- Write only your slice's files, all inside: apps/mirsal/**, apps/api/app/mirsal/**, apps/api/tests/test_mirsal_*.py,
  apps/api/tests/fixtures/mirsal/**, docs/submissions/mirsal/**. Everything else is read-only: apps/web/** (frozen),
  apps/site/**, apps/memory/**, apps/api/app/communities.py (Community's), apps/api/app/identity/**,
  apps/api/app/memory_bridge/**, PLAN.md, ARCHITECTURE.md, supabase/**, packages/**, docs/submissions/shared/**,
  and every other module in apps/api/app/.
- Messages are chat records, not memories. Memory only through apps/api/app/memory_bridge, with per-conversation
  consent (Off / Session only / Save approved memories); default private. Other people's messages are never facts
  about the user. No group content goes to a model or to memory without the group policy and consent.
- The /agents/memory Redis store is NOT the shared memory: bridge it, never present it as long-term memory.
- Every external effect (sending on the user's behalf, creating a task or calendar event, posting, sharing a file)
  is a registered capability with an approval card listing the exact recipient and payload, plus an idempotency key.
  The LLM proposes; it never sends.
- Seeded chats (src/chats/data.ts) only in an explicit demo mode, labelled Demo data; never presented as the
  two-user test passing.
- No E2EE claim. No WhatsApp unofficial interfaces (manual Export chat only). No Gemini API. Licensed image and
  sticker providers with spending caps; failures are reported honestly.
- No office- or client-owned asset beyond what M0 cleared. No Meta or WhatsApp branding.
- Synthetic fixtures only. Every workflow: a happy-path AND a failure-path test. Keys from env only.
- Report back: files changed, the exact test commands you ran WITH their output, anything left open.
```

## 3. Use subagents

At most 4 lanes in parallel, following `DELIVERY_ROADMAP.md`; parallel slices never share a file. Typical lanes:
- **Chat core:** identity from `apps/api/app/identity`; 1:1 and group chats; persistent messages; receipts; realtime transport; attachments with signed access; reconnect; offline retry; idempotent sends; block and report.
- **Creative and voice on real chats:** sticker picker and Builder hook (`mirsal-builder-io` as an external service), image and video APIs, the voice engine, `@mirsal` skills. Generated assets travel **between two accounts** end to end.
- **Memory:** the bridge from Redis facts to the shared memory, per-conversation consent, cited recall ("What laptop did I mention last week?"), and Forget.
- **Business agents:** Decision Keeper, Action Tracker, Project Brief, Knowledge Assistant, and approval cards into `apps/api/app/mirsal/` (registered capabilities on the Dubai-io action layer).
- **Demo and packaging:** the Stage 2 pilot chain (Summarise → Decision Keeper → draft task → approval → task created → evidence-backed brief, plus the access-denied case), deck, video.

You merge each lane into `business` after **re-running** gates 1–4 (`docs/submissions/CLAUDE.md` §4, with gate 4 = the Mirsal app's own test and build commands) yourself. A subagent's report is not evidence. A lane needs a read-only file changed? Use the shared-change exception (its own `shared(<area>):` commit, a test, `mirsal/shared-changes.md`). If the file is a shared-contract file, send it to the B0 lead on `contest-shared` instead.

## 4. Done means

- The spec's §8 acceptance criteria pass in tests, as far as the roadmap's slices reach. The first is two **real authenticated** users sending, receiving, editing and deleting messages across devices, with the state surviving a restart.
- Gates 1–4 are green in your own run.
- UI slices have a recorded founder visual review of a staged preview.
- The demo script runs end to end three times without a manual fix.
- Packaging for **Fri 18 Dec 2026** is done: deck (10 slides, English), video (≤ 4 min), hosting or tunnel, and the Stage 2 team pilot with consenting participants written up in `mirsal/log.md`, with observed measures, not invented ones.

A partial slice is never "done".

## 5. Final report (to the founder, ≤ 20 lines)

Slices merged with commit hashes · test counts (API vs baseline, Mirsal app) · which of the spec's §8 criteria are green (with test names) · what is `Demo data` or fixture mode on stage · the M0 path taken · shared changes · open risks · what is needed from the founder (keys, provider budget, pilot participants, visual review).
