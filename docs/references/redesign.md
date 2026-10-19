# Dubai-io: redesign prompt series (GPT Image 2)

**Historical screen prompts, with current overrides (13 Oct).** Use these for visual anatomy and exact copy only where consistent with `CLAUDE.md` and `PLAN.md`. Supplied prompt blocks below are preserved; they do not override newer founder decisions.

- Current tabs: **io · Maps · Services · Me**; Civic remains LATER. Idle has one bottom composer above the tab bar; active chat hides the bar. Top-search/no-idle-composer instructions below are superseded (`PLAN.md` §4 (reference parity)).
- Home is the cyan coverflow stage. The `01-home.png` hero/card layout now belongs at the top of Services (`PLAN.md` §4 (reference parity)); remove duplicate assistant inputs.
- Cyan is selected. Every stage card uses C1’s preferred laser/chromatic reflection at 70% of its previous strength; onboarding card movement must be slower and smoother (`PLAN.md` §4 (reference parity)).
- Community/tickets and extra reference bridge scopes are unresolved scope candidates, not automatic build requirements (`PLAN.md` §2). Order requests remain the only approved business bridge action.
- References are not evidence of completed functionality. C6 recovery still needs the driver/report sheets and cash/card paths; compare each approved surface at 390 px. Arabic RTL and dark-mode implementation are not approved by the retouch table alone.


One chat, in order. The shape is always the same: **context first, then a screen, then the popups that
belong to that screen, then the next screen.** Same chat = same style, so later prompts just say "same
app, same style".

> Assumption: "gpt 2" = OpenAI's image model (GPT Image 2). The prompts work in any image tool that
> keeps conversation context.

## Series map

| # | Prompt | Type | Images | Core |
|---|---|---|---|---|
| **0** | System prompt (context) | context only, no image | 0 | ★ |
| **1** | Home, idle: AI search on top, glass tab bar | screen | 1 | ★ |
| 1a | Chat takes over: glass bar → composer (before / after) | state change | 1 (2-up) | ★ |
| 1b | Arrival guide: waypoints | popup over Home | 1 | ★ |
| 1c | Guide states: "I'm lost" + map zoom | popups over Home | 1 (2-up) | |
| **2** | Ask → provider rows | screen | 1 | ★ |
| 2a | Partner app: sign-in → signed in | popup over rows | 1 (2-up) | ★ |
| 2b | Shopping app: product → order placed | popup over rows | 1 (2-up) | ★ |
| **3** | Approve → provider events | screen | 1 | ★ |
| 3a | Proactive notification banner | popup over any screen | 1 | |
| **4** | Lost item in a taxi | screen | 1 | ★ |
| 4a | Driver detail + RTA report | popups over the lost-item chat | 1 (2-up) | |
| **5** | Services + Me tabs | screens (2-up) | 1 | ★ |
| 5a | Merchant app + shop onboarding | popups over Services | 1 (2-up) | |
| 6 | Backstage operator console | desktop, optional | 1 | |

★ = the 9 images that are enough to redesign the app. The rest are completeness. Total with everything:
14 images from 15 prompts. **Lock Home (1) before sending anything else.**

**Resident / VIP arc:** see Part 2 (R-series, 8 images + a context patch). Built after the visitor redesign ships.

**Scope of the redesign:** layout, hierarchy, iconography, spacing, states and motion cues.
**Palette stays locked** (`demo/styles.css` tokens; CLAUDE.md: "do not invent new palettes").

## How to run it

1. New image chat. Paste **Prompt 0**. The model should reply "Ready" and wait. If it generates an image,
   say "no image yet, wait for the first screen".
2. Paste **Prompt 1**. Iterate until Home is right (AI search on top, glass tab bar at the bottom, no
   composer), because everything after copies it. Do not continue until Home is locked.
3. Then 1a (chat takes over), its popups (1b, 1c), the next screen, its popups, and so on.
4. If style drifts: "Match the Home screen exactly: same AI search, glass tab bar, cards, chips, icons."

**Already pasted the old Prompt 0?** Paste only the block below, then Prompt 1 again. It replaces the
navigation rules in that chat.

```text
NAVIGATION UPDATE: replace any earlier navigation rules with this. Do NOT generate an image for this
message, reply with exactly: "Ready".
Think of the Apple Store and Apple TV apps.
1) IDLE (no chat started): the screen starts with an AI search field at the top ("Ask Dubai-io", magnifier and
   sparkle icon, microphone). At the bottom floats an iOS Liquid Glass tab bar: a translucent, blurred,
   rounded capsule with four tabs (Companion, Services, Civic, Me). Content scrolls behind the glass. The glass
   bar and the AI search stay present on every tab for as long as no chat is used.
2) CHAT ACTIVE (the visitor typed in the AI search or tapped a suggestion): the conversation takes over. The
   glass tab bar is REPLACED at the bottom by the chat composer (a glass pill "Ask Dubai-io" with a circular
   cyan send button). The top becomes a compact header: back chevron (close chat), "Dubai-io", small search
   icon.
3) Closing the chat (back chevron) returns to IDLE: glass bar back, AI search on top.
4) Popups (bottom sheets, lightboxes) cover the glass bar; banners slide in over the top.
Never show the tab bar and the composer together at the bottom.
```
5. Export PNG portrait **1170 × 2532** (2-up images 2400 × 2532). **File names:** each prompt starts with
   `FILE NAME: …` and the model answers with one line `FILE: …`. Rename the download to that name.
   The tool cannot set the download name itself (it saves as "ChatGPT Image …"), so the `FILE:` line is
   what you copy. If you skip renaming, drop the files into `demo/_ref/` in any order: they are matched
   to this series by content.
6. Image models garble long text. Every prompt gives exact copy; fix one line at a time: "replace the
   heading with exactly: …".

---

## Prompt 0 — System prompt (context)

**Paste once, first. No image.** Locks product, style, trust rules and output format.

```text
You are a senior iOS product designer. I am redesigning "Dubai-io", a chat-first AI companion for people
living in or visiting Dubai. Do NOT generate an image for this message. Read it, then reply with exactly
one word: "Ready".

PRODUCT
One conversation does three things:
1) Companion: greets visitors on arrival, guides them through the airport step by step, remembers what they
   tell it, and sends proactive in-chat messages they opted into.
2) Services: any request ("find a group", "buy airpods", "I lost my bag") returns ROWS of apps. Each row opens
   its own mini-app in a bottom sheet with that provider's own branding. The app's next move (a join accept,
   a purchase, a driver reply) comes back into the chat.
3) Platform: a new shop joins from a photo of its price list and the AI generates its mini-app for review.
The chat is the home of everything, but the app opens as a calm home screen with an AI search field, not as
a chat window. Four tabs: Companion, Services, Civic, Me.

HOW WE WILL WORK
I will send screens one at a time. After each screen I will send the POPUPS that belong to it (bottom
sheets, banners, lightboxes), then the next screen. Always keep the exact same app chrome, type and
components so the set reads as one app.

NAVIGATION MODEL (important, applies to every screen)
Think of the Apple Store and Apple TV apps.
1) IDLE (no chat started): the screen starts with an AI search field at the top ("Ask Dubai-io", magnifier and
   sparkle icon, microphone). At the bottom floats an iOS Liquid Glass tab bar: a translucent, blurred,
   rounded capsule with four tabs (Companion, Services, Civic, Me). Content scrolls behind the glass. The glass
   bar and the AI search stay present on every tab (Companion, Services, Civic, Me) for as long as no chat is
   used.
2) CHAT ACTIVE (the visitor typed in the AI search or tapped a suggestion): the conversation takes over the
   screen. The glass tab bar is REPLACED at the bottom by the chat composer (a glass pill "Ask Dubai-io" with
   a circular cyan send button). The top becomes a compact header: a back chevron (close chat), "Dubai-io",
   and a small search icon. Bubbles and cards fill the middle.
3) Closing the chat (back chevron) returns to IDLE: glass bar back, AI search on top.
4) Popups (bottom sheets, lightboxes) cover the glass bar; banners slide in over the top.
Never show the tab bar and the composer together at the bottom.

STYLE LOCK
- iOS light mode, native iPhone feel (Apple Health, Wallet and Messages level of polish), SF Pro, large bold
  titles, generous spacing, 16 px card radius, soft shadows, 44 px minimum tap targets.
- Palette ONLY: grouped background #F2F2F7, cards #FFFFFF, separators #E5E5EA, text #000000 / #3C3C43 /
  #8E8E93, cyan tint #0A9CC2 (soft #E3F6FB, line #B8E6F2), bot bubble #E9E9EB, user bubble #0A9CC2 with white
  text, ok green #1E8E3E on #E8F8EC, demo amber #B25E00 on #FFF3E0, trigger purple #8E44AD on #F3E8FA.
  Use cyan sparingly: actions and the active state only.
- Icons: SF Symbols style, 1.8 px stroke, no emoji in the app chrome.
- Liquid Glass: the tab bar and the composer are translucent iOS 26 glass (background blur, 0.5 px light
  border, soft shadow, capsule radius), floating 12 px above the home indicator. Active tab icon and label
  cyan, inactive #8E8E93.
- Provider mini-apps inside sheets keep THEIR OWN branding (colour, logo tile); the Dubai-io chrome around
  them stays cyan and white. That contrast is the idea.

TRUST RULES (visible in the UI)
- Small pills where relevant: "Demo data", "Demo estimate", "You told me", "Demo trigger", "Merchant update",
  "Partner app (demo)", "Dubai-io".
- Every price reads "AED x (demo)". Never invent live prices.
- Status words may only be: SUBMITTED, ACCEPTED, READY, COMPLETED, DECLINED, CANCELLED, EXPIRED,
  UNKNOWN_STATUS, PREPARED_NOT_FILED, pending, driver en route. Show a human line plus the mono code.
- Approval cards always list "Will be shared" and "Never shared" before anything leaves the phone.
- The app never claims an indoor position the user did not confirm.

FORBIDDEN
Government emblems or ministry logos, the DubaiNow layout, real brand logos (use only: Meetly (demo) violet
#6B4EFF, CircleHub (demo) orange #E0663A, Souq Express (demo) green #1F8A5B, CartNest (demo) burnt orange
#C2410C, DealDash Dubai (demo) purple #7C3AED, Palm Leaf Pharmacy, Marina Express Laundry), gold/black luxury
styling, stock photos of people, phone frames or mockup backgrounds.

FILE NAMING
Every prompt I send starts with a line "FILE NAME: <name>.png". After you generate the image, reply with
exactly one line and nothing else: "FILE: <name>.png", using that exact name. Never invent expressive names
like "home screen first try", and never describe the image in words.

OUTPUT FORMAT
One flat portrait UI screen per image, 1170x2532 px, status bar at 9:41, no device frame, no captions
outside the UI. "2-up" means two full screens side by side, each 1170x2532, with a 40 px light-grey gap.
Render the text I give exactly; keep any other text short.
```

---

## Screen 1 — Home (idle: AI search + glass tab bar)

**Feeds:** tokens, app bar, AI search field, hero card, chips, "Try asking" strip, Liquid Glass tab bar.
**Lock this one first.**

```text
FILE NAME: 01-home.png
SCREEN 1: HOME (Companion tab), IDLE state, arrival at the airport. Use the system context and the NAVIGATION
MODEL above. No chat has started, so there is NO composer at the bottom.
Top: status bar, then a compact app bar with "Dubai-io" in large bold (the "-io" in cyan) and a "Visitor" mode
pill on the right. Directly under it the AI SEARCH field, the first and most prominent control: full-width
rounded field with a magnifier icon on the left, a sparkle icon, placeholder "Ask Dubai-io" and a microphone
icon on the right. Below it a thin context strip: "At DXB · Terminal 3 · you told me".
Content (scrolls behind the glass bar):
1) Hero card (white, large): small eyebrow "Dubai-io · Proactive" with a purple pill "Demo trigger" and an
   amber pill "Scripted demo"; big bold title "Hello, visitor."; body: "Welcome to Dubai. Your flight
   EK 002 has landed at DXB Terminal 3 at 00:40. I'll walk you from the gate to your taxi or Metro, one
   step at a time."
2) White question card (not a chat bubble): "Where are you staying tonight?" with two outlined cyan chips
   "Business Bay" and "Dubai Marina".
3) "Try asking" strip of three compact suggestion cards with a small icon each: "Find a group" (people
   icon), "Buy something" (bag icon), "I lost something" (suitcase icon).
Bottom: ONLY the floating iOS Liquid Glass tab bar (translucent capsule, content faintly visible through it)
with Companion (active, cyan), Services, Civic, Me. Nothing else at the bottom. Calm, airy, one clear focal
point.
```

### 1a — State change: chat takes over (2-up)  ★

**Feeds:** the navigation model: AI search → chat, glass bar replaced by the composer, back chevron.

```text
FILE NAME: 01a-chat-takeover.png
STATE CHANGE, 2-up: the same Home screen before and after the first message. Same app, same style.
LEFT, idle: exactly Screen 1 (AI search field on top, floating Liquid Glass tab bar at the bottom).
RIGHT, chat active, a moment after the visitor typed "find community of egyptians about ai engineering":
the glass tab bar is GONE and REPLACED at the bottom by the chat composer (a glass pill "Ask Dubai-io" with a
cyan circular send button). The top is a compact header: back chevron, "Dubai-io", small search icon. In the
middle: a cyan user bubble with the typed text; a tiny subtle chip with a sparkle icon "Luna understood:
Community · AI · Engineering · Egyptian"; a grey bot bubble "Looking for groups near you…" with a three-dot
typing indicator. No tab bar anywhere on the right screen.
```

### 1b — Popup: Arrival guide (waypoints)  ★

**Feeds:** `miniapps/dxb-guide.html`, sheet chrome, route timeline, stop states, media slots, side-stop.

```text
FILE NAME: 01b-guide.png
POPUP over Screen 1. Keep the Home screen visible behind, dimmed by a 30% black scrim (the glass tab bar is
hidden behind the sheet). A bottom sheet covers 88% of the height with a grabber and 14 px top corners.
Sheet header (Dubai-io chrome): "DXB arrival guide", small grey "Built-in mini-app · Dubai-io", round close
button on the right.
Content, Google-Maps-directions feeling (waypoints, NOT turn-by-turn), calm and airy:
- Title row "Terminal 3 → Dubai Marina" with amber pill "Demo data"; grey line "6 waypoints · tap
  \"I'm here\" wherever you are". Under it a segmented route bar of 6 short capsules, first one cyan.
- A vertical timeline with a thin rail and numbered circles, all 6 stops visible.
  Stop 1 (current, expanded, cyan outline, soft cyan glow on its circle): "Off the plane", cyan caption
  "Current stop"; an airport diagram (isometric duty-free concourse map, pink/orange/blue zones, small
  legend) in a rounded 16:9 crop with a small "Tap to zoom" label; cyan pill "Reference map" and grey
  caption "T3 concourse & Dubai Duty Free · not your live position"; body "Follow the Arrivals signs.
  Depending on your gate, a short airport train may link your concourse to passport control."; a dashed
  side-stop card with a small lounge-map thumbnail: "Need a break?" / "Business Class Lounge, if your
  ticket includes it · tap to see the map"; cyan button "Done ✓ next stop".
  Stop 2 collapsed: passport icon tile, "Passport control", grey "Not yet".
  Stop 3 collapsed: suitcase tile, "Baggage reclaim", "Not yet".
  Stop 4 collapsed: customs tile, "Customs", "Not yet".
  Stop 5 collapsed: small check-in hall diagram thumbnail, "Arrivals hall", "Not yet".
  Stop 6 collapsed: small airport overview thumbnail with a cyan pin, "Choose your ride", "Not yet".
- Bottom: full-width white "I'm lost" button with cyan text.
- Tiny footer: "Reference maps are airport diagrams, not your live position. I only know a stop when you tap
  it: no indoor GPS."
```

### 1c — Popups: guide states (2-up)

```text
FILE NAME: 01c-guide-states.png
POPUPS over Screen 1, 2-up. Both are the same arrival guide sheet as 1b.
LEFT: the "I'm lost" panel open at the bottom of the sheet: white panel, text "I can't see where you are
indoors. Tap what's around you and I'll pick up from there.", five outlined cyan chips: "Gate numbers,
duty-free shops", "Passport counters or smart gates", "Baggage belts and screens", "Customs, green/red channel
signs", "Arrivals hall, people waiting". Stops 1 to 2 above are green-check "✓ You confirmed", stop 3 is current.
RIGHT: the map lightbox: full-bleed dark #111 background, top bar "Dubai International · Terminal 3" with
small "Reference map · not your live position" and zoom −, +, close buttons; the airport overview map
filled in, zoomed, with a pulsing cyan pin and a black tag "Terminal 3 · you told me".
```

---

## Screen 2 — Ask → provider rows

**Feeds:** `providerRows()` card, the "Luna understood" chip, row anatomy. Same card serves shopping.

```text
FILE NAME: 02-rows.png
SCREEN 2: CHAT ACTIVE after the visitor types a request (see NAVIGATION MODEL). Compact header with back
chevron, "Dubai-io" and a small search icon. At the bottom the glass composer "Ask Dubai-io" REPLACES the glass
tab bar (no tab bar shown). Same bubbles, cards and chips as Home.
Timeline:
1) Cyan user bubble: "find community of egyptians about ai engineering"
2) Tiny subtle system chip under it with a sparkle icon: "Luna understood: Community · AI · Engineering ·
   Egyptian" (low contrast, tappable feel, collapsible, not a bubble).
3) Grey bot bubble: "Here's where I found AI · Engineering · Egyptian groups: Dubai-io's own communities plus
   2 partner apps. Each opens its own mini-app. All demo examples, no real people."
4) One white card "Communities", subtitle "Opt-in groups · mutual accept only", amber pill "Demo data". Three rows
   with hairlines. Each row: 44 px rounded logo tile left, app name bold, small publisher pill, one metric
   line, one grey blurb line, cyan "Open" button right.
   Row A: tile cyan "D", "Dubai-io Communities", pill "Dubai-io", "2 matching groups · best fit 3 of 3",
   "Built-in · opt-in groups around you".
   Row B: tile violet "M", "Meetly (demo)", pill "Partner app (demo)", "2 matching groups · best fit 3 of
   3", "Partner app · meetups and clubs".
   Row C: tile orange "C", "CircleHub (demo)", pill "Partner app (demo)", "2 matching groups · best fit 2 of
   3", "Partner app · communities by origin and interest".
   Footer small grey: "No precise locations · nothing shared until you approve".
Make the rows a clean scannable list (Talabat-style clarity), best match first.
```

### 2a — Popup: partner app, sign-in → signed in (2-up)  ★

**Feeds:** sheet template, provider branding inside a sandbox, Google sign-in strip, group cards, match chips.

```text
FILE NAME: 02a-partner-sheet.png
POPUPS over Screen 2, 2-up. Chat dimmed behind (30% black scrim). Each is an 88% bottom sheet with grabber.
Sheet header (Dubai-io chrome): "Meetly (demo)", small grey "Partner mini-app · their own HTML", close button.
Inside, the PARTNER's own branding: violet #6B4EFF header with a white rounded logo tile "M", "Meetly (demo)"
bold white, "Partner app · their own mini-app", translucent chip "Demo data · synthetic groups, no real people".
LEFT, before sign-in: centered white card "Sign in to Meetly (demo)", "Use the Google account you already
use with Dubai-io. No new password.", a white "Continue with Google (demo)" button with a multicolour G,
small print "Shares your name and email with Meetly (demo). Dubai-io keeps the sign-in token; this app never
sees it."
RIGHT, signed in: green strip "Signed in with Google (demo) · name + email shared with Meetly (demo)", line
"Looking for: AI · Engineering · Egyptian", two white group cards:
 "AI Engineers Dubai · Arabic-speaking", "Talks and code nights", "Meetup group · 240 members · Business Bay
 (approximate)", soft cyan chips "✓ AI" "✓ Engineering" "✓ Egyptian", violet "Request to join";
 "Dubai Python Night", "Monthly lightning talks", "Meetup group · 410 members · Media City (approximate)",
 chips "✓ Engineering" "✓ AI", violet "Request to join".
Mono tiny footer on both: "manifest v2.3.0 · scopes: auth.signin, community.join_request" left,
"sandbox · no network" right.
```

### 2b — Popup: shopping app, product → order placed (2-up)  ★

**Feeds:** shopping template, "(demo)" price lines, buy-on-their-site note, success state.

```text
FILE NAME: 02b-shop-sheet.png
POPUPS over Screen 2 (a price comparison), 2-up, same sheet chrome as 2a. Partner: "Souq Express (demo)", green
#1F8A5B, white logo tile "SE", chip "Demo data · demo list prices".
LEFT, product: green strip "Signed in with Google (demo) · name + email shared with Souq Express (demo)"; a
white product card with a 120 px abstract earbuds-case image on a green-to-charcoal gradient (no real brand),
title "Airpods Pro", big price "AED 85 (demo)", grey "List AED 85 (demo) + shipping free · arrives Tomorrow",
full-width green "Buy now". Small grey note: "You pay here, on Souq Express (demo)'s page. Dubai-io never
charges or sees your card."
RIGHT, placed: a centered white card with a big green check, "Order placed", "Airpods Pro · AED 85 (demo)",
"Order #SE-53209 · arrives Tomorrow".
Mono footer: "manifest v4.1.0 · scopes: auth.signin, purchase.report" and "sandbox · no network".
```

---

## Screen 3 — Approve → provider events

**Feeds:** approval card (Will be shared / Never shared), status track, "Merchant update" messages, calendar
follow-up. Truth-in-status is visible here.

```text
FILE NAME: 03-approve-events.png
SCREEN 3: CHAT ACTIVE showing an approval and what happens after. Compact header with back chevron, glass
composer at the bottom replacing the tab bar. Timeline:
1) White approval card: title "Request to join AI Engineers Dubai · Arabic-speaking?", grey sub "Meetup group ·
   Business Bay (approximate) · via Meetly (demo)", amber pill "Demo data". Two light-grey info blocks:
   "WILL BE SHARED": "First name · interests (AI · Engineering) · approximate area (Dubai Marina) · contact via
   in-app chat". "NEVER SHARED": "Phone number · exact location · email". Small grey "Nothing is sent until
   you tap. The group's admin decides." Buttons: cyan "Approve and send", grey "Cancel".
2) Compact status card: "Request sent to AI Engineers Dubai", "Nothing is shared until a group admin
   approves.", mono tag "SUBMITTED", a vertical track: "Sent to group" done, "Group admin accepted" now.
3) Bot bubble with purple pill "Community update": "AI Engineers Dubai accepted you ✓. Their next meetup:
   Saturday, public café in Marina. Say the word and I'll add it to your plan."
4) Bot bubble with purple pill "Merchant update": "I found you purchased Airpods Pro (#SE-53209) from Souq
   Express (demo) for AED 85 (demo). I'm adding a follow-up to your calendar."
5) White calendar card with a calendar icon: "Calendar · follow-up", "Delivery check: Airpods Pro ·
   Tomorrow", amber pill "Demo data", mono tag "ACCEPTED", grey "From order #SE-53209 at Souq Express
   (demo). Dubai-io never charged anything."
Make the hierarchy obvious: what needs my tap, what happened, what is only information.
```

### 3a — Popup: proactive notification banner

**Feeds:** `trip.*` / `geo.*` trigger presentation (Demo trigger, quiet hours, one message per trigger).

```text
FILE NAME: 03a-banner.png
POPUP over ANY screen (use the idle Home screen with its glass tab bar dimmed slightly behind). A notification banner sliding down from the
top, below the status bar: white rounded card with soft shadow, left a round cyan Dubai-io icon, bold title
"Marina Mosque is 400 m away", grey body "Bring wudu? Next prayer: Maghrib 17:52.", purple pill "Demo
trigger", small grey "now". Under it a smaller second banner variant stacked: title "Good morning. Flight
departs 12:40", body "VAT: validate before your 10:30 check-in.", and a cyan pill "Quiet hours 22:00–07:00
respected: queued for 07:00".
```

---

## Screen 4 — Lost item in a taxi

**Feeds:** `recovery()` flow: pay-choice chips, trace states, driver card with fake photos, `driver en route`.

```text
FILE NAME: 04-lost-item.png
SCREEN 4: LOST-ITEM FLOW, CHAT ACTIVE. Compact header with back chevron, glass composer at the bottom replacing
the tab bar. Timeline:
1) Cyan user bubble: "I left my bag in the taxi"
2) Bot bubble: "I'm sorry. I don't have your taxi details saved. How did you pay? That decides how we trace the
   driver." Under it a white card "How did you pay?" with two outlined chips "Paid by card" and "Paid cash",
   purple pill "Demo trigger · Simulated trace".
3) Cyan user bubble "Paid cash". Bot bubble: "Contacting the Airport taxi valley team… Cash trips can't be
   traced by payment, so they check the rank records for your pickup." Then a white status card "Airport taxi
   valley team", sub "Request sent (simulated) · waiting for their reply", a progress dot row, mono tag
   "UNKNOWN_STATUS", grey "Unknown until they reply. I won't invent a result."
4) Reply card, the hero of the screen: title "Matched from your route and time", sub "DXB T3 → Dubai Marina ·
   00:40". Left: a rounded placeholder photo of a cream taxi (flat illustration, plate "DXB-4471"); right:
   a round driver portrait placeholder (abstract silhouette, no real face) with "Imran K." and "Taxi
   #DXB-4471". A green-tinted block: "Driver notified, he is on his way", mono tag "driver en route", "ETA 12
   min to the Terminal 3 rank". Purple pill "Demo trigger · Simulated trace". Buttons: cyan "Message
   driver", grey "Prepare RTA report anyway".
5) Small grey foot: "Simulated reply from the valley team (demo fixture)."
Calm and reassuring: the visitor is stressed, so one obvious next step.
```

### 4a — Popups: driver detail + RTA report (2-up)

```text
FILE NAME: 04a-driver-rta.png
POPUPS over Screen 4, 2-up, 88% bottom sheets over the dimmed chat.
LEFT, "Driver": sheet title "Taxi #DXB-4471", grey "Matched from your route and time". A large placeholder
photo of the cream taxi, a driver portrait placeholder, "Imran K.", mono tag "driver en route", "ETA 12 min to
the Terminal 3 rank", a "Demo trigger · Simulated trace" pill, buttons "Message driver", "Call the valley
team".
RIGHT, "Lost item report": sheet title "Lost item report", pill "Not filed yet". A white block "Trip" with
"Time 00:40 · Pickup DXB Terminal 3 taxi rank · Drop-off Dubai Marina · Plate DXB-4471 · Roof cream · Receipt
photo" and a green pill "You told me"; a field "Describe the bag" with placeholder "e.g. black backpack,
laptop inside"; cyan "Prepare report". Below it the done state as a small card: mono tag
"PREPARED_NOT_FILED", "Handoff to the official channel (RTA lost & found). I won't mark anything recovered until
you tell me", buttons "Contact official lost & found", "Copy report".
```

---

## Screen 5 — Services and Me (2-up)

**Feeds:** Services list ("Talabat-normal"), category chips, rows, Me tab memory ("You told me"), permissions.

```text
FILE NAME: 05-services-me.png
SCREEN 5, 2-up: two full portrait screens side by side, no device frames. Both are IDLE state: the AI search
field ("Ask Dubai-io") sits at the top under the title, and the floating Liquid Glass tab bar is at the bottom
(no composer), because no chat is in use.
LEFT, Services tab active: large title "Services", grey lead "Each merchant opens as its own mini-app, inside a
sandbox." A horizontal category segment: "Pharmacy" (selected, cyan fill), "Laundry", "Groceries", "Tailors".
Vertical list of white merchant rows: coloured logo tile with initials, name bold, "★ 4.7 · from AED 9 (demo) ·
0.8 km", grey short offer line, amber pill "Demo merchant", cyan "Open". Rows: "Palm Leaf Pharmacy" (green
tile PL), "Night Owl Pharmacy" (indigo tile NO).
RIGHT, Me tab active: large title "Me". iOS Settings-style groups: "Profile": row "Mode" with grey "Set by you,
never guessed" and a Visitor/Resident segmented control. "What I remember (you told me)": "Staying in ·
Dubai Marina", "Baggage belt · Belt 7 · EK 002 (demo)", "Interests · AI · Engineering · Egyptian", each with a
green pill "You told me". "Permissions": "Trip reminders" green pill "On"; "Background location" grey pill
"Off · not used". Glass tab bar with Me active.
```

### 5a — Popups: merchant app + shop onboarding (2-up)

```text
FILE NAME: 05a-merchant-onboarding.png
POPUPS over the Services screen, 2-up, 88% bottom sheets.
LEFT, merchant mini-app (their own branding): green #2F7D5B header "Palm Leaf Pharmacy", "Everyday medicines,
delivered", chip "Delivering near you"; a 2-column grid of product tiles with an icon, name and "AED x (demo)"
and −/+ steppers (e.g. "Paracetamol 500mg ×24 AED 9 (demo)", "Sunscreen SPF 50 AED 59 (demo)"); sticky bottom
bar "AED 18.00 (demo)", "fixed total · pay on delivery", green "Send order request". Dubai-io header:
"Palm Leaf Pharmacy" / "Merchant mini-app · their own HTML".
RIGHT, shop onboarding: Dubai-io chrome card "Deira Star Laundry", "Shirt press AED 6 · Suit AED 25 ·
Same-day", pill "Operator review", text "AI-generated mini-app preview is ready. Nothing goes live without
operator approval.", a small phone preview thumbnail of the generated mini-app (green, price list), cyan
"Operator: approve and publish".
```

---

## 6 (optional) — Backstage operator console (desktop 16:10)

```text
FILE NAME: 06-backstage.png
Same product, a DESKTOP operator console beside the phone, 1600x1000 px, same palette and type. Title "Under
the hood", sub "What the agent, the merchants and the sandbox are doing", a cyan "Restart demo" button. Panels
in rounded #F2F2F7 cards: "Merchant inbox" (rows with request id, merchant, status tag, small Accept / Mark
ready / Complete buttons), "Trigger panel (operator)" with four chips "geo.mosque_nearby",
"trip.event_tomorrow", "trip.departure_am", "qibla.now" and the note "Fires a Demo trigger. Each fires twice
-> one message.", and an "Event log" with colour-coded kinds (trigger purple, agent blue, tool teal, bridge
amber, action green, memory cyan, security red) in a monospace list with timestamps and small JSON detail.
```

---

## Part 2 — Resident / VIP arc (R-series)

Second arc, built **after** the visitor redesign ships (PLAN.md items 10–11). Same chat, same style lock, same
navigation model. Paste **R0** once, then R1 … R6.

**Personality (the one line):** Dubai-io does not just answer, it **mobilises**. You state a goal; it makes a
plan, sends agents to providers' sites, APIs and tools, prepares every step and comes back with **one thing
to approve**.

```text
Goal → Plan → Agents fan out (websites, partner agents, APIs, tools) → Steps prepared, live status
     → ONE approval → Provider confirms → Calendar entries, to the second
```

**Rules that hold in every R prompt**

| Rule | In practice |
|---|---|
| No quotes | Fixed published prices. Providers answer **slot requests**: "Can do Thu 10:00" / "No slot" / "Waiting". The price never changes |
| No government execution | A private runner visits the centre. Official portal = handoff link. Fines are display-only. Never "Renewed" without a provider event |
| Truth in status | Only the status words in Prompt 0, always a human line + mono code, with `hh:mm:ss` timestamps |
| Fictional providers | Runners Valet Hands (demo), Rank Runner (demo), Express Pit (demo) · insurers Shield Motor (demo), Gulf Assure (demo), Palm Cover (demo) · marketplaces Souq Express (demo), NestHome (demo) · pros FixIt Pros (demo), Maid Match (demo), BuildRight (demo) · found shop Al Barsha Cooling (demo). No real brands (Amazon, IKEA …) |
| VIP | A small cyan "VIP" pill plus a "Priority" line. No gold, no new colours |

| # | Prompt | Type | Core |
|---|---|---|---|
| **R0** | Resident / VIP context patch | context only | ★ |
| **R1** | Home, resident + VIP | screen | ★ |
| **R2** | Goal in motion: renew car licence (plan, agents at work) | screen | ★ |
| R2a | Papers check | popup | |
| **R3** | Providers: fixed prices + slot replies | screen | ★ |
| R3a | Runner proposal + approval | popup | ★ |
| **R4** | Insurance choice (2-up) | screen + popup | ★ |
| **R5** | Done: timeline + calendar to the second | screen | ★ |
| **R6** | Home services: fix it / maid / renovation (2-up) | screen + popup | ★ |

### R0 — Resident / VIP context patch

```text
RESIDENT / VIP UPDATE. Do NOT generate an image for this message, reply with exactly: "Ready".
Dubai-io now also serves residents, especially VIPs. Same app, same style lock, same navigation model.
PERSONALITY: Dubai-io does not just answer, it mobilises. The user states a goal; Dubai-io makes a plan, sends
agents to the providers' websites, APIs and tools, prepares each step, and comes back with ONE thing to approve.
Show this as a "goal plan": steps in order, each with the sources being contacted (small chips: website, partner
agent, API, tool) and a live status, with timestamps to the second (hh:mm:ss).
RULES: fixed published prices only. Providers reply to SLOT requests ("Can do Thu 10:00", "No slot", "Waiting")
and the price never changes; no quotes or bids anywhere. Dubai-io never submits to a government entity: a
private runner visits the centre, the official portal is a handoff link, fines are display-only. Status words
only from the list; every status comes from a provider event, shown as a human line plus the mono code.
VIP is a small cyan "VIP" pill plus a "Priority" line. No gold, no new colours.
FICTIONAL PROVIDERS ONLY: runners Valet Hands (demo), Rank Runner (demo), Express Pit (demo); insurers Shield Motor (demo), Gulf Assure
(demo), Palm Cover (demo); marketplaces Souq Express (demo), NestHome (demo); pros FixIt Pros (demo), Maid Match
(demo), BuildRight (demo); found shop Al Barsha Cooling (demo).
```

### R1 — Home, resident + VIP

```text
FILE NAME: R1-resident-home.png
SCREEN R1: HOME (Companion tab), IDLE state, resident. Same layout as the visitor Home: AI search on top, floating
Liquid Glass tab bar at the bottom, NO composer.
Top: "Dubai-io" large bold, right side two small pills "Resident" and "VIP". AI search "Ask Dubai-io". Under it a
context strip: "Dubai Marina · you told me".
Content: 1) hero card: eyebrow "Dubai-io · Priority", title "Good afternoon, Alex.", body "Two things are coming up.
I can handle both." 2) "Coming up" card with two rows: car icon "Car licence expires in 12 days" with cyan
"Renew" chip; wrench icon "AC service is due this month" with cyan "Fix it" chip. 3) "Try asking" strip of three
cards: "Renew my car licence", "Fix something at home", "Find a maid". Amber pill "Demo data" on the hero.
Bottom: glass tab bar only (Companion active, Services, Civic, Me).
```

### R2 — Goal in motion: renew my car licence

**Feeds:** the goal-plan card: the visual core of the "mobilise" personality.

```text
FILE NAME: R2-goal-plan.png
SCREEN R2: CHAT ACTIVE (compact header with back chevron, glass composer replacing the tab bar).
1) Cyan user bubble: "renew my car licence"
2) Subtle chip with sparkle: "Luna understood: Resident · Vehicle · Licence renewal"
3) Grey bot bubble: "On it. I'm preparing everything and I'll come back with one thing for you to approve."
4) Large white "goal plan" card: title "Renew car licence", sub "5 steps · 2 done · 00:01:12 elapsed", purple pill
   "Demo trigger", amber "Demo data". A vertical step list with a rail, each step with a status icon, a
   human line, a mono tag and a hh:mm:ss time:
   1 "Check your papers" · done · "From what you told me" · ACCEPTED · 14:02:07
   2 "Find pickup providers" · in progress · three small source chips "Valet Hands (demo) · site",
     "Rank Runner (demo) · agent", "Shield Motor (demo) · API" · "3 slot requests sent" · SUBMITTED · 14:02:11
   3 "Propose a runner" · waiting · pending
   4 "Choose insurance" · waiting · pending
   5 "Confirmed by the provider" · waiting for provider · pending
   Footer small grey: "Prices are published and fixed. Nothing is marked done until a provider confirms."
Make it feel like quiet, competent work happening in parallel, with one clear thing coming next.
```

### R2a — Popup: papers check

```text
FILE NAME: R2a-papers-check.png
POPUP over R2, 88% bottom sheet. Title "Your papers", grey "Checked from what you told me. Verify on the official
portal." Rows with icon, name, value, green pill "You told me": "Vehicle registration · expires 24 Oct",
"Emirates ID · valid", "Insurance · expires 24 Oct", amber chip "Vehicle test · needed". A row "Fines" with grey
"Display only · open the official portal" and an external-link icon. Cyan button "Add a document photo".
Footer: "Dubai-io never submits anything to RTA or Tasjeel."
```

### R3 — Providers: fixed prices + slot replies

```text
FILE NAME: R3-providers-slots.png
SCREEN R3: CHAT ACTIVE, same chrome as R2. Bot bubble: "Three providers can pick up and renew. Prices are
published; they only confirm slots." One white card "Pickup and renewal", amber "Demo data". Three rows: logo
tile, name, pill "Partner app (demo)", fixed price "AED 180 (demo) · fixed", a slot-reply chip and a mono tag,
cyan "Open":
Valet Hands (demo), green tile VH, "Can do Thu 10:00", ACCEPTED, reply time 14:02:19.
Rank Runner (demo), teal tile RR, "No slot today · next Fri 09:00", DECLINED.
Express Pit (demo), indigo tile EP, "Waiting for reply…", pending.
Footer: "Price never changes after a reply."
```

### R3a — Popup: runner proposal + approval

```text
FILE NAME: R3a-runner-proposal.png
POPUP over R3, 88% bottom sheet in Dubai-io chrome. Title "Valet Hands (demo)", pills "Partner app (demo)" and
"Priority · VIP". Runner row: round silhouette avatar, "Faisal M.", "Licensed runner · 4.9 ★ (demo)". A plan block:
"Thu 10:00 pickup · Dubai Marina" → "Vehicle test and renewal at a licensed centre" → "Back by 14:00". Fixed price
"AED 180 (demo)". Two info blocks: "WILL BE SHARED": "Registration copy · Emirates ID copy · pickup address ·
contact via in-app chat". "NEVER SHARED": "Insurance details until you choose · payment card". Buttons: cyan
"Approve and send", grey "Cancel". Small grey: "A private runner visits the centre. Dubai-io submits nothing."
```

### R4 — Insurance choice (2-up)

```text
FILE NAME: R4-insurance.png
SCREEN R4, 2-up. LEFT: chat with a white card "Motor insurance" listing three insurers sorted by price, each with
a logo tile, name, pill "Partner app (demo)", fixed yearly price and a "Choose" button: Palm Cover (demo)
"AED 1,320 / year (demo)", Shield Motor (demo) "AED 1,450 / year (demo)", Gulf Assure (demo) "AED 1,780 / year
(demo)". RIGHT: Shield Motor's sheet (88% bottom sheet, its own deep-blue branding, Google sign-in strip): three
plan cards "Third party · AED 980 (demo)", "Comprehensive · AED 1,450 (demo)" selected, "Comprehensive + agency ·
AED 1,980 (demo)", mono footer "manifest · scopes: auth.signin, policy.select" and "sandbox · no network".
```

### R5 — Done: timeline + calendar to the second

**Feeds:** the proof of follow-through: every step, who confirmed it and when, as calendar entries.

```text
FILE NAME: R5-done-timeline.png
SCREEN R5: CHAT ACTIVE. White card "Car licence renewal", green mono tag "COMPLETED", sub "Confirmed by Valet Hands
(demo) · Thu 12:03:17". Under it a month strip showing three small dots on Thu. Then a vertical timeline, each
event with a hh:mm:ss time, a human line, the source chip and a small calendar icon "Added to calendar":
14:02:07 "Papers checked" · you told me
14:02:19 "Valet Hands replied: Thu 10:00" · ACCEPTED
14:05:33 "You approved the runner"
Thu 09:58:02 "Runner arrived at Dubai Marina" · provider update
Thu 10:41:55 "Vehicle test passed" · provider report
Thu 12:03:17 "Registration renewed" · COMPLETED · provider confirmed
Thu 13:10:44 "Insurance policy issued by Shield Motor (demo)" · COMPLETED
Thu 13:58:20 "Car returned to Dubai Marina" · provider update
Footer small grey: "Every line came from a provider. Dubai-io submitted nothing to RTA."
```

### R6 — Home services: fix it / maid / renovation (2-up)

```text
FILE NAME: R6-home-services.png
SCREEN R6, 2-up. LEFT: chat after "my AC is not cooling". A white card "Fix it · AC", three category chips on top
"Fix it" (selected), "Maid", "Renovation". Rows with logo tile, name, source pill and a fixed price:
NestHome (demo), pill "Marketplace", "AC service pack · AED 220 (demo)", "Delivered + installed Thu";
FixIt Pros (demo), pill "Pro", "from AED 150 (demo) · next slot today 17:00";
Al Barsha Cooling (demo), pill "Found nearby", "from AED 120 (demo) · next slot tomorrow 09:00".
RIGHT: FixIt Pros' sheet (88% bottom, its own orange branding): "AC check and gas refill · AED 150 (demo)", "AC
deep clean · AED 220 (demo)", a slot picker chips "Today 17:00" (selected) "Tomorrow 09:00" "Tomorrow 14:00",
green strip "Signed in with Google (demo)", orange "Request this slot" button, footer "price is fixed · they
confirm the slot".
```

---

## Other retouchings (not image work)

Found while building. Tackle after the images land, in this order.

| # | Retouch | Where | Why |
|---|---|---|---|
| 0 | Navigation model: AI search on top, Liquid Glass tab bar when idle; composer replaces the bar in chat; back chevron returns | `index.html`, `styles.css`, `app.js` `showTab()` / `start()` | Today composer and tab bar show together |
| 1 | Typing indicator (three dots) instead of silent delays | `app.js` `typing()` | Chat feels dead for 0.5 s |
| 2 | Icons: replace emoji with one SVG set | cards, tiles, tabs | Consistency with prompt 0 |
| 3 | Human status lines + mono code (never a raw `UNKNOWN_STATUS`) | `statusTag()` | Readable trust labels |
| 4 | Guide: collapse the map on the current stop, sticky "Done / I'm here" bar | `miniapps/dxb-guide.html` | CTA is below the fold on stop 1 |
| 5 | Rows card: 2 lines per row, publisher pill beside the name | `providerRows()` | Dense at 390 px |
| 6 | Starter suggestions on first load | `start()` | Luna is invisible until the user types |
| 7 | "Luna understood" chip in chat, then collapses | `app.js` router | Today only in Under the hood |
| 8 | Loading and empty states | `providerRows`, mini-apps | Only the happy path exists |
| 9 | Transitions inside sheets (sign-in → content) | partner templates | Hard swap today |
| 10 | Arabic and RTL | `styles.css`, `lang` | Luna already reads Arabic |
| 11 | Dark mode tokens | `styles.css` `:root` | Many phones default to dark |
| 12 | Accessibility: amber pill contrast, 44 px targets, focus order | global | Audit before submission |
| 13 | Arrival-side maps, image licence check | `demo/maps/*` | `airportmaps.com` watermark, departures diagrams |
| 14 | Backstage log: group, collapse JSON, filter by kind | `index.html`, `app.js` | Stage readability |
| 15 | Real extractor behind `LUNA.understand` | `apps/api` (Phase 1) | Mock covers 3 intents |

## After the images arrive

1. Save to `demo/_ref/` on the `redesign` branch (names from the series map; R-series as `R1-…png`).
2. Build in series order: tokens and chrome (0, 1) → navigation takeover (1a) → guide (1b, 1c) → rows (2) →
   sheet templates (2a, 2b) → approvals (3) → banner (3a) → recovery (4, 4a) → tabs (5, 5a) → console (6).
3. Verify each screen with a Playwright screenshot at 390 px against its reference image, then run the
   guardrail audits (no `allow-same-origin`, bridge audit returns zero lines, prices say "(demo)").
