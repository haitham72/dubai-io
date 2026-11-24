# Dubai-io — Locked Mobile UI Spec (20-11-2026, rewritten 24-11-2026)

**Status:** Locked design baseline. The four founder images below are the visual TARGET; this file measures them.
**Asset folder:** `design/20-11-2026/` · **Related:** `PLAN.md` §2, `design/CLAUDE.md`, root `CLAUDE.md` (UI rules), `docs/plan/Memory/memory.md` §17–§18
**Provenance of the images:** AI-generated, founder-supplied / approved. References, not evidence that anything is built.
**Companions:** `assets-needed.md` (every image slot and where it comes from) · `design/demo/quest_memory_management_mockup.html` (Antigravity's interactive mockup, the IMPLEMENTATION reference for image density, section 12).

> How to read the numbers. All sizes are **pt at a 390 x 844 phone** (safe-area top 59, bottom 34). Measured from the mockups (the phone screen is about 480-490 px wide in each JPG, so 1 px is about 0.8 pt) and rounded. Colors are **sampled by eye**; treat them as targets, then compare against the image (section 11). When a number here and the image disagree, the image wins and this file gets fixed.

---

## 0. Catalog

| File | Frames | Screens |
|---|---|---|
| `Dubai-io_ A Cinematic UI Showcase.jpg` (1500x1125) | 2 | **Today** (hero + peeking section) · **Today scrolled** (two image carousels) |
| `Dubai-io Chat App Mockup.jpg` (1500x1000) | 2 | **Chat** · **Chat drawer** (My Dubai-io + History) |
| `Dubai-io Quest Milestones Showcase.jpg` (1672x941) | 2 | **Quests** (hero quest, More Quests, Momentum) · **Quests scrolled** (More Quests, Fall 2026 Milestones, Quest Badges) |
| `Dubai-io Knowledge Graph Vault.jpg` (1500x1000) | 2 | **Memory / Subjects** · **Memory / People & Places** |

Note: the Quest Milestones JPG is an untracked file in the main worktree. It must be committed from `main` by the founder or orchestrator; this branch does not copy or move it.

The mic orb appears on **Today and Quests only** (4.3).

---

## 1. Global rules (every screen)

### 1.1 Canvas
- 390 x 844. Content is full-bleed; the page background runs behind the status bar and tab bar.
- Horizontal margin: **22 pt** for headers, titles, text; **16 pt** for full-width cards; tab bar side margin 12-19 (4.3).
- Scroll content bottom padding **110 pt**.
- Status bar: system. Do not draw a custom one.

### 1.2 Typography (two families only)
| Role | Family | Description |
|---|---|---|
| **Headline serif** | **Newsreader** (Google Fonts, already used by the Antigravity mockup) weight 600-700, optical size 72; or **Source Serif 4** 700. Fallbacks: Playfair Display 700, Georgia Bold. | A **bold, high-contrast serif**: thick stems, thin hairlines, tight tracking (-0.5 to -1%). Used for the app title, greeting, section titles, card titles on images, milestone row titles, badge labels, Vault title. |
| **Body sans** | System sans: SF Pro on iOS; **Inter** or Plus Jakarta Sans on web/Android. | 400 / 500 / 600. Captions, chat text, chips, tab labels, subtitles, list sub-lines. |

Never set a headline in a light or regular-weight serif. Minimum headline weight 600.

### 1.3 Type scale (pt / line-height)
| Token | Family, weight | Size / line | Where |
|---|---|---|---|
| `title-app` | serif 700 | 24 / 28 (Today), **28 / 32** (Chat, Quests, Memory) | "Dubai-io" wordmark |
| `subtitle-app` | sans 400 | 14 / 18, `#6B6B6B` | "Quest AI Companion" |
| `greeting` | serif 700 | **38 / 40** | "Good morning, Haitham" (2 lines) |
| `date-line` | sans 400 | 16 / 20 | "Dubai . Saturday, 14 Oct" |
| `hero-title` | serif 700 | **36 / 38**, white | "Your Weekly Recap" |
| `hero-body` | sans 400 | 16 / 22, white 92% | recap subtitle |
| `page-title` | serif 700 | **32 / 36** (Active Quests), **30 / 34** (Your Knowledge Vault) | screen titles |
| `page-sub` | sans 400 | 15 / 20, `#5A5A5A` | "Your personal roadmap in Dubai" |
| `section-title` | serif 700 | **24 / 28** (Today carousels), **22 / 26** (Quests) | "Gaming & Hardware", "More Quests", "Momentum", "Fall 2026 Milestones", "Quest Badges" |
| `section-title-sans` | sans 700 | 18 / 22 | Vault only: "Key Knowledge", "Key Relationships & Places" |
| `card-title-img` | serif 700 | **30 / 32** white (Today cards, Quests hero); 20 / 22 (More-Quests cards) | titles on images |
| `card-sub-img` | sans 400 | 14 / 18, white 92% | subtitle on image |
| `row-title-serif` | serif 700 | 14.5 / 18 | milestone row titles |
| `row-title` | sans 600 | 15 / 19 | Vault rows, drawer rows |
| `row-sub` | sans 400 | 12 / 15, `#6F6F6F` | milestone / Vault sub-lines |
| `body-chat` | sans 400 | 16 / 22 | chat |
| `caption` | sans 400 | 11 / 14 | timestamps, node counts |
| `chip` | sans 500 | 12 / 14 | status chips, quest chips, legend |
| `tab-label` | sans 500 | 11 / 13 | tab bar |
| `button` | sans 500-600 | 16 / 20 | "Watch Recap", "Continue Quest"; "Apology Accepted" 15 |

### 1.4 Color tokens (sampled by eye)
| Token | Hex | Use |
|---|---|---|
| `bg-warm` | `#FBF4EC` (to `#F9EFE6` at the bottom) | Today, Quests page background: warm peach-cream, never pure white, never yellow |
| `bg-white` | `#FDFDFC` | Chat, Memory page background |
| `surface` | `#FFFFFF` | rows, stat cards (`#FFFAF2` for badge tiles) |
| `text-1` | `#1D1D1F` | titles, body |
| `text-2` | `#6B6B6B` | subtitles, captions |
| `text-3` | `#9A9A9A` | timestamps, drawer day labels |
| `gold` | `#C5902F` | icons, checks, progress dots, active labels |
| `gold-deep` | `#A8681A` | proactive header text, "In progress" text, VIP text |
| `gold-btn` | gradient `#CFA04A` to `#B07D3A` | Apology Accepted, send button |
| `gold-fill` | `#F6E3C4` | active segmented tab; VIP pill gradient `#FAEBCB` to `#F1D9A6` |
| `beige-pill` | `#F3E7D6` | active tab pill; drawer "Today" row `#F7EBDD` |
| `chip-neutral` | `#F1EEE9` | ingested row, count badges; planned chip `#ECECEC` |
| `chip-done` | bg `#E8F1E6`, text `#3E6B3A` | Done |
| `chip-progress` | bg `#FBE9CC`, text `#A8681A` | In progress |
| `user-bubble` | `#3C3D42`, text `#FFFFFF` | user chat box (measured charcoal slate; the old `#1E2022` was too dark) |
| `ai-text` | `#1D1D1F` | assistant text |
| `proactive-tint` | gradient `#FBEFD9` to `#FDF8EE` (135 deg) | proactive repair card |
| `mic-orb` | gradient `#F6F4FD` to `#DDD8F3`, glyph `#7A74C9` | the glass orb |
| `scrim` | `rgba(60,60,65,0.45)` | right 24% behind the drawer |
| `hairline` | `rgba(120,90,50,0.10)` | the only border color (section 5) |

Cluster colors: 4.12.

### 1.5 Radii
Image cards 20 · hero quest card 24 · list rows / stat cards / badge tiles 14-16 · chat bubbles 20 (tail corner 6) · chips and buttons full pill · tab bar capsule 30 · inputs full pill.

---

## 2. Screen: TODAY (`Cinematic UI Showcase.jpg`, left frame)

| y (pt) | Element | Spec |
|---|---|---|
| 0-59 | Status bar | system |
| 59-103 | **Header row** (44) | left: "Dubai-io" `title-app` 24/28 at x=22; right: **Quest VIP pill** (4.9), right margin 22 |
| 112-196 | **Greeting** | "Good morning," / "Haitham" `greeting` 38/40, x=22. Under it "Dubai . Saturday, 14 Oct" `date-line`, 6 gap |
| 112-700 | **Hero image** | **full-bleed, 390 x about 590**, starts at y=112 behind the greeting. Top 90 and bottom 110 pt fade into the page background. See 4.1 |
| 560-700 | Hero text (on image) | "Your Weekly Recap" `hero-title` 36/38 white, x=28; body `hero-body` 16/22, max 2 lines, width 330; **Watch Recap** button 44 x 150, 16 below body |
| 722 | Carousel dots | 3 dots centered at x=195. Active 8 pt white, inactive 6 pt white 55%, gap 7 |
| 760-790 | Section title | "Gaming & Hardware" `section-title` 24/28, x=22 |
| 800-844 | Peeking card row | first card top at y=800; only its top 44 pt shows above the tab bar (scroll affordance) |
| 752-812 | Tab bar | 4.3, floating, bottom edge 34 above screen bottom |

---

## 3. Screen: TODAY scrolled (right frame)

| y | Element | Spec |
|---|---|---|
| 59-103 | Header row | as Today |
| 118-148 | Section title "Gaming & Hardware" | 24/28, x=22 |
| 160-417 | **Image card row** | card 1: **290 x 257**, x=24, radius 20 (4.2). Card 2 at x=326 (**gap 12**), **64 pt visible**, cropped by the screen edge |
| 417-476 | Section title "Developer & AI Systems" | 24/28 |
| 486-696 | Second row | card 1 **290 x 210**, same x, gap, peek |
| 752-812 | Tab bar | |

**Card ratio is measured, flag.** Cards are **landscape-ish (about 8:7 and 4:3)**, not 3:4 portrait. The earlier INDEX said 3:4; that was wrong. Use **290 x 257** (feature) and **290 x 210** (compact). Width is 74% of the screen; the next card peeks 64-72 pt (about 17%). Horizontal scroll snaps to card start, left inset 24. (Antigravity's HTML used 3:4 media inside a white bordered card; do not copy that, see 12.)

---

## 4. Components

### 4.1 Hero image card (Today)
- Full-bleed image, `object-fit: cover`, 390 x 590, no border, no radius. Top fade 90, bottom fade 110 into `bg-warm`.
- **Overlay gradient:** transparent at 45% of height to `rgba(60,25,10,0.55)` at 88% (warm dark brown, not black).
- Headline `hero-title` 36/38 white, 2 lines, no text shadow. Body white 92%.
- **Watch Recap:** height 44, padding-x 20, radius 22, fill `#F7EBDD`, text `text-1` 16/20 medium, leading **filled black play triangle 18 pt** + 10 gap, no border.
- **Dots:** 3, 22 pt below the button.
- Source chip: see 12.2 (generated recap art needs none; a live image needs one).

### 4.2 Image card (Today carousels)
- 290 x 257 or 290 x 210, radius 20, `overflow: hidden`, full-bleed image.
- Gradient: transparent at 40% to `rgba(20,10,35,0.70)` at 100%.
- **Title on image:** bottom-left, x inset 24, bottom inset 38; `card-title-img` 30/32 white. **Subtitle:** 12 below, `card-sub-img` 14/18.
- **Price chip** (when there is a price): top-right inset 14, height 30, padding-x 14, radius 15, gradient `#F6D58E` to `#E8B95C`, text `#2A1D08` 17/20 semibold, "AED 299". Carries `provenance` + `as_of`.
- **Source chip** (live results): bottom-right inset 10, height 20, padding-x 8, radius 10, fill `rgba(28,26,23,0.78)` with 4 pt blur, white 10 pt bold, text = provider ("Dubizzle", "Rockstar Newswire"). **Demo data pill** (fixtures): top-left inset 10, same shape, fill `rgba(255,255,255,0.92)`, text `text-1`.
- Peek card: same component; its title is cropped by the screen edge, never shifted.

### 4.3 Tab bar
**Floating capsule**, not edge-to-edge.
- **4 tabs, icon + label**, equal width: Today (calendar-window), Chat (speech bubble), Quests (layers), Memory (brain). Icons 24 pt, stroke 1.6, `text-1` 80% inactive / `gold` active (Chat icon filled). Label `tab-label` under the icon, gap 3.
- **Capsule:** height **60**, radius 30, fill `rgba(255,255,255,0.85)` + 20 pt backdrop blur, 1 px `hairline`. Bottom edge **34 above the screen bottom**. Side margin **12** on Today/Quests (includes the orb), **19** on Chat/Memory (width 352).
- **Active tab:** **beige pill** `#F3E7D6`, radius 26, height 52, width = tab width (about 70 with orb, 84 without), behind icon + label. Active label `text-1` on Today/Quests, `gold` on Memory.
- **Mic orb (Today, Quests only):** a **separate 54 pt circle** at the right end of the capsule (4 inset); the 4 tabs share the remaining width, so the orb never overlaps a tab. Fill `mic-orb`, 1 px `#D9D4F0`, glyph a **vertical 5-bar waveform** 26 pt `#7A74C9`. Translucent lavender glass. NOT gold.
- **Chat and Memory: no orb**; tabs spread over the full capsule.
- Home indicator (134 x 5) below the capsule.

### 4.4 Chat bubbles
- **User:** right margin 24, **max width 240**, fill `#3C3D42`, text white 16/22, padding 14/16, radius 20 (bottom-right 6). Timestamp 11, white 65%, bottom-right inside.
- **Assistant (mock):** left margin 24, max width 280, fill `#F1F1F2`, `ai-text`. **Conflicts with root rule** ("plain AI text, tinted user box"). **Default to the rule (no fill, plain text) until the founder decides** (section 9, C2).
- Gaps: between messages 12; message to card 14.

### 4.5 Proactive repair card
- Left 25, **width 340**, padding 18, radius 20, fill `proactive-tint`, **no border, no top stripe**.
- Header: sparkle/wand 16 pt `gold-deep` + "Proactive Ping . Memory Repair" 15/18 semibold `gold-deep`.
- Body 17/22 `text-1`, 12 under the header.
- **Button** "Apology Accepted" + thumbs-up: centered, 38 x 190, radius 19, `gold-btn`, white 15 medium. After the tap: "Resolved" state only once the engine confirms the `end` / `update` op (rule 1).
- Label **Demo trigger** when not user-caused (rule 8).

### 4.6 "Ingested into Temporal Memory" row
- Left 25, 310 x 38, radius 16, fill `chip-neutral`. Check 18 pt `gold` at x=12. Text at x=44: "Ingested into Temporal Memory" 13/16 medium; "trust: T1 . topic: gaming/preferences" 11.5/14 `text-2`. Only after `POST /api/memory/chat/turn` succeeds.

### 4.7 News / context card (chat)
- Left 25, width 340, white, radius 16, 1 px `hairline`. Top image strip **340 x 68** (cover; title on the image, serif 700 28/30 white). Below: title `row-title` 15, sub 12 `text-2` "Shared News DB . 2h ago", chevron 18 `text-3`. Total height 112. Strip image is a live result (12) with a source chip.

### 4.8 Chat input dock
- Field: left 22, right 70, height 40, full pill, white, 1 px `#E4E1DC`; placeholder "Message Dubai-io..." 15 `text-3`; mic 20 pt `text-2` inside right (inset 14).
- **Send:** 40 pt circle, `gold-btn`, white arrow 20, right margin 22, gap 8. Dock 12 above the tab bar.

### 4.9 Quest VIP pill
- Height 26, padding-x 12, radius 13, gradient `#FAEBCB` to `#F1D9A6`, 1 px `#E8D0A0`, **crown** 14 pt `gold-deep`, "Quest VIP" 13/16 medium `gold-deep`. Width about 98.

### 4.10 Quests components
- **Hero quest card:** x=16, **358 x 293**, radius 24, full-bleed image, left-weighted gradient (`rgba(40,20,70,0.55)` left to transparent right). Inset 20:
  - Title 30/32 serif white, 3 lines.
  - **Phase chip** 12 below: height 28, padding-x 12, radius 14, `rgba(255,250,242,0.92)`, `text-1` 13 medium.
  - Description white 14/18, 2 lines.
  - **Continue Quest:** 40 x 150, radius 20, `#F7EBDD`, black play 16 + 16 medium.
  - **Status chips row** (bottom inset 16): 3 chips, height 28, radius 14, `rgba(255,255,255,0.20)` + blur, 1 px `rgba(255,255,255,0.35)`, white 11.5, leading check or hollow ring 14 pt, gap 6.
- **More Quests row:** title 22/26, x=22. Cards **274 x 112**, radius 20, first x=16, **gap 9**, next peeks **about 85 pt**. Title on image 20/22 serif white, 2 lines, inset 18; sub 12 white 92%.
- **Momentum:** two stat cards **168 x 52**, gap 8, radius 14, `surface`, no border (section 5). Icon 24 `gold` at x=14; value 15 semibold ("300 applications"), sub 11.5 `text-2`.
- **Milestone timeline:**
  - **Connector line** x=22, 1.5 wide, `#E0C9A0`, through the nodes.
  - **Nodes 20 pt:** Done = filled `#C98A2E` + white check; In progress = 2 pt gold ring with 8 pt filled center (active) or fully hollow (queued); Planned = filled `#C9C9CC`.
  - **Rows:** x=44, width 330, stacked, height 48, white, hairline separators; first row radius 14 top, last 14 bottom. Title `row-title-serif`; sub `row-sub` 11.5.
  - **Status chip** right inset 12: height 26, padding-x 10, radius 13, `chip` 12 medium. Done = `chip-done` + check 12; In progress = `chip-progress`; Planned = `#ECECEC` / `#555`.
- **Badge tiles:** three **115 x 78**, gap 9, radius 16, `#FFFAF2`, no border. **Line icon 34 `gold`** (laurel, cubes, brain); label `row-title-serif` 13 centered, 2 lines max.

### 4.11 Drawer (Chat, right frame)
- **Panel:** x=0, **width 295 (76%)**, white, full height; remaining 95 pt shows the chat behind `scrim`.
- Header: "Dubai-io" 28/32 + subtitle; **close X** 36 pt white circle, 1 px `hairline`, X 16.
- "My Dubai-io" label 15/18 `text-2`, x=22, y about 195.
- **Category rows:** 6 rows, **height 38** (hit area 44), margin 0 12, radius 12. Icon 22 line at x=14; label `row-title` 15; right count 12 `text-2` in a 24 pt `chip-neutral` circle. **Active row ("Today") filled `#F7EBDD`** with gold 4-point sparkle.
- Divider 1 px `#EDE9E3`, 16 vertical margin.
- "History" label 15/18 `text-2`; **rows** height 40, bubble-outline 20 `text-2`, title 14.5, right day label 13 `text-3`, 1 px hairline separators, newest first.
- Counts are real, from the memory engine. Drawer categories follow the engine's clusters after founder confirmation (C8).

### 4.12 Memory / Knowledge Vault
- **Header row:** wordmark + subtitle; **search** and **overflow** 36 pt white circles, 1 px `hairline`, icons 18, gap 10, right margin 22.
- **Page title** y=122: `page-title` 30/34; subtitle `page-sub` 14/18 ("What I've learned, organized, and verified about you." / "The people in your life and the places that matter.").
- **Segmented control** y=180, x=22, **346 x 36**: track `#F6F4F1` + 1 px `#E6E2DC`, radius 18; **active segment** `gold-fill` pill inset 2, 15 semibold; inactive 15 regular.
- **Graph canvas** y=228-448 (**height 220**), full width. **Expand button** top-right inset 14: 34 pt white circle, 1 px hairline.
  - **Center "Haitham":** 26 pt **gold sphere** (radial `#F0D08A` to `#A9732A`) + white label pill beneath (radius 14, height 28, 14 semibold).
  - **Hubs:** 14 pt colored sphere (same radial treatment) + white label pill; each hub has **12-22 leaf dots** (4-7 pt, cluster color 85%) on 0.6 pt cluster-colored edges (40%). Hub-to-center edges 0.8 pt `#C9C9CE`.
  - Labels 13 semibold on white pills (radius 14, height 26, padding-x 12). People & Places labels add a second line `(Family)` 10 `text-2` and a leading 14 pt icon (person blue, pin purple, plane for Travel).
  - **Mock colors:** Career `#2F80ED`, Projects `#8E5BD9`, Learning `#F2A33A`, Gaming `#EC5B9A`, Travel `#1CC5C0`, Health `#4CAF50`.
  - **Engine clusters (founder D-a, 24 Nov): 7, no Health, no Gaming.** Career `#2F80ED`, Learning `#F2A33A`, Projects `#8E5BD9`, **People & family `#EC5B9A`** (only stated or confirmed facts), **Events `#4CAF50`**, **Home & money `#6B7A90`**, Travel `#1CC5C0`. The last three assignments are proposals for the founder.
- **Counts row** (y=460, 12 pt): 8 pt dot + "Career (142)" `chip` `text-2`, 3 columns (4 + 3 items for 7 clusters); right: total "458" 17 semibold over "nodes" 11, separated by a vertical hairline. Real counts only.
- **Section header** y=508: "Key Knowledge" `section-title-sans`, right "View All >" 13 `text-2`.
- **Key rows:** x=16, **358 x 52**, gap 4, radius 14, white, **1 px `hairline`, no shadow**. Icon 26 line at x=16 in its cluster color; title `row-title`; sub `row-sub` (dot-separated); right **verified check = 22 pt circle `#D9A441` + white check**, then chevron 16 `text-3`. The check shows ONLY for confirmed (`user_supplied` / user-confirmed) facts.
- **People & Places:** same layout; legend "People (28)" blue / "Places (19)" purple / "Relations (132)" gray `#C9C9CE`, total "179 nodes". Key rows: person icon, pin, layers. T1 only after the user confirms (D-c).
- **Rule 9:** family relations ("Mamty / Your mother", "Khalid (Family)") may render only when the user stated or confirmed them; otherwise a neutral person node.

---

## 5. Depth without shadows

Root rule: **no shadows**. What the mocks show:
- Phones carry a device shadow (not UI; ignore).
- **UI in the mocks DOES carry soft elevation:** image cards (diffuse drop about 0/10/24 at 12% black), floating tab bar (about 0/6/20 at 10%), orb (soft lavender glow), Vault rows, milestone rows, stat cards, badge tiles (about 0/2/8 at 6%). Antigravity's HTML does the same (`box-shadow: 0 8px 24px rgba(0,0,0,.06)`, capsule `0 16px 36px -8px`).
- This **conflicts with the no-shadows rule.** Build the **tonal / 1 px alternative** and flag it for the founder:

| Element | Mock | Build (no shadow) |
|---|---|---|
| Image cards, hero | soft drop | none; the image separates from `bg-warm`; no border |
| Tab bar | soft shadow | `rgba(255,255,255,0.85)` + 20 pt blur + 1 px `hairline` |
| Mic orb | lavender glow | gradient + 1 px `#D9D4F0`; no glow |
| Stat cards, badge tiles (on `bg-warm`) | soft | `#FFFFFF` on `#FBF4EC` (tonal step), no border |
| Vault rows, news card | soft | white on near-white: 1 px `hairline` |
| Proactive card | soft | tint only, no border |
| Milestone rows | soft | white rows, hairline separators, no outer border |
| Chat input | faint | 1 px `#E4E1DC` |

`hairline` is allowed ONLY on: tab bar, circle icon buttons, Vault key rows, news card, chat input, segmented track, VIP pill, and separators inside lists. Everything else is a **tonal fill**, not a border.

---

## 6. Per-screen checklists

- **Today:** header + VIP; 2-line greeting + date; hero **image** with fade, headline on image, Watch Recap pill, 3 dots; "Gaming & Hardware" title; peeking **image cards**; floating tab bar with **icons + labels** and glass orb right.
- **Today scrolled:** two titled carousels of **image cards** with peek; price chip; source chip; title and subtitle ON the image.
- **Chat:** wordmark + subtitle + overflow circle; user dark bubble; AI message; proactive card; ingested row; news card with image strip; input pill with mic + gold send; 4-tab capsule, no orb.
- **Chat drawer:** 76% white panel, scrim, X, "My Dubai-io" 6 rows with counts, "History" 5 rows.
- **Quests:** header + VIP; "Active Quests"; hero **image** card with phase chip, Continue Quest, 3 status chips; "More Quests" image row with peek; "Momentum" 2 stat cards; capsule with orb, Quests active.
- **Quests scrolled:** More Quests; "Fall 2026 Milestones" 5 rows (Done / In progress / Planned); "Quest Badges" 3 tiles.
- **Memory / Subjects:** search + overflow; title; segmented control; graph; counts row; "Key Knowledge" rows; Memory active in gold.
- **Memory / People & Places:** same shell, social graph, "Key Relationships & Places".

---

## 7. NEVER list

1. **No colored top border stripe** on any card.
2. **No text-only card where the mock shows an image** (Today hero and carousels, Quests hero, More Quests, news strip). No image yet = a labelled fallback image (section 12), never an empty text box.
3. **No text-only tab bar.** Icons + labels, beige pill on the active tab.
4. **No gold orb (or any circle) covering or replacing a tab.** The only orb is the lavender glass mic at the right end, on Today and Quests only.
5. **No bordered box as the default container.** Default = tonal fill; hairline only where section 5 lists it.
6. **No thin / light / regular serif for headlines.** Bold high-contrast serif 600-700.
7. **No shadows** (root rule); use section 5.
8. **No generic cream "Claude-style" UI of flat bordered cards.** No image and no serif headline = wrong.
9. **No third-party art baked into static assets, the repo, the deck or icons** (GTA, PS5, publishers, DubaiNow, emblems). Third-party imagery appears only as a live, source-labelled result (12).
10. **No invented numbers:** counts, AED prices, node totals carry provenance + `as_of`; fixtures show **Demo data**.
11. **No hard-coded Health or Gaming cluster** in the Vault; the engine's 7 clusters.
12. **Do not modify `apps/web`.**

---

## 8. Web (1440 x 900)

The mocks define only the **phone**. At 1440 x 900 render the same screen in a centered **phone column, max width 430**, on the page background; column height 100vh; tab bar floats inside the column. Hero cropped, not stretched. Desktop layouts (rail, 3 columns) need a new founder image; the 17-Nov desktop board is a different design.

---

## 9. Conflicts between the mocks and founder rules (founder decides)

| # | Mock shows | Rule | Default here |
|---|---|---|---|
| C1 | Soft drop shadows on cards, tab bar, rows | no shadows | tonal / 1 px (section 5) |
| C2 | AI reply in a gray bubble | "plain AI text, tinted user box" | plain AI text |
| C3 | "Mamty - Your mother", "Khalid (Family)" as plain facts | Rule 9 | only when stated / confirmed |
| C4 | `T1` on Mamty | D-c: T1 only on user confirm | after confirm |
| C5 | Health and Gaming clusters, 458 / 179 totals | memory.md §17: 7 clusters, no Health; real counts | engine's 7; real counts |
| C6 | 3:4 cards per old INDEX | measured landscape 8:7 / 4:3 | measured sizes |
| C7 | AED 299, GTA VI, PS5, "300 applications" | rule 2 + Demo data; no baked third-party art; interest feeds imply inference (rule 9) | live interest-matched results with source chip + provenance; Demo data on fixtures |
| C8 | Drawer: Gaming & Hardware, Career & Projects, People & Family, Travel & Places, Home & Money | engine's 7 clusters | engine names; founder confirms labels |
| C9 | "Apology Accepted" as instant success | rule 1 | resolved only after the engine responds |
| C10 | Antigravity HTML hot-links Rockstar / Steam / Riot art as static `<img>` | NEVER 9 | acceptable only as live, source-labelled API results |

---

## 10. Backend alignment

1. Chat turns: `POST /api/memory/chat/turn`; the ingested row shows only on success.
2. Pings: `GET /api/memory/chat/pings`; "Apology Accepted" resolves via `/facts/{id}/resolve` (memory.md §18).
3. Vault graph: `/vault/graph?view=subjects|people` (7 clusters, Rule 9 gated, `+N more`, T1 + suggestions); verified check = confirmed trust / user-supplied.
4. Today / Quest card content: from the app's own API (12.1).

---

## 11. Definition of done for any UI task

Not done until the PR description contains:
1. **Side-by-side screenshots** of the build at **390 x 844** and **1440 x 900**, each next to the matching founder image (or frame crop), same scroll position.
2. A **list of every remaining difference** with measured numbers (pt, hex) from this file vs the build. "Looks close" is not acceptable.
3. The **section 6 checklist** for that screen, ticked.
4. The **section 7 NEVER list** reviewed, "no violations" or exceptions.
5. **Images:** no card without its image; every live image has a source chip; every fixture or fallback image is labelled (12).
6. **Founder approval** of the screenshots before merge. An agent's own "matches" is not approval.
7. `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web` passes.

---

## 12. Imagery: where images come from, and what Antigravity's mockup got right

Visual TARGET = the four images in this folder (serif headlines, layout, tab bar). `design/demo/quest_memory_management_mockup.html` is the IMPLEMENTATION reference for **image-led density**.

### 12.1 Image sourcing (founder, 24 Nov)
Each Today / Quest card shows a **live, interest-matched result image from the app's own API**, with a **source chip + provenance + `as_of`**. Pipeline: Google OAuth (client in `apps/api/app/oauth.py`, keys server-side only) pulls the user's YouTube likes / subscriptions / watch history and Gmail via `scripts/sync_google.py`, then interests via `scripts/extract_all_interests.py`, then `scripts/run_two_tower_recommender.py` picks live deals, news and videos with their real images. Provider calls (Google Shopping / Places / news) go through the app's own API proxy in `apps/api` (for example `apps/api/app/google_maps.py`); the client never calls providers or holds keys.
- A **generated or licensed fallback image** (stored locally) is used only when no live result exists.
- **Fixture data** shows the **Demo data** pill.
- Large visuals with no provider (Today hero recap, Quests hero) use generated or licensed art stored locally.
- Third-party art may appear **only** as a live, source-labelled result; never baked into static assets, the deck or icons. Interest-matching is inference: it re-ranks only, with a "Because..." chip (rule 9).
- Slot list: `assets-needed.md`.

### 12.2 Source chip spec
Height 20, padding-x 8, radius 10, fill `rgba(28,26,23,0.78)` + 4 pt blur, white 10 pt bold, text = provider name ("Dubizzle", "Rockstar Newswire"), bottom-right inset 10. Tap opens the source. Also show `as_of` (relative, "2h ago") in the card detail and provenance in the evidence sheet.

### 12.3 What Antigravity's mockup got right (port these)
1. **Image fill:** every card is an `<img>` with `object-fit: cover` filling its box (`width:100%; height:100%`), a neutral `#F7F8FA` placeholder behind it, and an `onerror` fallback image so a card is never empty. Port: the fallback chain (live result, then local fallback), not the hot-linking.
2. **Gradient overlay:** `linear-gradient(to top, rgba(28,26,23,0.55), transparent)` over the image bottom for legibility; use the longer 40-100% ramp in 4.2.
3. **Corner badge on media:** `rgba(28,26,23,0.85)` + `blur(4px)`, white 9 px / 700, radius 6, bottom-right at 5 px: the source chip (12.2).
4. **Floating publisher label** on hero media: white 94% + blur 6, radius 20, 11 px / 700, top-left at 10 px: a good pattern for the Demo data pill.
5. **Filter chips:** 6 / 13 padding, radius 20, 12 px / 600; inactive white + hairline, **active = dark `#1C1A17` fill with white text**; horizontally scrolling, scrollbar hidden. Use above the Today feed.
6. **Floating capsule nav:** height 56, radius 28, white 94% + `blur(20px)`, 1 px hairline; matches 4.3 (minus its shadow).
7. **Density:** many small image thumbs (rows with 13 px-radius thumbnails, quest thumbs with 18 px radius over a radial-gradient fallback), horizontal `scroll-snap` carousels, 12-14 px gaps. Cards are filled with imagery, not text boxes.
8. **Palette:** gold `#B88E3E`, soft gold `#F4EBD9`, cream `#FAF7F0`, text `#1C1A17` / `#635E55` / `#968F84`; the pastel pill pairs (green, blue, pink, purple, orange, teal) are good for cluster / status chips.
9. **Serif + sans pairing:** Newsreader (serif, 400-700) for section titles, Plus Jakarta Sans for UI.
10. **Gold proactive card:** `linear-gradient(135deg, #FFFDF9, #FFF9EE)`, radius 18; take the gradient, drop the 1.5 px gold border (section 5).

Do NOT port from it: the box-shadows, the white bordered card wrapper around media (the 20-Nov images use full-bleed image cards), the 3:4 media in a small card, the hot-linked third-party URLs (Rockstar, Steam, Riot, Unsplash) as static content.
