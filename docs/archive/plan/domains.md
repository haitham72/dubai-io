# Domain taxonomy — website assistant (29 Oct 2026)

Status: implemented in `apps/site` sidebar (Plan 1 threads). Behaviour target replaces Grok Bot “predetermined bot channels” with **product domains**.

## Rule

- **Domains** = where a conversation/task lives in the left card (website ≈ desktop).
- **Service categories** = 5–15 fixed job types when the user wants something done (laundry, AC, …).
- **Projects** (API workspaces) remain for multi-chat campaigns; domains do not replace them.
- Classification is keyword-based today (`classifyDomain`); the user can later move a thread (UI not yet).
- DEWA / Salik / official portals stay **Household** reminders + links — never government execution.

## Domains

| Id | Label | Typical intents |
|---|---|---|
| `household` | Household | Home, maintenance, hotels, DEWA reminders, schools (KHDA), insurance network |
| `places` | Places & trips | Near me, best places, outings, parking, routes, airport |
| `services` | Services | Catalog jobs (laundry, cleaning, car wash, …) |
| `work` | Work & admin | Email, calendar, meetings, reimbursement, visa paperwork |
| `general` | General | Unclear / small talk until classified |

## Service categories

See `SERVICE_CATEGORIES` in `apps/site/unified/data/domains.ts` (bounded 5–15).

## Website focus

Ship and polish on **`apps/site` website** first (`/` — same React shell as `?desktop`). Device frames and packaging stay later. Native Swift remains stopped until the website assistant is done.
