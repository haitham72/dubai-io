# E0 — Real-data round: the final Dubai-io app on the founder's own data (read by every E task)

**Founder, 24 Nov:** "I need the final app. I need to test mobile / website / desktop on real data. The only test user is my own sign-in. When everything works I sign in with a new Gmail assigned as tester. When everything is OK, then we refine design." **Design polish waits.** Don't restyle screens in this round.

**Decided:**
- **Sign in with Google on the PC** (website or desktop: the localhost redirect works). **The iPhone pairs by scanning a QR code** shown by the PC session. There's no Cloudflare domain yet.
- The founder's Google OAuth client already exists. Its secrets stay in `apps/api/.env` **on the server only**. Never print, log, commit or send them to the phone.

## Round definition of done (the founder runs this)

1. `scripts/dev/start-all.ps1` starts everything on the PC. The health check shows every service green (E1).
2. Sign in with Google on the PC website, then scan the QR with the iPhone (Expo Go). Both show the founder's name; there's no demo user anywhere (E2).
3. Connect Gmail, Calendar and YouTube with consent; optionally upload Takeout / WhatsApp; the desktop app pulls browser history + Claude / Codex sessions. Backfill progress is visible (E3).
4. **Today** shows cards from the founder's real interests with live images and source chips. **Chat** answers from his memory with citations. **Memory** shows his real graph. **Forget** removes data everywhere (E2 + E4).
5. **The founder's tester Gmail already exists and works** (Google Testing mode, 24 Nov). Sign in with it on a second browser profile or device. Its data never shows for the founder, and the reverse (E2 isolation test). More users come later.

## Rules (all E tasks)

- **Branching (D16, monorepo):** branch from `main` (`e<N>/<slug>`), commit only there. **Claude merges into `main`** after verification. Never push `main`.
- **Real personal data never enters the repo.** It lives in the local Postgres, `data/` (gitignored) or `G:\Haitham\lab-data\`. Tests use synthetic fixtures only.
- **Keys stay server-side** and are read from `.env`. The phone and the website hold only a revocable session.
- **Root `CLAUDE.md` rules 1, 2, 6, 8 and 9:**
  - no fake success statuses;
  - provenance + `as_of` on every number;
  - consent per source, default **off**;
  - no proactive messages from LLM polling;
  - "You told me" only for user-stated facts;
  - health, family and faith never inferred.
- **`apps/web` is frozen.** Never touch it.
- **The LLM for extraction and chat** goes through the configured runners: the founder's `claude -p` subscription (Haiku, medium effort), with local Qwen (LM Studio) as an alternative. **No Gemini API calls.** Log the model actually used.
- **Done for each task:** tests (happy + failure path) on the real Postgres, the touched apps' full suites green (only the known `test_ops` / redis env failure allowed), a report at `apps\memory\upgrade\reports\E<N>.md` + a line in `reports\STATUS.md` (in the `G:\Haitham\VsCode\contest-memory` worktree; don't commit reports).
- **Team:**
  - E1 run stack + E4 chat & Today feed: **Gemini**;
  - E2 sign-in, pairing, app wiring: **Gemini** (reassigned 24 Nov: Cursor ran out of quota), after E1, before E4;
  - E3 real data in: **Codex**;
  - Claude verifies and merges.
