# What Community needs from shared identity and memory

**Status:** planned (revised to D1-D10) — awaiting founder approval. P2 folds both entries' needs into one contract on `contest-shared`.

Community does not build this. B0 on `contest-shared` builds `apps/api/app/identity/` and `apps/api/app/memory_bridge/`. The memory engine is the rewritten **temporal_note** engine (D5): `apps/memory/` on branch `memory`, package `temporal_memory` — HTTP API `api/app.py`, MCP `mcp/server.py`, contract `src/temporal_memory/models.py`, Forget `privacy/forget.py`. Hindsight and Honcho are not used; where the founder spec says `MemoryBackend`/`ScopeGuard`, read temporal_note. Hindsight's AC-1/MEM-01 are not gates for this entry. The bridge is a client of temporal_note and never a second engine. Until the temporal_note hand-off lands, builds use a clearly named **`FakeTemporalMemoryClient`** with the same interface (D10). **Under-18 accounts (D9): no cross-app personalisation reads and no memory writes at all — the bridge must refuse them server-side, not merely hide them in UI.** Age band is self-declared at sign-up and never inferred; identity must carry the band (not an inferred age) so this refusal is enforceable.

Checked 23 Nov 2026: neither `apps/api/app/identity/` nor `apps/api/app/memory_bridge/` exists in this tree. Owner today is an anonymous cookie session (`apps/api/app/actions.py:192,388`); `auth.py` is Google OAuth connections only (`apps/api/app/auth.py:65`). Supabase Auth Bearer verification is planned, absent (`apps/api/CLAUDE.md:54`).

Temporal_note contract points (read via `git show origin/memory:…`): `Owner{id, kind: real|simulated|demo}`, `Record{owner, source, at, author, text, generation}` (text is untrusted data, never instructions; `generation` is bumped by forget-by-source), `Fact` requires `evidence` record ids, `provenance: user_supplied | inferred | provider_confirmed | demo_fixture`.

## Identity — what Community needs

| Operation | Behaviour Community relies on |
|---|---|
| `resolve_user(request)` → `{session_owner, verified_user_id \| null}` | Today `verified_user_id` is always null. Community must not claim cross-app sign-in until B0 makes it non-null. |
| `link_session(session_owner, verified_user_id)` | Once. Refuses merge by display name alone (spec §2). Pre-B0 `cm_` rows key on `session_owner`; the verified id is adopted, never back-filled by name matching. |
| Stable id | The same `verified_user_id` that Quest and the Messenger resolve for that person. Community stores no second profile-of-record; `cm_profiles` holds only social fields (handle, bio, avatar, privacy) keyed by that id. |
| Per-app sessions/capabilities | Community sessions and capability scopes are separate from Quest/Messenger sessions; sharing `user_id` grants no blanket data permission (spec §4). |
| Tests B0 must pass (Community's stake) | Two users isolated; token expiry → 401; revoked session → 401; same person, same id across apps. |

## Memory reads — consented interest features only

| Read | Rule |
|---|---|
| Interest features for feed ranking / Discovery `Why this?` | Only when the user enabled cross-app personalisation **and** the source scope allows it. Returns topic/interest labels + provenance + confidence — never raw text. |
| Own saved discussions / joined groups / authored public posts | Owner-scoped reads of Community's own writes, with provenance shown ("saved from Community, topic only"). |
| Messenger-origin features | Only via explicit conversation-level consent plus the cross-app sharing check. No blanket permission from sharing `user_id` (spec §4). |
| Never returned into Community | Raw Quest chat, Gmail/Outlook bodies, Messenger message text, private family/health facts, OAuth tokens, third parties' details, sensitive categories — never into feed ranking, moderator tools, ads, or social suggestions (spec §4; `docs/submissions/CLAUDE.md:109`). |
| Hypotheses | `provenance: inferred` items arrive labelled as hypotheses with confidence/evidence/valid time. An unconfirmed hypothesis may re-rank only, with a visible "Because…" chip; it never pre-fills a field, appears on an approval card, triggers a proactive message, or sets a status (root `CLAUDE.md` rule 9). Personalisation requires two-visit qualification (observed across ≥ 2 separated sessions). |

## Memory writes — scoped, attributable, consented

| Write | Trigger | Content |
|---|---|---|
| Saved discussion signal | User taps Save on a public discussion | Source-linked record: source `community:<post_id>`, actor = saving user, time, scope. Topic-level signal, not the discussion text as a "fact about" anyone else. |
| Joined-group signal | User joins a group (public signal only) | Group topic interest, weak signal; inferred interests still need two-visit qualification (spec §4). One click is never a confirmed interest. |
| Authored public post | User publishes their own public post | Attributable to its author only. Another user's post is third-party content and never becomes a confirmed fact about the reader (spec §4). Private-group content is never written as a cross-app signal. |
| Explicit interest choice | User picks interests at onboarding / edits profile interests with consent | `user_supplied`, shown as "You told me". |

Every write carries source, actor, host app, time, scope, trust tier, provenance and supersession history; corrections supersede, never overwrite (spec §4). Community content is untrusted data, never instructions, and — per the parked code's own rule — community text never silently becomes profile facts (`apps/api/app/communities.py:5`).

## Consent toggles (Community settings: Connected Memory page)

- Cross-app personalisation: **Off by default**; per-source scopes (Quest interests, Community activity, Messenger-origin features each separately toggleable).
- Save-to-memory for Community activity: on/off, with activity list and deletion (spec §3 Connected Memory page).
- Toggling off stops future reads/writes for that scope and offers Forget for what was already written. Privacy of a post and memory consent are independent controls (spec §4).

## Forget behaviour

- Forget by item or by source ("forget everything from Community") deletes the memory items, unlinks their evidence, and invalidates cached ranking runs/reasons immediately (spec §7: delete/revoke makes it unavailable immediately).
- A forgotten Community signal must be unavailable to Quest recall and Community ranking at once; a stale worker/cache write after Forget must not resurrect it (generation fence in temporal_note's forget-by-source).
- Forget removes memories; it does not delete the user's social posts — post deletion is a separate, visible control. Withdrawing consent stops future writes and offers Forget; it does not silently delete posts.

## What Community will not ask memory to do

- Rank the feed from raw chats or mail from any app.
- Store scraped comments, other users' posts, or third-party details as facts about the signed-in user.
- Infer or store family, faith/religion, health, ethnicity, nationality-as-trait, gender, sexuality, politics, or third parties' private matters (rule 9; two-layer fail-closed screen `apps/api/app/lab/sensitive.py:15,61` must gate any ingest).
- Claim any temporal_note behaviour as tested before this team runs it.
