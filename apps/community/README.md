# Dubai-io Community — web preview (CM-B10)

Staged preview for founder visual review. Not marked done until the founder approves it visually.

## Run

```powershell
npm install
npm run dev   # http://localhost:3060
npm test
npm run build
```

## Notes

- API base: `NEXT_PUBLIC_CM_API` (default `http://localhost:8060`), see `.env.example`.
- Feed / Communities / Create / Inbox / Profile. Inbox shows notifications only; there is no message composer — "Message" shows the hand-off note "Messaging lives in the Messenger app".
- Seeded preview content is labelled with a `Demo data` pill. When the API is unavailable, pages show an honest notice and keep drafts rather than faking success.
- Light mode only, no shadows, warm-white canvas (`#FFFFFF` / `#FAF8F5`) with sparing gold accents (`#C5A059` / `#D4AF37`).
- Connected Memory toggles on Profile are UI-only in this preview; nothing is saved from them.
- Playwright is not included in this slice (not already available cheaply); Vitest covers PostCard, DemoPill and lane filtering.
