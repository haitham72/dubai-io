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
  - Gate: `git grep -n -i -e "m[i]rsal" -- apps/messenger apps/api/app/messenger docs/submissions/messenger` prints nothing.

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

## Still open (raise at the founder gate after P2)

- **O1** The sticker Builder service (`D:\Vscode\mirsal-builder-io`): is it the founder's own or the office's, and what is its new name? Until answered, the Messenger's sticker features use only founder-authored code, or are labelled as a pending dependency.
- **O2** The Messenger's new product name.
- **O3** Anything the P1 planners list as blocking in their `open-questions.md`.
