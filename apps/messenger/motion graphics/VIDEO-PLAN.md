# Messenger: the redesign film (plan)

Documentation review (2026-10-08): This is the film storyboard and recorded render history. Current app capabilities and verification are in [ARCHITECTURE.md](../ARCHITECTURE.md); the film has not been rerendered for the latest voice, meeting, and image changes. No generation or rendering was run during this documentation update.

**Recorded status (2026-10-04): second cut rendered, `out/film_sound.mp4` (60 s).** After Haitham's notes ("the first 25 seconds were slow"): the logo is 3 s; a cursor hovers and clicks with the camera pushing in on every click; chats, messages, mail and calendar reveal row by row; the AI Chat opens on an extreme close-up of the prompt typing, thinks with live status lines and placeholders, then bursts into photos, a plan, day cards and chips; Weather clicks through Summer, Winter, Rain and Wind (the stills in `app/public/photos/weather-*.jpg`, with live snow, rain and wind drawn over them). Will's lines are retimed (`VO` in `film.ts` = `film_mix.py`). The shot table in §4 below is the first cut's; `film.ts` is the current one. Run the kit on its own port: `bunx vite --port 5393`, render with `--url http://localhost:5393`.

---

## 1. The brief

A launch film for the **Messenger redesign**: the private chat app with its built-in assistant and its workspaces (`../Messenger-redesign.md`, the 15 reference screens in `../Slides/output_grid/`).

- **Feel:** clean, elegant and calm, like the ChatGPT launch films. Smooth transitions and unhurried shots. It should feel like a premium Apple product page.
- **Not** the Messenger Creator reel. That one is fast, punchy and sticker-loud. This one breathes.
- **Look:** the redesign itself: iOS/macOS light glass, a soft sky behind frosted windows, Messenger blue `#1677FF` with the lavender of Messenger Updates `#7C3AED`, primary text `#101828`, secondary `#667085`, very soft shadows.

## 2. Length and pace

| | |
|---|---|
| Length | **60 s** (a 45 s cut-down is the same film minus §4 shot 7) |
| Pace | 3 to 6 s per shot; never a hard cut on a beat. Shots flow into each other |
| Music | calm, warm, about 90 BPM (prompt in `audio/suno-prompt.md`) |
| Voice | one calm narrator, sparse: about 70 words over 60 s, with music-only gaps between lines |
| Format | 1920×1080, 60 fps (the kit's fixed size; 9:16 is separate work) |

## 3. Transition vocabulary (the ChatGPT smoothness)

Every shot change is one of these. Hard cuts are not allowed.

| transition | how (Canvas2D in the kit) | use for |
|---|---|---|
| **Soft dissolve + drift** | the outgoing shot fades over 0.6 to 0.9 s while both keep a slow camera drift; the incoming one scales 1.02 → 1.00 | the default |
| **Blur dissolve** | the outgoing shot blurs 0 → 24 px while fading; the incoming one sharpens from 24 px (`ctx.filter = 'blur()'`) | between workspaces |
| **Match move** | one element carries across the cut: the Updates card becomes the tray, a flight card becomes the Calendar event | the hero moments |
| **Glass push** | a frosted panel slides over the frame (`backdrop`-style blur of the frame under it) and the next shot is behind it when it slides away | into the AI Chat, into the Profile |
| **Depth pull** | the window recedes (scale 1 → 0.8) and settles into a field of all the screens floating at different depths | the finale |

Motion rules: ease-in-out cubic or a soft spring (overshoot at most 2%). Camera moves are slow (5 to 8% of the frame per second). Nothing shakes, flashes or glitches. Motion blur comes from the renderer's sampling (`--samples auto`).

## 4. The film

Times are approximate; the voice will set them exactly (the kit's aligner, as in the Creator film).

| # | time | picture | transition in | narrator |
|---|---|---|---|---|
| 1 | 0 – 6 s | A soft sky (the references' blurred clouds). The glass **M** tile fades up and settles; "Messenger" writes in beside it, light weight, large | fade from white | "This is Messenger." |
| 2 | 6 – 14 s | **Chats**, the golden screen (R04): the window glides up into place; the camera drifts across the chat list to Arif Khan's conversation; a new message arrives ("Hey! Are you free this weekend?") | glass push | "Your conversations, calm and in one place." |
| 3 | 14 – 22 s | **Messenger Updates**: the lavender card ("Image ready, flight found, 5 more…") glows once, then opens to the right as the horizontal tray (R13): Image ready, Flight found, Research ready, Email draft ready, sliding in one after another | match move (the card becomes the tray) | "Your assistant works in the background, and tells you when it's done." |
| 4 | 22 – 30 s | **Image ready** opens (R16): the Dubai beach picture, "Generated 2 minutes ago · Ready"; the cursor presses **Use in chat**; the image flies into Arif's chat as a message | match move | "Use the result right in your chat." |
| 5 | 30 – 38 s | **AI Chat**: "Generate a beautiful photo of cherry blossoms in Kyoto…" types in; the minimal status "Searched 8 sources · 12 s"; the image resolves softly; the Sources column fills | glass push | "Ask anything. Messenger searches, writes and creates." |
| 6 | 38 – 46 s | **Flights**: "Flights Dubai to London next Friday"; the Flight found card (EK007, 7h 25m); **Add to calendar**; the card flows into the **Calendar** week view and becomes the green event on Wednesday | match move (the flight card becomes the event) | "Find a flight, and it's already on your calendar." |
| 7 | 46 – 52 s | A slow glide through the workspaces, about 1.5 s each, blur dissolves: **Weather** (Dubai 32°, sunny), **Stocks** (AAPL 224.91), **Mail** ("Your booking is confirmed", with *Summarize with Messenger AI*) | blur dissolve | "Weather, markets, mail: everything you need, one click away." |
| 8 | 52 – 56 s | **Profile**: the frosted modal settles over the chats (R14): Arif Khan, Online, Status | glass push | "Private, and yours." |
| 9 | 56 – 60 s | Depth pull: the window recedes into a slow field of all the screens floating at different depths, then they fade and the **M** tile and "Messenger" return to centre | depth pull, fade to sky | "Messenger. Your chats, with a private assistant." |

About 70 words. The narrator speaks in roughly half the film; the music carries the rest.

### Every screen is the real design

The screens are drawn in code (crisp at any zoom, every element animatable), following the spec's geometry: nav 208 px, sidebar 380 px, workspace the rest, radii 14 to 20 px, frosted surfaces `rgba(255,255,255,.74)` with blur. The 15 reference images are for layout and content, not for pasting. Photos (the Dubai beach, Kyoto, city cards) are fetched once into `app/public/photos/` from the Unsplash ids the app already uses, never at runtime. Names and data come from the app's fake data (Arif Khan, Sara Ali, EK007 Dubai → London). No real person's private details.

## 5. Sound

- **Music:** Suno, `audio/suno-prompt.md`. Calm and warm; it carries the film, so it must be good.
- **Voice:** one calm narrator from ElevenLabs. Not Liam (too energetic for this film). Will (*Relaxed Optimist*), chosen from two-line samples (`audio/takes/samples/`).
- **Effects:** very few and soft: a gentle message arrival, a soft tick when the tray opens, a glassy swell on the depth pull. No whooshes or impacts.
- **Mix:** voice on top, music ducked under it by about 6 dB, master at −14 LUFS (`analysis/reel_mix.py` is the template).

## 6. Before coding (setup notes for the build)

1. `cd app && bun install` (node_modules are not copied).
2. **Port:** the Messenger app's own dev server uses 5173. Run the kit on another port (`bunx vite --port 5392`) and render with `--url http://localhost:5392`. Otherwise the renderer opens the app instead of the film. This happened once already.
3. `app/src/timeline.ts` still points at the Creator film's `reel` scene, which is not copied: replace it with this film's scenes.
4. `data/audio.json` / `data/lyrics.json` are the Creator film's. The narrator's read plus `analysis/align_vo.py` and `audio_vo.py` replace them.
5. Reusable from the kit: `scenes/card.ts` (`drawOrb`, the clean karaoke card), `scenes/_vo.ts` (camera, karaoke, text layout), Inter in `app/public/fonts/inter/`, the post-processing already set to the clean look.
6. This folder belongs to this project's lead. Sessions here do not commit (`../CLAUDE.md`).

## 7. Decided (Haitham, 2026-10-04)

- **Length:** 60 s.
- **Narrator:** Will (ElevenLabs, *Relaxed Optimist*), nine lines in `audio/vo/`.
- **Closing line:** "Messenger. Your chats, with a private assistant."
- **Music:** both were made. Stable Audio is `audio/takes/stability-1.mp3`; the Suno track is still to come (`audio/suno-prompt.md`). Haitham picks one by ear.
