# API catalog (19 Oct 2026)

Reference for wiring provider adapters. Scope still comes from `PLAN.md` §2; this file adds nothing to scope. Every adapter goes through the action engine (`apps/api/app/actions.py`): a registered capability, one approval, provider evidence, `UNKNOWN_STATUS` on doubt.

**Status key:** **Live** = wired and verified · **Ready** = adapter pattern fits, needs a key/account · **Partner** = needs a commercial agreement · **No API** = no public route exists · **LATER / NEVER** = blocked by `PLAN.md` §2 / CLAUDE.md.

## Wired today

| Need | API | Status | Notes |
|---|---|---|---|
| Understanding | OpenAI Responses API (`LUNA_MODEL`) | **Live** | Luna, understanding only |
| Nearby places | Google Places API (New) Text Search | **Live** | Discovery list only; attribution; no prices; never pinned on the MapLibre map (needs a Google map) |
| Drive time | Google Routes API | **Live** | Ride-card ETA, labelled `Estimate · Google` |
| Fixed-price orders | Dubai-io sandbox merchant inbox | **Live** | `order.request` → `merchant.py`; real merchant taps |
| Web answers | Tavily (primary), SerpAPI (fallback) | **Live** | Luna `info_question` → `luna/research.py`; answer only from cited sources; civic questions refused |
| Market quotes | Finnhub `/quote` | **Live** | Luna `market_quote`; fixed template, no model-written numbers |

## Read-only additions (fit the contest; need a key)

| Need | Candidates | Status | Use in Dubai-io |
|---|---|---|---|
| Real "flight landed" trigger | AeroDataBox, FlightAware AeroAPI, Aviationstack | **Ready** | Replaces the `flight_landed` Demo trigger with a real event (still deduped/consented) |
| Weather | Open-Meteo (no key), OpenWeather | **Ready** | Context card only |
| Geocoding hotel area | Google Geocoding API | **Ready** (same key) | Replace the area-label lookup in `guide.js` |
| Google map with pins | Maps JavaScript API | **Ready** (same key) | Needed before plotting Places results |
| Calendar reminders | Google Calendar API | **Ready** | OAuth connector exists (`oauth.py`); needs client ID/secret + callback |
| Speech (push-to-talk) | OpenAI transcription / Realtime | **Ready** | Optional voice spike |

## Commerce: what is actually possible

| Provider | Public API? | Status | Honest option |
|---|---|---|---|
| Amazon (consumer purchase) | No consumer "buy" API. Amazon Business Ordering API is B2B, onboarding + customer OAuth | **No API** (consumer) / **Partner** (B2B) | Affiliate discovery via Creators API (eligibility rules apply) + deep link; the user checks out on Amazon |
| Third-party "buy on Amazon" services (e.g. Zinc) | Unofficial, logs in as the user | **NEVER** for now | Payments are LATER, and automating someone's account is outside rule 6/7 |
| Noon | Noon Partners API is seller/integrator-side | **Partner** | Deep link for consumers; seller module only with a consenting seller |
| Talabat / Careem / Deliveroo (food) | No consumer ordering API; Careem has a restaurant POS API | **No API** | Deep link handoff; order inside Dubai-io only from onboarded partner mini-apps |
| Careem / Uber (rides) | Deep links; ride APIs restricted | **No API** (booking) | "Opens your app. Dubai-io doesn't book it." (already in the guide) |
| Booking.com, Expedia Rapid, GetYourGuide, Viator | Affiliate/partner APIs | **Partner** | Discovery + affiliate handoff |
| Payments (Stripe, Checkout.com, Telr) | Yes | **LATER** | `PLAN.md` §2 lists payments as LATER; never show `Paid` without a processor event |
| RTA, DEWA, Salik, Dubai Police | — | **NEVER** (execution) | Display-only or "Open official portal" (CLAUDE.md rule 4) |
| WhatsApp Business Platform | Yes, templates + opt-in | **Partner** | Merchant notifications only, opted-in; no outbound campaigns (telemarketing hold) |

## Order of work when keys arrive

1. Flight status trigger → 2. Maps JS + Geocoding → 3. Calendar via the existing OAuth connector → 4. Affiliate discovery (Amazon Creators / Booking). Purchasing and payments need a `PLAN.md` §2 decision first.

Sources (checked 19 Oct 2026): [Amazon Business Ordering API](https://developer-docs.amazon.com/amazon-business/docs/ordering-api), [Zinc on Amazon buy APIs](https://zinc.com/blog/amazon-api), [AWS re:Post on buyer APIs](https://www.repost.aws/questions/QUSMgWjPH_RhKHPpCYTqGE9Q/obtaining-order-information-and-purchase-invoices-directly-from-an-amazon-api-as-a-buyer), [Careem POS API listing](https://jentic.com/apis/careemnow), [Talabat on API Tracker](https://www.apitracker.io/a/talabat/developers). Earlier verified sources for Places, Creators API, Noon Partners and Custom Search are in `docs/archive/DUBAI-IO_Product_Enhancement_Review.md` §15.
