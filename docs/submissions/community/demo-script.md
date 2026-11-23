# Dubai-io Community — Demo script (Scenes A–D, ≤ 4 minutes)

**Status:** planned (revised to D1-D10) — awaiting founder approval. Source: spec §6 (`docs/submissions/shared/founder-inputs/02_DUBAI_IO_COMMUNITY_PLAN.md:79`). Persona throughout: one newcomer test account, the same verified `user_id` in Quest and Community. On stage, seeded feed filler carries a visible `Demo data` pill and any jump the user did not cause is labelled `Demo trigger` (root `CLAUDE.md` rules 2 and 8). No Meta affiliation, no civic-integration claim: Scene C retrieves public information; it does not execute a government transaction.

| Time | Scene | On-screen action | Narration gist | Evidence shown |
|---|---|---|---|---|
| 0:00–0:55 | **A — New resident** | Fresh sign-up → pick public interests → group recommendations appear, each with *Why this?* → tap one → join → post a comment | "Three weeks in Dubai. She tells us only what she chooses — two taps later she's in rooms full of people who already solved her problems." | *Why this?* chip naming the exact interest used; group cards. Seeded posts carry `Demo data` pill |
| 0:55–1:50 | **B — Same person, Quest → Community** | Cut to Quest (same `user_id` shown) → back in Community, toggle *Cross-app interest-only personalisation* ON → feed re-ranks | "One identity, two apps. She allows one interest — never the conversation — to travel. Watch the feed change; watch what doesn't appear." | Settings: scope toggle + source list. Caption/payload view proving only an interest label crossed, never private text (spec §4 example) |
| 1:50–2:55 | **C — Sourced Community Answer** | Ask "How can I find reliable local resources about [verified civic topic]?" → agent retrieves sources → draft with citations → user edits → **Approve exact revision + destination** → posts to the test community | "The agent does the reading, a human does the publishing. Nothing posts until she approves these exact words, in this exact group." | Citation cards (source, publisher, timestamp); approval sheet with final revision + destination; published post with citations attached |
| 2:55–4:00 | **D — Memory loop + Forget** | Save a public discussion → *Connected Memory* shows the scoped signal ("saved from Community, topic only") → open Quest → it recalls the topic as a preference **within scope** → tap **Forget** → Quest no longer recalls it; Community signal gone | "Saving is not surveillance. The signal is labelled, scoped, and hers to erase — and erasing works everywhere, on camera." | Provenance + scope on the memory item; before/after recall in Quest; Forget propagating to both apps |

## Real vs seeded — say this on stage

| Real (must genuinely work) | Seeded / labelled |
|---|---|
| Sign-in + same `user_id` across Quest/Community; join/comment persistence after restart; *Why this?* from the user's own chosen interests; citation retrieval from live public sources; approve-exact-revision → post; save → scoped signal → scoped recall → Forget propagation | Feed filler posts/profiles = `Demo data`; fast-forward between apps = `Demo trigger`; test-community members. The AI draft **never** auto-publishes (spec §7 gate) |

## Run rules

- The script runs end to end three times without a manual fix before it counts as ready (slice CM-B11).
- Scene C needs genuinely retrievable public sources at record time; keep a non-civic fallback topic ready.
- Any failure of the sourced-answer integrity metric (see `sources.md` metrics) blocks the take.
