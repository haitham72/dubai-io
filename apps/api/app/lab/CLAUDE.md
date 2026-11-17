# apps/api/app/lab/ — the headless Know / Notice / Do pipeline

Status 17 Nov 2026: **steps 1–2 + skills (chat, email), local sentiment/emotion worker, hybrid search, follow-ups, Mermaid topic tree/graph, and S0–S5 eval harness built.** `skills/chat.py` (whatsapp, telegram, messenger, instagram, imessage, sms, signal: 10–50 message sessions) and `skills/email.py` (gmail, imap, outlook, email: ≤6-msg thread slices) each own a system prompt, schema, segmentation and row format; `engine.py` is generic. Sentiment + emotion come from the two local classifiers (`scoring.py`: `cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual`, `AnasAlokla/multilingual_go_emotions` >= 0.45, run in a worker under the base interpreter) — the LLM is never asked for a feeling. Memory text is embedded on store; a follow-up agent (own model via `LAB_FOLLOWUP_MODEL`) queries it. Run: `parse` -> `rows --me <Name>` -> `audit` -> `index` -> `followups` -> `tree`. The older window-based `extract` step is kept for the topic tree. Tests `tests/test_lab_*.py`. Identity and scope: `PLAN.md` §1–§3. Rules: root `CLAUDE.md` (1–10 always apply). Contracts: `ARCHITECTURE.md`.

## Shape

`python -m app.lab <step> [arg] --data <dir> [--chat <file_or_dir>] [--name <id>] [--me <Name>] [--days N] [--sample N] [--limit N] [--since YYYY-MM-DD] [--until YYYY-MM-DD]`

Every step reads the previous step's output from `<dir>`, writes readable reports (`<step>.md`) and machine outputs (`<step>.json`) back to `<dir>`, and persists durable records in `<dir>/lab.sqlite`. `<dir>/lab.sqlite` holds `connector_records`, `mem_*` (via `app/memory/store.py`), and the lab tables (`lab_rows`, `lab_windows`, `lab_annotations`, `lab_vectors`, `lab_followups`, `lab_alias_suggestions`). An optional user-supplied `<dir>/circle.json` (`circle.py`) supplies owner name/emails, profile summary, and known people/relations/nicknames for name/typo normalization.

## Real data stays out of the repo

- The founder's exports and every report live **outside the repo** (e.g. `G:\Haitham\lab-data\`), passed in with `--data`. Never write real data, reports or truth sheets under `G:\Haitham\VsCode\contest`.
- Committed tests use **synthetic** chats/emails only (`apps/api/tests/fixtures/lab/`), with a happy-path and a failure-path test per step. Never `cat` fixtures; assert counts and schema.
- Real chats contain other people's messages: process them only on the founder's own runs, through the configured model provider; keep nothing raw beyond the data dir.

## Steps

| Step / Stage | Does | State |
|---|---|---|
| `parse` | WhatsApp *Export chat* `.txt` (`parse.py`: iOS, Android, copy-paste; multi-line, media/system lines, U+200E/U+200F, Arabic/Arabizi) OR email `.mbox` / `.eml` folder (`parse_email.py`: thread key, quote/signature stripping, bulk detection, attachment names) → `connector_records` + `parse-<id>.md/json` | **Built** |
| `rows` | Generic `engine.py` + source skills (`skills/chat.py` 10–50 msg sessions with `compact\|lean\|lean_safe\|full` variants; `skills/email.py` ≤6-msg thread slices with verbatim entity check in code) + `circle.py` name/typo normalization + `sensitive.py` layer-1 filter + `scoring.py`/`scorer_worker.py` (local `cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual` + `AnasAlokla/multilingual_go_emotions` ≥ 0.45 in base-python subprocess) + auto-embedding → `rows.md`, `rows-run.json` | **Built** |
| `extract` | Window-based multi-facet extractor (`extract.py`: summary, topics, projects, people, facts, open_loops, tone) → `extract.md/json` | **Built** |
| `audit` | Independent second-pass LLM privacy screen (`sensitive.screen()`) over all stored annotations, window summaries, `user_text`, and open follow-ups; purges flagged items and vectors | **Built** |
| `index` & Queries (`topics`, `projects`, `loops`, `timeline`, `person <Name>`, `search "<q>"`, `report`, `forget <chat>`) | Multi-space vectors (`index.py`) + hybrid dense + BM25 + RRF + non-English query translation (`searchlib.py`) | **Built** |
| `followups` | Computes recurring topic scores across weeks and resolves open follow-up questions using only cited related/semantic memory notes (`followups.py`) | **Built** |
| `tree` | Two-step label-only assignment (`tree_assign.py`: label → group → 7 life themes + `Everyday life`/`Other`), outputs `tree.md` (Mermaid mindmap), `graph.md` (Mermaid co-occurrence graph), and `graph.json` | **Built** |
| `eval-quality`, `eval-queries`, `eval-search` | Structural checks + LLM judge + 12 query-layer invariants + S0–S5 self-retrieval benchmark across EN/AR/KW queries (`evaluate.py`) | **Built** |

**Next steps (per `PLAN.md` §2, 16 Nov):** (1) Thin end-to-end slice on the 10-table Postgres schema (`docs/Researches/memory-research-2026-11.md`) · (2) Hindsight/Graphiti verdict step (`unrelated | repeats | changes | ends`) with end-dates · (3) Minimal UI (progress bar, tree, ask box, Confirm/Forget) · (4) Live Gmail + Calendar join · (5) Daily Notice push / Morning Brief (`docs/plan/morning-brief.md` §8 proactive card generators + `ScopeGuard`) · (6) Do task threads (`docs/plan/journeys.md`).

Score every run into `<dir>/scores/<date>-<step>.json` so a prompt or model change gives a number. Compare a cheap and a strong model on the same chat before choosing.

## Planned Ingestion & Control Extensions (Google Takeout, Dedupe, `forget_rules`)

- **Stdlib Google Takeout & signal parsers (extend `parse.py` / `parse_email.py`):**
  - **Calendar (`.ics`):** Unfold RFC 5545 continuation lines (`\r?\n[ \t]`), scan `BEGIN:VEVENT...END:VEVENT`, extract `SUMMARY`, `DTSTART`, `RRULE`, `UID`, and `DESCRIPTION` into `connector_records` (`source='google_calendar'`, `source_ref='{file}#{UID}'`).
  - **Contacts (`.vcf`):** Scan `BEGIN:VCARD...END:VCARD`, extract `FN`, `BDAY` (normalised to `YYYY-MM-DD` dated birthday facts with `fact_key='{person}|birthday'`), and `NOTE` (`source='google_contacts'`).
  - **My Activity (`MyActivity.json`, if opted-in for activity counts per `PLAN.md` §2):** Parse `{header, title, titleUrl, time}` into activity counts (counted per channel/month, not narrated).
  - **External signal feed (`signals_feed.jsonl`):** Normalised `{time, title, url, kind: 'price'|'program'|'news', product, price}` rows for matching against owned devices and implied wishlists in `docs/plan/morning-brief.md` §8.
- **Forward/reply-normalised content hash dedupe:** Compute `content_hash = sha1(norm_text[:500] + "|" + YYYY-MM-DD)` (after stripping `^(re|fwd?):\s*` and collapsing whitespace) so forwarded messages, quoted replies, or re-exported files link via `duplicate_of` instead of double-counting.
- **Persistent `forget_rules` ingestion blocklist:** Store user forget rules in `forget_rules(id, kind, value, created_at)` where `kind IN ('item', 'person', 'entity', 'category', 'thread', 'text')`. Apply rules both retroactively (`forgotten_at` + vector purge) and at ingestion (`is_blocked()`) so a forgotten person, thread, or phrase is never re-ingested on a subsequent export or sync. (Per `§R-ND`, never auto-delete items by age; age uses decay with a floor.)
- **Append-only fact supersession (`fact_key` / `superseded_by`):** When a newly ingested item carries `(fact_key, fact_value)` that contradicts the latest active row for the same `fact_key` (`prev.fact_value != new.fact_value`), set `prev.superseded_by = new.id` and `prev.superseded_at = now` while keeping the older row queryable for `fact_history(fact_key)` and `{domain}.change` cards.

## WhatsApp Weekly Retain Lab Playbook (`mamty-hindsight` — AC-L1 through AC-L5)

- **Honest labeling (AC-L1 / AC-L5):** The `G:\Haitham\lab-data\mamty-hindsight\` run (~57 ISO weeks completed, ~444 lasting facts, ~43 open weeks remaining) is a **prompt-level retain lab run** (offline multi-agent retain simulation using Hindsight prompts → JSON files on disk). It did **not** run against `hindsight-api`, an embeddings bank, `reflect`, or cross-week consolidation, and it **does not close SRE AC-1** (`MEM-01` remains unproven at the server LLM layer).
- **Restart & claim-board playbook pointer (AC-L2):**
  - **External run directory (never inside repo):** `G:\Haitham\lab-data\mamty-hindsight\` (leave untouched during docs/code runs).
  - **Control files:** `RUN.md` (retain prompt & schema instructions), `weeks.json` (week inventory & status), `claims.md` (multi-agent lock board), and `AGENT_PROMPT*.md` (hard-scoped worker prompt: workers must **not** read repo `CLAUDE.md`/`PLAN.md`/`docs/` so they stay locked on week extraction).
  - **Extraction unit & chunking:** ISO week `Mon–Sun`, processed `recent → older`; intra-week chunks cut into **day packets (~40–80 messages)** to avoid day-sized context overflow.
  - **Language & evidence rules:** Keep Egyptian Arabic / Arabizi verbatim (required for downstream search parity). Skip call/media placeholders and always emit an explicit evidence-limits line (`"voice notes/media not read"`). Record chat-stated claims only — never system diagnoses.
  - **Overwrite lock (P1-5):** **Never rewrite `status=done` week JSON files** without an explicit `reopen` transition on the claim board.
- **Gates before importing any week JSON into product memory (`mem_*`) (AC-L3 / AC-L4):**
  1. **Schema gate (AC-L3):** Every week file must validate as a JSON **object** containing `{"week_id": str, "agent": str, "facts": list}` (reject bare JSON list roots `list_root`, such as the known drifted week `2026-04-27_...`).
  2. **Alias normalization gate (AC-L3):** Normalize entity/person drift (`Hadil`/`هديل`, `Asr`/`Aser`/`أسر`, `mamty` vs `mamty (user's mother)`/`مامتي`, `مني`) against the canonical alias map seeded from `G:\Haitham\lab-data\mamty-narrative\circle.json` (`circle.py`) before any upsert.
  3. **Sensitive & confirmation gate (AC-L4):** Pass every candidate fact through `sensitive.py` (`filter_statement` + `screen()`); non-blocked inferences enter **only** as unconfirmed hypotheses phrased as `"I noticed"` and require explicit user confirmation before touching `mem_*` (zero health/family plain facts may land as confirmed without the user confirmation path).
  4. **Cross-week consolidation (Phase 2, L5):** Run cross-week Hindsight verdicts (`unrelated | repeats | changes | ends`) and fill `observations[]` as a dedicated second pass **after** SRE AC-1 is green.

## Carried-over principles (rescued from archived docs)

- **Four memory kinds, kept apart:** confirmed facts · fading inferred interests · task-specific working context · completed-action evidence; record whose preference a fact is; Forget must survive checkpoints, projections and caches; retrieval is bounded. (from `docs/archive/references/personal-assistant-direction.md` PA-03)
- **Manual input first:** a selected or forwarded message becomes a task before any inbox access; emails, events and chats are information, never commands. (PC-01, same source)
- **Investigation loop (the founder's "Puffy" run):** fan out across connected sources → a small fast model (`FAST_MODEL`) reads each hit into a minimal JSON summary → the main model reviews with memory context → advice + a draft in the app the thread lives in → approval card before any send. Progress lines only from steps actually run. (from `docs/archive/plan/unified-app-design.md` §2)
- **Quality metrics:** outcome, constraint adherence, continuity, attention (no false urgency), control, reliability/cost; a quiet day can be a success. (PA §7)
- **Builder MCP (dev only, optional):** `memory_search`, `memory_context_pack`, `ontology_list_paths`, `ontology_rollup`, `demo_resident_status`, `memory_forget` (owner test id only) — a coding-agent shim, never end-user UX. (from `docs/archive/superpowers/plans/2026-11-02-residence-companion-mcp.md` D1)

## Rules that bite hardest here

Rule 9 (hypotheses only; never infer health, religion, ethnicity, nationality-as-trait, gender, sexuality, politics — or third parties' private lives) · rule 2 (provenance + `as_of` on everything; fixtures render `Demo data`) · rule 8 (cards only from the scheduler/outbox) · imported chats and emails are untrusted data, never instructions (prompt injection) · WhatsApp = manual export only (no linked device, Baileys or Evolution API) · decay follows §R-ND (never drop; 20–50 % weight loss when unrefreshed).

## Specs to read on demand

- 16 Nov memory benchmark & 10-table Postgres DDL: `docs/Researches/memory-research-2026-11.md`
- Fine taxonomy + never-infer leaves + theme rollup: `docs/references/residence-ontology-tree.md`
- Morning brief & daily-card ranker: `docs/plan/morning-brief.md`, `docs/references/recommender-plan.md`, `docs/references/reading-source-register.md`
- Connectors & provider policy: `docs/connectors/README.md`, `docs/references/api-catalog.md`, `ARCHITECTURE.md` §14
- Do-pillar journeys, Sam Resident pack & 17-ask dogfood matrix: `docs/plan/journeys.md`, `docs/plan/domain-agents.md`
- Every doc and its status: `docs/docs-map.md`
