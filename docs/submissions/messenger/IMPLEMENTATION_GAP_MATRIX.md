# Messenger — requirements to code

**Status:** planned (revised to D1–D6) — awaiting founder approval (23 Nov 2026, Cursor).  
**Reuse column:** D1. Founder-authored code comes in as a squashed snapshot under `apps/messenger/`, then the rebrand (`MG-B2`). Exclude and rebuild rows are in `ip-and-baseline.md`. The redesign paths below are how a builder finds the code. S/M/L is the work after that snapshot.

Spec: `docs/submissions/shared/founder-inputs/03_MIRSAL_AI_MESSENGER_PLAN.md` (the filed spec still uses the retired name; that file is not edited). POC commit: `6b45ba4`.

| Feature | Source evidence | Reuse candidate | Missing work | Size | Dependency | Acceptance test |
|---|---|---|---|---|---|---|
| Rebrand snapshot | D1. 908 name lines in 172 files, plus 2 logo assets (`DELIVERY_ROADMAP.md`) | Squash of founder-authored code, after the signed keep/exclude list | Rename identifiers, paths, and strings. Delete the logo and the Builder tokens | L | Signed list, `MG-B2` | `git grep` gate prints nothing |
| Real 1:1 and small-group chat | Spec §2 P0. POC `src/store.ts:106` `seedMessages`; send appends in the browser (`:162-172`) | The chat UI, after rebrand. Not the seed array as real traffic | `mg_conversations`, `mg_memberships`, `mg_messages`. WebSocket fan-out | L | `MG-B2`. Verified `user_id` waits for Gate S | `test_messenger_two_users_send_reload` |
| Contact request before a 1:1 | Spec §2. Community `chat_*` is per-owner and is not this store (D3) | None in Community | `mg_contact_requests`. No thread until accepted | M | `MG-B3` | `test_messenger_no_bulk_or_cold_send` |
| Edit, delete, delivery, read | Spec §2 P0. Not in the POC message model | None | Tombstone keeps `seq`. `mg_receipts` | M | `MG-B3` | `test_messenger_edit_delete_receipts` |
| Attachments | Spec §2 P0. POC media is local or demo | None | `mg_attachments`. Signed URL after the membership check | M | `MG-B3` | `test_messenger_attachment_member_only` |
| Idempotent send, offline retry, reconnect | Spec §2 P0 | None | Unique `(conversation_id, sender_id, client_msg_id)`. Replay by `last_seq` | M | `MG-B3` | `test_messenger_idempotent_retry` |
| Typing and presence | Spec §2 | None | Socket-only. Not stored | S | `MG-B3` | `test_messenger_typing_not_persisted` |
| Block and report | Spec §2 P0 | None | Block on the contact request. Report row in `mg_audit` | S | `MG-B3` | `test_messenger_block_hides_thread` |
| Isolated demo mode | Spec §2, rule 2 | Seed shape only | `provenance=demo_fixture` and a Demo data pill | S | `MG-B3` | `test_messenger_demo_pill` |
| Per-conversation AI Off / Session / Save | Spec §5 | None | `ai_mode` on `mg_memberships`, default off | M | `MG-B3` | `test_messenger_ai_default_off` |
| Group consent | Spec §4–§5 | None | One `off` member blocks the prompt | M | `MG-B5` | `test_messenger_group_off_blocks_model` |
| Summarise unread | Spec §2 P1 and §7 | Offline chat skills, after rebrand | Run on authorised `mg_messages`, with ids and a scope line | M | `MG-B6` | `test_messenger_summary_cites_scope` |
| Search inside a conversation | Spec §2 P1 | Photo pgvector is the wrong index (`api/photos.ts`) | Member-scoped search. A non-member gets 404 | M | `MG-B3` | `test_messenger_non_member_404` |
| Smart reply, user taps Send | Spec §2 P1 | Offline voice policy waits before an outward send | Draft only. `sender_id` comes from the session | S | `MG-B6` | `test_messenger_suggestion_does_not_send` |
| Voice notes | Spec §2 P1. POC voice socket is dictation, not chat transport | Offline voice tests | Store the audio. Transcription stays labelled unverified | M | `MG-B4` | `test_messenger_transcript_keeps_original` |
| Decision Keeper | Spec §2, §7 | None | Candidate until a member taps Record | M | `MG-B6` | `test_messenger_decision_stays_candidate_until_tap` |
| Action Tracker | Spec §2, §7 | Redis `tasks:{user}` is dropped | Quoted candidates. No `tasks.py` row until approval | M | `MG-B6` | `test_messenger_joke_is_not_an_obligation` |
| Approval card and task create | Spec §2, §8. `CAPABILITIES` has no task id (`actions.py:82-103`) | `approve()` stays in `actions.py` and is not edited | Register `workspace.task.create` from `apps/api/app/messenger/capabilities.py` at import. No adapter: draft stays blocked | L | `MG-B6`, rule 7 | `test_messenger_ai_side_effect_needs_approval` |
| Project brief | Spec §2, §7 | None | Cited brief of this thread. “Since yesterday” only when a real window exists | M | `MG-B6` | `test_messenger_brief_cites_visible_messages` |
| Knowledge assistant | Spec §2 | Demo fact-check is not scoped retrieval | This membership only, with message ids | M | `MG-B6` | `test_messenger_qa_scope` |
| Access denied | Spec §7, §8 | None | Non-member search, task, and answer return 404 | S | `MG-B3`, `MG-B6` | `test_messenger_non_member_404` |
| Third-party reminder | Spec §7 Stage 1 | Outbox pattern in `proactive.py`, not edited | No outbox row for anyone but the caller, and only after that person’s tap | S | `MG-B6`, rule 8 | `test_messenger_no_reminder_for_another_member` |
| Prompt injection in a message | `ARCHITECTURE.md` §9.1 | Offline eval gate | Body cannot send, call a capability, write a fact, or change membership | M | `MG-B3` | `test_messenger_message_injection_cannot_act` |
| No bulk or cold send | `PLAN.md` D14 | None | No recipient-list endpoint | S | `MG-B3` | `test_messenger_no_bulk_or_cold_send` |
| No end-to-end-encryption claim | Spec §5 | None | Copy says encrypted in transit to the server. The server stores plaintext | S | `MG-B3` | `test_messenger_copy_has_no_e2ee_claim` |
| Consented memory write | Spec §4. POC `/agents/memory` is Redis | temporal_note via `memory_bridge` (D5). Not a port of the Redis lists | `write_consented` only after Save, the group gate, and Confirm. Source `messenger:<conversation_id>` | L | Gate S, `MG-B5` | `test_messenger_save_writes_record_with_evidence` |
| Chat-scoped read | Spec §4 | `read_chat_scope` | That owner and that source only | M | Gate S | `test_messenger_read_scope_excludes_other_chat` |
| Forget versus delete | Spec §4. `privacy/forget.py` `forget_source` | The temporal_note function, called through the bridge | Two buttons. Forget cascades facts. Delete tombstones messages | M | Gate S, `MG-B5` | `test_messenger_forget_keeps_messages` |
| Redis review, then drop | Spec §6 | POC keys are not facts | Do not import them. No dual write | S | `MG-B5` | `test_messenger_redis_keys_not_inserted` |
| Founder sticker packs | D7. Redesign `public/stickers/` is excluded | None. New files the founder supplies | `apps/messenger/public/packs/manifest.json`. Tray sends `packId` and `stickerId` | M | `MG-B4` | `test_messenger_pack_sends_file_from_manifest` |
| User sticker cut-out | D7, founder 23 Nov: any subject | BiRefNet general primary (MIT). Phone fallback is U²-Net-P, Apache-2.0, `u2netp.pth` not vendored | Photo in, foreground matte as alpha. No painted pixels | M | `MG-B4` | `test_messenger_cutout_any_subject_png_has_alpha`, `test_messenger_cutout_missing_model_keeps_original`, `test_messenger_u2net_p_fallback_keeps_original_when_missing` |
| AI image, video, and sticker generation | Spec §8. `api/images.ts`, `api/videos.ts`, `sticker_builder.py` | Dropped. D7 forbids them | No route, no Higgs call, no Builder client | S | `MG-B2` deletes them | `test_messenger_no_image_generation_route` |
| Voice actions on real messages | Spec §6. Offline engine passed | The policy, after rebrand | Point it at `mg_messages` and the registered capability | M | `MG-B3`, `MG-B4` | `test_messenger_voice_does_not_send_unconfirmed` |
| Connectors | Spec §4. POC connectors are mocked | Shared connector layer only | Do not demonstrate a grant that is absent. WhatsApp is Export chat only | M | Not the first slice | `test_messenger_missing_connector_labelled` |
| AI workspace | D4. `openUpdates()` sets `screen: "ai"` (`src/store.ts:147-148`) | Keep the 19 Nov workspace. The spec tray line is outdated | Rebrand the visible name. Do not restore a tray that unmounts nothing and also do not invent a second layout | S | `MG-B2` | The Chats row still opens the AI workspace after the rename |
| Seven-theme export | Spec §4 | `export_md.render` on temporal_note | Messenger asks the bridge. It does not write a second tree | S | Gate S | `test_messenger_export_comes_from_bridge` |
| Stage 1 usability | Spec §7 | None | Consenting family and friends. Blanks in `demo-script.md` | M | `MG-B3` on real devices | The Stage 1 table, filled from a run |
| Stage 2 business pilot | Spec §7 | None | Opt-in project group, the approval tap, the cited brief, the denied teammate | L | `MG-B6` | `test_messenger_demo_chain_and_denial` |
| Deck, video, hosting | Spec §9. Internal target 18 Dec 2026 | `demo-script.md`, `sources.md` | Working name Messenger until O2. No excluded logo | M | `MG-B8` | Founder watches the script on a staged build |

## Already true, and not a Messenger build

| Fact | Evidence |
|---|---|
| Offline agent policy suite | 200 passed, 1 Redis skip, `audit.md` |
| Cookie sessions and the approval engine | `actions.py`, `ARCHITECTURE.md` §3 and §9 |
| Community chat tables are not a messenger | `communities.py:1-8` and `:40-48`. D3 leaves them parked |
| No verified `user_id` yet | `auth.py` |
| temporal_note contract on `origin/memory` | `apps/memory/src/temporal_memory/models.py`, `api/app.py`, `privacy/forget.py` |
