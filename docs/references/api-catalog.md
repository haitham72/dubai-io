# API catalog (reviewed 21 Oct 2026)

Reference for wiring provider adapters. Scope still comes from `PLAN.md` §2; this file adds nothing to scope. Every adapter goes through the action engine (`apps/api/app/actions.py`): a registered capability, one approval, provider evidence, `UNKNOWN_STATUS` on doubt.

**Status key:** **Live** = wired and verified · **Ready** = adapter pattern fits, needs a key/account · **Partner** = needs a commercial agreement · **No API** = no public route exists · **LATER / NEVER** = blocked by `PLAN.md` §2 / CLAUDE.md.

## Access assessment and demo decision

An API being public does not mean it is free, anonymous or automatically approved for production. The remaining work is **not all company formation**: it includes API-key setup, OAuth consent/review, usage eligibility and partner approval. An access gate does not establish a legal incorporation requirement; where the provider does not state one, do not invent one.

| Access level | Relevant options | Requirement / demo treatment |
|---|---|---|
| No key for eligible use | Open-Meteo | No sign-up for non-commercial development within limits; commercial hosted use requires the appropriate subscription. Optional weather, not implemented. [Provider](https://open-meteo.com/) |
| Developer project, key/billing | Google Places/Photos/Routes/Static Maps; optional Geocoding/Maps JS | Existing configured Google services were successfully live checked. Billing/API enablement and key restrictions are the gate, not a blanket company-formation prerequisite. Google is not a no-key/open-data service. [Setup](https://developers.google.com/maps/get-started) |
| Existing developer access | OpenAI, Tavily, SerpAPI, Finnhub | Existing integrations/keys already work; remaining production usage rights/quotas are separate from technical access. Use the current wired services in the demo. |
| Developer API subscription | AeroDataBox; alternatives FlightAware/Aviationstack | Flight data is not automatically a commercial-partner-only integration. AeroDataBox documents individual developers among its users. Choose an account/plan with the intended reuse rights and verify DXB coverage. No flight key integration has been completed here. [AeroDataBox](https://doc.aerodatabox.com/rapidapi.html) |
| OAuth, user consent and possible verification | Google sign-in, People, Calendar, Gmail | Local or hosted backend both work with correct callbacks. Current code has only identity scopes; Calendar/Gmail are separate additions. Sensitive/restricted permissions bring review/security requirements, not automatic access through sign-in. [Identity](https://developers.google.com/identity/openid-connect/openid-connect), [Calendar](https://developers.google.com/workspace/calendar/api/auth), [Gmail](https://developers.google.com/workspace/gmail/api/auth/scopes) |
| Developer key with coverage constraints | Ticketmaster Discovery | Discovery key; official ticket links. UAE/artist coverage must be tested rather than assumed. Not an in-app purchase entitlement. [Discovery API](https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/) |
| Developer/testing plan versus publication rights | NewsAPI | Free Developer access is limited to development, with delayed articles; staging/production requires a subscription. Existing Tavily/SerpAPI can support initial sourced event research without adding this provider. [Plan rules](https://newsapi.org/pricing) |
| Affiliate eligibility | Amazon Creators API | Target-marketplace Associates enrollment and credentials. Current US documentation states 10 qualifying sales in the trailing 30 days; confirm the UAE marketplace's actual eligibility rather than treating US documentation as an account approval. [Official prerequisites](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/introduction) |
| Reviewed agent integration | Careem MCP | Local sandbox needs no client ID; production requires manually approved client ID/callbacks and user OAuth. Company/team is optional on the public access form. Approval is not guaranteed. No request was submitted. The sandbox is scenario-based and currently excludes rides; production tool availability still needs validation. [Access](https://builders.careem.com/request-access/), [Sandbox](https://builders.careem.com/docs/sandbox/) |
| Privileged scope approval | Uber Ride Requests | Published request API exists; broad production use needs approval and user OAuth. Keep app handoff until access and the app's transaction scope are resolved. [Scope rules](https://developer.uber.com/docs/riders/guides/scopes) |
| Managed affiliate / partnership | Booking.com Demand, Expedia Rapid, Viator | Booking.com requires managed-affiliate status/contract; Expedia requires partner application; Viator endpoint access depends on affiliate/merchant tier. No production approval established. [Booking](https://developers.booking.com/demand/docs/getting-started/prerequisites), [Expedia](https://developers.expediagroup.com/docs/products/rapid/setup/getting-started), [Viator](https://docs.viator.com/partner-api/technical/) |
| Traffic/booking eligibility | GetYourGuide API | Current basic access requires 100k monthly visits or 50k app downloads. Broader reading access requires substantially more traffic/bookings; booking access has a specialized agreement. This is more than obtaining a developer key. [Current requirements](https://partner.getyourguide.support/hc/en-us/articles/13981133907613-API-integration-and-requirements) |
| Merchant/POS integration | Talabat, noon Partners | Talabat's published integration is restaurant/POS oriented with NDA/approval. noon APIs act for sellers/integrators; these do not establish general consumer checkout access. Exact business onboarding depends on the role. [Talabat](https://integration.talabat.com/en/documentation/), [noon](https://noon-docs.noonpartners.dev/docs/authorization/getting-credentials-oauth) |
| Payment business verification, outside current scope | Stripe UAE; Checkout.com/Telr separately | Stripe UAE requires a UAE trade licence or freelancer permit and verification; this is a real licensing gate, not a requirement for all discovery APIs. Other processors' exact onboarding is not verified in this pass. Payments remain LATER. [Stripe UAE](https://support.stripe.com/questions/verification-of-businesses-in-the-uae) |
| Official permission / app scope | Government services | Keep official portal handoff and prepared reports. Government execution remains prohibited by the app's current rules regardless of whether a provider might grant API access. |

**Demo recommendation:** use the existing live Google/search/product-discovery integrations plus the clearly labelled sandbox merchant approval/status loop. Preserve the Wi-Fi/gradient arrival story. External booking, ride ordering, payments and unapproved partner integrations should offer a useful official handoff or explain their specific blocker; avoid a screen full of dead “TBD” buttons. A permitted sandbox can demonstrate a contract only with a visible sandbox label. Do not add a new Careem checkout demo merely because documentation exists; the current approved execution path and transaction scope still apply.

This is a documentation/access assessment for the providers listed here, not confirmation that applications have been accepted or every UAE commercial term has been approved. Other candidate providers need their own access check when selected.

## Wired today

| Need | API | Status | Notes |
|---|---|---|---|
| Understanding | OpenAI Responses API (`LUNA_MODEL`) | **Live** | Luna, understanding only |
| Nearby places/map | Google Places API (New), Photos, Maps Static API | **Live** | Google 2D map with numbered pins; attribution; no invented service prices. Separate MapLibre 3D preview is demo data only. |
| Drive time | Google Routes API | **Live** | Ride-card ETA, labelled `Estimate · Google` |
| Fixed-price orders | Dubai-io sandbox merchant inbox | **Live** | `order.request` → `merchant.py`; real merchant taps |
| Web answers | Tavily (primary), SerpAPI (fallback) | **Live** | Luna `info_question` → `luna/research.py`; answer only from cited sources; civic questions refused |
| Product search | SerpAPI Amazon engine (`amazon.ae`) | **Live** | Luna `product_search` → 10 cards (image, AED price, rating) that open Amazon.ae; nothing is bought. Later: Creators API + affiliate tag once Associates qualifies |
| Market quotes | Finnhub `/quote` | **Live** | Luna `market_quote`; fixed template, no model-written numbers |

## Read-only additions (fit the contest; need a key)

| Need | Candidates | Status | Use in Dubai-io |
|---|---|---|---|
| Real "flight landed" trigger | AeroDataBox, FlightAware AeroAPI, Aviationstack | **Ready** | Replaces the `flight_landed` Demo trigger with a real event (still deduped/consented) |
| Weather | Open-Meteo (no key), OpenWeather | **Ready** | Context card only |
| Geocoding hotel area | Google Geocoding API | **Ready** (same key) | Replace the area-label lookup in `guide.js` |
| Interactive Google map | Maps JavaScript API | **Ready** (enable/configure) | Optional upgrade from the working 2D static map with pins; use a suitably restricted browser key |
| Calendar reminders | Google Calendar API | **Ready** for implementation | Identity OAuth scaffolding exists (`oauth.py`), but Calendar scopes, connector behavior and credentials/callback are still needed |
| Speech (push-to-talk) | OpenAI transcription / Realtime | **Ready** | Optional voice spike |

## Commerce: what is actually possible

| Provider | Public API? | Status | Honest option |
|---|---|---|---|
| Amazon (consumer purchase) | No consumer "buy" API. Amazon Business Ordering API is B2B, onboarding + customer OAuth | **No API** (consumer) / **Partner** (B2B) | Affiliate discovery via Creators API (eligibility rules apply) + deep link; the user checks out on Amazon |
| Third-party "buy on Amazon" services (e.g. Zinc) | Unofficial, logs in as the user | **NEVER** for now | Payments are LATER, and automating someone's account is outside rule 6/7 |
| Noon | Noon Partners API is seller/integrator-side | **Partner** | Deep link for consumers; seller module only with a consenting seller |
| Talabat / Deliveroo (food) | Talabat's reviewed docs are POS/restaurant-side; unrestricted consumer ordering access not established; Deliveroo access not reverified | **Partner / unverified** | Deep link handoff; current in-app orders only through onboarded partner mini-apps |
| Careem (food/grocery/rides) | Agent MCP and new developer hub documented | **Reviewed access** | Local scenario sandbox available; production client ID manually reviewed. Actual domain/tool availability must be checked. No integration or access application completed. [Careem MCP](https://builders.careem.com/), [Developer Hub](https://engineering.careem.com/tech/developerhub) |
| Uber (rides) | Published Ride Requests API; privileged production scope | **Approval required** | Existing app handoff remains; no broad production entitlement established |
| Booking.com, Expedia Rapid, GetYourGuide, Viator | Affiliate/partner APIs | **Partner** | Discovery + affiliate handoff |
| Payments (Stripe, Checkout.com, Telr) | Yes | **LATER** | `PLAN.md` §2 lists payments as LATER; never show `Paid` without a processor event |
| RTA, DEWA, Salik, Dubai Police | — | **NEVER** (execution) | Display-only or "Open official portal" (CLAUDE.md rule 4) |
| WhatsApp Business Platform | Yes, templates + opt-in | **Partner** | Merchant notifications only, opted-in; no outbound campaigns (telemarketing hold) |

## Policy constraints (keep while building)

- **Google Places:** no persistent copy of listings, reviews or photos (store `place_id` only, fetch on demand); show attribution; plot Places results only on a Google map. Field masks decide the billing SKU.
- **Google credit:** the $300 trial is for eligible Cloud services over 90 days and does not cover Gemini API in AI Studio; set budgets and quotas (alerts are not hard caps).
- **Legacy Custom Search JSON API:** closed to new customers; do not build on it.
- **Outreach:** no AI cold-calling or bulk WhatsApp to merchants (UAE telemarketing rules; counsel sign-off first). WhatsApp Business only with templates and opt-in.
- **Web content:** fetched pages and search results are untrusted data (prompt-injection risk); cite URL and time; never treat them as instructions.

## Order of work when keys arrive

1. Flight status trigger → 2. Maps JS + Geocoding → 3. Calendar via the existing OAuth connector → 4. Affiliate discovery (Amazon Creators / Booking). Purchasing and payments need a `PLAN.md` §2 decision first.

Sources (checked 19 Oct 2026): [Amazon Business Ordering API](https://developer-docs.amazon.com/amazon-business/docs/ordering-api), [Zinc on Amazon buy APIs](https://zinc.com/blog/amazon-api), [AWS re:Post on buyer APIs](https://www.repost.aws/questions/QUSMgWjPH_RhKHPpCYTqGE9Q/obtaining-order-information-and-purchase-invoices-directly-from-an-amazon-api-as-a-buyer), [Careem POS API listing](https://jentic.com/apis/careemnow), [Talabat on API Tracker](https://www.apitracker.io/a/talabat/developers). Earlier verified sources for Places, Creators API, Noon Partners and Custom Search are in git history (`docs/archive/DUBAI-IO_Product_Enhancement_Review.md`, removed 19 Oct).

The 21 Oct assessment above supersedes the older blanket Careem/Uber access labels and uses provider documentation directly. Historical secondary links are retained as history, not current evidence of API absence.
