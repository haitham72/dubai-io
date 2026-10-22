# FOUNDER FEEDBACK 23 Oct (highest priority; supersedes below)

Muse works on **3 branches**, each in its own worktree:
- `redesign-community` (`../dubai-io-rc`): **minimal changes only**, limited to the fixes listed here.
- `dubai-io-web`: the Apple.com-inspired site, full depth, same backend.
- `ios-swift`: the Swift app.

**General:** use real, openly licensed images (Unsplash, Pexels, Wikimedia) for people, food, places and items. No placeholders. Record each image's source and licence.

**Feed:**
- Excellent; keep it.
- Replies must be nested threads like Facebook, not Twitter-style @mentions.
- Fix the story circles: they must be true circles, evenly aligned.

**Chat:**
- Remove the phone icon next to the profile icon; it's confusing.
- Copy the new WhatsApp structure: a Calls screen with search and tabs Calls | Contacts | Keypad | Favorites.
- The mock chat is underwhelming. Spin up a small, low-to-medium effort agent to create 10–15 personas with real photo thumbnails and believable chat histories.
- Use `NARAROUTER_API_KEY` with model `agnes`. Fall back to the models listed in `opencode.json` if a model isn't annotated.

**Communities:**
- Joining a community must carry through to Chat › Communities.
- Create 10–15 communities with deep nested interactions among about 100 users, each with a persona and a thumbnail.
- Topics are what Dubai residents really post, e.g. selling used items, hiring problems, visas, rent, moving, recommendations. Search Reddit (r/dubai, r/UAE) for reference.

**Home news:**
- Match Google News: a full-width thumbnail, then the title, then a subtitle under it.
- The current small thumbnail beside the text is wrong.

**Services:** exactly 3 thumbnails per row, never 1.5. Add more tiles if needed.

---

# UPDATE 23 Oct: two branches, two worktrees (supersedes "Branches" below)

You are **Muse**. Work on two branches at the same time, each in its **own git worktree**. Never switch branches inside the founder's main folder, because another agent is running a server there on `redesign-community`.

```
git fetch origin
git worktree add ../dubai-io-ios ios-swift
git worktree add -b dubai-io-web ../dubai-io-web origin/redesign-community
```

1. **`ios-swift`** in `../dubai-io-ios`: the iPhone app (SwiftUI). Merge `origin/redesign-community` first and at the start of each session.
2. **`dubai-io-web`** in `../dubai-io-web`: the public website in `apps/site` (Next.js on Vercel). Apple.com-level design: this needs a lot of design work.
   - Start with a design system: type scale, colour, spacing, image bands, motion.
   - Then build the hero and feature pages.
   - Then the signed-in `/app`.
   - Merge `origin/redesign-community` regularly.

On both branches: never edit `apps/web`, `apps/api` or `supabase`. Ask for backend changes in `docs/request-backlog.md` → "Native/site requests". Report per branch: commit hash, how it was verified, and what is not verified.

---

# Prompt for the native iOS + website agent (23 Oct 2026)

Paste everything below the line into a new agent session opened at the repository root.

---

You are building the **native iOS app and the public website** for Dubai-io, a personal assistant for everyday life and work in Dubai. Another agent is working on the web prototype and the backend at the same time, so follow the branch rules exactly.

## Read first, in order
1. `CLAUDE.md` (hard rules), then `PLAN.md`, `ARCHITECTURE.md`, `handoff.md`.
2. `docs/references/ios-swift-plan.md`: the top section "Native iOS + website plan — 23 Oct 2026" is your spec. It covers architecture, hosting, screens, API contracts and build order.
3. `design/CLAUDE.md` and the 12 Claude Duet frames in `design/references/claude duet/` (interaction references only).
4. Run the web prototype to see the behaviour you are matching:
   - `cd apps/api && .venv/bin/python -m uvicorn app.main:app --port 8020`, then open `http://127.0.0.1:8020/index.html#home`. Python 3.13 venv; `pip install -r requirements.txt` if needed.
   - Keys go in `apps/api/.env`; never print or commit them.

## Branches
- Work on **`ios-swift`**. First: `git fetch origin && git switch ios-swift && git merge origin/redesign-community`.
  - On conflicts in shared docs, take `redesign-community`'s version and keep the iOS-only files (`apps/ios/**`, `handoff-ios.md`).
  - Push.
- Merge `origin/redesign-community` into `ios-swift` at the start of every session, and whenever the backend contract changes.
- **You own:** `apps/ios/**` and a new `apps/site/**`.
- **Do not edit:** `apps/web/**`, `apps/api/**`, `supabase/**` or the canon docs.
  - If you need a backend change, add a row under "Native/site requests" in `docs/request-backlog.md` on your branch and tell the founder. The web agent implements it on `redesign-community`.
- Commit small, verified slices; push after each.

## What to build
**1. iOS (SwiftUI, iOS 26+, Xcode 26.3 on this Mac; founder's device: iPhone 13 Pro Max).**
- Extend `apps/ios/Core` (typed `APIClient`, models, contract tests) to every endpoint in the plan.
- Then follow the iOS build order in the plan: shell → Home (compact Today, decision/result cards, brief, news) → Feed + story viewer → Chat hub, threads, Contacts → Services + mini-app host → Maps (Google Maps SDK for Places content) → local notification banners.
- Verify each step in Xcode Previews and the Simulator; finish with a physical-device pass.

**2. Website (`apps/site`, Next.js App Router + TypeScript, deployed on Vercel).**
- Apple.com in spirit: big confident type, generous white space, full-bleed image bands, one cyan accent, subtle motion that respects reduced motion, light and dark modes, very fast.
- No UI kit, no shadows.
- Build marketing pages first (Home, Privacy "what we never do", Demo), then a signed-in `/app` with parity to the web prototype, using the same API.
- Env: `NEXT_PUBLIC_API_BASE`, `NEXT_PUBLIC_MAPS_KEY` (referrer-restricted).

## Non-negotiables (from `CLAUDE.md`)
- Never show Confirmed/Paid/Delivered without an authoritative event.
- Approval card before any send or share.
- Every number has provenance.
- Seeded data shows a **Demo** label.
- No government execution and no DubaiNow look.
- No payments.
- Community content is untrusted.
- Keys stay server-side; only the restricted Maps keys reach clients.

## Hosting decision you build against
- Supabase = Postgres, Auth (Sign in with Apple + email) and Storage.
- The Python FastAPI + LangGraph API stays in Python and is deployed as a container (Fly.io, Railway, Render or Cloud Run), not rewritten as Edge Functions.
- Vercel hosts the website.
- Both clients call the same API.

## Report back
After each slice: what you built, how you verified it (Previews, Simulator, device, `xcodebuild`/`npm run build` output), what is not verified, and the commit hash.
