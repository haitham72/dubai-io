# Brief P1b — Revise the Messenger plan to the founder's decisions · branch `business`

Lead: **Cursor** (it wrote the plan on 23 Nov). Paste everything below the line.

---

You planned Entry 3 on branch `business` (commit `cad6c83`). The founder has since answered your blocking questions and changed the entry's name. **Revise your plan to match**, keeping all your evidence. You write docs only: no code, no import.

## 0. Setup

- Local: `D:\Vscode\dubai-io-business`. Cloud: `git fetch origin && git switch business && git pull --ff-only`.
- Your files have moved from `docs/submissions/mirsal/` to **`docs/submissions/messenger/`** (commit on `business`). Work only there.
- **Never** commit to or push `main`; never force-push; never push to the redesign repo. Edit no file outside `docs/submissions/messenger/` (`docs/submissions/CLAUDE.md` §1–§2: the zero-conflict rule).

## 1. Read first

`docs/submissions/shared/founder-decisions.md` (D1–D6, overrides everything) · `docs/submissions/CLAUDE.md` (updated: zero-conflict rule, gates 1–5, roster).

## 2. Apply

1. **D1 — IP and name.**
   - The office owns the old product and brand. Every feature the founder added in the redesign repo is the founder's own, and the office app never implemented them.
   - **M0 is no longer clean-room.** It is *reuse the founder-authored code as a rebranded snapshot*.
   - Rewrite `ip-and-baseline.md` around one table: **path or asset · origin evidence · keep / exclude / rebuild · reason**. It is the list the founder confirms. Use your evidence: the logo `public/<old>-logo.png`, concept sheets "supplied", Diwan pictures and Diwan Hamdan, Nadi, any code that could come from the office app, and the git accounts.
   - Keep your evidence. Change only the recommendation and the structure.
2. **The name.**
   - The working name is **Messenger**; the final name is open question O2. Never use the old name as the product's name.
   - Cite the redesign repo's own paths only where a builder needs them to find code.
   - Rename everywhere:
     - `apps/<old>/` → `apps/messenger/`; `apps/api/app/<old>/` → `apps/api/app/messenger/`;
     - `test_<old>_*` → `test_messenger_*`; table prefix `ms_` → `mg_`; slice ids `MS-B*` → `MG-B*`; lane prefix → `mg/`;
     - headers such as `x-<old>-user` → `x-messenger-user`.
   - Plan the **rebrand slice**: rename the `@<old>` skills, packages, `agents/<old>_agents/`, routes, strings and assets. Gate: `git grep -n -i -e "m[i]rsal" -- apps/messenger apps/api/app/messenger` prints nothing.
3. **D3 — messaging boundary.** Your recommendation stands: the Messenger owns all person-to-person messaging, and Community only deep-links. Mark the question answered.
4. **D4 — design.** The 19 Nov **AI workspace** (commit `6b45ba4`) is current; the spec's tray line is outdated. Update the UI slices and close the question.
5. **D5 — memory.** Memory is the rewritten **temporal_note** engine (`apps/memory/` on branch `memory`: HTTP API `api/app.py`, MCP `mcp/server.py`, contract `models.py`, Forget `privacy/forget.py`). It is not Hindsight or Honcho, and never the Redis `/agents/memory` store. Update `identity-memory-needs.md` and the memory slice.
6. **D6 + D7 — stickers.** Agents use nothing from the sticker Builder service: no code, prompts, design, emoji-bank data, MCP adapter or integration.
   - Built-in emoji and sticker packs are made **manually by the founder** and supplied as finished files. Plan where they live (for example `apps/messenger/public/packs/`) and how they load.
   - User-made stickers are **image + background removal only**: the user adds a photo, the app removes the background, and the result is saved as a sticker. Pick a local, licence-checked background-removal model with an honest failure path.
   - **No AI image or sticker generation.** Drop or re-plan every AI image, video or sticker-generation feature of the spec, and say so in the gap matrix.
7. **Zero-conflict rule.** Check that no slice edits an existing file. Capabilities are registered from `apps/api/app/messenger/`; settings come from env in your own package. Remove any planned `shared-changes.md` entry, or turn it into an open question.
8. **`open-questions.md`.** Move your five blocking questions under "Answered (23 Nov)", citing D1, D3, D4 and D6. Keep **transport** open for P2 (your recommendation: a cookie-authenticated FastAPI WebSocket until B0 identity exists). Add **O2, the name**. List anything new.
9. Set the status lines to `planned (revised to D1–D6) — awaiting founder approval (<date>, Cursor)`, and add a `log.md` entry.

## 3. Use subagents

These lanes run read-only; you write:
- **Lane A:** the M0 keep/exclude table, from your IP evidence and the redesign repo.
- **Lane B:** the rename and rebrand inventory, every old-name occurrence in the redesign repo that the rebrand slice must change. Count them by kind: identifiers, paths, strings, assets.
- **Lane C:** the sticker re-plan under D7: founder-supplied packs plus image + background removal, with no AI generation and no Builder.

## 4. Finish

- Commit on `business`: `docs(messenger): revise P1 plan to founder decisions D1–D6`, then push `business`.
- Final message (≤ 12 lines): commit hash · the M0 keep/exclude table summary (counts) · what changed in the roadmap · the remaining open questions.
