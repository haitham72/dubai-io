# Moderate recommender and memory plan — 22 Oct 2026

**Implementation checkpoint:** REC-01/02 are implemented. REC-03A/B temporal qualification and trusted live places are implemented and verified on SQLite/in controlled browser checks (128 backend tests, seven browser scenarios); PostgreSQL write health/verification/reconciliation remains a deployment gate. Next: REC-03C service/product eligibility and verified completions, then REC-04 measurements. The full proposal below is not all implemented. See ../implementation-plan.md for exact scope and gates. Current retention is 24 hours for ranking runs and 90 days for events, with cleanup on activity; all client observations are organic-only. Google OAuth is last.


**Design and behavior contract, updated 22 Oct 2026.** Parts are implemented as recorded above; remaining slices are tracked explicitly in [the detailed plan](../implementation-plan.md). Target: Supabase Postgres/Auth, with the existing FastAPI/LangGraph service. Execution order and outstanding requests: [request backlog](../request-backlog.md). Existing contest scope remains in `PLAN.md`.

## Intended behavior

Dubai-io should adapt after a few meaningful interactions in the current visit. Opening several seafood options can raise seafood recommendations immediately; it does not establish a permanent preference. Explicit current requests and constraints outrank inferred interests. Keep some variety and let users dismiss, correct or reset recommendations.

The first version uses deterministic, weighted content matching. Use app-owned category/item tags, recency, explicit preferences, distance/time fit and available provider evidence. Collaborative filtering and model training can wait for enough real feedback. No LLM call is needed for each click.

### Adaptive behavior contract (founder clarification, 22 Oct)

1. **Now:** the current category, explicit request and hard constraints determine what is eligible. Asking for coffee stops seafood history from taking over that request. Changing tasks does not erase history; it changes which history is relevant.
2. **This visit:** a few distinct meaningful interactions can influence the next relevant list. A browser visit rotates after 30 minutes idle or 24 hours maximum. Current lists remain stable until explicit refresh, sort/filter changes or re-entry.
3. **Across visits:** one evening's browsing is insufficient. Initially require two distinct options across at least two visits separated by six hours before inferred long-term influence is eligible. Additional tabs at the same time do not qualify. Confirmed preferences are a separate explicit source and do not need click evidence.
4. **Change over time:** session signals halve every 30 minutes and expire after 24 hours; inferred long-term signals halve every 30 days and expire after 90 days without reinforcement. New negative evidence reduces influence; old positive evidence cannot lock the user into a permanent taste. These defaults need evaluation, not marketing claims.
5. **Choice and variety:** strongest current intent first, then confirmed preference, qualified session and long-term influence, plus practical fit. Keep a bounded relevant variety slot in longer personalized lists. No random shuffle, fake recommendations or feedback from merely seeing a card.
6. **Correction:** Confirm/Edit/Not true/Forget/Resume remain visible. Dismiss one place temporarily without declaring dislike of its entire category. Forget invalidates stored evidence, model checkpoints and cached/in-flight explanations. This is separate from deleting browser chat history.
7. **Suggestion eligibility:** occasions, future events and sponsorship will reuse temporal relevance only after their own date/source/consent rules. A cake suggestion requires an explicit occasion; browsing cakes does not prove a birthday. News about an artist does not prove a dated concert or ticket stock. Organic evidence stays out of sponsorship until ADS-01 defines an eligible consented path.

**Example:** two seafood detail opens tonight can promote seafood candidates on the next relevant discovery refresh. Opening coffee immediately shows coffee. Returning tomorrow without reinforcement starts a new visit and does not preserve last night's session boost. Repeated seafood choices on separated visits can establish an explicitly visible, fading across-visit hypothesis. It never becomes a confirmed preference unless the user confirms it.

## What already exists

| Component | Current state | Planned change |
|---|---|---|
| `luna/graph.py` | Thread checkpoints through PostgresSaver or SQLite; last 12 history entries sent to the model | Add bounded selected-card/task context and memory retrieval; manage accumulated checkpoint history |
| `user_profile.py` | `profile_facts` with provenance/validity; `user_profile` projection | Keep this as the authoritative store for told/confirmed facts across threads |
| `profile.py`, web `profile.js` | Six allowlisted hypotheses, recorded episodes/overrides, browser confidence math | Compute ranking/profile projections on the server; extend the reviewed taxonomy and preserve Confirm/Not true/Forget |
| Maps/offers | Category, distance and provider ordering | Introduce an explicit “For you” order while preserving explicit closest/price sorting |

## Four kinds of memory

| Memory | Storage | Use and lifetime |
|---|---|---|
| Conversation working state | LangGraph PostgresSaver, owner-scoped thread | Recent turns, summary, selected entity/card/fragment, active task ID/revision. Revalidate focus and live evidence each turn. |
| Current intent | PostgreSQL session-interest rows, keyed by browsing session | Fast adaptation within/across surfaces. Initial half-life: 30 minutes; expire after 24 hours. Task changes reduce unrelated influence. |
| Inferred preferences | PostgreSQL long-term interest rows | Weaker influence until supported across separate visits; initial half-life: 30 days. Always visible as “I noticed,” with evidence and controls. |
| Confirmed facts/preferences | Existing `profile_facts` / `user_profile` | User statements and confirmations. Respect validity windows and superseding statements; do not promote clicks into confirmed facts. |

These lifetimes are proposed tuning defaults. Short-term LangGraph memory means thread scope, not automatic deletion after a short time. Across-thread profile access goes through the existing typed ProfileStore in graph nodes; a second generic memory store should not become a competing source of profile truth. LangGraph also supports PostgresStore if a later non-profile memory use requires it. [LangGraph memory model](https://docs.langchain.com/oss/python/concepts/memory), [persistence integrations](https://docs.langchain.com/oss/python/langgraph/add-memory).

## PostgreSQL data model

Reuse `user_profile`, `profile_facts`, `episodes` and `profile_overrides`. Add three focused tables:

| Table | Fields / role |
|---|---|
| `recommendation_events` | UUID, owner, browsing_session, optional thread_id, event_type, entity_source/id, app-owned topic keys, recommendation_run_id, server timestamp, expiry, dedupe_key and data-use classification. Append-only evidence; no copied provider listings or full transcripts. |
| `profile_interests` | Owner, topic_key, scope (`session`/`long_term`), context_key (session ID or `all`), usage_class, positive/negative evidence, distinct evidence count, last_decay_at, last_seen_at, expires_at, bounded evidence references and projection version. This is the profiling table used for ranking. |
| `recommendation_runs` | UUID, owner/session, surface, active intent, profile/ranker version, ordered candidate IDs, reason codes, created/expiry timestamps. Links impressions and later choices to the list actually shown. |

`profile_interests` has a unique key on `(owner, topic_key, scope, context_key, usage_class)`. Index events by `(owner, received_at)` and `(owner, browsing_session, received_at)`; enforce unique `(owner, dedupe_key)`. Index interests by owner/scope/context and runs by owner/time. Add a recommendation revision to `user_profile` independently of its confirmed-fact version.

Retain the current owner representation through an explicit Auth migration, then map authenticated Supabase UUIDs server-side. Browsing session, conversation thread and authenticated user are distinct identifiers. A user may have multiple threads/devices. Never accept owner IDs, event weights or completion claims from the client.

Event insertion and affected interest updates run atomically; duplicate events do not increment aggregates. Decay is applied from `last_decay_at` before updating and at read time. Rebuilds from evidence must produce the same result. Bound repeated activity on the same item/session so rapid repeated taps do not create false confidence.

## Signals and ranking

Starting signals: category choice/detail open = weak positive; save/explicit selection = stronger positive; authoritative service completion = strong evidence of a choice. An order submission is intent, not completion. An impression alone is not a preference. Missing a click is not a dislike. Dismissal initially suppresses that item; a topic-level “less like this” is needed to reduce a whole category.

Map events to a reviewed taxonomy such as `food.seafood`, `events.live_music` or `service.laundry`; keep sensitive traits outside it. Existing episode endpoints accept only their current kinds/positive weights, so signed recommendation feedback requires a new validated event contract rather than assuming it works today.

First filter candidates by the explicit request, date/area, known constraints and source freshness. Do not treat unknown opening hours, ticket stock or travel time as verified availability. Current place discovery supports category/type, radius and open-now controls; other constraints require their pending adapters/context contracts. Explicit topic intent also filters the generic rank input. Then rank eligible candidates using a versioned formula with normalized features:

`score = .45 current_intent + .20 confirmed_preferences + .15 session_interest + .10 longer_term_interest + .10 practical_fit`

Weights are initial defaults, not measured results; neutral/missing terms are handled consistently. Session and long-term terms are signed and individually qualified; category taps do not count as distinct options. Inferred negative evidence does not cancel an explicitly confirmed preference. Explicit budget/distance/deadline constraints remain filters, not preferences that a high score can overrule; unsupported constraints must not be described as verified. Show one concrete reason per influenced option, e.g. “Because you explored seafood this visit.” The place ranker reserves every fifth position for a different eligible topic where possible, using stable baseline order. A user-selected closest/price sort keeps that ordering; recommendations cannot silently override it. Label straight-line distance and estimates.

Re-rank at the next list refresh or completed interaction, not while a finger is targeting a card. Cache keys include owner, session/intent, profile revision, candidate set and ranker version. Failure falls back to an honest deterministic list. Initial target: under 150 ms p95 for scoring an already fetched candidate batch, excluding provider/network/LLM time; measure before claiming it.

## LangGraph and API integration

1. Resolve the authenticated owner and thread; validate selected entity/card/task IDs against server/provider data.
2. Load relevant confirmed facts and bounded session/long-term interests. Include only what affects this request, with provenance and timestamps.
3. Run existing normalize/understand/validate nodes. The validated current request supplies immediate constraints even before a new stated fact is persisted.
4. For discovery intents, retrieve fresh candidates, apply constraints and deterministic ranking. Ordinary browsing uses the same ranker without invoking LangGraph. Order status continues to come from the action engine.
5. Return ranked cards and reasons. Save only validated stated facts through the existing remember path; behavioral updates stay in the event/projector path.

Proposed contracts: `POST /api/recommendation-events` (bounded batch), `POST /api/recommendations` (surface/focus/constraints), and `GET /api/profile/interests` plus validated Confirm/Not true/Forget controls. The server resolves sources, weights and candidate attributes. Start from `luna/schema.py` for any Luna contract changes.

Use a small trusted context envelope around untrusted provider/card text. A selected fact about museum tickets selling out is a reason to check dated availability, not proof. Keep itinerary revisions explicit. Summaries stay bounded and preserve uncertainty; they never become confirmed profile facts by themselves.

## Supabase deployment and data controls

Use local Supabase for schema/Auth integration when the Windows container runtime works, then apply versioned migrations to hosted development/staging. Local Google OAuth is supported with its registered callback; phone tests need reachable URLs. See `supabase/README.md`. Keep Python orchestration, approval binding and the outbox; small real webhooks can use Edge Functions.

Use a backend database connection appropriate to LangGraph/psycopg; prefer direct or session pooling for this persistent service. Confirm checkpoint setup/migrations and connection lifecycle against the pinned library. Supabase's transaction pooler has prepared-statement/pipelining limits, so do not switch connection modes blindly. [Connection documentation](https://supabase.com/docs/guides/database/connecting-to-postgres).

Keep checkpoints, profiling and action internals in private schemas; apply RLS to exposed user-owned tables and retain API ownership checks. A privileged SQL connection does not automatically act as the signed-in user. Migrate anonymous history only after proof of ownership; map merchant/operator roles separately.

Retain provider IDs and permitted app-owned signals, not an unrestricted copy of Google listings/photos/reviews or provider-derived attributes. Source permissions govern persistence. Keep Google Workspace-derived context separate from evidence eligible for sponsored targeting: Workspace data cannot be used for advertising. Never mix restricted data into an ad profile and assume a later filter can remove it. [Google policy](https://developers.google.com/workspace/workspace-api-user-data-developer-policy).

Retention: session-interest rows 24 hours, behavioral events 90 days, ranking runs 24 hours, inferred preferences until expiry/forgetting, stated facts until their validity changes or the user forgets them. Cleanup currently runs on activity; scheduled cleanup remains REC-04. Transient browser place snapshots are limited to 16 contexts. Explain these choices in the user-facing controls before launch. Forget removes/rebuilds affected projections, evidence links, caches and summaries; remove or rewrite affected checkpoints so old text cannot recreate forgotten facts. Conversation deletion has a distinct, clearly described scope. [Checkpoint deletion](https://docs.langchain.com/oss/python/langgraph/add-memory#delete-all-checkpoints-for-a-thread).

## Implementation sequence and acceptance gates

1. **Supabase foundation:** versioned schema, database health/backup check, auth/anonymous-owner mapping and cross-user access checks. Preserve the original database; migration is separate from recovering it.
2. **Session recommender:** event contracts/dedupe, server projector/ranker and one existing surface. A scripted sequence of distinct seafood interactions must change the next ranking; repeated taps must not inflate it. Explicit new intent must immediately take precedence. Keep UI stable during interaction.
3. **Long-term memory/context:** cross-thread confirmed facts, decaying hypotheses, selected-card follow-ups and visible controls. Validate expiry, contradictory statements and complete forgetting, including checkpoints. Existing JS profile vectors can anchor the Python port.
4. **Broaden coverage:** reuse the ranker for existing service/product/place candidates; validate source-specific retention and recommendation reasons. Add events/occasion feeds or sponsorship only through their separately tracked scope/data-source work.

Compare relevance and useful selections against the current distance/category baseline, along with dismissal rate, diversity and latency. Do not optimize clicks alone. Test deterministic ranking/decay, duplicate/out-of-order/concurrent updates, evidence authenticity, cross-user isolation, provider failures, and existing order/approval behavior. SQL/tag matching is sufficient initially; pgvector can later improve semantic retrieval over permitted content without becoming a prerequisite. [pgvector search behavior](https://github.com/pgvector/pgvector#querying).
