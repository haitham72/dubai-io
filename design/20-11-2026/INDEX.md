# Dubai-io (Quest Companion) — Visual Design Catalog & UI Architecture (20-11-2026)

**Date Created:** 20 November 2026  
**Status:** Locked Design Baseline for Mobile Interface & Sovereign Knowledge Vault  
**Asset Folder:** `design/20-11-2026/`  
**Related Docs:** `PLAN.md` §2, `design/CLAUDE.md`, `ARCHITECTURE.md`, `docs/plan/Memory/memory.md`  

---

## 1. Executive Summary & Design Rationale

The `design/20-11-2026/` asset suite establishes the **production visual standard** for Dubai-io ("Quest AI Companion"). It transitions the interface from early flat cards into a **warm luxury, white-canvas experience (`#FFFFFF` / `#FAF8F5`)** built around:
1. **The 4-Pillar Capsule Dock:** `Today` · `Chat` · `Quests` · `Memory` (with a center floating audio waveform orb).
2. **3:4 Vertical Aspect Ratio Cards:** Designed for mobile ergonomics with peeking cards (~18% edge visible) to naturally signal horizontal swiping.
3. **Proactive Empathy & Memory Repair:** In-chat gold proactive notification cards allowing one-tap acknowledgment ("Apology Accepted 👍") and live temporal memory ingestion badges.
4. **The Sovereign Knowledge Vault:** An interactive, dual-view force graph (`Subjects` vs `People & Places`) visualizing verified facts, life themes, and trust boundaries (T1 Inner Circle).

---

## 2. Asset Catalog & Screen-by-Screen Breakdown

| Asset File | Display Dimensions | Screens Shown | Core Theme |
|---|---|---|---|
| `Dubai-io_ A Cinematic UI Showcase.jpg` | 1500 × 1125 px | 2 Mobile Frames (Hero & Carousel) | Today / Daily Feed & 3:4 Swiping Carousels |
| `Dubai-io Chat App Mockup.jpg` | 1500 × 1000 px | 2 Mobile Frames (Chat & Drawer) | AI Companion Chat, Proactive Memory Repair & Life Drawer |
| `Dubai-io Knowledge Graph Vault.jpg` | 1500 × 1000 px | 2 Mobile Frames (Subjects & Social) | Sovereign Memory Graph & Verified Fact Vault |

---

### Asset 1: `Dubai-io_ A Cinematic UI Showcase.jpg`

#### Screen 1A: Hero Home / Today Brief (Left Frame)
- **Status Bar & Header:** Clean iPhone dynamic island, `Dubai-io` serif branding, right-aligned `👑 Quest VIP` badge in subtle metallic gold.
- **Personalized Header:**
  - Greeting: *"Good morning, Haitham"* (Playfair / Cormorant serif typography).
  - Geolocation & Date: *"Dubai · Saturday, 14 Oct"*.
- **Hero Weekly Recap Card:**
  - Visual: High-definition cinematic view of the Dubai skyline at sunset with the Burj Khalifa reflecting in the canal.
  - Title: *"Your Weekly Recap"*.
  - Subtitle: *"The top updates, new releases, and what's next in your Dubai-io world."*
  - CTA Button: Translucent pill with *"▶ Watch Recap"*.
  - Carousel Pager: 3 pagination dots indicating multiple daily briefings.
- **Section Peek:** Bottom of the viewport hints at *"Gaming & Hardware"* with a peeking GTA VI card.
- **Navigation Dock:** Bottom floating capsule containing `Today` (active), `Chat`, `Quests`, `Memory`, and a central audio waveform trigger button.

#### Screen 1B: 3:4 Vertical Cards & Horizontal Carousels (Right Frame)
- **Header:** `Dubai-io` + `👑 Quest VIP` badge.
- **Carousel Section 1: "Gaming & Hardware"**
  - Section Header: *"Gaming & Hardware"* with horizontal carousel navigation controls (`<` and `>`).
  - Card 1 (Active, 3:4 Aspect Ratio):
    - Visual: Neon sunset palm trees with custom sports car and GTA VI protagonist overlooking the Vice City / Dubai skyline.
    - Badging: Floating gold price tag `AED 299`.
    - Content: *"GTA VI — An all-new open world experience."*
  - Card 2 (Peeking Right):
    - Visual: PS5 Bundle with DualSense controller and headset on minimalist marble pedestal.
- **Carousel Section 2: "Developer & AI Systems"**
  - Section Header: *"Developer & AI Systems"* with carousel navigation controls.
  - Card 1 (Active, 3:4 Aspect Ratio):
    - Visual: Dark-mode IDE code editor on MacBook with glowing holographic AI assistant orb and `</>` coffee mug.
    - Content: *"ide-companio — Your AI coding companion."*
  - Card 2 (Peeking Right):
    - Visual: Metallic robotic android bust representing the *"Hermes Agent"*.
- **Ergonomic Design:** Each card occupies ~78% of viewport width, allowing ~18% of the subsequent card to peek from the right margin, providing a subconscious affordance that the list is horizontally scrollable.

---

### Asset 2: `Dubai-io Chat App Mockup.jpg`

#### Screen 2A: Active Companion Chat Stream (Left Frame)
- **Header:** `Dubai-io Quest AI Companion` with right-hand action overflow `···`.
- **User Message Bubble (Dark Charcoal `#1E2022`):**
  - Text: *"Can you improve the formatting in the last report? The sections felt a bit dense."* (Timestamp: `10:24 AM`).
- **Assistant Response Bubble (Soft Off-White `#F4F5F7`):**
  - Text: *"Got it. I've logged your feedback and updated my report style to be more structured and scannable."* (Timestamp: `10:25 AM`).
- **Proactive Empathy & Memory Repair Card (Warm Amber / Gold `#FDF8EE` with `#D4AF37` accent):**
  - Header: `⚡ Proactive Ping · Memory Repair`
  - Body: *"I'm sorry I missed your gaming interests earlier. I've updated your permanent memory profile to include gaming (GTA, hardware, and releases)."*
  - Action Button: Prominent gold pill button *"Apology Accepted 👍"*.
- **Temporal Memory Ingestion Badge:**
  - Pill badge with green checkmark: `✓ Ingested into Temporal Memory | trust: T1 · topic: gaming/preferences`.
  - Transparent proof of the bi-temporal memory write pipeline (`mem_events` + `mem_patterns`).
- **Shared News DB Context Card:**
  - Header: GTA VI artwork thumbnail.
  - Text: *"GTA 6 PC timeline update"* (Subtitle: `Shared News DB · 2h ago`).
  - Chevron trigger `>` for deep-dive context.
- **Bottom Input Dock:**
  - Text field: *"Message Dubai-io..."*
  - Dedicated Microphone / Voice Waveform icon + Gold circular Send arrow.
  - Navigation Dock with `Chat` active.

#### Screen 2B: Life Category Drawer & Conversation History (Right Frame)
- **Drawer Header:** `Dubai-io Quest AI Companion` with dismiss `✕` icon.
- **Section: "My Dubai-io" (Life Theme Ontologies):**
  - ✨ `Today`: 6 active items
  - 💼 `Career & Projects`: 12 verified items
  - 👥 `People & Family`: 8 verified contacts
  - 🎮 `Gaming & Hardware`: 4 active tracks
  - ✈️ `Travel & Places`: 3 itineraries
  - 🏠 `Home & Money`: 5 financial anchors
- **Section: "History" (Thread Log):**
  - `Report formatting feedback` — Today
  - `GTA 6 PC timeline` — Today
  - `Istanbul trip planning` — Mon
  - `Job application update` — Sun
  - `Gaming setup recommendation` — Fri

---

### Asset 3: `Dubai-io Knowledge Graph Vault.jpg`

#### Screen 3A: Subjects Force Graph & Topic Constellation (Left Frame)
- **Header:** `Dubai-io Quest AI Companion`, Search icon `🔍`, overflow `···`.
- **Page Title:** *"Your Knowledge Vault"*
- **Subtitle:** *"What I've learned, organized, and verified about you."*
- **Segmented Control:** `[Subjects]` (Active) | `[People & Places]`
- **Interactive Force Graph:**
  - Central Core Node: `Haitham` (Warm Gold node)
  - Clustered Thematic Galaxies:
    - 🔵 `Career` — 142 nodes (AI Engineering, UAE roles, interview prep)
    - 🟣 `Projects` — 98 nodes (Dubai-io, Mirsal, RAG, agent systems)
    - 🟡 `Learning` — 76 nodes (LLM, MLOps, AWS, Arabic NLP)
    - 🔴 `Gaming` — 64 nodes (GTA VI, PS5, Steam hardware)
    - 🟢 `Travel` — 41 nodes (Istanbul, Cairo, DXB flights)
    - 🟢 `Health` — 37 nodes (Sleep, gym, wellness)
  - Total Node Counter: **458 nodes** with zoom/expand toggle `⤢`.
- **"Key Knowledge" List (Verified Facts):**
  - 💼 `Career`: AI Engineering · UAE roles · Interview prep `[✓]` `>`
  - 📦 `Projects`: Dubai-io · Mirsal · RAG · Agent systems `[✓]` `>`
  - 📖 `Learning`: LLM · MLOps · AWS · Arabic NLP `[✓]` `>`
- **Navigation Dock:** `Memory` pillar highlighted in gold.

#### Screen 3B: Social & Geographic Constellation Graph (Right Frame)
- **Page Title:** *"Your Knowledge Vault"*
- **Subtitle:** *"The people in your life and the places that matter."*
- **Segmented Control:** `[Subjects]` | `[People & Places]` (Active)
- **Interactive Social Graph:**
  - Central Core Node: `Haitham`
  - Connected Nodes & Trust Boundaries:
    - 🔵 `Mamty (T1)` — Inner Circle boundary, highest trust tier
    - 🔵 `Khalid (Family)`
    - 🔵 `Radwa (Family)`
    - 🔵 `Abdelaziz (Friend)`
    - 🟣 `Dubai (Home)`
    - 🟣 `Istanbul (Travel)`
    - 🟣 `Mirsal Studio (Project)`
  - Metrics Legend: `People (28)` · `Places (19)` · `Relations (132)` = **179 nodes**.
- **"Key Relationships & Places" List:**
  - 👥 `Mamty`: *"Your mother · Inner Circle (T1)"* `[✓]` `>`
  - 📍 `Dubai`: *"Home base · Work · Career"* `[✓]` `>`
  - 📦 `Mirsal Studio`: *"Personal project · App · AI features"* `[✓]` `>`

---

## 3. UI Token Architecture & Specifications

```scss
// Colors
$bg-canvas: #FFFFFF;
$bg-surface: #FAF8F5;
$bg-card: #FFFFFF;
$border-light: rgba(0, 0, 0, 0.06);

// Brand Accents
$gold-primary: #C5A059;
$gold-metallic: #D4AF37;
$gold-surface: #FDF8EE;
$gold-border: #E8D5A3;

// Life Theme Cluster Palette
$theme-career: #2F80ED;
$theme-projects: #9B51E0;
$theme-learning: #F2994A;
$theme-gaming: #EB5757;
$theme-travel: #00B4D8;
$theme-health: #27AE60;

// Card Proportions & Layout
$card-aspect-ratio: 3 / 4;
$card-viewport-width: 78vw;
$card-peek-width: 18vw;
$card-border-radius: 20px;
$card-shadow: 0 8px 24px rgba(0, 0, 0, 0.04);
```

---

## 4. Alignment with Dubai-io Architecture & Backend Endpoints

1. **Hot Active Turn Memory vs Cold Vault:**
   - Active chat turns and feedback are ingested synchronously via `POST /api/memory/chat/turn` (`apps/api/app/memory/api.py`).
   - The green `✓ Ingested into Temporal Memory` badge reflects the bi-temporal write confirmation.
2. **Proactive Pings & Empathy Repair:**
   - Autonomous background events (apology repairs, shared news updates) are fetched via `GET /api/memory/chat/pings`.
   - The user's tap on *"Apology Accepted 👍"* resolves the open memory contradiction in Hindsight via the `ends` verdict.
3. **Knowledge Vault Graph Visualization:**
   - Fed directly by `GET /api/memory/graph` or `apps/api/app/lab/tree.py`.
   - The 7 Life Themes match the sovereign directory structure in `docs/plan/Memory/memory.md` §12.
   - The `T1` badge on `Mamty` directly enforces `ScopeGuard` privacy boundaries (`docs/plan/Memory/memory.md` §2).
