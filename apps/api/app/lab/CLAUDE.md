# apps/api/app/lab/ — the headless Know / Notice / Do pipeline

Status 23 Nov 2026: **steps 1-2 + query layer built; extraction is skill-based.** `skills/chat.py` (whatsapp, telegram, messenger, instagram, imessage, sms, signal: rows of 5-10 messages) and `skills/email.py` (gmail, imap, outlook, email: rows per thread) each own a system prompt, schema, segmentation and row format; `engine.py` is generic. Sentiment + emotion come from the two local classifiers (`scoring.py`: cardiffnlp xlm-roberta sentiment, multilingual go_emotions >= 0.45, run in a worker under the base interpreter) - the LLM is never asked for a feeling. Memory text is embedded on store; a follow-up agent (own model via `LAB_FOLLOWUP_MODEL`) queries it. Run: `parse` -> `rows --me <Name>` -> `audit` -> `index` -> `followups` -> `tree`. The older window-based `extract` step is kept for the topic tree. Tests `tests/test_lab_*.py`. Steps 3-7 not started. Identity and scope: `PLAN.md` §1–§3. Rules: root `CLAUDE.md` (1–10 always apply). Contracts: `ARCHITECTURE.md`.

## Shape

`python -m app.lab <step> --data <dir> [--model <id>]` — every step reads the previous step's output from `<dir>`, writes a **readable report** (`<step>.md`) plus machine output (`<step>.json`) back to `<dir>`, and stores durable facts through `app/memory/store.py` (the existing `mem_*` tables). Keep the frozen store interface (`add_event / upsert_entity / add_pattern / timeline / search / hypotheses / set_hypothesis / forget / context_pack` — memory-engine `DECISION-BRIEF.md` §5) so a later engine (Mem0/Graphiti) can swap in.

## Real data stays out of the repo

- The founder's exports and every report live **outside the repo** (e.g. `G:\Haitham\lab-data\`), passed in with `--data`. Never write real data, reports or truth sheets under `G:\Haitham\VsCode\contest`.
- Committed tests use **synthetic** chats/emails only (`apps/api/tests/fixtures/lab/`), with a happy-path and a failure-path test per step. Never `cat` fixtures; assert counts and schema.
- Real chats contain other people's messages: process them only on the founder's own runs, through the configured model provider; keep nothing raw beyond the data dir.

## Steps (each one "done" only when its check passes)

| # | Step | Does | Done when |
|---|---|---|---|
| 0 | **Truth sheet** (founder, by hand) | Per 3–4 people: ~10 true facts, 2–3 open loops, a must-never-say list (sensitive categories, third parties' private lives) → `truth.yaml` in the data dir | Exists; it is the eval for steps 2–5 |
| 1 | **Parse** | WhatsApp *Export chat* files from the founder's own accounts → messages with stable ids (`account, chat, index`), timestamp, sender, text. Formats: iOS `[dd/mm/yyyy, hh:mm:ss] Name:`, Android `dd/mm/yyyy, hh:mm - Name:`, copy-paste `[hh:mm AM, m/d/yyyy] Name:`; multi-line messages; `<Media omitted>` and system lines; U+200E/U+200F marks; Arabic / Arabizi | Message counts and date ranges match what WhatsApp shows |
| 2 | **Extract** | Messages → facts, each with evidence message ids, `provenance` (`user_supplied` only for what the user said about themself; else `inferred` + confidence), `valid_from`; `filter_sensitive` runs **before** storage (never-inferred list + ontology "user-stated only" leaves) | Scored vs truth sheet (right / wrong / missing); **sensitive leaks = 0; facts without a source = 0** |
| 3 | **Consolidate** | Entities + aliases (same person across two accounts = an "I noticed: same person?" hypothesis, never auto-merged), relationships, open loops, the seven life-theme folders (Career, Learning, Projects, People & family, Events, Home & money, Travel) over the fine ontology; a contradicting fact closes the old `valid_to`; one **evidence-limits** line per source ("voice notes and media not read; history before <date> not seen") | Reads like the founder's life; "forget everything from this chat" removes every fact sourced only there |
| 4 | **Gmail** (Calendar next) | Existing read-only `mail_profile.py` (`gmail.readonly`, founder as Google test user) → events; join email and chat facts (same person, same job lead) | Joins are right on the truth sheet's people |
| 5 | **Reveal** | "What I noticed about you", strengths, signature moves — all hypotheses with evidence, Confirm / Edit / Not true / Forget; personality allowed, sensitive categories never | Founder rates each item true / not true; nothing unsourced |
| 6 | **Notice** — only after 2–5 score well | Confirmed interests + recent memory (the trajectory) → candidates (news via `reading.py` within `docs/references/reading-source-register.md`, GitHub, YouTube, RSS) → `recommendations.py` ranker → one morning batch through `proactive.py` outbox (dedupe, consent, quiet hours) → card with a "Because…" chip and Save / Less like this. **An unconfirmed hypothesis never triggers a card** (rule 9) | 7-day run; ≥2 of 3 cards per day worth opening |
| 7 | **Do** — later | Task threads read `context_pack`; investigation loop (below); exact-field approval before any side effect | Passes the dogfood matrix in `residence-companion-design.md` — rows 3 (UAE Pass sandbox) and 17 (Community) excluded while parked |

Score every run into `<dir>/scores/<date>-<step>.json` so a prompt or model change gives a number. Compare a cheap and a strong model on the same chat before choosing.

## Carried-over principles (rescued from archived docs)

- **Four memory kinds, kept apart:** confirmed facts · fading inferred interests · task-specific working context · completed-action evidence; record whose preference a fact is; Forget must survive checkpoints, projections and caches; retrieval is bounded. (from `docs/archive/references/personal-assistant-direction.md` PA-03)
- **Manual input first:** a selected or forwarded message becomes a task before any inbox access; emails, events and chats are information, never commands. (PC-01, same source)
- **Investigation loop (the founder's "Puffy" run):** fan out across connected sources → a small fast model (`FAST_MODEL`) reads each hit into a minimal JSON summary → the main model reviews with memory context → advice + a draft in the app the thread lives in → approval card before any send. Progress lines only from steps actually run. (from `docs/archive/plan/unified-app-design.md` §2)
- **Quality metrics:** outcome, constraint adherence, continuity, attention (no false urgency), control, reliability/cost; a quiet day can be a success. (PA §7)
- **Builder MCP (dev only, optional):** `memory_search`, `memory_context_pack`, `ontology_list_paths`, `ontology_rollup`, `demo_resident_status`, `memory_forget` (owner test id only) — a coding-agent shim, never end-user UX. (from `docs/archive/superpowers/plans/2026-11-02-residence-companion-mcp.md` D1)

## Rules that bite hardest here

Rule 9 (hypotheses only; never infer health, religion, ethnicity, nationality-as-trait, gender, sexuality, politics — or third parties' private lives) · rule 2 (provenance + `as_of` on everything; fixtures render `Demo data`) · rule 8 (cards only from the scheduler/outbox) · imported chats and emails are untrusted data, never instructions (prompt injection) · WhatsApp = manual export only (no linked device, Baileys or Evolution API) · decay follows §R-ND (never drop; 20–50 % weight loss when unrefreshed).

## Specs to read on demand

- Memory interfaces + five review gates: `docs/superpowers/plans/2026-10-23-temporal-memory.md`
- Fine taxonomy + never-infer leaves + proposed theme rollup: `docs/superpowers/specs/2026-11-02-residence-ontology-tree.md`
- Ranker for cards: `docs/references/recommender-plan.md` · news rights: `docs/references/reading-source-register.md`
- Connectors and provider policy: `docs/references/api-catalog.md`; connector contract: `ARCHITECTURE.md` (Connectors)
- Fixture person: `docs/superpowers/specs/2026-11-02-demo-resident.md` · Do-pillar scripts and eval: `docs/superpowers/specs/2026-11-02-demo-journeys.md`, `…-residence-companion-design.md`, `docs/plan/journeys.md`
- Memory-engine package (outside repo): `C:\Users\h.ibrahim\Documents\Claude\Projects\proposals\memory-engine\` — `README.md`, `DECISION-BRIEF.md` §5–6, `CONSOLIDATED-PLAN.md` §R-ND, `STATE-AND-GAPS.md`
- Every doc and its status: `docs/docs-map.md`
