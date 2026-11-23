# Messenger IP list and M0 recommendation

## Founder confirmation — 23 Nov 2026

The founder confirmed M0 and changed these rows. Where this section and the table below disagree, this section wins.

**Keep, as the founder’s own**

- Concept sheets: `Slides/*.jpg` and `Slides/output_grid/`.
- Screen frames under `screens/`: `4 screens.jpg`, `Layer 0.jpg` through `Layer 10.jpg`, and `GPT design/01.jpg`.
- Video clips in `media/videos/`.
- Motion-graphics audio, and `motion graphics/app/public/photos/`.

**Still excluded**

- `screens/dynamic island/` scrapes.
- The office logo and favicon.
- Diwan commemoration pictures and the 97 files in `public/photos/`.
- The four sticker packs and sticker-generation code.
- The pytest dump directory.

**Any image or frame that visibly shows the old name or the old logo is excluded from the shipped app**, even if its folder is in the keep list above.

**Drop, in addition to the earlier exclude rows**

- The Diwan connector: `agents/mirsal_agents/diwan.py`, `agents/mirsal_agents/routes/diwan.py`, `src/updates/diwan.ts`, `agents/mirsal_agents/diwan_demo.json`, and their UI hooks and tests.
- The Nadi connector: `agents/mirsal_agents/skills/nadi.py`, `agents/mirsal_agents/routes/nadi.py`, and their UI hooks and tests.
- The cleaner’s `remove-ai-watermarks` dependency, and any feature that removes an AI watermark or a provenance mark. That conflicts with the provenance rules.
- There is no Higgsfield at all (D8, 23 Nov 2026). Exclude `lib/higgsCli.ts` and every Higgsfield API call, CLI call, UI hook, and test. That includes the HTTP client in `lib/http.ts`, the CLI job in `server/server.py`, and the `HF_CREDENTIALS` and `HIGGS_*` keys.

**User-sticker cut-out — chosen 23 Nov 2026 (MG-B4).** Primary is BiRefNet general. Licence: MIT, including the weights. The author states that all the codes and weights are under the MIT licence, which allows selling copies of the software ([LICENSE](https://github.com/ZhengPeng7/BiRefNet/blob/main/LICENSE), [weights note](https://github.com/ZhengPeng7/BiRefNet/issues/316)). Official browser file, from the same repository release: `BiRefNet-general-bb_swin_v1_tiny-epoch_232.onnx` (213.6 MB, [release v1](https://github.com/ZhengPeng7/BiRefNet/releases/tag/v1)). It is not vendored. A phone WebGPU session is refused: that graph plus the default 1024-pixel pass does not fit the 256 MiB minimum GPU buffer, so the photo stays unchanged until a smaller official weight is supplied. U²-Net (Apache-2.0, commercial use allowed, no official ONNX), IS-Net (Apache-2.0 names the code only; the dataset terms are non-commercial and the weights are not granted), and InSPyReNet (MIT for the software, no official ONNX) were compared and not chosen. MediaPipe Selfie Segmentation (Apache-2.0) is the person-only fallback. A non-person photo on that fallback fails closed. No AI image generation.

**Rebuild, and fix in the rebrand**

- Fonts that have no notice in the tree: attach the notice, or drop the file.
- Google Fonts links: self-host with the notice, or replace the link with a system stack.
- Unsplash and Pravatar hotlinks: replace them. They are not owned assets.

**Project licence.** `apps/messenger/NOTICE.md` is the founder licence statement. It ships with a placeholder for the founder’s sign-off. The pdoom MIT file and the OFL notices do not licence the app.

**Status:** confirmed for the snapshot and the rebrand — 23 Nov 2026 (founder).  
**Gate:** M0. This file copies nothing.  
**Recommendation: reuse the founder-authored code as a rebranded snapshot.** This replaces the 23 Nov clean-room recommendation. D1 is the decision.

The office owns the old product and its brand. The redesign repo is the founder’s own separate app. Every feature the founder added there is the founder’s, and the office app never implemented those features. The import, after this list is confirmed, is:

```
git subtree add --prefix=apps/messenger https://github.com/haitham72/Mirsal-redesign master --squash
```

A rebrand commit follows immediately. The old repo’s history stays in the source repo. Nothing in this plan runs that command.

**Counts: keep 12, exclude 8, rebuild 16.**

The sentence the founder signs: **I confirm this keep/exclude/rebuild list.**

## Keep / exclude / rebuild

Paths below are the redesign repo’s own paths, so a builder can find the files. They are not the Messenger product name.

| Group | Path or asset | Origin evidence | Decision | Reason |
|---|---|---|---|---|
| Brand | `public/mirsal-logo.png` | `fb13b2fa` (2026-10-05): cut-out of `Slides/mirsal-logo.png`, which is not in HEAD | exclude | Office brand graphic. |
| Brand | `public/favicon.png` | Same commit. `index.html` uses it as the favicon | exclude | Same cut-out. |
| Brand | `public/manifest.webmanifest` | Product name and the logo path | rebuild | Retired name, and the icon points at the excluded logo. The founder supplies the Messenger name and a new mark. |
| Brand | `index.html` title, apple title, touch icon, favicon | Those tags | rebuild | Same retired name and the same two excluded images. |
| Brand | Logo `<img>` and menu name in `src/shell/Nav.tsx` and `src/shell/MacDesktop.tsx` | Those tags load the excluded logo | rebuild | The shell stays in the `src/` keep row. These tags point at a new mark. The visible name is renamed in the rebrand. |
| Concept sheets | `Slides/*.jpg`, including `Slides/Mirsal.jpg` and `Slides/output_grid/output_grid_1.jpg`–`4.jpg` (19 images) | Design doc lines 8 and 1321 call them supplied. Added in foundation `7f580a8` | rebuild | Founder confirms each sheet is founder-authored and contains no office logo or office-app screenshot. A sheet that fails that check moves to exclude. |
| Concept sheets | `Slides/output_grid/combine_slides.py` | Grids `Slides/*.jpg` | rebuild | Tooling for those sheets. It stays only if the sheets stay. |
| Screen frames | `screens/GPT design/01.jpg` | `d77dea6` (2026-10-06) | rebuild | No licence. Founder confirms it is founder-made and is not an office screen. |
| Screen frames | `screens/dynamic island/` (6 files, including `flighty-dynamic-island.webp`, `sddefault.jpg`, `81ChrBjnuEL.png`) | `d77dea6` | exclude | Reference scrapes with no licence. Filenames are a third-party island, a video thumbnail, and a marketplace-style id. |
| Screen frames | `screens/4 screens.jpg`, `Layer 0.jpg`, `Layer 2.jpg`–`Layer 10.jpg`, `calender.jpg`, `files.jpg`, `research.jpg` | `d77dea6` and `3145409` | rebuild | Founder-added frames, no licence. Founder confirms they are not office-app screenshots. |
| Diwan pictures | `public/diwan/rashid-bin-saeed-anniversary/` (6 JPGs) | `diwan_demo.json` line 2: supplied commemoration posts, and variations Diwan already holds. `ARCHITECTURE.md` line 156: the app never makes these pictures | exclude | Client assets. |
| Diwan client | `agents/mirsal_agents/diwan.py`, `routes/diwan.py`, `src/updates/diwan.ts`, and the event calls in `src/apiclient/agents.ts` | `ARCHITECTURE.md` lines 87–88: the events backend is the separate Diwan project, formerly Diwan Hamdan | keep | Founder-authored client. It asks Diwan for events and for pictures Diwan already has. The rebrand renames the product string. The excluded pictures are not imported with it. |
| Diwan demo copy | `agents/mirsal_agents/diwan_demo.json` | Paths point at the excluded pictures | rebuild | Replace with a non-client demo before import. |
| Nadi | `agents/mirsal_agents/skills/nadi.py`, `routes/nadi.py` | The module says connector `"demo"`. `ARCHITECTURE.md`: no real HR system is called | keep | Founder-authored demo connector. A live Nadi URL is not part of this import. |
| Photos | `public/photos/` (97 JPGs) | Commit `9fecf2f`. No licence file | exclude | Unlicensed photographs, not app code. |
| Video clips | `media/videos/desert-highway-dusk.mp4`, `dubai-beach-sunset.mp4`, `dubai-skyline-golden-hour.mp4` | Design notes call them bundled Kling clips. Added in `d77dea6` | rebuild | No licence. Founder confirms redistribution or replaces them. Playback code stays in `src/`. |
| Sticker packs | `public/stickers/` (`nile-days`, `yalla`, `wheels-up`, `office-mood`, plus `index.json`) | Claude commit `d5b6607`, “Four demo packs” | exclude | D6 and D7. Builder stand-in packs are not imported. Founder-made packs are new files under `apps/messenger/public/packs/`. |
| Sticker generation | `agents/mirsal_agents/sticker_builder.py`, `routes/stickers.py`, `skills/stickers.py` (`BuilderLibrary`), `agents/tools/demo_stickers.py`, and the generate calls in `src/apiclient/agents.ts` and `src/chats/skills.ts` | `sticker_builder.py` calls an external pack service or returns demo mode | exclude | Nothing from the Builder service. User stickers are a photo plus background removal, planned separately. |
| UI | `src/` (shell, chats, screens, mobile, store, ui kit, voice) | Foundation `7f580a8` | keep | Founder-authored UI. Logo tags and sticker-generation calls are the rows above, not this keep. |
| HTTP API | `api/*.ts` and `lib/http.ts` | Photo route stores metadata. The 97 JPGs stay excluded | keep | Founder API. The Higgsfield client is the exclude row below. Image and video generation endpoints are dropped because D7 forbids them. |
| Higgsfield | `lib/higgsCli.ts`, the HTTP client in `lib/http.ts`, the CLI job in `server/server.py`, `HF_CREDENTIALS`, `HIGGS_*`, and every UI hook and test that calls or names that provider | D8, 23 Nov 2026: there is no Higgsfield at all | exclude | The snapshot must not call, configure, or offer that provider. |
| Agents | `agents/` except the Diwan, Nadi, and sticker-generation files already rowed | Voice, research, mail, memory, meeting, cleaner, MCP client | keep | Founder agent service. Diwan client and Nadi stay. Sticker generation stays out. |
| Retired server | `server/` | The repo guide calls it the retired Python API | keep | Founder code, later retired. It is not the office app. |
| iPhone samples | `design/ios/*.html`, `ios.css`, `ios.js` | `d77dea6` | keep | Founder samples. Unsplash and Google Font links are the rows below. |
| Unsplash and Pravatar | Hotlinks in `design/ios/*.html` and `src/ui/index.tsx` | No licence in the repo | rebuild | Replace the hotlinks or add the notices. They are not owned assets. |
| Lucide | `lucide-react` 0.460.0 | Lockfile licence ISC | keep | The ISC notice stays with the package. |
| OFL fonts | Inter and Archivo under `motion graphics/app/public/fonts/`, with `OFL.txt` | SIL OFL 1.1 notices are in the tree | keep | The notices ship with the files. |
| Fonts without notices | Cormorant, IBM Plex Mono, and `motion graphics/app/public/fonts/stroke/` | No matching notice in HEAD | rebuild | Attach each licence or drop the files. |
| Google Fonts links | `index.html` and `design/ios/index.html` | Hotlinked families with no OFL file in the repo | rebuild | Self-host with notices, or keep the link and add the notices. |
| Cleaner dependency | `remove-ai-watermarks==0.45.1`, named in the cleaner docs, not vendored | No licence file in this repo | rebuild | Record that package’s licence or drop the dependency. The founder wrappers `ai_cleaner.py` and `ai_cleaner_engine.py` stay in the agents keep. |
| Motion engine | `motion graphics/LICENSE.pdoom-engine` and `motion graphics/app/src/` | MIT, Copyright (c) 2026 Giacomo Magnanini | keep | The MIT notice travels with the engine. |
| Motion audio | `motion graphics/audio/` (`music.mp3`, `sfx/`, `vo/`) | No licence for the mp3s | rebuild | Founder confirms who made the audio and that Messenger may ship it, or replaces it. |
| Motion photos | `motion graphics/app/public/photos/` | No licence in that folder | rebuild | Founder confirms rights or replaces the files. |
| Pytest dump | `pytest-of-h.ibrahim/` | Commit `cce429a`. Pytest basetemp plus cleaner JPEGs | exclude | Accidental test output. `h.ibrahim` is only a directory segment. The commit author is `haitham72`. |
| Project licence | Repo root | `package.json` is `"private": true` and has no `license` field | rebuild | The snapshot needs a founder licence statement. The pdoom MIT file and the two OFL notices do not licence the app. |
| Founder docs | `README.md`, `ARCHITECTURE.md`, `CLAUDE.md`, the design doc, `PRESENTATION_GUIDE.md`, `prompt.md`, `run.md`, `docs/` | Diwan and Nadi contracts live in `ARCHITECTURE.md` | keep | Founder design and build docs. The rebrand renames the product string. |
| Founder tests | `tests/` and `agents/tests/` | Photo-window script in `package.json`. The pytest dump is the exclude row | keep | Tests travel with the kept code. Drop or rewrite tests that only cover excluded sticker generation or excluded images. |

## Repo identity (kept from the 23 Nov audit)

| Item | Evidence |
|---|---|
| Local clone | `D:\Vscode\Mirsal-redesign`, branch `master`, not switched |
| Remote | `https://github.com/haitham72/Mirsal-redesign.git` |
| HEAD | `6b45ba48874a60174c728eecedc6c94c0b818231` — 2026-11-19 20:20 +0400 — Haitham Mohamed `<ihisam@outlook.com>` — AI workspace replaces the Updates tray |
| First commit | `7f580a816933cd34a3f31ce7f7b0f94a2c322ab5` — 2026-10-04 — Haitham `<system722@gmail.com>` — foundation |
| Commits on HEAD | 142 |
| Project licence | None at the repo root. The only licence files in the tree are `motion graphics/LICENSE.pdoom-engine` and the two SIL OFL notices |
| GitHub visibility | Not stated in the local docs. The README calls the Vercel demo link private. That is not a statement about the GitHub repo |

Git identities on `--all`: `haitham72 <ihisam@outlook.com>` 74, `haitham72 <ihisam@Outlook.com>` 26, `Haitham <system722@gmail.com>` 25, `Claude <noreply@anthropic.com>` 8, `haitham72 <59456439+haitham72@users.noreply.github.com>` 5, `Haitham Mohamed <ihisam@outlook.com>` 3, `Vercel <vercel[bot]@users.noreply.github.com>` 1. Trailers: 45 Claude co-author lines, and one Cursor trailer on `3145409d`. A personal git email is not title. D1 is what settles the keep rows: the founder states that the features added in this repo are the founder’s, and that the office app never implemented them.

No commit message in the four named docs uses the words employer, NDA, or work-product. “client” in those docs means API client, except the Diwan pictures, which the architecture describes as pictures Diwan already holds.

## What this file does not decide

The test rerun and the working/mock classification stay in `audit.md`. They do not change this list. Public visibility on GitHub would still not prove ownership. The rename inventory and the sticker re-plan are separate sections of the revised plan.
