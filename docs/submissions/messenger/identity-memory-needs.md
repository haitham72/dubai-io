# What Messenger needs from shared identity and memory

**Status:** planned (revised to D1–D6) — awaiting founder approval (23 Nov 2026, Cursor).

Messenger does not build this. B0 on `contest-shared` does, in `apps/api/app/identity/` and `apps/api/app/memory_bridge/`. The memory engine is the rewritten **temporal_note** package on branch `memory` (D5):

- HTTP API: `apps/memory/src/temporal_memory/api/app.py` (`create_app`, `/health`, `/v1/owners`, `/v1/tokens`, job claim and result)
- MCP: `apps/memory/src/temporal_memory/mcp/server.py` (`create_mcp_app`)
- Contract: `apps/memory/src/temporal_memory/models.py`
- Forget: `apps/memory/src/temporal_memory/privacy/forget.py` (`forget_source`, `plan_forget`)
- Readable export: `apps/memory/src/temporal_memory/api/export_md.py` (`render`)

Hindsight and Honcho are not used. Where the founder spec says `MemoryBackend` or `ScopeGuard`, read temporal_note. Hindsight’s `AC-1` and `MEM-01` are not gates for this entry. The bridge is a client of temporal_note and never a second engine. Until temporal_note is on `main`, Messenger tests use a clearly named fake with the operations below.

Checked on 23 Nov 2026: `apps/api/app/memory_bridge/` is not in this tree. `auth.py` is Google OAuth grants on the anonymous cookie. There is no verified-JWT `user_id`.

`models.py`, read with `git show` and the branch not checked out:

- `Record`: `owner`, `source`, `at`, `author`, `text`, `generation`. Text is untrusted data, never instructions. `generation` is bumped by forget-by-source.
- `Fact`: `evidence` is a list of record ids and is required. `provenance` is `user_supplied | inferred | provider_confirmed | demo_fixture`.
- The model does not apply facts. A worker returns `ExtractionOutput`. Validator then applier.

## Identity

| Operation | Behaviour |
|---|---|
| `resolve_user(cookie)` | `{session_owner, verified_user_id \| null}`. Today `verified_user_id` is null. |
| `link_session(session_owner, verified_user_id)` | Once. Refuse a merge on display name. |
| Stable id | The same `verified_user_id` Quest and Community resolve for that person. |

Messenger copies that id into `mg_user_link` only. The row has no bio and no facts. Until B0, chat rows may use `session_owner`, and the UI must not say the same person is signed in across the three apps.

## Memory bridge

Chat rows stay in `mg_*`. A message becomes memory only through these calls.

| Operation | When Messenger calls it | What it does |
|---|---|---|
| `read_chat_scope(owner, source, limit)` | The signed-in owner asks about one conversation, and that conversation’s control allows the read. | Facts for that owner whose evidence records use `source = messenger:<conversation_id>`. Does not return `mg_messages`. Does not return another owner’s facts. |
| `write_consented(owner, *, source, actor, at, text, message_id, provenance)` | Save is on, the group gate passed, and the owner tapped Confirm on that candidate. | Inserts one `Record`. `source` is `messenger:<conversation_id>`. Record id is `mgmsg:<message_id>`. `text` is data. Then enqueue extract for that record. A `Fact` exists only after validate and apply, with that record id in `evidence`. |
| `forget(owner, record_ids)` | The owner chooses “Forget memories from this chat”. | Calls `forget_source`. Derived facts cascade. `mg_messages` stay. |

`actor` is the confirming user. `at` is the source message time. A hypothesis may be shown as “I noticed” with Confirm / Edit / Not true / Forget. It does not pre-fill a field, sit on an approval card, send a proactive message, or set a status (`ARCHITECTURE.md` §7). Family, faith, and health are never inferred (rule 9). Other people’s words may be stored only as evidence. `Fact.owner` is the confirming user.

## Consent toggles

Stored on `mg_memberships.ai_mode`, default **off**, per member, per conversation.

| Mode | Model | Memory |
|---|---|---|
| Off | No call, no embedding, no bridge write. | None. |
| Session only | Bounded recent text of this conversation, while the socket is open. The model does not write a chat message. | None. |
| Save approved memories | Same as Session. | One bridge write per Confirm tap. |

**Group gate.** A model may see the transcript only when every active member is `session` or `save`. One `off` member blocks the call. A join, leave, or switch to `off` drops in-flight calls. **Save** also requires `ai_mode=save` on the caller and on every member whose message is cited.

## Forget is two controls, both shown

- **Forget memories from this chat** calls `forget`. The chat remains.
- **Delete chat** tombstones `mg_messages` and removes attachment objects. Derived memories remain until Forget is also chosen.

Withdrawing Save stops future writes and offers Forget. It does not delete the chat by itself.

## The redesign’s Redis store is not this

The redesign file `agents/mirsal_agents/store.py` is a key-value get/set. The route identity is the header `x-mirsal-user`, or the string `"demo"`. The rebrand renames that header to `x-messenger-user`. Neither header is a Dubai-io user. The real path does not accept it. Those keys are not inserted as `Fact` rows, because `evidence` is required. There is no ongoing dual write. `/agents/memory` in the redesign is not temporal_note.

## What Messenger will not ask memory to do

- Rank a Community feed from raw chats. Community may later read a consented interest feature only, through the P2 contract.
- Treat a Gmail, Outlook, YouTube, Chrome, or WhatsApp body as a Messenger message. WhatsApp is manual Export chat only.
- Claim a Hindsight acceptance gate. D5 says those gates do not apply here. A temporal_note test is claimed only after this team runs it.
