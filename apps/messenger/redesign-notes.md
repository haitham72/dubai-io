# Messenger Redesign — Desktop UI/UX Specification

**Implementation note (2026-10-08):** This remains the approved desktop design reference; its checklists are design requirements, not test results. Current runtime behavior and verification live in [ARCHITECTURE.md](ARCHITECTURE.md) and [agents/README.md](agents/README.md). Voice keeps the chat clear, meeting drafts float without resizing it, and event/chat images expand in a shared viewer. Current offline checks: 169 passed / 1 skipped; voice dev 113/113 and holdout 32/32. Live audio/cloud and browser interactions remain unverified; local models are deferred.

**Status:** Approved visual direction  
**Primary viewport:** 1920 × 1080  
**Style:** iOS/macOS light glass, minimal, calm, spacious  
**Source of truth:** the 15 selected concept images supplied in the final contact sheets  
**Scope:** desktop Messenger redesign and interaction model

---

## 1. Product direction

Messenger is a private chat application with an integrated agentic assistant and utility workspaces.

The redesign must feel like one coherent native desktop product rather than a chat app with unrelated AI widgets added on top.

The core product model is:

- **Chats** for person-to-person messaging.
- **Messenger Updates** for background agent tasks and completed results.
- **Dedicated workspaces** for Flights, Stocks, Weather, Mail, Calendar, Files and AI Chat.
- **Profile / account** as a focused modal over the current screen.
- A **persistent global rail** that makes every major capability one click away.

The visual reference is closer to modern Apple Mail / Calendar / Files conventions than to a dense enterprise dashboard.

---

# 2. Core design principles

## 2.1 Minimal by default

The normal state must show only what is immediately useful.

Do not permanently expose:
- agent task details,
- large notification cards,
- deep controls,
- verbose AI reasoning,
- extra navigation panels,
- repeated toolbars.

Complexity appears only after an explicit user action.

## 2.2 Progressive disclosure

Messenger uses four information depths:

1. **Collapsed**
   - one compact row or icon,
   - e.g. `Messenger Updates 9+`.

2. **Preview**
   - a horizontal set of compact cards,
   - used for recent agent results.

3. **Detail**
   - one selected card expands downward as an anchored overlay.

4. **Full workspace**
   - opening the result or selecting a module replaces the main workspace with the complete feature UI.

## 2.3 Glass, not glass everywhere

Use frosted translucent surfaces for:
- global navigation,
- notification surfaces,
- floating dropdowns,
- modals,
- selected cards,
- module sidebars.

Main content should remain mostly white / near-white for readability.

Avoid excessive blur, gradients or transparency inside dense text/data areas.

## 2.4 Preserve the user’s context

Notification previews and result cards are overlays.

They must **not resize, compress, crop or reflow the underlying chat**.

When an overlay closes, the user returns to exactly the same chat position.

## 2.5 Content-first

Large areas are reserved for:
- the conversation,
- the selected email,
- the calendar,
- the flight search,
- the stock chart,
- the file grid,
- the generated image,
- the research output.

Navigation and controls stay visually quiet.

---

# 3. Global application architecture

At desktop size the app uses up to three visual zones:

```text
┌────────────┬───────────────────────────┬─────────────────────────────────────────┐
│ Global rail│ Module sidebar / index    │ Main workspace                          │
│ ~88 px     │ ~360–450 px               │ Remaining width                         │
└────────────┴───────────────────────────┴─────────────────────────────────────────┘
```

### Zone A — persistent global rail

The narrow far-left rail remains present across the application.

Typical destinations:

- Messenger / Home
- Chats
- Flights
- Stocks
- Weather
- Mail
- Calendar
- Files
- AI Chat
- Research
- History
- Settings
- User avatar

Only the selected icon receives a soft blue or lavender selected background.

### Zone B — module sidebar / index

The second column changes completely depending on the selected module.

Examples:

- Chats → people/conversation list.
- Flights → bookings, quick search, popular routes.
- Stocks → market overview, watchlist, indices.
- Mail → inbox folders and message list.
- Calendar → mini calendar and calendar groups.
- Files → file categories, recents, storage sources.
- AI Chat → new chat and conversation history.
- Profile → modal navigation.

**The chat list is not persistent when another module is selected.**

### Zone C — main workspace

The right side is the working surface of the selected module.

Examples:
- conversation,
- flight search,
- stock chart,
- weather dashboard,
- email reader,
- weekly calendar,
- file browser,
- AI answer.

---

# 4. Layout and spacing

## 4.1 Desktop target

Design against **1920 × 1080**.

Recommended practical dimensions:

| Element | Guideline |
|---|---:|
| Global rail | 80–92 px |
| Module sidebar | 360–450 px |
| Top header | 72–88 px |
| Main outer margin | 20–28 px |
| Major card gap | 14–18 px |
| Minor row gap | 8–12 px |
| Main card radius | 18–24 px |
| Compact control radius | 10–16 px |

Do not scale controls up simply to fill the screen.

The reference designs rely on **whitespace**, not oversized UI.

## 4.2 Density

Use Apple-like density:

- compact labels,
- comfortable but not oversized rows,
- restrained icon size,
- thin separators,
- one primary action per card,
- secondary actions as text/buttons or overflow.

---

# 5. Visual system

## 5.1 Base palette

Approximate semantic palette:

- App background: `#F5F8FC`
- Main surface: `rgba(255,255,255,0.90–0.96)`
- Glass surface: `rgba(245,248,255,0.72–0.84)`
- Border: `rgba(50,80,130,0.08–0.14)`
- Primary text: `#101828`
- Secondary text: `#667085`
- Messenger blue: `#1677FF`
- Messenger purple: `#7C3AED` / soft lavender tint
- Success: `#22C55E`
- Warning: amber
- Error: red

Exact values may be tuned during implementation; visual hierarchy matters more than literal hex values.

## 5.2 Typography

Use a modern system sans-serif stack.

Suggested:

```css
font-family:
  -apple-system,
  BlinkMacSystemFont,
  "SF Pro Text",
  "SF Pro Display",
  "Segoe UI",
  sans-serif;
```

Hierarchy:

- Page/module title: 26–32 px
- Section title: 18–22 px
- Standard body: 14–16 px
- Secondary metadata: 12–14 px
- Tiny badges/timestamps: 11–12 px

Avoid excessive bold text.

## 5.3 Shadows

Shadows are very soft.

Use stronger elevation only for:
- modal windows,
- notification expansion,
- dropdown result cards.

No heavy dark shadow.

## 5.4 Frosted surfaces

Typical glass treatment:

```css
background: rgba(255,255,255,.74);
backdrop-filter: blur(24px) saturate(140%);
border: 1px solid rgba(255,255,255,.55);
box-shadow: 0 12px 40px rgba(30,60,110,.08);
```

---

# 6. Chats — default state

Reference: **R04 / R13**

The chat module is the primary communication view.

## 6.1 Middle column

Contains:

1. `Chats` title.
2. Compose and filter controls.
3. Search:
   - `Search chats, tasks, files...`
4. Messenger Updates summary, when agent activity exists.
5. Conversation list.

Conversation rows contain:
- avatar,
- display name,
- latest message,
- timestamp,
- unread count,
- read/mute state where relevant.

## 6.2 Main conversation

Header:
- contact avatar,
- name,
- online/status,
- voice call,
- video,
- search,
- overflow.

Conversation:
- incoming bubbles left,
- outgoing bubbles right,
- images retain proper media aspect ratio,
- voice messages remain compact horizontal players,
- sender avatar is shown on incoming content where appropriate.

Composer:
- attachment,
- text input,
- emoji,
- microphone,
- send.

### Media rule

Images sent in chat must never appear as stretched decorative strips.

Use:

```text
max width: ~560–680 px desktop
natural aspect ratio
object-fit: cover only when a fixed preview crop is explicitly intended
rounded corners: 14–18 px
```

The approved Dubai beach image is a normal chat media message with the sender avatar aligned to it.

---

# 7. Messenger Updates notification system

This is one of the defining interactions of the redesign.

The purple notification surface lives **inside the Chats middle column**, above people.

It is inspired by the highlighted Apple Mail informational block.

---

## 7.1 State A — collapsed summary

Reference: **R04**

Example:

```text
✦ Messenger Updates                         9+
  Image ready, flight found, 5 more...    >
```

Properties:

- lavender glass background,
- one row,
- icon + title + concise summary,
- unread counter,
- right chevron,
- same width as the chat-list content,
- does not invade the conversation.

This is the default state.

---

## 7.2 State B — horizontal update tray

Reference: **R13**

Clicking the purple summary expands it **to the right as an overlay**.

```text
[Messenger Updates] [Image ready] [Flight found] [Research ready] [Email draft ready]
```

Rules:

- anchored to the purple middle-column card,
- extends over the chat,
- does not push the conversation down,
- one coherent frosted lavender container,
- individual update cards are compact,
- cards behave like an Instagram Stories tray,
- horizontal scrolling is allowed,
- a partial next card may remain visible,
- close button restores State A.

Suggested animation:

```text
180–240 ms
opacity + horizontal reveal
ease-out
```

---

## 7.3 State C — vertical activity list

Reference: **R08**

A downward swipe / pull / explicit expand gesture on the purple summary reveals a compact list **inside the middle column**.

Example:

```text
Image ready                  5m ago     ✓
Flight found                12m ago     ✓
Generating video                45%      ◌
Research                  2:23 seconds   ◌
Email draft ready             1h ago     ✓
```

Rules:

- same lavender glass family,
- compact 40–48 px rows,
- no large cards,
- active jobs use a spinner/progress indicator,
- completed jobs use a check,
- progress text is right aligned,
- people list begins directly below it,
- collapse returns to the one-row summary.

This view is for **task status scanning**, not detailed results.

---

# 8. Update-card detail behavior

When State B is open, selecting one update card opens a **downward anchored detail overlay**.

Important:

- the detail begins visually under the selected top card,
- the selected card receives a subtle active border,
- the overlay is layered over the chat,
- the chat is not cropped, resized or compressed,
- the overlay should use the minimum width necessary for its content,
- a wide result may extend toward the right edge,
- closing the detail returns to the horizontal tray.

---

# 9. Image Ready detail

Reference: **R12**

Top card:

```text
Image ready
Your social post visual is ready
```

Expanded detail:

- title,
- generated image at proper aspect ratio,
- generated timestamp,
- `Ready` status,
- actions:
  - Open
  - Share
  - Use in chat

Do not turn the preview into a banner strip.

The media preview is the focal point.

---

# 10. Flight Found detail

Reference: **R09**

Top card:

```text
Flight found
3 flights to Dubai
from AED 1,240
```

Expanded detail uses a compact flight-results table/list rather than oversized booking cards.

Each result shows:

- airline + logo,
- flight number,
- date,
- departure airport/time,
- duration / stop state,
- arrival airport/time,
- fare,
- class,
- best-price tag when relevant,
- right chevron.

Actions:

- View all flights
- Share
- Use in chat

Selecting `View all flights` opens the full Flights workspace.

---

# 11. Research Ready detail

Reference: **R14**

Top card:

```text
Research ready
5 key insights
on market trends
```

Expanded state is split into:

### Left / result index
A compact list of completed research items.

Example:
- UAE AI market trends 2026
- RAG vs fine-tuning comparison
- Instagram comment moderation
- Local LLM deployment options
- UAE AI job market analysis

### Right / preview
Selected result with:
- title,
- timestamp,
- short introduction,
- numbered key findings,
- concise text.

Actions:
- Open full report
- Share
- Use in chat

The detail should feel like a document preview, not another chat message.

---

# 12. Email Draft Ready detail

Reference: **R07**

Top card:

```text
Email draft ready
Your follow-up draft is prepared
```

Expanded detail:

### Left
List of recent drafts / follow-ups.

### Right
Selected draft:
- To
- Subject
- email body
- minimal actions

Primary actions:
- Open draft
- Share
- Use in chat

The email content remains readable and mostly white; purple is an accent, not a full background.

---

# 13. Flights workspace

Reference: **R10**

Selecting Flights on the global rail changes the module sidebar and main workspace.

Chats disappear.

## 13.1 Flights sidebar

Contains:

- `Flights`
- search flights/bookings/airlines,
- New Booking,
- My Bookings,
- Quick Search:
  - Return Trip
  - One Way
- Popular routes/destinations.

This sidebar is the navigation/index for the Flights module.

## 13.2 Main Flights workspace

Top:
- natural-language Messenger prompt:
  - `Where would you like to fly?`
- filters.

Destination cards:
- Dubai,
- Riyadh,
- Cairo,
- London,
- or contextually relevant destinations.

Booking/search form:
- Flights / Hotels / Cars tabs,
- From,
- To,
- Departure,
- Return,
- Passengers,
- Class,
- search CTA.

Below:
- recent searches,
- booking results or recommendations.

Use the same glass language but keep the form surface largely white.

---

# 14. Stocks & Markets workspace

Reference: **R05**

## Module sidebar

Contains:

- Market Overview
- My Watchlist
- Popular indices

Watchlist rows:
- ticker,
- company,
- sparkline,
- current price,
- daily change.

## Main workspace

Top:
- Messenger stock/market query field,
- market selector.

Main navigation:
- Overview
- Chart
- Financials
- News
- Analysis
- Peers

Primary stock detail:
- ticker/company,
- current price,
- daily move,
- timeframe selector,
- chart.

Additional information:
- market cap,
- P/E,
- 52-week range,
- volume,
- dividend yield,
- beta.

Right-side contextual panel may include:
- follow,
- key stats,
- analyst ratings,
- price target,
- Buy/Sell actions if supported by product requirements.

News cards remain secondary.

---

# 15. Weather workspace

Reference: **R06**

Weather should feel visually immersive but still minimal.

Top:
- Weather title,
- natural-language assistant entry,
- location search,
- optional location action.

Hero:
- city,
- country,
- temperature,
- condition,
- feels-like,
- humidity,
- wind,
- UV,
- air quality,
- relevant skyline/weather visual.

Navigation:
- Today
- Hourly
- 7 Days
- Air Quality
- Maps

Below:
- hourly forecast,
- 7-day forecast,
- weather map,
- air quality,
- Sun & Moon.

Avoid turning the weather page into a dense analytics dashboard.

---

# 16. Mail workspace

Reference: **R03**

Use Apple Mail-inspired hierarchy.

## Mail sidebar/index

Contains:

- Mail title,
- search,
- inbox categories,
- message list.

Example categories:
- All
- Primary
- Social
- Updates
- Promotions

Message rows:
- sender,
- subject,
- preview,
- timestamp,
- unread marker,
- attachment/star state.

## Reader workspace

Top action bar:
- archive,
- delete,
- move,
- label,
- snooze,
- more,
- optional `Summarize with Messenger AI`.

Email body occupies the main center.

A narrow contextual right panel may show:
- sender information,
- attachments,
- AI summary,
- quick actions.

Mail should still feel like a mail client first.

---

# 17. Calendar workspace

Reference: **R01**

## Calendar sidebar

Contains:

- New Event,
- compact month picker,
- My Calendars,
- Other Calendars.

Use colored category toggles:
- Personal
- Work
- Travel
- Family
- Holidays
- Flights

## Main schedule

Views:
- Day
- Week
- Month
- Agenda

Week view:
- clean columns,
- restrained event colors,
- all-day row,
- hourly grid.

Selecting an event opens a contextual detail pane.

Travel events can show:
- route,
- airline/flight,
- date/time,
- terminals,
- passengers,
- booking reference,
- booking link,
- update toggle,
- hotel/travel-plan shortcuts.

---

# 18. Files workspace

Reference: **R15**

Files is a clean hybrid of iOS Files and Google Drive.

## Files sidebar

Contains:

- Upload Files
- All Files
- Recents
- Shared with me
- Starred
- Trash

### Categories

Files are grouped by type:

- Images
- Videos
- Documents
- PDFs
- Audio
- Folders

### Storage sources

- iCloud Drive
- Google Drive
- Local Files

Show storage usage subtly.

## Main workspace

Top:
- natural-language search,
- type filter,
- sort/view controls.

Sections:
- Quick Access
- Recent Files
- Shared with Me

Quick Access uses large visual category cards for:
- Images
- Videos
- Documents
- PDFs

Recent files use compact cards.

Shared files may use a table/list for scanability.

---

# 19. AI Chat workspace

Reference: **R02**

AI Chat should look like a **normal modern chat website**, not an orchestration dashboard.

Avoid giant reasoning panels.

## Sidebar

Contains:
- New Chat,
- chat history,
- normal Messenger global navigation.

## Main conversation

User turn:
- simple chat bubble.

Assistant turn:
- normal markdown,
- headings where useful,
- concise bullets,
- images/files inline,
- source references where relevant.

### Thinking / agent status

Extremely minimal.

Acceptable:

```text
✓ Searched 8 sources · Reasoned for 12s  ▾
```

or:

```text
Searching...
```

Do not expose a multi-step internal workflow by default.

## Generated-image state

The selected reference shows:

```text
User:
Generate a beautiful photo of cherry blossoms in Kyoto...

Assistant:
[large generated image]
short response
```

Actions beneath assistant content:
- copy,
- like/dislike,
- more.

## Sources

A right-side sources panel is allowed when the answer uses web/research sources.

It can contain:
- source title,
- domain,
- thumbnail,
- open action,
- related queries.

The sources panel is secondary and should not reduce the main answer to a narrow column.

---

# 20. Profile / Account

Reference: **R11**

Profile opens as a centered frosted modal over the current screen.

The underlying screen remains visible but heavily softened/blurred.

## Profile modal navigation

- Profile
- Account
- Subscription
- Devices
- Storage
- Data & Privacy
- Connected Apps
- Notifications
- Appearance
- AI Preferences

## Profile page

Hero:
- avatar,
- online indicator,
- display name,
- short bio,
- Edit.

Details:
- Full name
- Email
- Phone
- Location
- Date of birth
- Language

Status:
- online / away / busy / invisible as supported.

About:
- short personal status/bio.

Other tabs handle account, devices, storage and subscription without leaving the modal.

---

# 21. Settings behavior

Settings can use the same modal shell as Profile.

Do not create a separate full-screen visual language.

Recommended categories:

- Account
- Appearance
- Notifications
- Privacy
- Connected Apps
- AI Preferences

Appearance:
- Light
- System
- Dark

AI Preferences may contain:
- web search,
- memory,
- response style,
- tool permissions.

Keep toggles and descriptions compact.

---

# 22. State and transition model

## Chat + notifications

```text
NORMAL CHAT
   |
   | click Messenger Updates
   v
HORIZONTAL UPDATE TRAY
   |
   | click result card
   v
ANCHORED RESULT DETAIL
   |
   | Open / View all
   v
FULL FEATURE WORKSPACE
```

Alternative:

```text
NORMAL CHAT
   |
   | pull/swipe down Messenger Updates
   v
VERTICAL ACTIVITY LIST
```

Closing any overlay returns to the previous state without losing chat scroll position.

---

# 23. Layering

Recommended z-index model:

```text
0   wallpaper/background
10  app shell
20  module content
30  sticky headers/composer
40  expanded vertical Messenger list
50  horizontal Messenger Updates tray
60  selected update detail
80  profile/settings modal backdrop
90  profile/settings modal
100 transient menus/tooltips
```

---

# 24. Interaction rules

## Hover

Use hover for:
- subtle card lift,
- action reveal,
- overflow controls,
- tooltips.

Do not trigger a large destructive layout change from accidental hover.

## Click

Click is the primary expansion action.

## Swipe / pull

Use for:
- the vertical Messenger Updates activity expansion,
- horizontal card tray on touch/trackpad,
- natural list scrolling.

## Escape

`Esc` closes:
1. context menu,
2. selected result detail,
3. horizontal update tray,
4. modal.

One level at a time.

---

# 25. Loading and progress

Background agent jobs appear in Messenger Updates.

States:

### Pending
```text
Research
Queued
```

### Running
```text
Generating video       ◌ 45%
Research                ◌ 2:23
```

### Complete
```text
Image ready             ✓
Flight found            ✓
```

### Failed
```text
Research failed         !
Retry
```

Use one compact spinner.  
Do not add verbose step-by-step reasoning to notification rows.

---

# 26. Empty states

## No Messenger updates

Do not reserve blank notification space.

The chat list begins immediately below search.

## No chats

Show:
- small illustration/icon,
- `No conversations yet`,
- primary action.

## No files

Show upload/drop zone.

## No bookings

Show New Booking CTA.

## No watchlist

Show Add stocks CTA.

---

# 27. Responsive priorities

These approved references are desktop-first.

For narrower widths:

1. Keep global rail.
2. Collapse module sidebar when necessary.
3. Preserve main workspace.
4. Result detail becomes a sheet/drawer.
5. Horizontal Messenger cards remain horizontally scrollable.
6. Do not scale desktop cards down until text becomes unreadable.

---

# 28. Accessibility

Minimum requirements:

- body text contrast ≥ WCAG AA,
- keyboard navigation for all navigation and overlays,
- visible focus ring,
- icon-only controls require accessible labels,
- minimum interactive target ~40 × 40 px,
- status is never communicated by color alone,
- loading animation respects reduced-motion preference.

---

# 29. Motion

Motion should feel native and restrained.

Suggested:

- hover: 100–140 ms,
- dropdown: 160–200 ms,
- Messenger tray expansion: 180–240 ms,
- modal: 180–220 ms,
- workspace navigation: subtle crossfade / slide ≤ 220 ms.

No bouncing, springy or exaggerated AI animations.

---

# 30. Component inventory

Suggested reusable components:

```text
AppShell
GlobalRail
ModuleSidebar
ModuleHeader
SearchField
GlassPanel
SectionHeader
ListRow
Avatar
UnreadBadge
StatusDot
PrimaryButton
SecondaryButton
IconButton
SegmentedControl
Toggle
MediaMessage
VoiceMessage
MessageBubble
MessageComposer

MessengerUpdateSummary
MessengerHorizontalTray
MessengerVerticalActivity
MessengerUpdateCard
MessengerResultOverlay
ProgressSpinner

FlightResultRow
ResearchResultRow
EmailDraftPreview
GeneratedImagePreview

StockRow
StockChart
WeatherHero
ForecastRow
MailRow
CalendarEvent
FileCard
FileCategoryCard

ProfileModal
SettingsModal
```

---

# 31. Final 15 approved visual references

The supplied four contact sheets contain the selected reference set.

## R01 — Calendar
`output_grid_1.jpg` — top-left

Defines:
- calendar module sidebar,
- week layout,
- event coloring,
- travel detail pane.

## R02 — AI Chat / image generation
`output_grid_1.jpg` — top-right

Defines:
- normal AI-chat proportions,
- generated image response,
- sources panel.

## R03 — Mail
`output_grid_1.jpg` — bottom-left

Defines:
- inbox/message split,
- email reader,
- sender/attachment/AI context rail.

## R04 — Chats / collapsed Messenger Updates
`output_grid_1.jpg` — bottom-right

Defines:
- baseline chat layout,
- collapsed purple Messenger Updates state,
- correct Dubai beach message proportions.

## R05 — Stocks & Markets
`output_grid_2.jpg` — top-left

Defines:
- watchlist/index,
- chart workspace,
- market detail hierarchy.

## R06 — Weather
`output_grid_2.jpg` — top-right

Defines:
- weather hero,
- hourly/weekly layout,
- map and air-quality cards.

## R07 — Email Draft Ready
`output_grid_2.jpg` — bottom-left

Defines:
- horizontal Messenger tray,
- selected email card,
- email draft detail overlay.

## R08 — Vertical Messenger activity
`output_grid_2.jpg` — bottom-right

Defines:
- pull-down vertical activity list,
- compact completed/running tasks,
- spinner/progress representation.

## R09 — Flight Found detail
`output_grid_3.jpg` — top-left

Defines:
- selected flight result in horizontal tray,
- compact multi-flight result table,
- anchored downward expansion.

## R10 — Flights workspace
`output_grid_3.jpg` — top-right

Defines:
- Flights module sidebar,
- destination suggestions,
- flight search form,
- recent searches.

## R11 — Profile / Account
`output_grid_3.jpg` — bottom-left

Defines:
- frosted modal,
- profile navigation,
- profile/account content.

## R12 — Image Ready detail
`output_grid_3.jpg` — bottom-right

Defines:
- selected generated-image card,
- media preview,
- Open / Share / Use in chat.

## R13 — Horizontal Messenger Updates tray
`output_grid_4.jpg` — top-left

Defines:
- purple update panel extending from chat-list column across the conversation,
- compact story-like cards.

## R14 — Research Ready detail
`output_grid_4.jpg` — top-right

Defines:
- research result index + selected result preview,
- compact insights,
- result actions.

## R15 — Files
`output_grid_4.jpg` — bottom-left

Defines:
- iOS/Google Drive-inspired file module,
- categories,
- quick access,
- cloud storage sources,
- recent/shared files.

---

# 32. Reference priority

When references appear to conflict, use this order:

1. **Interaction rules in this specification**
2. **The latest selected screenshot for that state**
3. **The shared global visual language across the 15 images**
4. Older experimental generations

In particular:

- Do not retain the older always-visible horizontal notification bar.
- Do not keep Chats visible when entering a dedicated feature workspace.
- Do not squash the chat beach image.
- Do not expose verbose AI thinking steps.
- Do not use the old oversized flight booking card design inside notification previews.

---

# 33. Content is illustrative

Names, dates, airlines, prices, stock values, weather values, emails and example text in the concept images are **demo content**, not product requirements.

Production UI must consume real data and handle:
- missing images,
- long names,
- RTL/Arabic,
- long subjects,
- localization,
- loading,
- errors,
- offline state.

---

# 34. Arabic / RTL requirement

Messenger should support full Arabic RTL.

When RTL is active:

- module sidebar remains structurally consistent but content direction flips,
- chat incoming/outgoing behavior follows product convention,
- chevrons reverse,
- labels and metadata align naturally,
- mixed Arabic/English text must remain stable,
- numbers, airport codes and ticker symbols should not be visually corrupted.

Use logical CSS properties (`margin-inline`, `padding-inline`, `inset-inline`) instead of hard-coded left/right where possible.

---

# 35. Implementation acceptance checklist

A build matches the approved redesign when:

- [ ] 1920×1080 looks spacious, not enlarged.
- [ ] Global navigation is narrow and persistent.
- [ ] Each selected module gets its own sidebar/index and workspace.
- [ ] Chat list disappears in non-chat workspaces.
- [ ] Chat images preserve proper aspect ratio.
- [ ] Messenger Updates is one collapsed purple row by default.
- [ ] Clicking Messenger Updates opens a horizontal overlay tray.
- [ ] Pulling down opens a compact vertical task list.
- [ ] Active jobs show spinner/progress/time.
- [ ] Selecting an update opens a downward anchored detail.
- [ ] Update overlays never resize the underlying chat.
- [ ] Image, Flight, Research and Email details use their approved unique layouts.
- [ ] AI Chat resembles a normal modern chat product.
- [ ] AI reasoning/status is extremely minimal.
- [ ] Mail remains mail-first.
- [ ] Files are grouped by Images / Videos / Documents / PDFs / Audio / Folders.
- [ ] Profile/Settings appear as frosted modals over the existing screen.
- [ ] All surfaces follow the same light glass design system.
- [ ] Arabic/RTL is supported.
- [ ] Keyboard and accessibility states are implemented.

---

# 36. Summary

The final Messenger redesign is a **light, native-feeling communication and agent workspace**.

The core identity is:

> **Normal chat when nothing needs attention; a compact purple Messenger Updates layer when agents are working; rich task results only when requested; and dedicated, fully designed workspaces when the user enters Flights, Stocks, Weather, Mail, Calendar, Files or AI Chat.**

The system should feel calm in its default state and powerful only when the user asks it to expand.
