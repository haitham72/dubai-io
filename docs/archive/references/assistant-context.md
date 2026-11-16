# Dubai personal assistant — context and suggestions

**Implementation checkpoint:** whole-place focus, removable chat chip, 30-minute expiry, bounded working history and owner checkpoint forgetting are implemented. Selected fragments, authoritative entity/plan resolution, ticket-availability guard and revision-bound draft itineraries remain CTX-02/PLAN-01. Events/occasions/sponsorship remain pending. Follow ../implementation-plan.md under root PLAN.md; do not read the proposal below as completed work.


Founder direction, 21 Oct 2026. Requirements and architecture proposal; the context/itinerary/sponsorship features below are not implemented. Existing contest scope remains in `PLAN.md`.

> hopefully you can check the new features your self, this is not maps app, this is Dubai personal assistant app

## Context before the model

The assistant should understand the user's current activity across places, services, products, events and plans. The map and carousel are views of that activity. The assistant must retain the selected entity and the card the user interacted with when opening chat.

The current Luna HTTP request carries text plus thread/user identifiers. The backend adds conversation history and confirmed profile facts. It does **not** currently receive the selected place/card/fragment or a structured itinerary; adding more prompt wording alone will not close that gap.

Proposed bounded turn context:

| Context | Contents |
|---|---|
| Current focus | Surface, resolved entity ID, selected card ID and selected fragment; user can clear/change the focus |
| Active activity | Request, order or plan ID and revision; distinguish draft and confirmed items |
| User situation | Confirmed preferences, party size, relevant dates, stated deadlines and accessibility needs only when supplied |
| Temporal context | Dubai time, intended date, available time, duration assumptions and travel estimates with sources |
| Evidence | Relevant provider/search responses with source, fetched time, validity and availability status |
| Available actions | Registered capabilities and their blockers; context never grants permission to execute |

Only the relevant subset should enter each turn. Resolve IDs against server/provider data; treat selected text and external snippets as untrusted quoted context, not instructions or newly confirmed profile facts. Never persist a browsing focus as a durable preference without user confirmation. Check freshness and plan revision before applying any proposed change.

## Museum example supplied by founder

> - user is looking at 'dubai future museum'
> - user just clicked on {card: did you know 3 facts, fact_3: visitors said tickets sell out fast so you should book weeks in advance} -> ai_response: if you want to add dubai future museum to your plan then i can merge it in same day as 'green house in deira' so you go their for 2 hours and then go to green house, launch stays as it is but postponed 2 hourse ....'

“Are tickets available?” should resolve to the selected museum and the user's intended visit date. A visitor comment about selling out is evidence to check availability, not proof of current stock. Resolve the other place by ID; do not guess which “Green House” is meant. Show the ticket check and a compact revised timeline together, with any changed lunch time and travel allowance visible. A draft itinerary can be rearranged locally; changing an external reservation or purchasing still requires the existing approval/action path. A two-hour visit is labelled an assumption unless supplied or provider-supported. If live ticket access is unavailable, preserve the plan and offer the official booking handoff.

## Suggestion policy

| Kind | Eligibility | Presentation |
|---|---|---|
| Sponsored restaurant | Food/restaurant conversation plus a relevant confirmed preference; match area, budget and availability first | `Sponsored` plus `Why shown: you told me you like seafood`; preserve organic choices, dismiss/mute controls and price provenance |
| Temporal shopping/celebration | Explicit birthday, anniversary, school term, visitor arrival or another dated user situation | A small relevant carousel, with lead time and a reason; never invent a personal milestone |
| Nearby events | Confirmed interest plus explicit area/consented location and a sourced future event date | Venue, date, travel estimate, source, checked time and official ticket handoff; news alone does not prove ticket availability |

Unconfirmed “I noticed” hypotheses may re-rank in-session options with a visible reason. They cannot trigger proactive messages or prefill shared fields. Proactive suggestions require explicit consent, deterministic scheduling, dedupe and quiet hours. Advertisers receive no raw profile/calendar/history. A displayed sponsored result is labelled even when it is also the best organic match.

Google sign-in supplies identity/profile scopes, not the user's private dish-interest profile. Google Analytics signals do not expose individual users. Use Dubai-io's own user-given/confirmed preferences or explicitly connected data. [Google identity scopes](https://developers.google.com/identity/openid-connect/openid-connect), [Google signals](https://support.google.com/analytics/answer/9445345).

## Personalization from the first session

Many chat sessions are not a prerequisite. Start with the active intent and selected place/card, relevant time and user-stated area. Offer a small optional choice when it materially improves the response, such as seafood/vegetarian/anything or festivals/live music/family outings. A statement or confirmation can become a visible profile fact immediately. A click is a weak, temporary relevance signal, not proof of a lasting preference; repeated choices may support an editable hypothesis. Return visits can improve the profile, with timestamps, confidence, evidence and expiry rather than unlimited transcript accumulation. Sponsor matching uses the same relevance constraints, with its paid status disclosed. Google Ads audience targeting is not an API for exporting each visitor's private Google interest labels into Dubai-io.

Founder clarification: “the app should build its owon temporal profiler, look at temu for example, multiple clicks and immediately locks on users recommendation.” Required behavior is rapid adaptation within the current session, with temporary intent separated from enduring preferences. This is a product reference, not a claim about Temu's internal implementation. Concrete design: [moderate recommender and memory plan](recommender-plan.md).

Google Workspace data, including Gmail/Calendar-derived context, must not be used for advertising. Its use for assistant planning does not make it eligible for sponsored targeting. [Workspace developer policy](https://developers.google.com/workspace/workspace-api-user-data-developer-policy).

## Reference check

Google documents conversational follow-ups, personalized planning, history and third-party actions in Ask Maps. The public Maps browser session inspected here was signed out and did not expose Ask Maps in its menu, so the specific personalized museum conversation could not be reproduced. Google's exact internal context payload is not public; the turn structure above is our design proposal. [Ask Maps help](https://support.google.com/maps/answer/16842041?co=GENIE.Platform%3DDesktop&hl=en), [August update](https://blog.google/products-and-platforms/products/maps/order-food-in-ask-maps/).

## In-app browsing

Founder request, 21 Oct: “some websites open an external browser” — use an in-app browsing experience comparable to Instagram/X. The founder subsequently authorized native work on `ios-swift`. Detailed browser behavior, boundaries and implementation slices: [native iOS plan](ios-swift-plan.md).

- Native iOS default for ordinary third-party links: a Safari browsing sheet (`SFSafariViewController`) with dismissal back to the same assistant context. If a custom browser surface is needed, use WebKit (`WebView`/`WebPage` or `WKWebView`) with visible domain, Back/Forward, Close and Open in browser controls. These are implementation choices, not a claim about Instagram/X's internals. [Safari controller](https://developer.apple.com/documentation/safariservices/sfsafariviewcontroller), [WebKit](https://developer.apple.com/documentation/webkit/wkwebview).
- Authentication uses `ASWebAuthenticationSession`, separately from general embedded browsing. Some provider flows/deep links may require an external browser or provider app; preserve a deliberate fallback. [Apple authentication](https://developer.apple.com/documentation/authenticationservices/aswebauthenticationsession).
- Current web/PWA: embed only app-owned or provider-permitted content. Arbitrary third-party pages can prohibit framing; a styled modal around an iframe cannot guarantee the native experience. Preserve external handoff when needed. [Framing restrictions](https://w3c.github.io/webappsec-csp/#directive-frame-ancestors).
- Preserve conversation, selected entity/card and draft when the browser closes. General third-party browsing remains separate from the privileged mini-app bridge; do not inject credentials or expose host action capabilities to arbitrary pages. Opening or closing a website does not prove that a booking/order/payment occurred. Use provider evidence or an explicit user report with its own provenance.
