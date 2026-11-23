# Founder decisions for Entries 2 and 3

**Recorded 23 Nov 2026** (founder's answers to Claude Code, verbatim where quoted). This file **overrides** `docs/submissions/CLAUDE.md`, every brief, and the founder inputs in `founder-inputs/` wherever they disagree. Add new decisions on top; never delete old ones (mark them superseded).

## D1 — Business entry: IP and name

> "mirsal belongs to the office, i create seperate design/app, the features i added in mirsal-redesign are all mine, they are even not implemented due to complexity"
>
> "the word mirsal should never be mentioned again"

- **Ownership:**
  - The **office owns the old product and its brand.**
  - The redesign repo (`github.com/haitham72/Mirsal-redesign`) is the founder's own separate design and app. **Every feature the founder added there is the founder's**, and none of them was ever implemented in the office app.
- **M0 = reuse the founder-authored code and features, fully rebranded.**
  - The P1 IP lane still lists every file or asset that may come from the office product: logos, icons, brand graphics, copy, and any code copied from the office app.
  - Those are excluded or rebuilt.
  - The founder confirms that list before anything is imported.
  - The import is a **snapshot** (`git subtree add --prefix=apps/messenger <repo> master --squash`), followed straight away by a rebrand commit. The old repo history stays in the source repo.
- **The old name is retired.** The entry's working name is **Messenger** until the founder picks a new one.
  - Paths: `apps/messenger/`, `apps/api/app/messenger/`, `docs/submissions/messenger/`. Lane prefix `mg/`, table prefix `mg_`, tests `test_messenger_*`.
  - The old name must not appear in the UI, code identifiers, package names, routes, `@`-skills, the deck, the video or any new doc.
  - The only exceptions are the source-repo URL, local paths that already exist, and the founder's own filed documents in `founder-inputs/`, which stay unchanged as history.
  - Planning docs may cite the redesign repo's own file paths so builders can find code; they never use the old name as the product's name.
  - Gate: `git grep -n -i -e "m[i]rsal" -- apps/messenger apps/api/app/messenger` prints nothing.

## D2 — Persocial

> Community replaces Persocial.

Dubai-io Community is the new home of the Persocial idea; Persocial stops as a separate project. Nothing has to be imported from it.

## D3 — The three apps and the messaging boundary

> "image facebook for community, but the messages is whatsapp 'mirsal-redesign', while dubai-io is the memory agentic companion like 'chatgpt'"

| App | Is like | Owns |
|---|---|---|
| Dubai-io / Quest (Entry 1) | ChatGPT | The memory-based agentic companion |
| Dubai-io Community (Entry 2) | Facebook | Feed, profiles, posts, groups, discovery, community agents |
| Messenger (Entry 3) | WhatsApp | **All person-to-person messaging** (1:1, groups, media, stickers) and the chat-to-action business agents |

- Community builds **no messenger of its own**. Its Inbox is notifications (replies, mentions, group activity) only. A "message this person" action hands off to the Messenger once shared identity exists.
- The parked `chat_*` tables in `apps/api/app/communities.py` are not extended into a chat product.

## D4 — The Messenger's current design

> AI workspace (19 Nov) is current.

The redesign's latest design is current: commit `6b45ba4`, "AI workspace replaces Updates tray". The founder spec's line about keeping the compact Updates tray is outdated.

## D5 — Memory engine: temporal_note

> The other PC's main "is using completly rewritten temporal_note mcp instead of hindsight or honcho".

- Memory for all three entries is the rewritten **temporal_note** engine: `apps/memory/`, package `temporal_memory` (HTTP API `api/app.py`, MCP server `mcp/server.py`, contract `models.py`, Forget `privacy/forget.py`).
- **Hindsight and Honcho are not used.** The founder inputs' mentions of Hindsight, `MemoryBackend` and `ScopeGuard` mean temporal_note. Hindsight's `AC-1` / `MEM-01` gates do not apply to these entries.
- `apps/api/app/memory_bridge/` is a client of temporal_note and never a second engine. Until temporal_note is on `main`, the bridge's tests use a clearly named fake with the same interface.
- The other PC's `main` builds Dubai-io's **iOS and desktop apps** and is far ahead of `origin/main`. These branches therefore only add new files in new folders (`docs/submissions/CLAUDE.md` §1–§2).

## D6 — The sticker Builder service is excluded

- The sticker Builder service (`D:\Vscode\mirsal-builder-io`) began as an office-assigned task, and its ownership is **contested**.
- The Messenger uses **nothing** from it: no code, prompts, system design, emoji-bank data or MCP adapter.
- This supersedes the old O1. The sticker rules themselves are in D7.

## D7 — Stickers: founder-made packs, and image-plus-background-removal only

> "stickers will only be manually created 'by mirsal-builder' to populate the emojis, but will be allowed to create 'stickers' by adding images and removing background not ai higgsfield"

- **Built-in emoji and sticker packs** are made **manually by the founder** with the Builder and supplied as finished asset files (for example under `apps/messenger/public/packs/`). Agents never run, call, copy or integrate the Builder.
- **User-made stickers:** the user adds an image, the app removes its background, and the result is saved as a sticker. Background removal runs locally where possible, with a licence-checked model; failures are honest.
- **No AI image or sticker generation** in the Messenger: no Higgsfield-style text-to-image or sticker generation.

## D8 — Messenger M0 confirmed; import and rebrand may start (23 Nov)

- **Keep (the founder's own):**
  - concept sheets (`Slides/*.jpg`, output grid);
  - screen frames (`screens/`: 4 screens, Layer 0–10, GPT design/01), but **not** the dynamic-island reference scrapes, which stay excluded;
  - video clips (`media/videos/`);
  - motion-graphics audio and photos.
- **But** any image or frame that visibly shows the old name or logo is excluded from the shipped app, because a text grep cannot find it.
- **Drop:** the Diwan connector and the Nadi connector (code, UI hooks, tests, demo data); the cleaner's `remove-ai-watermarks` dependency and any feature that removes AI watermarks or provenance marks; `lib/higgsCli.ts` and any Higgsfield API or CLI use ("there is no higgsfield at all").
- **User stickers:** any subject, not people only. Use a general background-removal model (U²-Net class, licence recorded, local where possible), with MediaPipe Selfie Segmentation only as a fallback.
- **Early start:** MG-B1 (snapshot import) and MG-B2 (rebrand) are approved now. Every other Messenger slice waits for the full gate.

## D9 — Community product rulings (23 Nov)

- **Visual authority:**
  - **Layout and content:** the Higgsfield v3 Community frames in `design/references/v3-higgsfield/`: desktop `l01`, `l05`, `l08`, `l09`, and phone `m02`, `m04`, `m08`, `m09`. Strip any "r/dubai"-style naming and drop the Stories rail. `m04`'s private chat is a hand-off to the Messenger (D3).
  - **Visual style:** `design/20-11-2026/`, the look the founder has moved the iOS app to, so Community reads as part of the Dubai-io family.
  - Higgsfield is never used inside any product.
- **Ages: all ages, with an age gate.**
  - The age band is self-declared at sign-up and never inferred.
  - Under-18 accounts get protections by default: no cross-app personalisation, no memory writes, private-by-default profiles, not discoverable or searchable by adults outside shared groups, and moderation priority on reports involving them.
  - Before CM-B3 the planner sources the UAE's official child digital-safety and child-data requirements (for example parental consent, and any minimum age) and proposes the under-13 policy. If a requirement cannot be met by 18 Dec, it stops and asks.
  - Testers in the multi-user test are consenting adults.
- **Private groups:** invisible to non-members. Members invite and a moderator approves. There is one owner, with named moderators (pin, remove), and every moderator action is logged and reversible by the owner.
- **Demo Scene C:** one official public-information topic, answered only from that authority's own public pages (allowlisted publishers), with no claim of any integration. A non-civic fallback topic is rehearsed too.

## D10 — Operations (23 Nov)

- **Demo and tests by 18 Dec:** through a secure tunnel from the founder's PC (no spend). It is used for the videos and for a test with at least 5 consenting adults per entry.
- **Accounts:** a separate Supabase **staging** project for both entries (sign-up disabled, test users only). Its Auth and RLS SQL is applied by a script from each app's own folder (`apps/community/supabase/`, `apps/messenger/supabase/`). `supabase/migrations/` stays frozen.
- **Memory team hand-off:** the temporal_note change requests (CR-TM-1…4: records, forget, resolve, context/search routes, plus the two fixes) go to the other team as **one hand-off file**, `docs/submissions/shared/handoff-temporal-note.md`. Our builds use a clearly named `FakeTemporalMemoryClient` until theirs lands.
- **Recommended founder action:** ask the organisers in writing (createaiagents@dubaichamber.com) whether a founder's own earlier prototype may be reused in an entry.

## Still open (raise at the founder gate after P2)

- **O2** The Messenger's new product name.
- **O3** Anything the planners still list as blocking in their `open-questions.md`.
