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
