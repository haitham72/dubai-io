# Dubai-io website (`apps/site`)

Next.js App Router + TypeScript marketing site and signed-in web view.
Plain CSS only — no UI kit, no Tailwind, no shadows. Cyan accent, generous
space, light/dark via `prefers-color-scheme`, `prefers-reduced-motion`
respected.

## Routes

| Route | What it is |
|---|---|
| `/` | Marketing home: hero, feature bands, image bands, CTAs |
| `/privacy` | “What we never do” — the seven hard rules |
| `/demo` | Contest demo walkthrough + image credits |
| `/app` | Signed-in Today: needs-you decisions, running, on-list, news |
| `/app/tasks/[id]` | Task detail + commands (complete / pause / cancel) |
| `/app/decisions/[actionId]` | Decision card: approve-this-revision or reload on 409 |
| `/app/feed`, `/app/feed/[postId]` | Stories, communities, posts, nested replies |
| `/app/chat`, `/app/chat/[id]` | Threads + Calls / Contacts / Keypad / Favorites |
| `/app/services`, `/app/services/[serviceId]` | Fixed-price catalog |
| `/app/ask` | Assistant composer over `POST /api/luna/turn` |
| `/app/map` | On-demand map (needs `NEXT_PUBLIC_MAPS_KEY`) |
| `/app/profile` | “You told me” facts + “I noticed” hypotheses |

All `/app` data comes from the same FastAPI backend (`apps/api`, read-only
from this track) with `credentials: "include"`. Every fetch has loading,
empty and error states; community content is labelled demo/untrusted;
approval precedes any send/share; status renders only from authoritative
events; every number shows provenance.

## Run locally

```bash
cd apps/site
npm install
npm run build   # must stay green
npm run dev     # http://localhost:3000
```

Point at a backend with `NEXT_PUBLIC_API_BASE` (default
`http://localhost:8000`). Start the API from `apps/api` (see root `handoff.md`).

## Photos

Real openly-licensed photos in `public/images/`, credited inline and in
[`public/IMAGE_LICENSES.md`](public/IMAGE_LICENSES.md). No placeholders;
pictured people are not affiliated with Dubai-io.

## Vercel readiness (not yet deployed — no deployment is claimed)

1. Create a Vercel project with root directory `apps/site`.
2. Environment variables:
   - `NEXT_PUBLIC_API_BASE` — public URL of the FastAPI container.
   - `NEXT_PUBLIC_MAPS_KEY` — referrer-restricted Google Maps browser key
     (restricted to the Vercel domain). No other keys belong in the browser;
     all provider keys stay server-side on the API host.
3. Deploy the API as a container (Fly/Railway/Render/Cloud Run) in the same
   region as Supabase, with CORS allowlisting the Vercel domain.
4. Verify: `npm run build` green, then open `/`, `/privacy`, `/demo` and
   each `/app` tab against the deployed API and confirm loading/empty/error
   states with the backend both up and down.
