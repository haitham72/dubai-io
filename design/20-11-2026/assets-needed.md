# Assets needed for the 20-11-2026 UI spec

Companion to `INDEX.md`. Every card and hero in the mockups is an **image**; the build currently has none. Sizes below are the **@3x pixel size** of the pt sizes in `INDEX.md` (export JPEG q85 or WebP, sRGB).

## Rules for all images
1. **Never use real third-party product art or logos**: no GTA VI artwork or logo, no PlayStation / PS5 / DualSense, no publisher or console marks, no DubaiNow or government emblems, no real person's likeness. The mockups contain such art only because they were AI-generated; it is a placeholder idea, not an asset.
2. Use **original generated imagery** (the founder's generator tools) or **properly licensed** images (keep the licence note next to the file).
3. Store **locally in the repo** under a path agreed with the app owner (suggested: `apps/mobile/assets/demo/`), never hot-linked. Name files `<screen>-<slot>.jpg`.
4. A fixture image is shown with the visible **Demo data** pill (root rule 2). A real photo of the user's own content is not a fixture.
5. Each image has a dark legibility gradient applied in code (see `INDEX.md` 4.1 / 4.2); export the image **without** baked text, price chips or gradients.
6. Keep the focal subject in the **left-center / upper 60%**, because titles sit bottom-left on the image.

## List

| # | Slot | Screen | Pt size | Export px | Aspect | Description (original art) |
|---|---|---|---|---|---|---|
| 1 | `today-hero-recap` | Today hero | 390 x 590 | 1170 x 1770 | about 2:3 | Dubai skyline at golden-hour sunset seen across a calm canal, a tall tower on the right third, warm peach / pink sky, soft sun low-center, palm fronds entering from the left edge, water reflections. Fades to cream at top and bottom, so keep the top 15% and bottom 18% low-detail |
| 2 | `today-gaming-feature` | Today card, "Gaming & Hardware" feature | 290 x 257 | 870 x 771 | 8:7 | **Original** neon-sunset coastal city illustration: purple / pink sky, palm silhouettes, an invented sports car and an invented character seen from behind, skyline on the water. Not Vice City, not GTA. Demo data |
| 3 | `today-gaming-peek` | Today card (peek) | 290 x 257 | 870 x 771 | 8:7 | **Original** minimalist white game-console-like object (no real console shape or logo) on a pale marble pedestal, soft cool light. Demo data |
| 4 | `today-dev-feature` | Today card, "Developer & AI Systems" | 290 x 210 | 870 x 630 | 4:3 | Dark-mode code editor on a laptop with a glowing violet holographic orb, a plant and a mug, purple rim light. Invented UI and code, no real IDE branding |
| 5 | `today-dev-peek` | Today card (peek) | 290 x 210 | 870 x 630 | 4:3 | Metallic humanoid robot bust, side profile, blue-cool light, dark navy background |
| 6 | `quests-hero-career` | Quests hero card | 358 x 293 | 1074 x 879 | about 11:9 | Dubai skyline at purple-pink sunset over water with a swirling light-trail wave over the tower; calm left third for the 3-line title |
| 7 | `quests-more-companion` | More Quests card 1 | 274 x 112 | 822 x 336 | about 2.45:1 | Palm silhouettes and skyline at purple sunset over water; calm left half for the title |
| 8 | `quests-more-studio` | More Quests card 2 (peek) | 274 x 112 | 822 x 336 | about 2.45:1 | Pale-blue daytime tower and sail-shaped building top against a white sky; calm left half |
| 9 | `chat-news-strip-gaming` | Chat news card strip | 340 x 68 | 1020 x 204 | 5:1 | Wide purple-pink dusk skyline with palms, calm left for the overlaid title. **Original**, not GTA artwork. Demo data |
| 10 | `today-hero-recap-2`, `-3` | Today hero carousel (dots) | 390 x 590 | 1170 x 1770 | about 2:3 | Two more hero variants for the 3 dots (e.g. a night skyline, a desert dawn), same safe zones as #1 |

## Icons (not images, but required; line style 1.6 pt stroke, 24 pt, rounded caps)
Tab icons: calendar-window, speech bubble, layers (stacked diamonds), brain. Mic-orb glyph: 5-bar vertical waveform. Drawer: sparkle, briefcase, people, gamepad (only if the founder keeps Gaming), plane, house, history bubble. Vault: briefcase, layers, open book, person, map pin, plane. Quest badges: laurel wreath, stacked cubes, brain. Provide an SVG set, not emoji.

## Other graphic assets
- The graph canvas is drawn in code (no image): spheres with radial gradients, leaf dots and edges, see `INDEX.md` 4.12.
- The 3 badge icons and the crown for Quest VIP are SVG, gold `#C5902F`.
