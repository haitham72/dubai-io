# Messenger delivery roadmap

**Status:** planned (revised to D1–D6) — awaiting founder approval (23 Nov 2026, Cursor).

Order follows spec §9, revised by founder decisions D1–D7. Code starts only after the founder signs the keep/exclude list in `ip-and-baseline.md`. Slices that need a verified `user_id` or temporal_note wait for Gate S. The rebrand and the local chat shell do not.

**Zero-conflict.** Every slice adds files only. Owned paths: `apps/messenger/**`, `apps/api/app/messenger/**`, `apps/api/tests/test_messenger_*.py`, `fixtures/messenger/**`, `docs/submissions/messenger/**`. RLS notes live in `apps/messenger/supabase/`. No new file under `supabase/migrations/`. No slice edits `actions.py`, `main.py`, `communities.py`, or any other existing file. Capabilities are registered by `apps/api/app/messenger/capabilities.py` inserting into `actions.CAPABILITIES` at import time. Settings come from env inside that package. Entrypoint: `app.messenger.server:app` on port 8070. There is no `shared-changes.md` entry.

Lane branches, when build starts, are `mg/<slice>` from `business`.

Internal package target: Fri 18 Dec 2026 (`PLAN.md` §5). That date is a deck, a video, a host or tunnel, and a small user test.

## MG-B1 — Audit and IP

**Depends on:** nothing.  
**Owns:** the docs in this folder. No application code.  
**This revision is the current commit.**

| | |
|---|---|
| Happy path | A reader sees the keep 12 / exclude 8 / rebuild 16 list, the 200 / 1 test rerun, and D1–D7 applied to the slices below. |
| Failure path | A path that is only a filename is not marked working. The Redis skip stays a skip. |
| Demo beat | None. It unlocks the founder’s signature on the M0 list. |

## MG-B2 — Rebrand snapshot

**Depends on:** the signed sentence in `ip-and-baseline.md` (“I confirm this keep/exclude/rebuild list.”).  
**Owns:** `apps/messenger/**` after the squash, then a rebrand commit in that tree only.  
**Does not edit** any file that existed before the snapshot.

Import, not run by this plan:

```
git subtree add --prefix=apps/messenger https://github.com/haitham72/Mirsal-redesign master --squash
```

The rebrand commit then applies the exclude and rebuild rows, and renames the rest.

Inventory at `6b45ba4`, from `git grep -i -c -e mirsal HEAD` in the redesign repo: **908 matching lines in 172 files**. Plus **53 paths** whose names match; 27 of those have no content match. Union: **199 files**.

| Kind | Lines |
|---|---|
| identifiers | 285 |
| paths | 193 |
| strings | 430 |
| assets (filename only, outside the 908) | 2 |

| Token | Replacement | Lines |
|---|---|---|
| package name `mirsal-poc` | `messenger-poc` | 3 |
| `agents/mirsal_agents/` (46 tracked files) | `agents/messenger_agents/` | 110 content lines; 25 files move with the directory |
| `@mirsal` skills | `@messenger` | 87 (3 further `@` hits are demo emails) |
| header `x-mirsal-user` | `x-messenger-user` | 2 |
| route `/agents/mirsal/<skill>` | `/agents/messenger/<skill>` | 16 |
| route `/mirsal/<skill>` in `src/apiclient/mirsal.ts` | `/messenger/<skill>` | 6 |
| `public/mirsal-logo.png` | delete the file and its 14 references | not a text line |
| Builder tokens (`mirsal_builder_*` and the builder path) | delete with the feature | 33 lines in 12 files, already inside the 908 |

Diwan is a different word. Keep `diwan.py` and `diwan_demo.json` basenames when the parent directory is renamed. The commemoration pictures stay excluded.

**Gate:** `git grep -n -i -e "m[i]rsal" -- apps/messenger apps/api/app/messenger` prints nothing.

| | |
|---|---|
| Happy path | The gate command prints nothing, and the exclude rows are absent from `apps/messenger/`. |
| Failure path | One remaining match fails the slice. A deleted logo that is still referenced fails the build. |
| Demo beat | The shell opens under the working name Messenger, with a placeholder mark until O2. |

## MG-B3 — Real chat core

**Depends on:** `MG-B2`. Verified `user_id` waits for Gate S. Until then, rows use the cookie session owner and the UI does not say the same person is in Quest or Community.  
**Owns:** new files under `apps/messenger/` and `apps/api/app/messenger/` for transport, `apps/api/tests/test_messenger_chat.py`, `fixtures/messenger/chat/`.

Transport recommendation, still open for P2: a cookie-authenticated FastAPI WebSocket until B0 identity exists. Durable store: `mg_*` tables in schema `dubaiio`, created with `CREATE TABLE IF NOT EXISTS` from Messenger code. Idempotent `client_msg_id`. Reconnect by `last_seq`. Media in object storage; a signed URL only after the membership check. RLS SQL is written under `apps/messenger/supabase/` and is not described as live until it is applied. Demo fixtures wear a Demo data pill.

D4: the 19 Nov AI workspace is the current design. `openUpdates()` sets `screen: "ai"`. The spec’s compact-tray line is outdated. The snapshot keeps that workspace. The rebrand renames the visible product string on it.

| | |
|---|---|
| Happy path | `test_messenger_two_users_send_reload`. `test_messenger_idempotent_retry`. `test_messenger_reconnect_replay`. |
| Failure path | `test_messenger_non_member_404`. `test_messenger_no_bulk_or_cold_send`. `test_messenger_message_injection_cannot_act`. `test_messenger_copy_has_no_e2ee_claim`. |
| Demo beat | Two devices, one real message each way. The business script stays labelled Demo data until this is green. |

## MG-B4 — Packs, cut-out stickers, and voice

**Depends on:** `MG-B2`. Voice-on-real-messages also depends on `MG-B3`.  
**Owns:** `apps/messenger/public/packs/` (founder-supplied files only), `apps/api/app/messenger/stickers.py`, `apps/api/tests/test_messenger_stickers.py`, `fixtures/messenger/stickers/`.

D6 and D7. Nothing from the Builder service: no code, prompts, design, emoji-bank data, MCP adapter, or URL. No AI image generation, no AI sticker generation, no text-to-video, no Higgs path. The redesign’s `api/images.ts`, `api/videos.ts`, `sticker_builder.py`, and `public/stickers/` are dropped in `MG-B2`, not reimplemented.

Built-in packs: the founder supplies finished files. The client reads `apps/messenger/public/packs/manifest.json` when the tray opens. A tap sends `{ kind: "sticker", packId, stickerId }`. Limits: PNG, WebP, or SVG; longest edge 512 px; PNG/WebP at most 512 KB; SVG at most 100 KB with no script and no external reference; at most 50 stickers in a pack and 20 packs.

User stickers: the user adds a photo. On-device MediaPipe Selfie Segmentation (Apache-2.0, bundled `selfie_segmentation.tflite`, about 249 KB) writes a PNG whose RGB is the photo and whose alpha is the person matte. The network does not emit colour pixels. Success stores one `mg_stickers` row and the object. Failure (`model_missing`, `timeout`, `low_contrast`, `person_not_detected`) leaves the photo unchanged, shows the error, and writes nothing. A pet, object, or logo fails closed.

Voice policy from the offline suite (a send waits for the person) is wired to `mg_messages` and the registered capability. It does not generate images.

| | |
|---|---|
| Happy path | `test_messenger_pack_sends_file_from_manifest`. `test_messenger_cutout_png_has_alpha` on a committed person fixture. |
| Failure path | `test_messenger_cutout_missing_model_keeps_original`. `test_messenger_no_image_generation_route`. `test_messenger_voice_does_not_send_unconfirmed`. |
| Demo beat | Optional. The business case does not depend on a sticker. |

## MG-B5 — Scoped memory

**Depends on:** `MG-B3` and Gate S. The bridge is a client of temporal_note (`apps/memory/` on branch `memory`: `api/app.py`, `mcp/server.py`, `models.py`, `privacy/forget.py`). It is not Hindsight, not Honcho, and not the Redis store. Hindsight’s `AC-1` / `MEM-01` gates do not apply.  
**Owns:** `apps/api/app/messenger/memory_client.py` only. It does not store facts and it does not edit `apps/memory/`. Tests: `apps/api/tests/test_messenger_memory.py`. Until temporal_note is on `main`, tests use a named fake with the same operations.

Source string: `messenger:<conversation_id>`. Record id: `mgmsg:<message_id>`. Operations: `read_chat_scope`, `write_consented`, `forget` as in `identity-memory-needs.md`.

| | |
|---|---|
| Happy path | `test_messenger_save_writes_record_with_evidence`. |
| Failure path | `test_messenger_ai_default_off`. `test_messenger_group_off_blocks_model`. `test_messenger_forget_keeps_messages`. `test_messenger_delete_keeps_facts_until_forget`. |
| Demo beat | Privacy walkthrough: Off, then Save, then Forget. |

## MG-B6 — Business agent

**Depends on:** `MG-B3`. Memory is not required for the chain. The chain uses message ids in `mg_messages`.  
**Owns:** `apps/api/app/messenger/capabilities.py`, `apps/api/app/messenger/business.py`, `apps/api/tests/test_messenger_business.py`, `fixtures/messenger/marina/`.

`capabilities.py` registers `workspace.task.create` into `actions.CAPABILITIES` at import. It does not edit `actions.py`. One tap. The card lists the exact fields in `demo-script.md`. No adapter: the card shows the blocker and the draft remains. Model text never sets Completed, Confirmed, or Paid.

| | |
|---|---|
| Happy path | `test_messenger_demo_chain_and_denial`. |
| Failure path | `test_messenger_ai_side_effect_needs_approval`. `test_messenger_joke_is_not_an_obligation`. `test_messenger_no_reminder_for_another_member`. `test_messenger_decision_stays_candidate_until_tap`. |
| Demo beat | The four-minute script. Seeded lines are Demo data. Operator-started steps are Demo trigger. |

## MG-B7 — Cross-account verification

**Depends on:** `MG-B3`, `MG-B6`, and `MG-B5` if the privacy walkthrough is in the same recording. Gate S still green.  
**Owns:** `apps/api/tests/test_messenger_e2e.py` and a note in `log.md`.

| | |
|---|---|
| Happy path | Two users, the denial, and a process restart with the thread still there. |
| Failure path | A third session, an injection message, and Save flipped to Off mid-flight. |
| Demo beat | Only tests that were actually run, with the command and the output in the log. |

## MG-B8 — Deck, video, hosting

**Depends on:** `MG-B6` green on a staged build, or the deck says the task step is still blocked. O2 if the visible name is still the working title. The excluded logo is not on the deck.  
**Owns:** packaging notes in this folder. The deck file stays out of the repo until the founder asks to add it.

| | |
|---|---|
| Happy path | The video shows the tap, the open task, the citations, and the refusal, with both pills visible. The product name on screen is Messenger, or the name chosen in O2. |
| Failure path | If `workspace.task.create` is not registered, the video shows the blocker and the draft. |

## MG-B9 — Stage 2 pilot

**Depends on:** `MG-B3` and `MG-B6` on real membership. The group is not the family chat.  
**Owns:** no new code. The blanks in `demo-script.md` are filled in `log.md` as counts.

| | |
|---|---|
| Happy path | One recorded decision, one confirmed action, one approval. Minutes to find the decision, both ways. |
| Failure path | A non-member cannot open the chat, the task, or the answer. |
| Demo beat | Replaces the seeded thread in the jury cut only after this session. |

## Deliberately out

Voice and video calling. A Community messenger. Any write to `apps/memory/` from this branch. Gemini. WhatsApp linked-device or Evolution. An end-to-end-encryption label. AI image, video, or sticker generation. Anything from the Builder service.
