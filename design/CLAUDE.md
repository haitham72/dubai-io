# design/ — what's inside (guide for LLMs)

Visual references only. Nothing in this folder is shipped code, and no image here is evidence that a feature is built.

## Layout

| Path | What it is | Origin |
|---|---|---|
| `screens/` | Earliest AI-generated explorations for Dubai-io (`4 styles.png`, `Dubai Concierge Companion Interface.jpg`, `Dubai-io Services and Civic Dashboard.jpg`). Historical — the `01–06` series below superseded them for layout/copy. | AI image tool, early commits (ex root `screens/`) |
| `references/01-home.png … 06-backstage.png`, `x-*.png/jpg` | The working screen set: Home, chat takeover, guide states, provider rows, partner sheet, approvals, lost-item flow, Services/Me, backstage. Generated from the prompt series in `docs/archive/references/redesign.md`. Note: prompts `01b` and `02b` have no PNG files. Visitor-first framing is superseded (22 Oct) — use for visual anatomy only where consistent with `PLAN.md`. | AI image tool (GPT Image 2) for this app |
| `references/claude duet/` | 12 timestamped JPG video frames of a Claude Duet presentation. Interaction references (approvals, artifacts, briefings) — not app assets, not freely licensed. Has its own `README.md` with a frame-by-frame review guide. Preserved with this review checkpoint. | Founder-supplied, 22 Oct |
| `references/carousel/` | Holographic/cards effect reference: 4 JPGs + `holographi ccards.mp4`. Technique ref for glow/metal card work, pointed to from `docs/archive/references/visuals-libraries.md` (ShipSwift update). | Founder-supplied effect ref |
| `references/services/` | Founder's structured service refs. `shops/` = user buys an item (cloth, coffee, restaurants); `service/` = someone does something for the user (pets). Mirrors the groups in `docs/services/intake.md`. The `Pulled data services for agents - app.jpg` sits at the group root. | Founder-taken, filed with structure |
| `references/quest/` | **PERMANENT LOCK — NEVER REMOVE:** Original reference screenshots of the Quest personal assistant app (`cards.jpeg`, `connectors.jpeg`, `full memory md files.jpeg`, `people.jpeg`, `user summary.jpeg`). Definitive visual baseline for Notice cards, Connectors, Memory Tree file views, and Executive user summaries. | Founder-supplied reference screens |
| `references/01 - Visitor onboarding/` | Single file (`01 - visitor wifi.jpg`). Purpose unconfirmed — ask the founder before using it for anything. | Unknown |
| `29-10-2026/` & `references/v3-higgsfield/` | Higgsfield light-mode redesign set (`desktop/l01–l10`, `phone/m01–m10`): assistant home, Services, thread approvals, taxi recovery, Me/memory, community. Full mapping and website priority in [`29-10-2026/INDEX.md`](29-10-2026/INDEX.md) (former `references/v3-higgsfield/README.md` archived to `docs/archive/references/v3-higgsfield-README.md`). | Founder-supplied / restored 29 Oct 2026 |
| `17-11-2026/` | **Target Morning Brief & Memory Controls visual reference (2 PNGs, light mode):**<br>1. `Dubai‑io Morning Brief Dashboard.png` — 3-column desktop Morning Brief (`Home / Chat / Do / Memory` + `Notifications` + `Quick Actions` left rail; hero banner + category pills + 2-column `"Your morning brief — 6 things I noticed for you"` grid in center; right evidence drawer showing `"Because..."` source rows, AED gift carousel, and `Remind me / Shop gifts / Not true / Forget` actions).<br>2. `Quest_ Thoughtful Memory Management.png` — 3-screen mobile reference: (a) swipeable category cards (`Family`, `Career`, `Health`) with AED gift carousel and `"Why am I seeing this?"` trigger; (b) `"Why am I seeing this?"` bottom sheet with `Evidence` (WhatsApp, Gmail, Calendar), `How I found it` (`ScopeGuard` tags: `family`, `person: Mom`, `window: Dec 2025`, `gifts`), `Signals` (`"I noticed she mentioned oud twice. Confirm?"` `Yes / Not really` two-visit confirmation), and `Fact history`; (c) `Memory` controls screen with `Sources` toggles, `Keep memories` (`Career: Always`, `Family: Always`, `Health: Ask first`, `Finance: 2 years, then fade` per `§R-ND`), and `Never remember` (`forget_rules` chips: `Person`, `Chat`, `Phrase` + `Forget something...`). | Founder-supplied, 17 Nov 2026 (aligned with `docs/plan/morning-brief.md` §8 & `PLAN.md` §2) |
| `20-11-2026/` | **Locked Mobile UI & Sovereign Knowledge Vault Standard (3 JPGs, luxury warm white `#FFFFFF`/`#FAF8F5`):**<br>1. `Dubai-io_ A Cinematic UI Showcase.jpg` — Hero Morning Brief with Burj Khalifa sunset, Weekly Recap video/audio card, and 3:4 vertical cards (`Gaming & Hardware`, `Developer & AI Systems`) with peeking next cards.<br>2. `Dubai-io Chat App Mockup.jpg` — AI Companion Chat stream with live temporal memory badge (`Ingested into Temporal Memory`), gold proactive empathy/apology repair card (`Apology Accepted 👍`), and slide-out Life Category drawer (`Today: 6`, `Career & Projects: 12`, `People & Family: 8`).<br>3. `Dubai-io Knowledge Graph Vault.jpg` — Dual-view sovereign knowledge graph: (a) `Subjects` force graph with 458 nodes across 6 life clusters (`Career`, `Projects`, `Learning`, `Gaming`, `Travel`, `Health`); (b) `People & Places` social constellation with 179 nodes and `T1` Inner Circle boundary (`Mamty`, `Radwa`, `Khalid`, `Abdelaziz`). Full spec in [`20-11-2026/INDEX.md`](20-11-2026/INDEX.md). | Founder-supplied / approved 20 Nov 2026 |

## Rules for LLMs working here

1. **Never move, rename or delete the founder's files** (`docs/services/intake.md` §1). If a ref was dropped loose, propose its folder and ask.
2. **References are not functionality.** Never claim a screen or flow is implemented because a PNG exists.
3. **Don't resurrect deleted refs.** The 19 Oct cleanup deliberately removed a real-brands rows variation, a `_rejected/` take, a laundry *quote* mockup (quotes are forbidden) and a civic-services montage (no DubaiNow clones, no official branding). Don't recreate them.
4. **Check scope before building from a ref.** If `PLAN.md` lists what a ref shows as LATER or NEVER, stop and ask — don't build a "small version" of it.
5. **Cite provenance.** When referencing an image, say whether it is AI-generated-for-this-app, founder-supplied, or unknown.

## Linked docs

- Prompts for the root PNGs: `docs/archive/references/redesign.md`
- Effects/carousel mapping: `docs/archive/references/visuals-libraries.md`
- Service-ref filing: `docs/services/intake.md`, `docs/services/cases.md`
- Frame review guide: `references/claude duet/README.md`
- Higgsfield v3 light-mode catalog & website priority: `29-10-2026/INDEX.md` (covers `29-10-2026/` and `references/v3-higgsfield/`)
- Morning Brief desktop dashboard & mobile Memory/Evidence sheets (17 Nov): `17-11-2026/` → spec in `docs/plan/morning-brief.md` §8 · realistic lab-fuel verdict vs these cards: `docs/plan/Memory/memory.md` §8
- Locked Mobile UI, 3:4 Peeking Carousels & Sovereign Knowledge Vault (20 Nov): `20-11-2026/` → catalog and spec in [`20-11-2026/INDEX.md`](20-11-2026/INDEX.md)
