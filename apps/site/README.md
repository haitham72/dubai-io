# Dubai-io app & website (`apps/site`)

Next.js App Router + TypeScript client for Dubai-io. **UI work is paused since 9 Nov 2026** while the headless Know / Notice / Do pipeline is built in `apps/api/app/lab/`. Plain CSS only — no UI kit, no Tailwind, no shadows; `prefers-reduced-motion` respected.

## 1. Unified App (`apps/site/unified/`, mounted at `/` via `app/page.tsx`)

The single React codebase for website (`/`), macOS desktop frame (`/?desktop`), and iPhone frame (`/?devices` with an **Original ⇄ New** toggle embedding the frozen `apps/web` mobile PWA reference).

Surfaces under `unified/`:
- `assistant/`, `tasks/`, `chats/`, `community/` (**parked 9 Nov**), `services/`, `maps/`, `dashboard/`, `me/`, `onboarding/`, `shell/`, `mobile/`, `ui/` (plus `data/` fixtures).

## 2. Pre-unified / Funnel Routes (`apps/site/app/`)

- `/about` — product overview
- `/privacy` — privacy rules ("What we never do")
- `/demo` — contest demo walkthrough
- `/signup`, `/setup`, `/first-win` — onboarding funnel
- `/dashboard` — dashboard view
- `/app/*` — signed-in Today, tasks, decisions, feed, chat, services, ask, map, and profile routes

API calls proxy same-origin through `next.config.ts` (`/api/:path*` → `DUBAIIO_API_ORIGIN`) so the anonymous session cookie stays on the site's origin.

## 3. Run & Test

```bash
cd apps/site
npm install
npm run dev    # http://localhost:3000 (proxies API via DUBAIIO_API_ORIGIN, default http://127.0.0.1:8030)
npm test       # Vitest unit tests
npm run e2e    # Playwright end-to-end suite (builds and serves on :3041)
```

Start the FastAPI backend from `apps/api` before testing live API routes (`docs/status.md`). Public photos and credits live in `public/images/` and [`public/IMAGE_LICENSES.md`](public/IMAGE_LICENSES.md).
