# What Mirsal needs from shared identity and memory

**Status:** planned — awaiting founder approval (23 Nov 2026, Cursor).  
Mirsal does not build this. B0 on `contest-shared` does, in `apps/api/app/identity/` and `apps/api/app/memory_bridge/`. The memory engine is the other team’s `apps/memory/` on branch `memory`. Mirsal will not add a second facts bank.

Checked on 23 Nov 2026: `apps/api/app/memory_bridge/` is not in the tree. `auth.py` is Google OAuth connection grants on the anonymous cookie `dubaiio_lab_session`. `actions.py` returns `mode: anonymous_lab_session`. There is no verified-JWT `user_id`.

The contract Mirsal will call is `origin/memory:apps/memory/src/temporal_memory/models.py` (read with `git show`, branch not checked out):

- `Record` (`models.py` around the raw-source dataclass): `owner`, `source`, `at`, `author`, `text`, `generation`. The module comment says text is untrusted data, never instructions. `generation` is bumped by forget-by-source.
- `Fact`: `evidence` is a list of record ids and is required. `provenance` is `user_supplied | inferred | provider_confirmed | demo_fixture`. Default in that dataclass is `inferred`.
- `forget_source(owner, record_ids)` bumps generation and cascades. It does not delete chat rows.
- The model does not apply facts. A worker returns `ExtractionOutput`. Validator then applier.

## Identity

Mirsal needs three operations. It copies the result into `ms_user_link` and nowhere else. That row has no bio, no interests, and no facts.

| Operation | Behaviour |
|---|---|
| `resolve_user(cookie)` | `{session_owner, verified_user_id \| null}`. Today `session_owner` is `sessions.owner` and `verified_user_id` is null. |
| `link_session(session_owner, verified_user_id)` | Once. Refuse a merge on display name (`ARCHITECTURE.md` §9.2). |
| Stable id | The same `verified_user_id` Quest and Community resolve for that person. |

Until B0, Mirsal can key rows by `session_owner` and must not claim the same person is signed in across the three apps.

## Memory bridge

Chat rows stay in `ms_*`. A message becomes memory only through the calls below.

| Operation | When Mirsal calls it | What it does |
|---|---|---|
| `read_chat_scope(owner, source, limit)` | The signed-in owner asks about one conversation, and that conversation’s control allows the read. | Returns facts for that owner whose evidence records use `source = mirsal:<conversation_id>`. Does not return `ms_messages`. Does not return another owner’s facts. |
| `write_consented(owner, *, source, actor, at, text, message_id, provenance)` | Save is on, the group gate passed, and the owner tapped Confirm on that exact candidate. | Inserts one `Record`. `source` is `mirsal:<conversation_id>`. Record id is `msmsg:<message_id>`. `author` is the message author. `text` is data. Then enqueue `extract.live` for that record. A `Fact` exists only after validate and apply, with `evidence` containing that record id. |
| `forget(owner, record_ids)` | The owner chooses “Forget memories from this chat”, or withdraws Save and then confirms Forget. | Calls `forget_source`. Derived facts cascade. `ms_messages` stay. |

`actor` is the confirming user. `at` is the source message time, carried on the record. A hypothesis (`provenance: inferred`, or `status: hypothesis`) may be shown as “I noticed” with Confirm / Edit / Not true / Forget. It does not pre-fill a field, sit on an approval card, send a proactive message, or set a status (`ARCHITECTURE.md` §7). Family, faith, and health are never inferred (rule 9). Other people’s words may be stored only as evidence records. `Fact.owner` is the confirming user. No fact is created about a third party.

## Consent toggles

Stored on `ms_memberships.ai_mode`, default **off**, per member, per conversation.

| Mode | Model | Memory |
|---|---|---|
| Off | No call, no embedding, no bridge write. | None. |
| Session only | Bounded recent text of this conversation, while the socket is open. Discarded with the reply. The model does not write a chat message. | None. |
| Save approved memories | Same as Session. | One bridge write per Confirm tap. |

**Group gate.** A model may see the transcript only when every active member is `session` or `save`. One `off` member blocks the call and no prompt is built. A join, leave, or switch to `off` drops in-flight calls. **Save** also requires `ai_mode=save` on the caller and on every member whose message is cited.

Default for a new membership, including someone who just joined, is Off.

## Forget is two controls, both shown

- **Forget memories from this chat** calls `forget`. The chat remains.
- **Delete chat** tombstones `ms_messages` and removes attachment objects. Derived memories remain until Forget is also chosen.

Withdrawing Save stops future writes and offers Forget. It does not delete the chat by itself.

## Redis facts in the POC

`agents/mirsal_agents/store.py` is a key-value get/set/delete/push. Identity on those routes is `x-mirsal-user` or `"demo"`. That header is not a Dubai-io user. The real path does not accept it.

| POC key | Holds | Bridge |
|---|---|---|
| `facts:{user}` | Up to 30 strings. No time, evidence, subject, or provenance. | Not inserted as `Fact`, because `evidence` is required. Optional one-time review: the signed-in user re-states a line, Mirsal writes one `Record` (`source=mirsal:poc-review`), and a `Fact` with `provenance=user_supplied` only after Confirm. Every unconfirmed string is dropped. |
| `tasks:{user}` | Dicts, 30-day TTL. | Dropped. They are not `tasks.py` rows and they have no assignee consent. |
| `thread:{user}` | Last 200 `{role, text, at}`. | Dropped. Session scratch, not chat and not memory. |

After the user finishes or skips the review, those three keys are deleted. There is no ongoing dual write.

## What Mirsal will not ask memory to do

- Rank a Community feed from raw chats, mail, or family details. Community may later read a consented interest feature only, through the P2 contract, never through Mirsal’s tables.
- Treat a Gmail, Outlook, YouTube, Chrome, or WhatsApp body as a Mirsal message. Those sources stay on the shared connector layer. WhatsApp is manual Export chat only.
- Claim `AC-1`, `AC-2`, or `AC-3`. They are unproven until the memory team runs them.
