# Mirsal — requirements to code

**Status:** planned — awaiting founder approval (23 Nov 2026, Cursor).  
**Reuse column:** nothing is imported while M0 is clean-room. The POC paths are audit evidence. Build agents on a clean-room do not open `Mirsal-redesign`. If the founder later sets M0 to reuse, the import is `git subtree add --prefix=apps/mirsal https://github.com/haitham72/Mirsal-redesign master`, and this column is re-read. S/M/L is the clean-room size.

Spec: `docs/submissions/shared/founder-inputs/03_MIRSAL_AI_MESSENGER_PLAN.md`. POC commit: `6b45ba4`.

| Feature | Source evidence | Reuse candidate | Missing work | Size | Dependency | Acceptance test |
|---|---|---|---|---|---|---|
| Real 1:1 and small-group chat | Spec §2 P0. POC `src/store.ts:106` `seedMessages`; send appends in the browser (`:162-172`) | None until reuse. Behaviour to reimplement: a conversation list and a thread | `ms_conversations`, `ms_memberships`, `ms_messages`. WebSocket fan-out. Two authenticated sessions | L | M0, Gate S, `MS-B2`. Verified `user_id` is B0; until then `session_owner` and no cross-app claim | `test_ms_two_users_send_reload` |
| Contact request before a 1:1 | Spec §2. Community `chat_*` is per-owner demo (`communities.py:40-48`) and is not this store | None | `ms_contact_requests`. Accept, decline, block. No thread until accepted | M | `MS-B2` | `test_ms_d14_no_bulk_or_cold_send` |
| Edit, delete, delivery, read | Spec §2 P0. Not in the POC message model | None | Tombstone keeps `seq` and clears `body`. `ms_receipts` | M | `MS-B2` | `test_ms_edit_delete_receipts` |
| Attachments | Spec §2 P0. POC media is local/demo | None | `ms_attachments` metadata. Object storage. Signed URL only after the membership check | M | `MS-B2` | `test_ms_attachment_member_only` |
| Idempotent send, offline retry, reconnect | Spec §2 P0. POC has no server cursor | None | Unique `(conversation_id, sender_id, client_msg_id)`. Client sends `last_seq` and the server replays | M | `MS-B2` | `test_ms_idempotent_retry` and `test_ms_reconnect_replay` |
| Typing and presence | Spec §2, “where desired” | None | Socket-only. Not stored | S | `MS-B2` | `test_ms_typing_not_persisted` |
| Block and report | Spec §2 P0 | None | Block on the contact request. Report row in `ms_audit` | S | `MS-B2` | `test_ms_block_hides_thread` |
| Isolated demo mode | Spec §2, rule 2 | POC seed data shows the shape of a fixture thread | `provenance=demo_fixture` and a Demo data pill. Seeds are never inserted as real traffic | S | `MS-B2` | `test_ms_demo_pill_and_not_real_traffic` |
| Per-conversation AI Off / Session / Save | Spec §5. POC has no such control | None | `ai_mode` on `ms_memberships`, default off | M | `MS-B2` | `test_ms_ai_default_off` |
| Group consent | Spec §4–§5 | None | One `off` member blocks the prompt. Epoch drops in-flight calls | M | `MS-B4` | `test_ms_group_off_blocks_model` |
| Summarise unread | Spec §2 P1 and §7 | POC chat skills passed offline against fakes (`audit.md`) | Run on authorised `ms_messages`, with message ids and an explicit scope line | M | `MS-B5`, real messages | `test_ms_summary_cites_scope` |
| Search inside a conversation | Spec §2 P1 | Photo pgvector is the wrong index (`api/photos.ts`) | Member-scoped search. A non-member gets 404, including embeddings | M | `MS-B2` for text; embeddings only after Save | `test_ms_non_member_chat_and_embeddings_404` |
| Smart reply, user taps Send | Spec §2 P1 | Voice engine waits on confirmation in offline tests | Draft only. `sender_id` comes from the session when the person taps Send | S | `MS-B5` | `test_ms_suggestion_does_not_send` |
| Voice notes | Spec §2 P1. POC voice WebSocket is dictation, not chat transport | Offline voice tests are behaviour notes, not a port | Store the audio. Transcription labelled unverified. Original remains | M | `MS-B3` | `test_ms_transcript_keeps_original` |
| Decision Keeper | Spec §2 business, §7 | None | Candidate card with who/when/message ids. Status becomes “Recorded in this group” only after a member tap | M | `MS-B5` | `test_ms_decision_stays_candidate_until_tap` |
| Action Tracker | Spec §2, §7 | POC Redis `tasks:{user}` has no evidence and is dropped | Candidate tasks with quotes. Unconfirmed candidates create no `tasks.py` row | M | `MS-B5` | `test_ms_joke_is_not_an_obligation` |
| Approval card and task create | Spec §2.5, §8. `actions.py` `CAPABILITIES` has no messaging or task id (`actions.py:82-103`) | The approval function itself (`approve`, snapshot hash, revision, idempotency key) | Register `workspace.task.create` from `apps/api/app/mirsal/`. Unknown id stays 400. No adapter: `BLOCKED`, draft kept. After a real tap, task state is `open` | L | `MS-B5`, rule 7 | `test_ms_ai_side_effect_needs_approval` |
| Project brief | Spec §2.3, §7 | None | Cited brief of an explicit set of groups. Seeded scene says “this thread”, not “since yesterday”, unless a real window exists | M | `MS-B5` | `test_ms_brief_cites_visible_messages` |
| Knowledge assistant | Spec §2.4 | POC fact-check skill is a demo, not scoped retrieval | Answer from this membership only, with message ids | M | `MS-B5` | `test_ms_qa_scope` plus the 404 test |
| Access denied | Spec §7, §8 | None | Non-member search, task, and answer return 404 | S | `MS-B2` and `MS-B5` | `test_ms_non_member_chat_and_embeddings_404` |
| Third-party reminder | Spec §7 Stage 1 | Outbox pattern in `proactive.py` | No outbox row for anyone but the caller, and only after that person’s tap | S | `MS-B5`, rule 8 | `test_ms_no_reminder_for_another_member` |
| Prompt injection in a message | `ARCHITECTURE.md` §9.1. `Record.text` is data | POC eval gate is offline utterances, not this table | Body cannot send, call a capability, write a fact, or change membership | M | `MS-B2` | `test_ms_message_injection_cannot_act` |
| No bulk or cold send | `PLAN.md` D14. `ARCHITECTURE.md` §10 bans Baileys and Evolution | None | No recipient-list endpoint. Group invites are one accept each | S | `MS-B2` | `test_ms_d14_no_bulk_or_cold_send` |
| No end-to-end-encryption claim | Spec §5. POC has no protocol | None | Copy says encrypted in transit to Mirsal’s server. The server stores plaintext | S | `MS-B2` | `test_ms_copy_has_no_e2ee_claim` |
| Consented memory write | Spec §4. POC `/agents/memory/*` is Redis (`audit.md`) | Bridge plan in `identity-memory-needs.md`. Not a port of the Redis lists | Call `memory_bridge.write_consented` only after Save, the group gate, and Confirm | L | B0 `memory_bridge`, `MS-B4` | `test_ms_save_writes_record_with_evidence` |
| Chat-scoped read | Spec §4 | `read_chat_scope` | Owner plus `mirsal:<conversation_id>` only | M | B0 | `test_ms_read_scope_excludes_other_chat` |
| Forget versus delete | Spec §4, `PLAN.md` forget-by-source | `forget_source` on the memory branch | Two buttons. Forget cascades facts. Delete tombstones messages | M | B0, `MS-B4` | `test_ms_forget_keeps_messages` and `test_ms_delete_keeps_facts` |
| Redis review, then drop | Spec §6, §8 | POC keys `facts:`, `tasks:`, `thread:` | One optional Confirm review. Then delete the keys. No dual write | S | `MS-B4`, and only if M0 is reuse or the founder asks to migrate a named user | `test_ms_unconfirmed_redis_fact_dropped` |
| Images and stickers between two accounts | Spec §8. `api/images.ts` and `api/videos.ts` default to fake. Builder is a separate repo | Call `mirsal-builder-io` by its API when configured. Do not copy it. Fixture mode stays labelled | Generate or pick, store, send, render on the other account. Quota failure stays visible | L | `MS-B3`, provider keys or an honest fixture flag | `test_ms_sticker_two_accounts` and `test_ms_image_quota_failure` |
| Voice actions on real messages | Spec §6, §9 C. Offline engine passed (`audit.md`) | Under reuse, the engine can be wired. Under clean-room, reimplement the policy (in-app early, send waits, paid confirms) without copying files | Point the policy at `ms_messages` and the registered capability, not at `seedMessages` | L | M0, `MS-B3` | `test_ms_voice_does_not_send_unconfirmed` |
| Connectors (Gmail and the rest) | Spec §4. POC connectors are mocked | Shared Dubai-io connector layer only | Do not demonstrate a connector whose grant is absent. WhatsApp is Export chat only | M | B0 / existing connectors, not Mirsal’s first slice | `test_ms_missing_connector_labelled` |
| Compact AI surface | Spec §3. Master replaces the tray (`audit.md`) | Do not port `openUpdates()` → `screen: "ai"` unless question 2 says so | Chat stays mounted. Opening AI does not remount the thread | M | Question 2, `MS-B2` UI | `test_ms_ai_surface_keeps_chat_mounted` |
| Seven-theme export | Spec §4 | The memory service’s markdown export, not a Mirsal writer | Mirsal asks the bridge. It does not write a second tree | S | B0 | `test_ms_export_comes_from_bridge` |
| Stage 1 usability | Spec §7 | None | Consenting family and friends. Measures are blanks in `demo-script.md` | M | `MS-B2` on real devices | The Stage 1 blank table, filled from a run |
| Stage 2 business pilot | Spec §7. Chain in `demo-script.md` | None | Opt-in project group, the approval tap, the cited brief, the denied teammate | L | `MS-B5`, real membership | `test_ms_demo_chain_and_denial` |
| Deck, video, hosting | Spec §9 F. `PLAN.md` §5, internal target 18 Dec 2026 | `demo-script.md`, `sources.md` | Record the working agent. Seeded thread stays labelled. Tunnel or host | M | `MS-B7` after a real `MS-B5` path, or the deck says the capability is still blocked | Founder watches the script on a staged build |

## Already true, and not a Mirsal build

| Fact | Evidence |
|---|---|
| Offline agent policy suite | 200 passed, 1 Redis skip, this audit |
| Cookie sessions and the approval engine | `actions.py`, `ARCHITECTURE.md` §3 and §9 |
| Community chat tables are not a messenger | `communities.py:1-8` and `:40-48` |
| No verified `user_id` yet | `auth.py` |
| Memory contract exists on `origin/memory` | `apps/memory/src/temporal_memory/models.py` |
