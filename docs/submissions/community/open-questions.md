# Dubai-io Community — Founder questions

**Status:** planned — awaiting founder approval (23 Nov 2026, Muse). At most 5 blocking; each with a recommended answer, what it blocks, and a deadline. P2 (shared contract) also needs these answered at the founder gate.

## Already answered — not re-asked

- **Persocial:** Community replaces Persocial; nothing to import (D2).
- **Inbox boundary:** notifications only; Community builds no messenger; "message this person" hands off to the Messenger once shared identity exists; parked `chat_*` tables are not extended (D3).
- **Memory engine:** temporal_note via `memory_bridge/`; Hindsight/Honcho and their AC-1/MEM-01 gates do not apply (D5).
- **Cross-app memory shape:** interest features only, never raw text; writes scoped and attributable; Forget propagates (`identity-memory-needs.md` — for P2 to fold into the one contract, not a founder question).

## Blocking (5)

### Q1 — Are the "last four social mockups" the Higgsfield v3 community frames?

No file carries that name; the phrase is prose in the spec. Lane B's inspected candidate set is the four desktop frames `l01` (hub), `l05` (post/Q&A), `l08` (for-you feed), `l09` (private handoff) plus phone mirrors `m02/m04/m08/m09` in `design/references/v3-higgsfield/`.
**Recommendation:** confirm this set as the visual authority (with `r/dubai` naming stripped, Stories rail dropped per spec P2 deferral). If a different set was meant, point us at it.
**Blocks:** CM-B10 web app fidelity and the founder visual-review gate. **Deadline:** before CM-B10 starts.

### Q2 — Minors policy: age gate, or adults-only at launch?

Lane C found zero age/minor handling in the spec or parked code, while rule 9 forbids inferring third parties' and minors' details. Community cannot safely design groups, discovery ranking, or moderation without a ruling.
**Recommendation:** launch adults-only (18+ self-declaration at sign-up, no age inference, no profiling of anyone age-unknown beyond the declaration), synthetic fixtures for all test users; revisit a supervised-teen model only as a separate, later decision.
**Blocks:** CM-B3 (groups), CM-B7 (moderation/minors tests), CM-B12 multi-user test eligibility. **Deadline:** founder gate, before CM-B3.

### Q3 — Private groups: who may invite, and who moderates?

Parked groups have open join and no roles, so the invite/approval and moderator model is a fresh product decision, not an audit finding.
**Recommendation:** private = invisible to non-members; join by member invite + moderator approval; one owner, named moderators with pin/remove powers; every moderator action logged in `cm_moderation_events` and reversible by the owner.
**Blocks:** CM-B3 design and its failure-path tests. **Deadline:** founder gate, before CM-B3.

### Q4 — Scene C topic and source allowlist for the Community Answer demo

The demo needs a civic-flavoured question whose answer is retrievable from live public sources at record time, with no implication of a civic integration (none exists).
**Recommendation:** pick one topic from official public information pages (e.g. a Dubai government service-guide question answered from the authority's own public pages), allowlist those publishers in the agent, and keep a non-civic fallback topic rehearsed. Sources are cited, never presented as an executed transaction.
**Blocks:** CM-B9 Community Answer scope and the 100% sourced-answer integrity metric. **Deadline:** before CM-B9; re-confirm at CM-B12 recording.

### Q5 — Packaging surface for 18 Dec: hosted, tunnelled, or local-only?

The internal target (Fri 18 Dec 2026) needs deck + video + hosting-or-tunnel + a multi-user test, but no deployment or budget is currently authorised for this entry.
**Recommendation:** tunnelled demo from the founder's machine for the video and the n ≥ 5 multi-user test (consenting adults, synthetic fixtures), with a hosted stub only if you approve spend; either way the multi-user test runs against the real `cm_` backend, not the parked demo.
**Blocks:** CM-B11/CM-B12 planning and the multi-user test write-up. **Deadline:** at approval of CM-B11.

## Non-blocking (listed, defaults proceed)

- Group size caps, reaction set (beyond the parked ±1 vote), and bookmark/share mechanics: builder's choice within the gap matrix; revisit after the multi-user test.
- Whether Discover also becomes a search destination tab later: spec says feed lane; keep it a lane for P1.
- Member-count display while seeded: always `Demo data` pill; real counts only from `cm_` membership rows.
- Final product name/branding for Community beyond "Dubai-io Community": working name stands until you say otherwise; no Meta-like marks either way.
