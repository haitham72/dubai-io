# Cursor Plan Review — Dubai-io Contest Package

**Reviewer:** Cursor (Auto)  
**Date:** 9 October 2026  
**Scope reviewed:** `dubai-io-implementation-plan.md` + `dubai-io-handoff/` (01–07)  
**Baseline:** handoff v1.2 (+ vision addendum 07) · implementation plan dated 8 October 2026  
**Status:** Proposed approval with conditions

---

## Verdict

**Approve with conditions.** Strong contest plan: honest scope, coherent hero journey, and architecture sized for a Personal AI Agent entry. Do not start application coding until Phase 0 closes the hard gaps below.

---

## Package reviewed

| Artifact | Role |
|---|---|
| `dubai-io-implementation-plan.md` | Architecture review, gap list, phased gates |
| `01-PRODUCT-VISION.md` | Product identity and horizons |
| `02-SYSTEM-ARCHITECTURE.md` | Modules, state, events, trust boundaries |
| `03-SCENARIO-LIBRARY.md` | S01–S25 backlog and flagship examples |
| `04-SERVICE-INTEGRATION-STANDARD.md` | Provider levels, manifests, action cards |
| `05-CONTEST-MVP-AND-VALIDATION.md` | Contest MVP, demo, evals, research register |
| `06-DETAILED-USE-CASES.md` | Expanded scenarios, T/X overlays, acceptance tests |
| `07-AI-NATIVE-SERVICE-ECOSYSTEM.md` | Living ecosystem / mini-app vision addendum (not MVP) |

---

## What’s strong

1. **MVP freeze is right.** One journey — iron near Marina → approve sharing → merchant acknowledgement → damage/dispute RAG in the same chat — proves companion + real action + civic trust without drowning in S01–S25.
2. **Truth-in-status discipline.** Explicit bans on fake `Booked` / `Paid` / `Confirmed`, portal-first merchant integration, and `UNKNOWN_STATUS` over invented success match what this championship should reward.
3. **Architecture is contest-sized.** Modular monolith (Next.js + FastAPI + one LangGraph + PostgreSQL) is the correct call; premature microservices would burn the timeline.
4. **Implementation plan earns its keep.** Correctly flags real handoff inconsistencies: `QUOTED` missing from architecture lifecycle, `approval_required` vs `requires_approval`, unbound action IDs, outbox/idempotency, RAG release gates, evidence upload underdesign.
5. **Category fit.** Best Personal AI Agent matches the product; civic RAG is a trust layer, not a fines-bot pivot.
6. **Timeline vs official contest.** Registration opened 7 October 2026; build Nov–Jan; close around Dec/Jan; semis February; Grand Final early May 2027. The Oct→Jan build window works if scope stays frozen.
7. **Document 07 alignment.** The ecosystem / registry / fewer-capability-contracts model reinforces long-term vision without requiring contest delivery of mini-apps or 1,000 MCP connections — treat it as narrative and extension design only.

---

## What’s weak / risky

| Risk | Why it matters |
|---|---|
| Contest artifacts still fuzzy | Plan admits rules / IP / category weren’t fully verified. Submission needs prototype + pitch deck + demo video — Phase 0 must lock exact deliverables and IP terms. |
| 24–35 engineer-days is optimistic | For one builder: auth, SSE chat, LangGraph, merchant inbox, RAG + citations, bilingual UX, staging, evals, demo. Treat as calendar weeks with parallel merchant/source work. |
| Merchant + corpus are critical path | Code cannot fake Phase 2/3. Recruit one consenting pilot and lock consumer-rights sources in Phase 0. |
| Doc sprawl invites scope creep | Seven handoff files + plan + X01–X20 candidates. Agents will implement vision. Need one **MVP freeze** artifact that overrides everything else. |
| Contracts not machine-owned yet | Gaps are listed but not closed as a single JSON Schema / state machine. Fix before writing agent tools. |
| ≥95% RAG target | Fine as a release aspiration; for contest, prioritize abstention + citations over chasing 95% on day one. Report numerators honestly. |
| Plan file pollution | ChatGPT Work vs Codex appendix in `dubai-io-implementation-plan.md` (approx. lines 116–161) does not belong in the architecture plan — move or delete. |
| Community nav vs MVP freeze | Architecture / vision keep Discover / Community destinations while contest excludes community. Keep Community as shell or hide until moderation exists. |

---

## Gaps to close before build (Phase 0)

1. Official rules: category criteria, IP ownership, exact submission pack, deadlines (recheck [Create AI Agents](https://www.dubaichamberdigital.com/en/create-ai-agents)).
2. One **versioned card schema** and one **request state machine** including `QUOTED` and evidence rules per capability.
3. Primary stack pins: OIDC, hosting, model, embeddings, object storage — versions pinned at repo setup.
4. One named pilot merchant and one operator who will actually acknowledge requests (sandbox labelled if needed).
5. Approved civic corpus list (URLs, dates, jurisdiction, reuse rights) for the damage/dispute flow.
6. Eval fixtures: ~10 happy-path + failure cases for the hero journey; start the RAG set early (do not wait for 40).
7. Write a short **MVP freeze** note that cites 05 + implementation plan and explicitly defers 07 ecosystem mini-apps, community, geofencing, tickets, indoor maps, and media vault.

---

## Recommendation

| Decision | Detail |
|---|---|
| **GO** | Three-capability MVP, modular-monolith stack, portal-based merchant integration, contract corrections, phase gates. |
| **Stretch only** | Scheduled in-chat reminder after the main journey works. |
| **NARROW if merchant stalls** | Discovery + request portal + civic recovery remains a valid Personal Agent story. Do not pivot to a compliance / fines product. |
| **Do not build for contest** | Community network, background geofencing, ticket wallet issuance, indoor maps, media vault, payments/escrow, government write APIs. Keep extension points only. |
| **Document 07** | Preserve for vision and post-MVP registry/mini-app story; do not expand contest scope. |

Application implementation should stay paused until Phase 0 exit gate: plan reviewed, primary providers selected, source/rules verification tracked, pilot path agreed.

---

## Suggested next artifacts (optional)

1. `mvp-freeze.md` — one-page override for builders/agents.
2. Machine-readable card schema + request state machine (closes §3 of the implementation plan).
3. Week-1 build backlog ordered by exit gates in Phases 1–2.
