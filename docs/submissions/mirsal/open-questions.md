# Mirsal — founder questions

**Status:** planned — awaiting founder approval (23 Nov 2026, Cursor).  
P2 cross-checks this list. Mirsal code does not start until these five are answered and Gate S has passed.

## Blocking

### 1. M0 — reuse, clean-room, or no-go

**Recommendation: clean-room.**  
The POC at `6b45ba4` has no project licence. Concept sheets are “supplied”. Diwan pictures are “supplied by Haitham” and `ARCHITECTURE.md` says a separate project, formerly Diwan Hamdan, already holds them. Personal git emails (`ihisam@outlook.com`, `system722@gmail.com`) do not settle title. Nothing in the README or the commit messages says the work was made for an employer, so this is not a no-go on the evidence we have.

**Blocks:** every code slice (`MS-B2` onward), the subtree import, and any use of the logo, screens, or slides.  
**Deadline:** the P2 founder gate, before Gate S is treated as permission to start Mirsal. Package target is Fri 18 Dec 2026.

Written confirmations that would flip this to reuse are listed in `ip-and-baseline.md`.

### 2. Updates tray

The spec (§0, §3) says: keep the compact Mirsal Updates tray, and do not reflow chat when it opens. Master does the other thing. `openUpdates()` sets `screen: "ai"` (`src/store.ts:147-148`), and the desktop row (`src/updates/index.tsx`) calls it. Commit `6b45ba4` is titled “Mirsal AI workspace replaces Updates tray”.

**Recommendation:** under clean-room, follow the spec. Chat stays mounted. AI is a compact surface on top of it. Under reuse, keep master’s workspace only if you explicitly override those two spec sentences.  
**Blocks:** the first UI slice.  
**Deadline:** same gate as M0. A reuse decision without this answer leaves the layout unspecified.

### 3. Messaging boundary with Community

`communities.py` already has `chat_threads`, `chat_messages`, `chat_reads`, `chat_archived`, and `contacts`, each scoped by `owner`. The module’s own comments say demo groups have no other real members. The Community spec says the Inbox is a placeholder or a minimal DM, and that two full messaging stacks should not be built. That file is owned by `societal`. This branch does not edit it.

**Recommendation:** Mirsal owns 1:1 and small-group person-to-person messaging. Community Inbox stays the placeholder it is. When Mirsal transport and B0 identity exist, Community may deep-link “Open in Mirsal”. That is a route, not a second write into `chat_threads`.  
**Blocks:** the P2 shared contract, and both teams’ chat designs.  
**Deadline:** P2, before either team creates another message table.

### 4. Transport

The spec allows Supabase Realtime plus Postgres RLS, or a justified WebSocket service. Schema `dubaiio` is revoked from `anon`, `authenticated`, and `service_role` (`supabase/migrations/20261021000100_backend.sql`). The live session is an anonymous cookie. Browser Realtime would need a grant that schema does not have, and a JWT that B0 has not built.

**Recommendation:** a cookie-authenticated FastAPI WebSocket. The durable store is `ms_*` tables in `dubaiio`, created with `CREATE TABLE IF NOT EXISTS` from Mirsal code (the `tasks.py` pattern). RLS SQL lives in `apps/mirsal/supabase/` and is not added to `supabase/migrations/` until the mains merge. Until that SQL is applied, the fence is the API membership check, and the docs must not call RLS live.  
**Blocks:** `MS-B2`.  
**Deadline:** P2, so the shared contract does not assume browser Realtime.

### 5. The name and the logo

Clean-room covers code and assets. The word Mirsal is already the spec’s name, and the orb logo is a file in the POC (`public/mirsal-logo.png`, commit `fb13b2fa`) with no assignment.

**Recommendation:** use the name Mirsal as the working title only if you confirm in writing that the name is yours (item 4 in `ip-and-baseline.md`). Do not ship the orb, the concept sheets, or the Diwan pictures in the entry until that same writing covers them. If the name is not yours, the deck uses a placeholder and the folder stays `apps/mirsal/` as the repo path already chosen.  
**Blocks:** the deck, the video, and any chrome that draws a logo.  
**Deadline:** before `MS-B7` (packaging). Earlier is better, because slide 1 will otherwise hedge the name.

## Not blocking

- Group size cap of 8. Change it when the first pilot needs a different number.
- Phone overlay versus desktop workspace. The spec rule (chat stays put) covers both once question 2 is answered.
- Photo-window, typecheck, Vite build, and the retired `server/` tests were not rerun. They do not gate M0.
- README totals 169 and 10, and the voice counts 113 and 32, are stale. The rerun number is 200 passed, 1 Redis skip.
- Voice and video calling stays P1. The business demo does not use it.
- Stage 1 (family and friends) is a usability test. It is not a business-user claim, and family content is not inferred into memory (rule 9).
- `workspace.task.create` is proposed in `demo-script.md` and is not in `CAPABILITIES` today. Registering it is build work on `MS-B5`, through `apps/api/app/mirsal/`, not a second approval policy.
