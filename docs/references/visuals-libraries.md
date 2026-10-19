# Visual effect references (founder-supplied)

Part 1 and Part 2 are copied **as supplied**. Part 3 is our own notes. Pointed to from `PLAN.md` §4 (reference parity).

**Current overrides (13 Oct):** cyan selected; the C1 laser/chromatic reflection style is approved on every stage card at 70% of its former intensity (`0.385`). The chromatic theme remains retired pending cleanup. The later ShipSwift MIT/notice update supersedes the earlier do-not-copy note. Package versions/licences below record previous research; no external package/licence verification was rerun during step 00.

---

## 01. Prompts for visuals

### Beam effect for chat

```text
Add the Beam effect from Libraries.dev to my React app.

Install:
npm install border-beam

Usage:
import { BorderBeam } from 'border-beam';

<BorderBeam size="md" colorVariant="colorful" strength={0.7}>
  <YourCard>Content</YourCard>
</BorderBeam>

Props:
- size: "md" | "sm" | "line" | "pulse-inner" | "pulse-outside"
- colorVariant: "colorful" | "mono" | "ocean" | "sunset"
- strength: 0-1, glow intensity
- active: boolean, pauses the animation when false
- theme: "light" | "dark"

Beam wraps a child element and rides an animated glow around its border.
It ships zero runtime dependencies and needs React 18 or newer.
Docs: https://libraries.dev/beam.html
```

### Voice effect

```text
Add the Voice effect from Libraries.dev to my React app.

Install:
npm install voice-glow

Usage:
import { VoiceBeam, useMicrophone } from 'voice-glow';

const mic = useMicrophone();

<VoiceBeam stream={mic.stream} processing={thinking}>
  <ChatInput />
</VoiceBeam>

<button onClick={mic.state === 'live' ? mic.stop : mic.start}>
  {mic.state === 'live' ? 'Stop' : 'Listen'}
</button>

// Without a microphone, drive it yourself (0–1, a number or a per-frame getter):
<VoiceBeam level={() => meter.current}>
  <Card />
</VoiceBeam>

Props:
- type: "default" | "pill" | "mobile" — geometry preset for a ~350px chat input, a ~150×44 recording pill or the bottom of a phone screen
- stream: MediaStream to react to (wins over level); level: 0–1 number or getter
- processing: boolean, gathers the glow into a beam that travels its range while work is in progress
- colorVariant: "colorful" | "mono" | "ocean" | "sunset" | "forest" | "candy" | "ice" | "gold"
- colors: up to 7 lobe colours; bandColors: { core, above, mid, below }
- sensitivity, threshold, attack, release: the input chain (gain, gate, envelope)
- reach, spread, flow, bend, idle: the shape of the reaction
- theme: "dark" | "light" | "auto"
- strength: 0-1, effect opacity; active, paused; scale

Voice wraps a child element and overlays a sound-reactive glow along its
bottom edge: a centered, colorful beam that rises and blooms with the
voice. It auto-detects the child's border radius, ships zero runtime
dependencies and needs React 18 or newer. The microphone needs a secure
context (https or localhost) and mic.start() called from a user gesture.
Docs: https://libraries.dev/voice.html
```

### Thinking orbs

```text
Add the Orb effect from Libraries.dev to my React app.

Install:
npm install thinking-orbs

Usage:
import { ThinkingOrb } from 'thinking-orbs';

<ThinkingOrb state="searching" size={64} />

Props:
- state: "working" | "searching" | "solving" | "listening" | "connecting" | "weaving" | "composing" | "breathing" | "shaping"
- size: 64 (chat-avatar scale) or 20 (inline-text scale) — each is separately tuned
- speed: multiplies the animation clock, default 1
- dark: boolean, picks the light or dark tuning
- paused: boolean, freezes the animation

Orb replaces the spinner in an AI "thinking" state with nine hand-tuned animated
states. It ships zero runtime dependencies and needs React 18 or newer.
Docs: https://libraries.dev/orbs.html
```

---

## 02. ShipSwift library

- https://github.com/signerlabs/ShipSwift/tree/main
- https://github.com/signerlabs/ShipSwift/tree/main/ShipSwift/SWPackage/SWAnimation/SWMetal

> Founder: "although this is a Swift library, for now let's learn from it."

---

## 03. Our notes (not part of the supplied text)

### Packages checked on npm (12 Oct 2026)

| Package | Version | Licence | Runtime deps | Peer |
|---|---|---|---|---|
| `border-beam` | 1.4.1 | MIT | none | react, react-dom ≥ 18 |
| `voice-glow` | 0.3.0 | MIT | none | react, react-dom ≥ 18 |
| `thinking-orbs` | 0.3.2 | MIT | none | react ≥ 18 |

All three come from `github.com/Jakubantalik/Libraries.dev`. Pin exact versions at scaffold; `voice-glow` and `thinking-orbs` are 0.x, so expect API drift.

### Where each one goes

| Effect | Use in Dubai-io | Notes |
|---|---|---|
| **Beam** (`BorderBeam`) | Border glow on the chat Composer while Luna is understanding, and on the goal-plan card while agents work | Use `size="md"` / `"line"`; `active={false}` when idle and under reduced motion |
| **Voice** (`VoiceBeam`, `useMicrophone`) | The Composer's mic button on Home and in chat; `processing` while `LUNA.understand` runs. `type="mobile"` fits the bottom of the phone | Mic needs **HTTPS and a user tap**; over LAN `http://` it will not start, so keep a typed fallback and a manual `level` driver for the demo |
| **Orb** (`ThinkingOrb`) | The bot avatar (size 64) and inline "working…" text (size 20), replacing the typing dots | Suggested states: `searching` = rows lookup · `connecting` = provider sign-in / valley team · `solving` or `weaving` = goal plan · `listening` = mic live · `composing` = reply · `breathing` = idle |

### Guardrails

- **Palette is locked** (CLAUDE.md). Of the colour variants use `ocean` (cyan family) or `mono`, or pass `colors` built from the tokens (`#0A9CC2`, `#E3F6FB`, white). Avoid `sunset`, `candy`, `gold`, `colorful`.
- **One glow at a time:** do not run Beam, Voice, the Orb and the L3 shader together on one screen; pick by state.
- **Reduced motion and battery:** pass `paused` / `active={false}` when `prefers-reduced-motion` is set or the tab is hidden.
- **Truth in status:** these are "working" indicators only. They never imply a result, and nothing is shown as done until a provider event.

### ShipSwift `SWMetal`: what to learn from (33 effects, Swift + Metal)

Technique ideas for the WebGL2 layer (PLAN.md §4 (reference parity), L3). Re-implement in GLSL; **do not copy code** before checking ShipSwift's licence.

| Our need | Look at |
|---|---|
| Hero field (slow, fluid, soft) | `SWGrainGradient`, `SWSimplexNoise`, `SWFractalClouds`, `SWPlasma`, `SWInkSmoke` |
| Glass bar edge / refraction | `SWGlass`, `SWChromaticGlass`, `SWLiquidChrome`, `SWPolishedAluminum` |
| Orb / avatar | `SWGlassOrb`, `SWMetaballs`, `SWSmokeRing` |
| Scroll / touch ripple | `SWWater`, `SWSwirl`, `SWVoronoi` |
| Success / "found it" sparkle | `SWGlitter`, `SWIntenseBling` |
| Dot-matrix accents | `SWDots*` family, `SWHalftone` |

### More libraries.dev packages (found 13 Oct; no founder prompt supplied)

| Package | Version | Licence | Peer | Use in Dubai-io |
|---|---|---|---|---|
| `metal-fx` | 2.0.11 | MIT | react, react-dom ≥ 18; WebGL2 (falls back to the plain child) | `MetalFx preset="silver"` on the one primary CTA. **No `gold`** (R0: no gold). Cyan theme selected; use the approved C1 reflection style without switching the page palette. `reflectionTargets` lets neighbouring cards catch the metal |
| `img-fx` | 0.5.1 | MIT | react, react-dom ≥ 18, `three` ≥ 0.149 | `ImageGeneration`: `sweep-gradient` for the onboarding soft reveal; `pixels-organic` only where an image is really generated (try-on). Lazy-load (three is heavy) |
| `liquid-gooey` | 0.2.2 | MIT | react, react-dom ≥ 18 | `Liquid` merges: agent-lane pills → one total; fitting-tray pill |
| `bot-avatars` | 0.2.2 | MIT | react ≥ 18 (2D canvas) | Not used (the ThinkingOrb is the avatar) |

### ShipSwift update

ShipSwift is **MIT**, so porting is allowed as long as the licence notice is kept in each ported shader file (the earlier "do not copy" note is superseded).
- **Holographic set** (`demo/_ref/carousel/holographi ccards.mp4`): `SWFoil`, `SWGlitter`, `SWIntenseBling`, `SWChromaticGlass`, `SWPolishedAluminum`, drag/tilt-driven.
- **Gradient source:** `SWGrainGradient`, `SWAnimatedMeshGradient` (`SWAnimation/`).

Mapping is in `PLAN.md` §4 (reference parity). The native app later uses the Swift originals.
