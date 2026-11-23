# Mirsal demo script — Best Business AI Agent

**Status:** planned — awaiting founder approval (23 Nov 2026, Cursor).  
**Scene length:** under 4 minutes.  
**What this is:** one seeded project-group scene. It is the business case. The family/friends beta is a separate usability test and is not this demo.

Every seeded line carries a **Demo data** pill (`provenance: demo_fixture`). Every agent step the operator starts is labelled **Demo trigger**. If two authenticated users are not sending live, the opening line says the thread was seeded. Seeded messages are not the two-user acceptance test (spec §8).

`workspace.task.create` is not in `apps/api/app/actions.py` `CAPABILITIES` today. Until that id is registered, the approval card shows the blocker and the draft stays. The operator does not tap through to a success status.

## The work outcome

One opt-in group, **Marina kiosk — week 12**. Members: Rana (operator), Layla (design), Omar (ops). Noor is a teammate on another project and is not a member.

Seeded thread, clock 23 Nov 2026, Asia/Dubai. Each line `as_of` its own timestamp.

| id | who | time | text |
|---|---|---|---|
| `m-0912` | Layla | 09:12 | For the Marina kiosk, the Arabic menu is what we ship this week. I’ll write the copy. |
| `m-0914` | Omar | 09:14 | Agreed. Copy needs to be in by Thursday 27 Nov, 16:00. I’ll hold the printer slot until then. |
| `m-0916` | Layla | 09:16 | Then Thursday 16:00 is the deadline, and I own the copy. |

The five agents sit in one chain (spec §2 and §7):

1. **Summarise** (catch-up utility, the start of the chain). Scope on the card: this conversation, these 3 messages. Citations only. No decision is written.
2. **Decision Keeper.** Candidate: Arabic menu copy ships this week; Layla owns it; deadline Thu 27 Nov 2026 16:00 Asia/Dubai. Evidence: Layla `m-0912` and `m-0916`, Omar `m-0914`. A member taps **Record**. Status becomes **Recorded in this group**.
3. **Knowledge Assistant.** “What did we agree about the Arabic menu?” Answer uses this group’s three messages. It does not read Noor’s chats or unconnected files.
4. **Action Tracker.** Two candidates: (A) write the Arabic menu copy, assignee Layla, due Thu 27 Nov 2026 16:00, evidence `m-0916` and `m-0912`; (B) hold the printer slot, Omar, evidence `m-0914`, left unconfirmed so a later pilot can count extracted versus confirmed. A stays **draft** until the approval tap.
5. **Approval Cards.** One card, one effect, the payload below. One tap. The task row is created only after that tap, state **open**, bound to the snapshot.
6. **Project Brief Agent.** Cited brief of this thread: decision recorded, task open, message ids. Title it “What changed since yesterday?” only when a real time window exists. In this seeded scene the brief says what is in the thread.
7. **Access denied.** Noor searches “Arabic menu”, opens the task link, and asks the same question. Chat, task, and answer are refused. Layla, a member, can open the task.

## Approval card the jury sees

- Effect: create one workspace task in “Marina kiosk — week 12”.
- Destination: this group’s task list. The card names that destination on its face.
- Title: Write the Arabic menu copy
- Assignee: Layla (member)
- Due: 2026-11-27 16:00 Asia/Dubai
- Evidence quote: “Then Thursday 16:00 is the deadline, and I own the copy.” (`m-0916`), also `m-0912`
- Provenance: `demo_fixture` · `as_of`: 2026-11-23 09:16 +04
- Buttons: **Approve** and Cancel
- Idempotency-Key: `demo-marina-task-a-001`

```text
capability_id: workspace.task.create   # proposed; not in CAPABILITIES today
revision: 1
snapshot_hash: <64 hex of this snapshot; Demo data>
fields:
  group: "Marina kiosk — week 12"
  title: "Write the Arabic menu copy"
  assignee_member_id: "member-layla"
  due_at: "2026-11-27T16:00:00+04:00"
  evidence_message_ids: ["m-0916", "m-0912"]
  provenance: "demo_fixture"
  as_of: "2026-11-23T09:16:00+04:00"
shares: [group, title, assignee_member_id, due_at, evidence_message_ids]
effect: "Create this task in this group."
```

`inferred` is not valid on this card (`ARCHITECTURE.md` §2). Title, assignee, and due time are copied from the seeded lines. A changed assignee, due time, or message id invalidates the approval. After the tap the audit line records who tapped, when, and the idempotency key. The visible state is **open**.

## Spoken script

**0:00–0:20.** “This is a project group, Marina kiosk, week 12. The three messages were seeded. Demo data. I start each agent step myself. Demo trigger. Traffic to the server is ordinary transport. Nothing here calls a government system.”

**0:20–0:45.** Show Layla 09:12, Omar 09:14, Layla 09:16.

**0:45–1:10. Summarise. Demo trigger.** Catch-up of these 3 messages. Three citations. No decision is written.

**1:10–1:40. Decision Keeper. Demo trigger.** Candidate card with owner, deadline, and who said it. Tap **Record**. “It was a candidate until that tap. The status is recorded in this group.”

**1:40–2:05. Knowledge Assistant. Demo trigger.** “What did we agree about the Arabic menu?” The answer quotes the deadline and the owner and links the three ids. “It can see this group only.”

**2:05–2:30. Action Tracker. Demo trigger.** Keep “Write the Arabic menu copy”. Leave “Hold the printer slot” unconfirmed. Task A is still a draft.

**2:30–3:05. Approval.** Read destination, title, assignee, due, quote, `demo_fixture`, and “Create this task in this group.” Tap **Approve** once. The task row appears, state **open**. “Open means the task exists in this group.” If the capability is not registered, read the blocker and leave the draft.

**3:05–3:25. Project Brief. Demo trigger.** Decision, open task, message ids. “These citations are this seeded thread.”

**3:25–3:45. Access denied.** Noor is not in the group. Search, task link, and the same question fail. Layla opens the task.

**3:45–4:00.** “A decision tied to three messages. A task that exists because I approved that payload. A brief that cites the messages. A teammate with no access.”

Leave off stage: WhatsApp or Meta marks, an end-to-end-encryption label, a live Salik/DEWA/RTA or calendar send, the words Confirmed, Paid, Booked, Filed, Verified, Delivered, any before/after percentage, and any line that the family beta was a business pilot.

## Stage 1 and Stage 2 stay apart

**Stage 1 — family/friends beta (usability).** Founder, mother, sister, and consenting friends. Observe onboarding, recovery, 1:1 and group send/receive, attachments, voice notes, stickers, reconnect, two devices, delete/forget. AI stays off until that person turns it on for that thread (Off / Session only / Save approved memories). The one AI check: a friend proposes a day to meet; a reminder is offered to the account owner and is created only after that owner confirms.

**Stage 2 — opt-in team pilot.** The chain above, with consenting members. Outsiders are the access-denied case.

### Blanks to fill after a run

These are observations to record. The deck prints the blanks.

| Stage | Record | Unit |
|---|---|---|
| 1 | Time from install to a message the other person can read | minutes |
| 1 | Device A send appears on device B after reload | trials, pass/fail |
| 1 | Tester can say which AI setting is on | correct / asked |
| 1 | Delete/forget and accidental-upload cases completed | count |
| 1 | Reminder created only after the owner’s tap | pass/fail |
| 2 | Minutes to locate the decision by scrolling, same person, same thread | minutes |
| 2 | Minutes to locate it from the Decision Keeper card | minutes |
| 2 | Candidate actions extracted | count |
| 2 | Of those, actions a human confirmed | count |
| 2 | Approval taps on an exact payload | count |
| 2 | Approvals invalidated because a field changed | count |
| 2 | Access-denied checks that held | pass/fail |
| 2 | Brief citations that open a message the caller may read | count |

If Stage 2 has not been run, the deck says “to be recorded”.

## Ten-slide outline

1. **The work outcome.** A recorded decision, one approved task, a cited brief, a denied teammate, in one project group. No number. Spec §1 caveat, §7 chain.
2. **Who it is for.** A small team coordinating in a messenger. Stage 2 is the opt-in project group. Stage 1 is usability and is a separate test. No number, unless the founder accepts the ministry citation in `sources.md` (lead re-fetch timed out).
3. **The coordination load, as context.** McKinsey estimate, 2012: 28% email, 19% finding information, 14% internal collaboration. Microsoft, reported, 2025: 117 emails a day; 153 Teams messages a weekday; 48% of employees say work feels chaotic. None of these is a Mirsal before/after. Drop the Microsoft lines that disagree with their own method note (`sources.md`).
4. **Why smaller firms feel a size gap.** OECD, 2024: SME turnover per person employed was 65% of large firms, unweighted average, 33 countries. That is an official size gap. It is context, and the slide does not say chat causes it. Gallup 2025 “20% engaged” is optional and is engagement, not missed tasks. Leave the dollar estimate off.
5. **Five agents, one chain.** Summarise, Decision Keeper, Knowledge Assistant, Action Tracker, approval, task, brief. Each step is started by a person. No number.
6. **The approval.** One tap. Exact title, assignee, due time, message ids, destination. Provenance on the card is `demo_fixture`. No number.
7. **Access.** Layla opens the task. Noor cannot open the chat, the task, or the answer. Group content is not silent long-term memory. No number.
8. **What we will measure.** The blanks above. The deck prints the blanks.
9. **What this build will say on stage.** Ordinary server transport, original visual language, honest draft when no adapter exists, demo mode until two authenticated users pass spec §8, written rights before any office-origin asset is submitted. No number.
10. **What the jury is asked to watch.** The tap, the open task, the cited brief, the refusal. Finalists present a working agent live (`PLAN.md` §5). This script is the scene. It becomes that proof when Stage 2 runs on real membership. The category grant is USD 150,000 (`PLAN.md` §5, official page last updated 15 Oct 2026). That is the prize.
