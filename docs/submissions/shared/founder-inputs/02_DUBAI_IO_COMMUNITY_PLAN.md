# Dubai-io Community — Submission 2: Best Societal AI Agent

**Planning baseline:** 23 November 2026 · **Revised:** 23 November 2026 after reviewing `haitham72/Mirsal-redesign`  
**Product type:** Facebook-style social network, with original branding, design, and AI community agents  
**Related products:** Quest (personal AI companion) and Mirsal (AI messenger / AI communication workspace). Mirsal is currently a UI/agent proof of concept, **not** an operational cross-user messaging service.  
**Status:** New proposal for the contest; not a claim that the listed features are implemented.

## 1. Positioning

**Product:** A full-featured social experience for Dubai residents and communities: feed, profiles, posts, media, reactions, groups, local discussions, search, discovery, notifications, and lightweight direct messaging.

**Agentic distinction:** It remembers the signed-in user's **permitted** interests and context across the Dubai-io ecosystem, recommends genuinely useful communities and discussions, and has agents that can research, explain, and help users participate in local life. The social experience is the product; AI is integrated without turning the feed into a chatbot.

**Contest story:** Instead of claiming to have built a generic Facebook replacement, demonstrate measurable community outcomes: help a Dubai newcomer find reliable local knowledge, relevant groups, contacts, and event opportunities, with evidence-backed assistance and clear privacy controls.

**Important:** Use Facebook's broad *interaction model* as inspiration, but create original design, branding, code, assets, and copy. Do not claim affiliation with Meta.

## 2. Product scope

### Social foundations — MVP / priority P0
- One common Dubai-io sign-in identity (`user_id`), verified across products. No account merge by name alone.
- User profile: avatar, bio, location at voluntary neighborhood/city granularity, interests, follow/friend relationships, and privacy settings.
- Feed with **Following**, **Communities**, and **Discover** lanes; chronological Following option; honest loading/empty states.
- Text/image posts; attachments; replies, threaded comments, reactions, bookmarks, share/copy link; user-owned delete/edit.
- Communities: public and private group membership, posts, moderators, pin posts, reporting, search.
- Search across posts, people, groups, and topics; notifications for relevant replies and mentions.
- **Inbox:** provide a placeholder or a fully tested minimal community DM capability where needed. Do **not** present `Mirsal-redesign` as a usable cross-user messenger yet: its chat data is seeded and its message store is client-side. A future Mirsal handoff requires real shared identity, verified chat transport and explicit cross-app routing. Avoid building two competing full messaging systems.
- Block, mute, report, remove, permission controls, basic spam moderation, and owner-scoped APIs.

### Differentiating AI — MVP / priority P0–P1
1. **Discovery Agent:** Match users to relevant conversations, communities and events using consented interest features, activity, and fresh public information; display a concise `Why this?` explanation.
2. **Community Answer Agent:** For questions about local services or rules, retrieve authorized and verifiable public sources; draft a response with citations. A human approves publication.
3. **Group Organizer Agent:** Within a group, summarize *authorized* discussions and propose events, shared checklists, or tasks. No autonomous posting, contacting people, or issuing invitations.
4. **Moderation Copilot:** Flag likely spam, fraud, abusive content, or duplicates and provide evidence for human moderation. Do not silently ban members based on a model verdict.

### Deferred / P2
- Stories and short-form video, creator monetization, sophisticated ranking model training, livestreaming, marketplace, advertising platform, native app-store releases, and full messaging/calling stack. Add only after a working core.

## 3. Design / interaction

- iPhone-first, responsive PWA / React; original Dubai-io aesthetic. Use the actual approved screenshots/design files in the repo as visual authority where found.
- Baseline if exact files are missing: warm-white canvas, light creamy surfaces, SF-like typography, subtle borders, generous whitespace, clean feed cards, restrained pastel category accents. Do **not** assert these reproduce the last four social mockups without inspecting them.
- Main tabs: **Feed / Communities / Create / Inbox / Profile**. Discover is a feed lane or search destination.
- Post cards prioritize author, context, media, and actions. AI explanation is subordinate, never a large intrusive card.
- Feed is primarily social content. The AI assistant appears as contextual actions: *Find relevant groups*, *Explain*, *Summarize*, *Draft reply*, *Why this?*.
- Provide a settings page with **Connected Memory**, source-level scopes, cross-app personalization toggle, activity and deletion.

## 4. Shared memory contract (not a second profile)

**Single identity target:** `user_id` maps to one central memory owner for Quest, Community and Mirsal; each front end has separate sessions/capabilities, not separate master profiles. **This is the target architecture, not existing Mirsal functionality:** the Mirsal prototype currently uses seeded contacts/messages and per-browser state, with separate Redis/in-memory agent facts/tasks.

**Authoritative store:** Supabase PostgreSQL + Hindsight behind `MemoryBackend`/`ScopeGuard`. The Obsidian-like seven-theme Markdown tree is a generated, inspectable view/export; it is **not** a writable alternate database.

**Ingest from Community:** user-authored public posts, explicitly saved interests, joining groups, meaningful choices, and consented profile edits. Treat one click as a weak temporary signal; inferred interests require the existing two-visit/confirmation policy. Do not write scraped comments or another user's post as a confirmed fact about the signed-in user.

**Retrieve into Community:** narrow topic/interests features when cross-app personalization is enabled. Mirsal-origin features must pass explicit conversation-level consent plus a cross-app sharing check; there is no blanket permission merely because the two apps share `user_id`. Do **not** return raw Quest chat, Gmail contents, Outlook contents, Mirsal chat excerpts, private family/health facts, OAuth tokens, or third-party details into feed ranking, moderator tools, advertisements, or social suggestions.

**Security:** isolate every query by verified owner; classify data by source and scope; label hypotheses vs. confirmed facts; preserve provenance, valid timestamps, supersession history, and `Forget` revocations. Privacy and public-post visibility are independent controls.

**Example:** A user tells Quest that they're learning PyTorch. With consent to use this interest across apps, Community can recommend a *Dubai ML developers* discussion. It cannot post “you are learning PyTorch” or disclose the original conversation to anyone.

## 5. Technical strategy

### Cross-application baseline checked from GitHub (23 Nov 2026)

`https://github.com/haitham72/Mirsal-redesign` is accessible publicly (default branch `master`). The repo's `README.md`, `ARCHITECTURE.md`, `src/chats/data.ts`, `src/store.ts` and `agents/mirsal_agents/routes/memory.py` show an existing **React/Vite demo plus Python agent service**—not a ready-to-use messaging backend. Conversations are seeded in `src/chats/data.ts`, app messages begin from `seedMessages` in `src/store.ts`, and its `/agents/memory/*` routes handle simple agent facts/tasks (Redis/in-process), **not** Hindsight/ScopeGuard. The documentation explicitly describes the app as a clickable investor demo. These are repository inspection findings, not independently executed runtime tests.

**Implication for Community:** reuse common memory/identity contracts and any legally reusable UI patterns, not Mirsal's sample chat store, mock profile data or isolated agent memory as a second authoritative account. The Community team's core feed/group work is independent of Mirsal's messenger conversion.

1. **Audit existing social code**, specifically the `communities`, `social_generation`, recommendation components and table definitions documented in `ARCHITECTURE.md` (parked on 9 Nov). Classify each route as working, partial, fixture, or absent with tests. Do not assume a feature is production-ready because a table exists.
2. Prefer a separate presentation surface (`apps/community` or equivalent), **sharing verified auth, FastAPI services and memory APIs**; avoid blindly duplicating the backend or changing Quest's frozen mobile baseline.
3. Postgres tables will likely include profiles, communities/memberships, follows, posts, comments/reactions, media, notifications, moderation events and recommendation events; map these to existing schema first and avoid competing duplicates.
4. Media in permissioned object storage; signed URLs and quotas. Server-side ownership and row-level security; secure pagination.
5. Independent recommendation adapter: candidate retrieval (social graph, public community content, relevant current topics) -> policy filters -> personalization/ranking -> explanation. No private-source leakage.
6. Keep AI content-generation tasks asynchronous and optional; controlled budgets and provider availability states. Only a deterministic approved action can publish/edit/remove externally.

## 6. Contest demo (end-to-end, factual)

**Scene A — new resident:** A new test account chooses public interests during onboarding. The app recommends active, relevant Dubai groups and explains the source of each suggestion. User joins and comments.

**Scene B — existing Quest user:** The same verified `user_id` signs into Community; turns on cross-app *interest-only* personalization. The feed improves using a permitted interest from Quest, without importing private text.

**Scene C — community AI action:** User asks, “How can I find reliable local resources about [verified civic topic]?” AI retrieves cited sources, drafts an answer, and user approves posting it to a test community. Show source, timestamp, approval, and final post.

**Scene D — memory loop:** User saves a public discussion. Community writes a scoped, attributable memory signal. Quest can subsequently recall the topic as a preference **only** within authorized scopes. Demonstrate correction/forget propagating. If Mirsal is part of the same demo, show only an explicitly consented interest feature reaching Community—**never** private Mirsal messages.

**Demo evidence:** Real sign-in, working cross-app identity, live data retrieval, a genuine public-source citation, a successful approved publication, and a source-aware memory read/write. Seeded posts can fill the visual feed but must be marked as demo data, never simulated as real community activity.

## 7. Verification / acceptance gates

- [ ] Two different users cannot read each other's private profile, drafts, saved content, or memory.
- [ ] Quest -> Community consented-interest personalization works; no raw private sources appear in the social API payload.
- [ ] Community -> Quest contribution has provenance; delete/revoke makes it unavailable immediately.
- [ ] Post/create/edit/delete, group join, replies, and notifications work after process restart.
- [ ] Group permissions and moderation actions are enforced on the server.
- [ ] AI drafts never publish without the user approving the exact revision and destination.
- [ ] Moderation false positives remain reviewable; reporting has a human resolution path.
- [ ] A new user can use the social network with no imported memory.
- [ ] Community works independently while Mirsal is still a visual POC; its Inbox neither fabricates live messaging nor assumes Mirsal contacts exist.
- [ ] When Mirsal integration is enabled later, a user-controlled per-source/scope permission determines whether any Mirsal-derived interest enters Community; private text is absent from payloads.

## 8. Delivery order

**A. Code audit and product contract:** inventory existing modules, designs and test gaps, then settle the smallest runnable slice.  
**B. Social core:** accounts, profiles, feed, media posts, comments, groups, reactions, moderation.  
**C. Memory integration:** consented topic features and attribution for social writes, correct owner isolation.  
**D. Agentic demo:** one working discovery flow, one sourced answer/draft/approve/post flow.  
**E. Polish / submission:** original design, multi-user tests, screen recording, 2–3 outcome metrics, disclosure of fixtures/limitations.

**Do not expand** into advertising, marketplace, a full second chat stack, or unverified civic integrations before P0 and the demo gates pass.
