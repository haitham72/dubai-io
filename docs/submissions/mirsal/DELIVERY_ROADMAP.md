# Mirsal delivery roadmap

**Status:** planned — awaiting founder approval (23 Nov 2026, Cursor).

Order follows spec §9. Mirsal code starts only after the founder decides **M0** and **Gate S** has passed (`docs/submissions/CLAUDE.md` §3). A clean-room decision means the people who build `apps/mirsal/` do not open `D:\Vscode\Mirsal-redesign`.

Owned paths on `business`, and only these: `apps/mirsal/**`, `apps/api/app/mirsal/`, `apps/api/tests/test_mirsal_*.py`, `fixtures/mirsal/`, `docs/submissions/mirsal/**`. RLS notes live in `apps/mirsal/supabase/`. No new file under `supabase/migrations/`. `communities.py`, `actions.py`, and `main.py` stay untouched; capabilities are registered from the Mirsal package. Entrypoint, when a server is needed: `app.mirsal.server:app` on port 8070.

Internal package target: Fri 18 Dec 2026 (`PLAN.md` §5). That date is a deck, a video, a host or tunnel, and a small user test. It is not a claim that Gate S has already passed.

## MS-B1 — Audit and IP

**Depends on:** nothing.  
**Owns:** the docs in this folder. No application code.  
**This slice is the current commit.**

| | |
|---|---|
| Happy path | A reader can see the POC class for every spec §0 row and every spec §6 module, with the rerun command and the 200 / 1 result, and can see why M0 is clean-room. |
| Failure path | A path that is only a filename is not marked working. Redis skip, unread typecheck, and unread Vercel handlers stay unverified. |
| Demo beat | None. It unlocks the founder’s M0 answer. |

## MS-B2 — Real chat core

**Depends on:** M0 decided, Gate S passed. B0 identity for a non-null `verified_user_id`. Until that link exists, rows use `session_owner` and the UI does not say the same person is in Quest or Community.  
**Owns:** `apps/mirsal/` client and `apps/mirsal/supabase/` notes, `apps/api/app/mirsal/` transport, `apps/api/tests/test_mirsal_chat.py`, `fixtures/mirsal/chat/`.

Transport: cookie-authenticated WebSocket, `ms_*` tables in schema `dubaiio`, idempotent `client_msg_id`, reconnect by `last_seq`. Media in object storage with a signed URL after the membership check. Demo fixtures wear a Demo data pill and are not the two-user test.

| | |
|---|---|
| Happy path | `test_ms_two_users_send_reload` — two sessions send, edit, delete, and see the thread again after restart. `test_ms_idempotent_retry`, `test_ms_reconnect_replay`. |
| Failure path | `test_ms_non_member_chat_and_embeddings_404`. `test_ms_d14_no_bulk_or_cold_send`. `test_ms_message_injection_cannot_act`. `test_ms_copy_has_no_e2ee_claim`. |
| Demo beat | Two devices, one real message each way. The business script stays labelled Demo data until this is green. |

## MS-B3 — Creative and voice on real chats

**Depends on:** `MS-B2`, M0. Under clean-room the policy is reimplemented (a send waits for the person, a paid action waits for the card). `mirsal-builder-io` is called as a service when its URL is configured. Its files are not copied.  
**Owns:** `apps/api/app/mirsal/creative.py`, voice adapter beside it, `apps/api/tests/test_mirsal_creative.py`, `fixtures/mirsal/creative/`.

| | |
|---|---|
| Happy path | `test_ms_sticker_two_accounts` — one account produces or picks a sticker and the other account’s thread shows it. |
| Failure path | `test_ms_image_quota_failure` — missing Higgs, Builder, or quota leaves a visible failure and sends nothing. `test_ms_voice_does_not_send_unconfirmed`. |
| Demo beat | Optional. The business case does not depend on a sticker. Fixture mode stays on screen if the provider is absent. |

## MS-B4 — Scoped memory

**Depends on:** `MS-B2`, B0 `memory_bridge` with `read_chat_scope`, `write_consented`, and `forget` as in `identity-memory-needs.md`.  
**Owns:** `apps/api/app/mirsal/memory_client.py` (calls the bridge, does not store facts), `apps/api/tests/test_mirsal_memory.py`, `fixtures/mirsal/memory/`.

| | |
|---|---|
| Happy path | `test_ms_save_writes_record_with_evidence` — Confirm writes one record whose evidence id is the message, source `mirsal:<conversation_id>`. |
| Failure path | `test_ms_ai_default_off` and `test_ms_group_off_blocks_model`. `test_ms_forget_keeps_messages`. `test_ms_delete_keeps_facts`. `test_ms_unconfirmed_redis_fact_dropped` only if a migration runs. |
| Demo beat | Privacy walkthrough: Off, then Save, then Forget. Not the jury’s work outcome. |

## MS-B5 — Business agent

**Depends on:** `MS-B2`. Memory (`MS-B4`) is not required for the chain. The chain uses message ids in the chat tables.  
**Owns:** `apps/api/app/mirsal/capabilities.py` (registers `workspace.task.create` into the existing registry from this package), `apps/api/app/mirsal/business.py`, `apps/api/tests/test_mirsal_business.py`, `fixtures/mirsal/marina/`.

The card lists the exact fields in `demo-script.md`. One tap. State after a real adapter is `open`. No adapter: the card shows the blocker and the draft remains. Model text never sets Completed, Confirmed, or Paid.

| | |
|---|---|
| Happy path | `test_ms_demo_chain_and_denial` — summarise cites the three fixture ids, Record is a tap, one approval creates one task, the brief cites those ids, the non-member is refused. |
| Failure path | `test_ms_ai_side_effect_needs_approval` (unknown capability, and a missing adapter). `test_ms_joke_is_not_an_obligation`. `test_ms_no_reminder_for_another_member`. `test_ms_decision_stays_candidate_until_tap`. |
| Demo beat | The four-minute script. Every seeded line is Demo data. Every operator-started step is Demo trigger. |

## MS-B6 — Cross-account verification

**Depends on:** `MS-B2`, `MS-B5`, and `MS-B4` if the privacy walkthrough is in the same recording. Gate S still green.  
**Owns:** `apps/api/tests/test_mirsal_e2e.py`, notes in `docs/submissions/mirsal/log.md`. No new product surface.

| | |
|---|---|
| Happy path | The two-user test, the denial test, and a restart of the API process with the thread still there. |
| Failure path | A third session, an injection message, and a Save toggle flipped to Off mid-flight. |
| Demo beat | The recording may include this only for tests that were actually run. The log cites the command and the output. |

## MS-B7 — Deck, video, hosting

**Depends on:** `MS-B5` green on a staged build, or the deck says the task step is still blocked. Question 5 if the logo or the name is still unsigned.  
**Owns:** `docs/submissions/mirsal/` packaging notes only, unless a tunnel config is required and it fits `apps/mirsal/`. The deck file stays out of the repo until the founder asks to add it.  
**Demo beat:** the script in `demo-script.md`, ten slides, sources only from `sources.md`. Host or tunnel. Prize figure only as the contest grant.

| | |
|---|---|
| Happy path | A reviewer plays the video and sees the tap, the open task, the citations, and the refusal, with both pills visible. |
| Failure path | If `workspace.task.create` is not registered, the video shows the blocker and the draft. It does not cut to a success. |

## MS-B8 — Stage 2 pilot

**Depends on:** `MS-B2` and `MS-B5` on real membership, consenting participants, a project group that is not the family chat.  
**Owns:** no new code required. The blank table in `demo-script.md` is filled in `log.md` from the session. Counts only. No percentage computed in the deck until both counts in a pair exist, and even then the deck quotes the counts.

| | |
|---|---|
| Happy path | The group records a decision, confirms at least one action, and completes one approval. Minutes to find the decision are written down both ways. |
| Failure path | A person who is not a member cannot open the chat, the task, or the answer. That pass/fail is written down. |
| Demo beat | Replaces the seeded thread in the jury cut only after this session has happened. Until then the jury cut stays labelled. |

## What is deliberately later

Voice and video calling (spec P1). A second messaging stack inside Community. Any write to `apps/memory/` from this branch. Gemini. WhatsApp linked-device or Evolution. An end-to-end-encryption label.
