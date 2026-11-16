# Desktop full load — long-horizon Dubai-io (29 Oct)

**Goal:** Website (`apps/site` `/`) looks fully loaded against Higgsfield **desktop** frames `l01–l10`. Ignore phone. Behaviour: Grok Bot task threads + Claude Duet decisions + Dots-style continuity.

**Refs:** `design/references/v3-higgsfield/desktop/` + INDEX in `design/29-10-2026/`.

## Fixture / DB truth (checked 29 Oct)

| Layer | Status |
|---|---|
| JSON fixtures | **Done:** 100 personas, 15 communities, 125 posts, 2717 comments, 15 chat personas, 15 threads, 180 messages under `apps/api/app/fixtures/` |
| Supabase `dubai-io` Postgres | **Not loaded:** community tables missing (`dubaiio.personas` etc. do not exist). Migrations exist (`20261023000200_communities.sql`, `…00300_social_personas.sql`, …) but were **not applied** |
| Runtime seed | API `ActionStore` seeds from fixtures on first community/chat request into whatever DB it uses |

**Actions:** apply community migrations → start API → hit `/api/communities` + `/api/chats` + `/api/feed` so rows exist → wire site screens.

## Desktop screen map → work

| Ref | Screen | Implementation |
|---|---|---|
| l02 | Assistant home | Enrich demo tasks + status strip “N moving · N need you”; category pills |
| l04/l07 | Thread + approval | Keep decision card; show Demo; long-horizon check-back copy |
| l10 | Taxi recovery | Thread UI already; ensure demo task opens rich view |
| l03 | Services | New Services screen (grid + Your requests) |
| l01/l05/l08/l09 | Community | Feed + post detail + private handoff panel |
| — | Chats | WhatsApp-style list from `/api/chats` |
| l06 | Me | You told me / I noticed from session memory |

## Non-goals this pass

Phone frames, Capacitor, Swift, Graphite polish, real Gmail OAuth send, government execution.

## Order

1. DB migrations + seed verify  
2. Services + Community + Chats + Me in `apps/site`  
3. Home polish to l02  
4. Run site+API, screenshot check vs refs  
