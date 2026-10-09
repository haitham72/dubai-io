# Dubai-io — Product Vision

**Working brand:** Dubai-io · **Tagline:** *Your Intelligent Dubai Companion*  
**One sentence:** A persistent AI companion that connects people, local community knowledge, trustworthy city guidance and real services throughout daily life in Dubai.

## 1. Product identity

Dubai-io is **not** a stand-alone city guide, a directory of mini-apps, or a fines/compliance bot. It is a lightweight everyday interface for visitors first and residents later. Think:

| Inspiration | What Dubai-io adopts | What it will not blindly copy |
|---|---|---|
| WeChat | Messaging, groups, service access, merchant interactions and continuity, **sandboxed inner-HTML widgets / mini-apps selected by the companion (compact card → expanded widget → full embed)** | Full native payments/network scale at launch; arbitrary HTML/JS execution without manifest + bridge allowlist |
| Reddit | Authentic local discussions, reviews, Q&A, meetups and expertise | Anonymous unmoderated rumor presented as fact |
| ChatGPT-style agents | Intent understanding, long-term consented context, retrieval, planning and tool use | Text-only chatbot with fabricated actions |
| Shopify | Merchants apply and publish services through structured capabilities | Custom mini-app for every merchant |
| Groupon | Real, verifiable, redeemable offers | A mandatory 10–15% discount from every merchant |

**Core proposition:** *One conversational interface. A growing set of actionable city capabilities.*

**Companion interaction model:** the companion is a participant in the user's ongoing conversation: it may **initiate** useful, consented messages when verified events occur, rather than waiting for prompts. Notifications, checklists, tickets, navigation cards, evidence, and reminders belong to the same persisted timeline.

## 2. The three lasting layers

1. **Companion intelligence:** conversation, current intent, authorized trip/user context, memory, tools, relevant reminders.
2. **People and community:** real chat, groups, posts, local experience, polls, recommendations, meetups, reporting/moderation.
3. **Services and civic intelligence:** businesses, discovery, quote/booking handoff, offers, official-source guidance, dispute support.

Long-term **personal media memory** (messages, photos, receipts, videos with timestamp retrieval) belongs to the companion but must use explicit user consent and appropriate privacy controls.

## 3. UX rules: simple front end, expandable back end

- Main screen: companion chat with small reusable **Dynamic Action Cards** that can expand into **inner-HTML widgets / mini-apps** (standard platform widgets first, provider-supplied HTML only via versioned manifest + sandboxed iframe + capability-scoped `postMessage` bridge).
- Four navigation destinations are sufficient initially: **Companion / Discover / Community / Me**; reduce further if UX testing supports it.
- Cards may show a map, shortlist, availability, verification/citation, form, QR offer, status, image or receipt. **Widget lifecycle: `discover → present → interact → authorize (when needed) → persist state → monitor/await event → notify/resume`. A widget interaction can create a persistent watch (e.g. "tell me when cheaper") that fires a future Jarvis message.**
- Do not force complex maps, media, payment or accessibility flows into a tiny chat bubble; full-screen detail views are allowed.
- The app changes **what it can do**, not how much interface clutter the user must navigate.
- Offer proactive help only when the context is reliable, the timing is relevant, and the user opted in. Delivery windows and movements are *signals*, not proof.
- Provide a **notification inbox embedded in the actual chat history**: delivery estimates, pre-trip checklists, arrival cards, event changes, ticket retrieval, indoor guidance and parking memory.
- Allow the user to disable each trigger type, set quiet hours, and correct assumptions ("I did not park", "I am not leaving yet").
- User must be able to inspect the source, permissions, costs, next step and actual confirmation state.

## 4. Example compound intents

- **Plan:** “I want skydiving tomorrow, then the beach. Compare travel and essentials.”
- **Discover:** “Find someone to iron five shirts before tomorrow.”
- **Connect:** “Find a breakfast meetup with people staying in Marina.”
- **Remember:** “Which video shows me spilling coffee at Dubai Mall?”
- **Recover:** “I left my passport in a taxi; help me report it.”
- **Resolve:** “My dry cleaner damaged my suit. What evidence and official process do I need?”
- **Act:** “Send the approved pickup request to the laundry provider.”
- **Proactively remind:** “Your snorkeling order is expected this afternoon. Your trip starts tomorrow; check your gear.”
- **Guide on arrival:** “You appear to be approaching the venue. Open your purchased family tickets?”
- **Navigate indoors:** “I can't locate you precisely indoors. Which shop or entrance are you beside?”
- **Remember parking:** “It looks like you stopped driving and started walking. Did you park? Save a photo of your floor and pillar.”

These are scenario goals, **not evidence of functioning integrations**.

## 5. Product principles

1. **Truth in action status.** Suggested ≠ Requested ≠ Confirmed ≠ Paid ≠ Fulfilled.
2. **Official information over rumor.** Community anecdotes are labelled and linked to originals, while law/administrative claims cite official versions.
3. **Least privilege.** The companion asks permission before sharing location, media, documents or sensitive attributes with providers.
4. **Reliability before breadth.** A genuinely completed action beats ten simulations.
5. **Composable services.** New merchants join a typed capability registry and reusable UI system.
6. **No fabricated engagement.** No bots pretending to be residents, fake discounts, fake reviews or invented merchants.
7. **Incremental AI-assisted onboarding.** AI helps map and test integrations; humans approve production deployment.

## 6. Horizons (do not conflate)

| Horizon | Core value | In / out |
|---|---|---|
| **Contest MVP** | One persistent agent + real service request + official-source RAG; scheduled in-chat reminder and proof of event pipeline if time permits | No escrow, public social network, payments, hospital workflow or full media vault |
| **Post-MVP early product** | Local community posts, opt-in groups, provider expansion, notification subscriptions, opt-in trip/parking detection and landmark-based indoor wayfinding | Moderation, consent, venue navigation data and reliable device events are prerequisites |
| **Platform growth** | Peer messaging, merchant tools, verified offers and booking, controlled media memory | Requires security, compliance, distributed operations |
| **Long-term ecosystem** | Cross-service execution, specialist agents, stronger city/official integrations | Requires formal access and partnerships |

## 7. Strategic differentiation hypothesis

The differentiated asset, **if validated**, is the combination of consented user context, trusted local knowledge, merchant relationships and real verified actions—not ownership of a foundation model or simply displaying a directory.

**Product proof:** a user can describe a goal once, discover the right provider, get an actionable response, verify completion, and continue in the same conversation when a related need arises.

## 8. Success is not feature count

Measure task completion, repeat use, source correctness, provider conversions, permission trust, user time saved, and real outcomes. Avoid claims that the product reduces government fines or guarantees discounts until demonstrated by evidence.

## 9. Proactive message experience — foundational product behavior

The companion speaks when it can genuinely help, not only when asked. A single user journey may generate several **related, timely messages**:

1. **Provider event:** “Your snorkeling kit is estimated to arrive between 2–7 PM.” Show a delivery-status card only if a legitimate merchant/order status supports it; otherwise call it an unverified estimate or user-entered plan.
2. **Trip countdown:** “Your snorkeling trip starts in 10 minutes. Have the passports and gear you said you need?” Scheduled from the user's trip plan, using a timezone-aware event.
3. **Possible departure:** Motion + permissioned geofence imply the user may be leaving home. Send a low-confidence prompt or simple well-wish, not a declaration of certain movement.
4. **Approaching destination:** Offer the actual already-issued tickets for the user and children from their authorized booking records, with each QR/barcode kept linked to its authentic issuer. **Do not generate usable tickets or assert that children are eligible without valid records.**
5. **Indoor orientation:** Ask for nearby store/entrance names and floor when position is unknown, show a minimal themed schematic using permitted venue map data, and advance one step at a time.
6. **Possible parking:** Vehicle-stop + walking transition near destination prompts the user to confirm parking and take a photo of bay, floor and pillar. Later “Where did I park?” retrieves the image and details.

**UX rule:** messages are part of chat history, but reminders, navigation and ticket cards support full-screen views. No flooding; bundle related messages and suppress duplicates. The assistant should always state uncertainty and invite corrections.
