# Messenger delivery roadmap

**Status:** approved — 23 Nov 2026 (founder, D11)

Order follows spec §9, revised by founder decisions D1–D11. MG-B3 through MG-B9 are approved. UI slices stop for the founder's visual review of a staged preview. Gate S is on `business`, so live chat and memory use the shared identity and the memory bridge. Transport is the shared-contract WebSocket on `:8070`, bound to the B0 `user_id`. The working name is Messenger until the final name, which comes before MG-B7.

**Zero-conflict.** Every slice adds files only. Owned paths: `apps/messenger/**`, `apps/api/app/messenger/**`, `apps/api/tests/test_messenger_*.py`, `fixtures/messenger/**`, `docs/submissions/messenger/**`. RLS notes live in `apps/messenger/supabase/`. No new file under `supabase/migrations/`. No slice edits `actions.py`, `main.py`, `communities.py`, or any other existing file. Capabilities are registered by `apps/api/app/messenger/capabilities.py` inserting into `actions.CAPABILITIES` at import time. Settings come from env inside that package. Entrypoint: `app.messenger.server:app` on port 8070. There is no `shared-changes.md` entry.

Lane branches, when build starts, are `mg/<slice>` from `business`.

Internal package target: Fri 18 Dec 2026 (`PLAN.md` §5). That date is a deck, a video, a host or tunnel, and a small user test.

## MG-B1 — Snapshot import, excluded items removed

**Depends on:** the 23 Nov founder confirmation in `ip-and-baseline.md`. Met.  
**Owns:** `apps/messenger/**` created by the squashed snapshot, then deletions inside that tree only.  
**Approved:** 23 Nov 2026.

| | |
|---|---|
| Happy path | The snapshot is under `apps/messenger/`, and the founder’s drop list is gone: logo, dynamic-island scrapes, Diwan connector, Nadi connector, watermark removal, sticker packs, Diwan pictures, the 97 photos, and the pytest dump. |
| Failure path | An excluded path still present fails the slice. An image that shows the old name or logo and was left in the tree fails the slice. |
| Demo beat | None. |

## MG-B2 — Rebrand

**Depends on:** `MG-B1`.  
**Owns:** renames and string replacements inside `apps/messenger/**` only, plus `apps/messenger/NOTICE.md`.  
**Does not edit** any file that existed before the snapshot.  
**Approved:** 23 Nov 2026. D11 then approved MG-B3 through MG-B9.

The import command, run in MG-B1:

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

**Depends on:** `MG-B2` and Gate S (`720d0a4` on `business`). Live chat uses `require_app_principal` and an Origin-bound WebSocket ticket. Live Supabase waits for local Docker (D12).  
**Owns:** new files under `apps/messenger/` and `apps/api/app/messenger/` for transport, `apps/api/tests/test_messenger_chat.py`, `fixtures/messenger/chat/`.

Transport, settled by the shared contract: a FastAPI WebSocket on `app.messenger.server:app` (`:8070`), bound to the B0 verified `user_id`. The client exchanges a messenger-app session for an HttpOnly `cs_session_messenger` cookie or a single-use, 60-second Origin-bound WebSocket ticket. Handshake checks `Origin` and the session or ticket. Subscribe, send, and replay recheck the session and `mg_memberships`. Revoking a session or removing a member disconnects the socket. Durable store: `mg_*` tables in schema `dubaiio`, created with `CREATE TABLE IF NOT EXISTS` from Messenger code. Idempotent `client_msg_id`. Reconnect by `last_seq`. Media in object storage; a signed URL only after the membership check. RLS SQL is written under `apps/messenger/supabase/` and is not described as live until it is applied. Demo fixtures wear a Demo data pill. Browser Supabase Realtime against `dubaiio` is prohibited.

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

User stickers: any subject, not people only. The user adds a photo. The primary model is BiRefNet general (MIT, official ONNX `BiRefNet-general-bb_swin_v1_tiny-epoch_232.onnx` from the same repository, recorded in `ip-and-baseline.md` on 23 Nov 2026). The weight is not vendored. The phone path refuses it because it does not fit the 256 MiB minimum WebGPU buffer, and the photo stays unchanged until a smaller official weight is supplied. It returns a matte for the foreground, and the saved PNG keeps the photo’s RGB with that matte as alpha. It does not paint new pixels. Do not use an ONNX conversion whose weight provenance is unrecorded. Because that BiRefNet file does not run in the phone browser, the fallback is U²-Net-P (Apache-2.0, official `u2netp.pth`, about 4.7 MB, not vendored). It cuts any subject. A missing weight keeps the original photo. Failure (`model_missing`, `timeout`, `low_contrast`) leaves the photo unchanged, shows the error, and writes nothing.

The offline rule is in the chat store: a voice transcript is a draft until the person confirms, and only then is an `mg_messages` row inserted.

| | |
|---|---|
| Happy path | `test_messenger_pack_sends_file_from_manifest`. `test_messenger_cutout_any_subject_png_has_alpha` on a committed object fixture. The official BiRefNet weight is not in the repo; the test supplies a matte and checks that the photo RGB is unchanged and the alpha is attached. |
| Failure path | `test_messenger_cutout_missing_model_keeps_original`. `test_messenger_u2net_p_fallback_keeps_original_when_missing`. `test_messenger_no_image_generation_route`. `test_messenger_voice_does_not_send_unconfirmed`. |
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

## MG-B7b — Wire web app to real chat core (UI slice)

**Status:** proposed next slice — **waits for founder review** (UI slice; requires staged visual review before marking done).  
**Audit finding (24 Nov 2026):** `apps/messenger/src/store.ts` still boots on `seedMessages` from `apps/messenger/src/chats/data.ts`, with zero references to `:8070`, `/api/messenger`, `/api/identity`, or `ws-ticket` across `apps/messenger/src/` (the only `WebSocket` usage is `/voice` streaming).  
**Depends on:** `MG-B3`, `MG-B7`, and founder visual review of a staged preview.  
**Owns:** `apps/messenger/src/**` (API client + store wiring to `/api/identity/*`, `/api/messenger/*`, and Origin-bound `/api/messenger/ws`, preserving `Demo data` pills when running seeded demo fixtures vs authenticated live sessions).

| | |
|---|---|
| Happy path | Authenticated user signs in, exchanges `messenger` session + WS ticket, sends and receives live messages via `:8070` with reload persistence, and clearly distinguishes live verified threads from `Demo data` threads. |
| Failure path | Unauthenticated, wrong-Origin, or non-member access fails closed cleanly without falling back silently to unlabelled seeded data or asserting E2EE. |
| Demo beat | Staged browser preview with two live user sessions approved in founder visual review. |

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
