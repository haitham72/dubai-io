# Mirsal IP evidence and M0 recommendation

**Status:** planned — awaiting founder approval (23 Nov 2026, Cursor).  
**Gate:** M0. The founder decides. This file copies nothing.  
**Recommendation: clean-room.**

A personal git author is not title. The POC has no project licence. Concept sheets and Diwan pictures are described as supplied. A separate project, formerly Diwan Hamdan, is the stated home of the events backend and of pictures Mirsal “never makes”. Nothing in the README, `CLAUDE.md`, `ARCHITECTURE.md`, `Mirsal-redesign.md`, or the commit messages says the POC was made for an employer, under an NDA, or as client work. Nadi is documented as a demo that calls no real HR system. The founder spec §1 (line 44) reports that the idea/design was discussed in connection with an office app. Keep the office link in the evidence record and obtain path-specific rights evidence.

Build agents for a clean-room `apps/mirsal/` do not open `D:\Vscode\Mirsal-redesign`, its screens, its slides, or its brand files. The idea in the founder spec may be used. The repo’s code, layout, name, logo, and assets may not, until the written confirmations below exist.

## Repo identity (re-checked 23 Nov 2026)

| Item | Evidence |
|---|---|
| Local clone | `D:\Vscode\Mirsal-redesign`, branch `master`, not switched |
| Remote | `https://github.com/haitham72/Mirsal-redesign.git` |
| HEAD | `6b45ba48874a60174c728eecedc6c94c0b818231` — 2026-11-19 20:20 +0400 — Haitham Mohamed `<ihisam@outlook.com>` — “Mirsal AI workspace replaces Updates tray; collapsible nav; white chat header” |
| First commit | `7f580a816933cd34a3f31ce7f7b0f94a2c322ab5` — 2026-10-04 — Haitham `<system722@gmail.com>` — foundation |
| Commits on HEAD | 142 |
| Project licence | None. `package.json` has `"private": true` and no `license` or `author` field. The only licence files in the tree are `motion graphics/LICENSE.pdoom-engine` (MIT, Copyright (c) 2026 Giacomo Magnanini) and SIL OFL notices for Inter and Archivo |
| GitHub visibility | Not stated in the local docs. `README.md` and `CLAUDE.md` call the Vercel demo link private. That is not a statement about the GitHub repo |

Git identities on `--all` (shortlog, lane A): `haitham72 <ihisam@outlook.com>` 74, `haitham72 <ihisam@Outlook.com>` 26, `Haitham <system722@gmail.com>` 25, `Claude <noreply@anthropic.com>` 8 (author and committer), `haitham72 <59456439+haitham72@users.noreply.github.com>` 5, `Haitham Mohamed <ihisam@outlook.com>` 3, `Vercel <vercel[bot]@users.noreply.github.com>` 1. Trailers: 45 `Co-Authored-By: Claude Opus 5.5`, and one Cursor trailer on `3145409d532a2c4026abf79c17df7e7b0a3f8d94`.

No commit message in the four named docs uses the words employer, NDA, or work-product. “client” in those docs means API client.

## Evidence per area

“Git author” means only who the commit records.

| Area | What the history shows | Still open |
|---|---|---|
| `src/` (138 files) | Earliest foundation commit, Haitham `<system722@gmail.com>`. Latest is HEAD, Haitham Mohamed `<ihisam@outlook.com>`. 76 commits. Authors are the personal identities above, plus 3 Claude and 1 Vercel | Whether `system722@gmail.com` is the founder’s personal account. Diwan/Nadi UI is wired from here (`CLAUDE.md`) |
| `api/` (11) | 8 commits, 2026-10-06 to 2026-10-11, only `haitham72` outlook addresses | Legal title |
| `agents/` (78) | Earliest `662217265b804b68ad723a178aa85fc7ac67fd85` 2026-10-08, authored by Claude `<noreply@anthropic.com>`. Latest 2026-10-15, `haitham72`. 13 commits: personal accounts plus 3 Claude | No grant for the Claude-authored first version. Diwan and Nadi connectors live here. `ARCHITECTURE.md:87`: the events backend is the separate Diwan project, formerly Diwan Hamdan. `agents/README.md`: Nadi is a demo HR connector and “no real HR system is called”. `ai_cleaner_engine.py` cites `remove-ai-watermarks v0.45.1` and has no copyright header |
| `server/` (5) | Foundation commit through 2026-10-11. `CLAUDE.md` calls `server/` the retired Python API. Authors: `haitham72` and `system722@gmail.com` | Same `system722` question |
| `design/` (9) | One commit, 2026-10-06, `haitham72 <ihisam@Outlook.com>`, `design/ios/*` | HTML hotlinks Unsplash. Unsplash is not founder-owned |
| `media/` (3) | Same 2026-10-06 commit. Three mp4s: desert highway, beach, skyline. Docs call them bundled Kling clips, generated once | Which account generated them, and whether they may be copied |
| `Slides/` (20) | Foundation commit only, Haitham `<system722@gmail.com>`. JPGs plus `output_grid/output_grid_1..4.jpg` | `Mirsal-redesign.md:8`: “15 selected concept images supplied in the final contact sheets.” `:1321`: “The supplied four contact sheets.” Supplier is unnamed |
| `screens/` (21) | Added 2026-10-06 by `haitham72`, Cursor co-author on `3145409d`, message “add run notes plus reference screens” | Filenames include `GPT design/`, `Layer *.jpg`, `dynamic island/`, `flighty-dynamic-island.webp`. Docs do not say who made them |
| `public/` (143) | Logo commit `fb13b2fa` 2026-10-05, `haitham72`, “Use the Mirsal orb logo”. Latest 2026-10-08 | See brand, Diwan images, photos, stickers |
| Brand | Product name from the foundation commit (`package.json` `"name": "mirsal-poc"`). `public/mirsal-logo.png` and `public/favicon.png` added only in `fb13b2fa`. The message says they are cut-outs of `Slides/mirsal-logo.png`. That path is not in HEAD | No trademark or assignment file. The named source PNG is not in git |
| Diwan images | Six JPGs under `public/diwan/rashid-bin-saeed-anniversary/`, commit `930a69d6`. `diwan_demo.json:2`: “2026 commemoration posts supplied by Haitham” and “variations Diwan already holds”. `ARCHITECTURE.md:156`: “Mirsal never makes pictures: it asks Diwan for the ones it already has.” | Who holds the pictures, and a yes or no on copying them |
| Photos | 97 JPGs in `public/photos/`, one commit `9fecf2fe` 2026-10-06, message “97 images in public/photos (Vercel CDN)” | No source and no licence |
| Stickers | 32 SVGs and four packs (`nile-days`, `office-mood`, `wheels-up`, `yalla`), only commit `d5b66074`, authored by Claude. `office-mood` is a pack title. `ARCHITECTURE.md` also points at a separate Mirsal Builder library | Whether the SVGs are original, Builder exports, or generated |
| `pytest-of-h.ibrahim/` | One commit, 2026-10-15, `haitham72`. Pytest temp images. The string `h.ibrahim` appears as that directory name only | Whose machine account that is |

## What the founder must confirm in writing

A git email is not enough. Each line is a separate confirmation.

1. `haitham72`, Haitham Mohamed, `<ihisam@outlook.com>`, and the 25 commits by Haitham `<system722@gmail.com>` are the founder’s own personal work.
2. The 8 commits authored by Claude, the 45 Claude co-author trailers, and the Cursor trailer on `3145409d` were made at the founder’s direction on the founder’s own project, and the founder has the rights to reuse that output.
3. The Vercel bot commit is the founder’s own Vercel project.
4. No employer, client, Diwan project, or Nadi system owns the POC code, the name Mirsal, or the orb logo.
5. Who supplied the 15 concept images, the four contact sheets, and the `screens/` files, and that they are not a client’s, a designer’s, or another third party’s.
6. Who supplied the six Diwan commemoration images, and a clear yes or no on copying them.
7. Source and redistribution rights for the 97 `public/photos/` files.
8. The three Kling clips were generated on the founder’s own account and may be copied.
9. The four sticker packs are original, and are not Mirsal Builder or other third-party artwork.
10. `pytest-of-h.ibrahim` is the founder’s own machine account, or a written explanation of whose it is.
11. Diwan (formerly Diwan Hamdan) and Nadi are outside systems the founder may name, and the demo fixtures are not confidential client or workplace data.
12. The founder is allowed to copy from `github.com/haitham72/Mirsal-redesign` into another repository, and under which licence. There is no project licence today.

Third-party notices stay under their own terms and are not founder-original: Unsplash hotlinks, Lucide, the OFL fonts, `remove-ai-watermarks`, and the pdoom MIT file.

## Contest eligibility

The organizer requires an original AI agent and restricts taking it from an existing repository. Existing businesses may propose a new capability. The public wording leaves the eligibility of this exact prototype-reuse path open. Ask the founder to obtain written organizer clarification before an import is approved. Any history-preserving import also needs rights clearance for historical material, including assets deleted at HEAD. [Official Participation rules](https://www.dubaichambers.com/en/web/dubai-chamber-of-digital-economy/create-ai-agents)

## What would change the recommendation

- **To reuse:** a written assignment or licence covering the code, the name, the logo, and every asset class above, plus a statement that `system722@gmail.com` and `h.ibrahim` are the founder’s own accounts and that Diwan and Nadi material is cleared or excluded. The import, if the founder then says reuse, is `git subtree add --prefix=apps/mirsal https://github.com/haitham72/Mirsal-redesign master`, keeping history. This plan does not run that command.
- **To no-go:** neither authorized reuse nor a separately authored, eligible clean-room submission is possible. If documentary evidence identifies an employer- or client-owned area, exclude it from the clean-room brief and require written rights for any proposed reuse.

## What this file does not decide

The test rerun and the working/mock classification are `audit.md`. They do not change M0. Public visibility on GitHub, if the repo is public, would still not prove ownership.
