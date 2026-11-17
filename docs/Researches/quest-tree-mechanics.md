# Quest memory: the md tree, how it is grabbed, how it updates

Source: `quest-memory-export/` (36 md files, untouched) and `quest-memory-export.zip`. Quest's own code is not public; everything below is read from the export or marked as the way we do it.

## 1. The full md tree Quest created

```
quest-memory-export/
├── USER.md                                  profile of the user (Identity, Personality, Values, Strengths & Tensions, Interests, Drive, Relationships)
├── MEMORIES.md                              index: ## Category, then - [Title](path) — one-line description
└── memories/
    ├── background/   location-and-faith.md        Location, heritage and faith
    ├── devices/      devices.md                   Devices
    ├── family/       family-context.md            Family context (sensitive)
    ├── health/       medical-and-dental.md        Medical and dental care
    ├── identity/     name-and-handle.md           Name and online handle
    ├── interests/    ai-tinkerers-dubai.md        AI Tinkerers Dubai interest
    │                 gaming-and-vr.md             Gaming and VR
    │                 generative-ai-video.md       Generative AI video (ComfyUI)
    ├── learning/     ai-ml-program.md             AI/ML learning program (2025–2026)
    │                 tech-education-history.md    Tech education history
    ├── lifestyle/    shopping-and-food.md         Shopping and food delivery
    ├── people/       abdelaziz.md  albin-xavier.md  brandon-hh.md  daanish.md  era.md  hadeel.md
    │                 islam-mohamed.md  khalo.md  macky.md  mamty.md  radwa-arafa.md          (one file per person)
    ├── projects/     arabic-poetry.md             Arabic poetry repos
    │                 claude-cowork.md             Claude Cowork (personal AI environment)
    │                 dubai-io.md                  Dubai IO (AI contest project)
    │                 mirsal.md                    Mirsal
    │                 prayer-tracker-app.md        Prayer-tracking app
    │                 regulense.md                 ReguLense
    │                 semantic-cache-experiment.md Semantic-cache experiment (unnamed)
    │                 tourism-package-prediction.md Tourism Package Prediction (GitHub)
    ├── wellbeing/    current-state-2026-11-06.md  Current state snapshot (2026-11-06)
    └── work/         ai-dev-tools.md              AI builder tools and subscriptions
                      ai-engineering-job-search.md AI engineering job search (2026)
                      design-3d-animation.md       Design / 3D / animation background
```

12 categories, 34 memory files plus `USER.md` and `MEMORIES.md`.

### File shapes

**Memory file** (`memories/<category>/<topic>.md`): a frontmatter block, then one bullet per fact.
```
---
name: Devices
description: one line, the same text the index shows
---
- fact, dated to the day, with where it was seen
- another fact
```

**Person file** (`memories/people/<name>.md`): the same, plus `relationship` (family, close friends), `closeness` (closest, close), `avatar`, `sources` (whatsapp) and `identities` (source/account/contact id). Bullets are dated facts and the file ends with an evidence-limits line (what was not read).

**MEMORIES.md**: `# Memories`, then one `## Category` per folder, then `- [Title](path) — description` per file.

**USER.md**: the profile in seven sections; every claim names the memory file it came from, for example `(memories/work/ai-engineering-job-search.md)`.

### How the facts are written
- One short bullet per fact, dated ("2026-10-12", "observed Sep–Nov 2026").
- The source comes first when a file has one ("From Quest chat on 2026-11-06", "Source: onboarding assessment").
- Anything uncertain says so: likely, probably, unconfirmed, unknown.
- Quotes stay in the original language with an English gloss.
- Counts are computed ("~980 messages in 57 days").
- People files end with what was not read ("182 voice notes and media not reviewed; history before 2026-09-10 not seen").

## 2. How it is grabbed

**What Quest reads** (from its privacy policy): Gmail (read-only, an index of senders, subjects and previews, not bodies), Google Calendar, Drive, Apple Health and location (opt-in), WhatsApp / Messenger / Instagram / TikTok through a cloud phone it controls, uploaded exports (Google Takeout, ChatGPT, Claude), a one-time import of YouTube history and Maps saved places, a public-web lookup by name and email, and voice notes (transcribed). It also talks to the user: the onboarding conversation is a source too.

**How you get the result out of Quest** (observed in this folder):
- the export: `quest-memory-export.zip`, which unzips to the tree above;
- asking Quest in chat: it answered with the same material as messages, each starting with its source and read date ("From Google Calendar (read 2026-11-06)").

**How we grab the same material:**
1. Import each source as records: WhatsApp export text, email mbox or Gmail read-only, YouTube history from Google Takeout, Instagram analytics export.
2. Cut the records into chunks, send each chunk to the model, and get back the memories in it: topic, people, short narrative, questions about anything vague.
3. Route every memory to a file of the tree (section 3) and write it as a dated bullet.
4. Build `MEMORIES.md` from the files' names and descriptions, and `USER.md` from the files.

## 3. When new input arrives: route, then new / update / delete

```
[new message]  ->  routed to health  ->  new | update | delete  (in memories/health/medical-and-dental.md)
```

### Step by step
1. **Route.** Show the model the index (`MEMORIES.md`: every title and description) and the new input. It answers which file(s) the input belongs to, or that a new file is needed. A person mentioned goes to `people/<name>.md`, found by the identities and nicknames in the person files.
2. **Load only those files.** Open the routed files (frontmatter and bullets). Nothing else is read, so a new message costs one or two small files.
3. **Decide per fact**, comparing the input with the file's bullets:

| Operation | When | Effect |
|---|---|---|
| **new** | the fact is not in the file | append a dated bullet |
| **update** | the fact changes or refines a bullet | rewrite that bullet; keep the older date in the text if it matters |
| **delete** | the input retracts or contradicts a bullet | remove the bullet |
| **none** | already known, or nothing lasting | change nothing |

4. **Write.**
   - Edit the file.
   - If the file is new, create it with `name` and `description` and add its line to `MEMORIES.md`.
   - If a file's meaning changed, refresh its `description` in the index.
5. **Refresh `USER.md`** from the changed files, in batches (after a set of updates or on a schedule), not on every message.

### What the model returns
```
{"route": [{"file": "health/medical-and-dental", "new_file": false}],
 "ops":   [{"op": "new",    "file": "health/medical-and-dental", "bullet": "Started braces on 2026-11-16 (said in chat)"},
           {"op": "update", "file": "health/medical-and-dental", "bullet_no": 2, "bullet": "Dentist visit moved to 2026-12-02"},
           {"op": "delete", "file": "health/medical-and-dental", "bullet_no": 3}]}
```

### The export already shows incremental updates
- `projects/dubai-io.md` grows by dated bullets (2026-11-06, 2026-11-07, 2026-11-15). An older bullet gets a pointer to the later one ("see 2026-11-15 update below"): a correction made by adding a dated bullet and annotating the old one.
- `people/islam-mohamed.md` carries the evidence-limits line, which moves as more history is read.
- `wellbeing/current-state-2026-11-06.md` is a dated snapshot, replaced by a new dated file instead of edited.
