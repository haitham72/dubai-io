# Memory extraction research: comparison, merged design, order of work

Research input, **not the plan of record**: decisions are in `PLAN.md` section 2 (16 Nov 2026). Written 16 Nov 2026 with a local qwen3.5-9b and Haiku simulations. Raw results and the chat they were run on stay outside the repo (`G:\Haitham\lab-data\comparison\`); this file quotes no chat content.

## Part 1. Extraction comparison: Mem0, Graphiti, Hindsight, a Quest-style tree and the founder's prompt

Input: one WhatsApp chat with a family member from 14 Nov 08:11:42 to 16 Nov, three episodes (one per day: 67, 86 and 4 messages). Each method ran twice: **for real** on the local qwen3.5-9b (LM Studio), and **as a simulation** by Haiku acting as that method's LLM (nothing executed, it picked "closest existing memories" by judgment). Numbers are in `results/` and `results_haiku/`; `STATUS.md` maps the files.

### 1. What is real and what is not

- **Real:** the prompts of Mem0 (v3 add-only and the older v2 two-step), Graphiti 0.31.2 and Hindsight (current code), taken from the installed packages or the repo. Quest's actual exported files were the starting memory for the tree router.
- **Not real:** each project's storage and candidate retrieval (in-memory lists and embeddings from LM Studio instead). The Quest-style router uses prompts I wrote from `quest.md`; it shows what that design does on a 9B model, not what Quest does. The Haiku runs are simulations.
- **Sample:** 3 days, one chat. One genuine state change exists in the data (a project goes from in progress to finished on 15 Nov). Treat everything below as behaviour seen once, not a benchmark.

### 2. Numbers

| Method | Local 9B: items / time / calls (failed) | Haiku simulation: items |
|---|---|---|
| Your prompt (one JSON row per episode) | 3 rows / 32 s / 3 (0) | 1 row (2 of 3 empty) |
| Quest-style tree router | 28 ops (24 new, 4 update) / 116 s / 10 (0) | 22 ops (21 new, 1 update) |
| Mem0 v3 (add-only, linked) | 11 memories, 1 link / 126 s / 3 (**1 failed**) | 26 memories, 9 links |
| Mem0 v2 (facts, then add / update / delete) | 22 ops: 13 ADD, 9 NONE, **0 UPDATE, 0 DELETE** / 51 s / 6 (0) | not simulated |
| Hindsight (facts, then verdicts) | 24: 21 new, 3 "changes" / 272 s / 6 (0) | 27: 26 new, 1 repeats, **1 ends** |
| Graphiti (entities + facts, dates, contradiction check) | **0 facts** / 294 s / 3 (**2 failed**) | 61 facts, 45 entities, **1 invalidation**, 0 duplicates |

Tokens in / out locally: your prompt 8.4k / 0.65k; Quest-style 26k / 2.5k; Mem0 v3 31k / 2.8k; Mem0 v2 11k / 1.0k; Hindsight 24k / 7.1k; Graphiti 11k / 8.1k.

### 3. What happened, method by method

**Your prompt.** One row per day. Local: day 1 flagged sensitive (empty), day 2 *not* flagged and written with the topic "health", day 3 fine. Haiku flagged both full days and returned empty rows, so nothing at all is kept about 14 and 15 Nov. Two problems show: a whole day is one narrative (you cannot ask "when did X happen"), and one sensitive flag over 67-86 messages blanks everything or nothing, and the 9B applied it inconsistently. It also writes no entities, dates or end dates per fact.

**Mem0 v3.** Rich, dated, English memories ("On 14 Nov 2026 the user's mother ..."), about 38 words each with Haiku, 20 with the 9B. With Haiku, 8 of the 15 day-2 memories link back to day-1 memories (the same story continuing across days). The 9B's second episode (86 messages, 12k prompt tokens) hit the output cap and the JSON was cut off, so day 2 is missing. v3 never ends or overwrites anything: old and new memories sit side by side.

**Mem0 v2.** Four, eight and one facts per day, about 7 words each. The compare step produced only ADD and NONE: no update, no delete (nothing in 3 days truly contradicted). One NONE-matched memory states a wrong family relation, which would then be kept.

**Hindsight.** Short one-sentence memories, no failures locally. The consolidation verdicts did what the project says on Haiku: it found the one real change ("working on the project" ended by "finished the project on 15 Nov 2026") and rewrote the memory in the past tense. The 9B gave three verdicts of "changes" where the text did not change at all, so they are no-ops. Its language rule says keep the source language: Haiku wrote 27 of 27 in Arabic, the 9B wrote English.

**Graphiti.** On Haiku: 61 short facts (about 10 words, Arabic), 45 entities, and one invalidation: the project fact got `invalid_at = 2026-11-15T12:31:36Z` when "finished" arrived. Its conservative prompt did not invalidate two other pairs that only looked related. Locally the 9B wrote until the 4,000-token cap on both full days and the JSON was cut off: zero facts. Graphiti expects short episodes (a message or a few); a whole day was the wrong unit, which is a fault of my test. A rerun with 12-message episodes is in `results/graphiti_small.json` (see the addendum when it finishes).

**Quest-style tree.** Day 1 routed to `people/<family member>` and a health file; day 2 to four files. The 4 "updates" are the same bullet with dated text appended; nothing was deleted. Two defects of my router showed: the 9B returned the path `memories/health/medical-and-dental` (with the folder prefix), which my code treated as a *new* file instead of the existing one, and when a file is rewritten, non-bullet lines (such as a "From Gmail (read ...)" provenance line) are silently dropped. It also filed a family member's health details into a file about the user's own health.

### 4. Findings that matter for the decision

1. **Model strength explains most of the gap.** Same prompts: Mem0 v3 11 vs 26 memories, Graphiti 0 vs 61, Hindsight no real change vs one correct "ends". A 9B model can run these prompts only on small chunks; for a demo, plan on a stronger model.
2. **"Extract everything" prompts overflow on a small model.** Graphiti and Mem0 v3 failed on day-sized inputs. Hindsight did not fail because its first step is selective (skips small talk) and its second step judges one fact at a time.
3. **Invalidation is rare in short spans, and only two methods caught the one case** (Graphiti and Hindsight, both on Haiku). Mem0 v3 cannot; Mem0 v2 returned no update or delete; the tree router only appends.
4. **Links:** Mem0 v3 links memory to memory (9 with Haiku, 1 with the 9B); Graphiti's links are entity edges; Hindsight and your prompt have none. Links showed story continuity, not contradictions.
5. **Sensitive content:** only your prompt has a gate. The other four stored health-related talk about a family member with no filter (crude keyword hits: Quest-style 17 of 28 local ops, Mem0 v3 6 of 11, Mem0 v2 9 of 22, Hindsight 4 of 24; Haiku: Graphiti 14 of 61, Hindsight 8 of 27, Mem0 v3 6 of 26, Quest-style 4 of 22). The counter is a keyword list, not a judgement.
6. **Language:** prompts that say "keep the source language" produce Arabic memories with Haiku and English with the 9B. This decides the language of search; the plan so far is English memories with Arabic names and quotes kept.
7. **Queryability.** Per-fact memories with times (Graphiti, Hindsight, Mem0 v3) can answer "flights over the past years"; a single narrative per day (your prompt) cannot, and a file tree (Quest-style) answers by topic but not by date.

### 5. What this says about direction

- Keep your prompt as the **chunk summary row** (a daily-style overview), but not as the only memory: add per-fact memories with times from a Hindsight-style selective extraction.
- Take **Hindsight's verdict step** (unrelated / repeats / changes / ends) and **Graphiti's end dates**, applied by code; take **Mem0 v3's links** for continuity; use the **Quest tree** as the view. This is the merge in `final-design.md`.
- Use small chunks locally (about 12-30 messages for the exhaustive prompts) or a stronger model; put the sensitive check on messages before extraction, not as one flag per day.
- GraphRAG was not needed for any of the behaviours above.

### 6. Limits of this comparison

Three days, one chat, one real contradiction. The Haiku runs are not independent evidence of what each project achieves; they show what each prompt does with a capable model. The local Graphiti and Mem0 v3 failures are about episode size, not proof that either is weak. The sensitive counter is a keyword list.

### Addendum

Graphiti with 12-message episodes (stopped after 5 of 14 episodes when the local model was shut down): 24 facts from 60 messages, 8 distinct entities, 1 duplicate recognised, 0 contradictions (nothing in that stretch contradicts), 31 model calls, 1 failed. Episode 3 hit the 4,000-token output cap even at 12 messages (141 s), so the 9B can still overflow on a short episode. The one real change in the data (15 Nov) was not reached, so this says nothing about Graphiti's invalidation on the 9B. Not a verdict on Graphiti.

## Part 2. The merged design: one memory service on Postgres

Merges three open-source memory systems (Mem0, Graphiti, Hindsight), the Quest memory tree, GraphRAG's data model, and your temporal_note engine into one Postgres schema and one MCP. Where a claim comes from a source it is named; the run results (real local runs + Haiku simulations) go into a separate report.

### 1. What each contributes

| Source | What we take | What we leave |
|---|---|---|
| **temporal_note** (yours) | Postgres + pgvector read layer; events with `embedding` and `tsv`; hybrid search fused by RRF (`rrf_search`, `search_all`); `entity_relationships.valid_from/valid_to`; `event_entities.role`; ULID identity; advice with `check_in_date`, `confidence`, `decay_rate`; the protocol *context first, draft, approval, write* | single user (every table gets `user_id`); the vault as the write layer |
| **Graphiti** | a fact has `valid_at` / `invalid_at` / `expired_at` and the episodes it came from; a conservative "can both be true?" prompt; code sets the end date | graph database; several LLM calls per fact |
| **Hindsight** | one-sentence memories; per new fact a fixed verdict against its closest memories: `unrelated / repeats / changes / ends` (its own comments: 36–38/40 on small models vs 29/40 for create/update/delete lists); occurrence time vs mention time; skip small talk as "momentary"; fusion of 4 search channels | the confidence-update system from its paper (its code removed opinions) |
| **Mem0 v3** | add-only; each new memory carries `linked_memory_ids` to related existing ones; rich, dated memory text | no invalidation (new and old stay side by side) |
| **Quest** | the tree: sections, topic files, people files, `USER.md` profile; dated hedged bullets; evidence limits; route a new message to a file | files as the store (we use tables) |
| **GraphRAG** | tables `documents, text_units, entities, relationships, communities, community_reports, covariates`; a community report = a written summary of a cluster; `covariates` has `status, start_date, end_date, source_text` (claims with time) | the Leiden pipeline and its cost, for now |

### 2. Generalized schema (ten tables, every one has `user_id`)

```sql
create extension if not exists vector;

create table sources (            -- what was connected; drives the "understanding you x%" bar
  id uuid primary key default gen_random_uuid(), user_id uuid not null,
  kind text not null check (kind in ('chat','email','activity')),   -- activity = YouTube history, Instagram analytics
  connector text not null, name text not null, status text not null default 'imported',
  n_records int, first_ts timestamptz, last_ts timestamptz, created_at timestamptz default now());

create table source_records (     -- normalized raw input: one message, one email, one watched video
  id bigserial primary key, user_id uuid not null, source_id uuid not null references sources(id) on delete cascade,
  ref int not null, ts timestamptz not null, author text, text text, meta jsonb not null default '{}',
  unique (source_id, ref));       -- "forget this source" = delete cascade

create table chunks (             -- processing log: progress = extracted / total
  id uuid primary key default gen_random_uuid(), user_id uuid not null, source_id uuid not null references sources(id) on delete cascade,
  first_ref int not null, last_ref int not null, tokens int, status text not null default 'pending'
  check (status in ('pending','extracted','failed')), model text, prompt_version text, updated_at timestamptz default now());

create table topics (             -- a bucket = one md file of the Quest tree = one community of GraphRAG
  id uuid primary key default gen_random_uuid(), user_id uuid not null,
  section text not null, name text not null, parent_id uuid references topics(id),
  aliases text[] not null default '{}', embedding vector(768),
  summary text, summary_updated_at timestamptz,   -- cached written summary (the md body / community report)
  unique (user_id, section, name));

create table memories (           -- the full temporal capture: one fact or short narrative
  id text primary key,            -- ULID
  user_id uuid not null, source_id uuid references sources(id) on delete cascade, chunk_id uuid references chunks(id),
  first_ref int, last_ref int,    -- the messages it came from (evidence you can show)
  occurred_start timestamptz, occurred_end timestamptz,   -- when it happened
  mentioned_at timestamptz,                               -- when it was said
  section text not null, topic_id uuid references topics(id),
  text text not null, certainty text not null default 'stated' check (certainty in ('stated','mixed','inferred')),
  valid_from timestamptz, valid_to timestamptz,           -- null valid_to = current (Graphiti's invalid_at)
  superseded_by text references memories(id),
  confidence numeric(3,2) not null default 0.5, decay_rate numeric(3,2) not null default 0.10, last_verified timestamptz,
  embedding vector(768),
  tsv tsvector generated always as (to_tsvector('simple', text)) stored,
  created_at timestamptz default now());

create table entities (           -- people, orgs, places, products, projects (Quest person file frontmatter)
  id uuid primary key default gen_random_uuid(), user_id uuid not null,
  kind text not null check (kind in ('person','org','place','product','project','other')), name text not null,
  aliases text[] not null default '{}', identities jsonb not null default '[]',   -- [{source, account, contact_id}]
  relationship text, closeness text, unique (user_id, kind, name));

create table links (              -- ONE edge table: Graphiti edges, Mem0 links, temporal_note event_links, entity_relationships
  id uuid primary key default gen_random_uuid(), user_id uuid not null,
  from_type text not null check (from_type in ('memory','entity','topic')), from_id text not null,
  to_type   text not null check (to_type   in ('memory','entity','topic')), to_id   text not null,
  kind text not null,             -- mentions | about | updates | extends | contradicts | same_event | mother_of | works_at ...
  valid_from timestamptz, valid_to timestamptz, evidence text[] not null default '{}', created_at timestamptz default now());

create table followups (          -- temporal_note advice_entries + our open questions
  id uuid primary key default gen_random_uuid(), user_id uuid not null, memory_id text references memories(id) on delete cascade,
  question text not null, type text not null, status text not null default 'open' check (status in ('open','resolved','withdrawn')),
  attempts int not null default 0, check_after date, resolution text, evidence text[] not null default '{}', updated_at timestamptz default now());

create table profile (            -- USER.md sections: personality, values, strengths, drive ...
  id uuid primary key default gen_random_uuid(), user_id uuid not null, aspect text not null, text text not null,
  evidence text[] not null default '{}', confidence numeric(3,2), decay_rate numeric(3,2) default 0.05, last_verified timestamptz,
  status text not null default 'hypothesis' check (status in ('hypothesis','confirmed','rejected')),
  updated_at timestamptz default now(), unique (user_id, aspect));

create table alias_suggestions (  -- name fixes proposed by the follow-up agent, waiting for a check
  id uuid primary key default gen_random_uuid(), user_id uuid not null, entity_id uuid references entities(id) on delete cascade,
  alias text not null, canonical text not null, count int not null default 1,
  status text not null default 'hypothesis' check (status in ('hypothesis','confirmed','rejected')), unique (user_id, entity_id, alias));

-- indexes: (user_id, section, topic_id); (user_id) where valid_to is null; hnsw on memories.embedding and topics.embedding;
-- gin on memories.tsv. Row-level security on every table: user_id = auth.uid().
```

How GraphRAG's tables land here: documents = `sources`, text_units = `chunks`/`source_records`, entities = `entities`, relationships = `links` (entity to entity), communities + community_reports = `topics` + `topics.summary`, covariates (claims with dates and status) = `memories` with `valid_from` / `valid_to`.

The md tree is an export: `select` the topics and their memories by section.

### 3. The update loop (the "route, then new / update / delete" of quest.md, with the verdicts of Hindsight and the end dates of Graphiti)

1. **Extract** a chunk into memories (the system prompt; JSON out): text, section, topic label, names, certainty, follow-ups.
2. **Place**: topic = nearest existing topic of this user (embedding + aliases) inside the section; create it when none is close.
3. **Candidates**: memories in the same topic plus nearest by embedding.
4. **One LLM call per batch**: for each new memory a verdict against its closest memories: `unrelated | repeats | changes | ends | extends` (Hindsight's format), using Graphiti's conservative rule: *only when both cannot be true*, never from recency alone.
5. **Code applies it**, append-only:
   - `changes` / `ends`: set the old memory's `valid_to` and `superseded_by`, insert the new one;
   - `extends`: insert and add a `links` row;
   - `repeats`: bump `confidence`, update `last_verified`;
   - dates compared by code, not by the model.
6. **Topic upkeep** in a scheduled job: merge topics with near-duplicate names/embeddings, split a topic that grew past a size, rewrite `topics.summary` when its memories changed.

### 4. The one MCP (tools, in the temporal_note style: context first, draft, approve, write)

| Tool | Does |
|---|---|
| `memory_progress` | per stage counts: sources imported, chunks extracted, topics consolidated; drives the 7% to 100% bar |
| `memory_ingest(source)` | register a source, normalize to `source_records`, queue chunks |
| `memory_context(message)` | one call: entities found in the message, memories on its subjects, open follow-ups; the default first call of the agent |
| `memory_subject(subject, k=10, since)` | "select flights": expand the subject (aliases, paraphrases), hybrid search, current memories only, newest first, with source snippets |
| `memory_search(query, section, since, until)` | semantic + keyword, rank-fused; non-English queries translated |
| `memory_timeline(since, until)` | memories in a date range |
| `memory_entity(name)` | entity card: aliases, identities, links, latest memories |
| `memory_draft(text)` | proposes new / update / end operations; never writes |
| `memory_apply(ops)` | writes append-only after approval |
| `memory_followups` / `memory_resolve(id)` | open questions; resolve only with cited memories |
| `memory_tree(section)` | export the md tree |
| `memory_forget(source or memory)` | delete by source (cascade) or retire a memory |

### 5. Order of work (internal target Fri 18 Dec 2026, contest submission January 2027; PLAN.md section 5)

About four and a half weeks to the internal target. The risk is not the memory idea, it is finishing a demo that works end to end.

Ranked gate, not a calendar: one active item, no re-ranking until #1 is done.

1. A thin end-to-end slice on real data in Postgres: import, chunks, memories, topics, one query. Nothing else until this works.
2. The verdict step with end dates (new / repeats / changes / ends), applied append-only.
3. A minimal UI: connect/upload with the progress bar, tree browser, ask box, Confirm / Edit / Forget.
4. Email as the second source.
5. YouTube history as activity counts.
6. Forget by source, demo data, speed (a cloud model option for the demo; the local 9B is slow), pitch.

Parked: GraphRAG, a graph database, images and voice, live WhatsApp linking. The `links` table keeps the graph route open with no migration. Start a graph effort only when a set of real questions fails on hybrid search plus links.

What I would cut: live WhatsApp linking (the project docs say manual export only), a graph database, GraphRAG, images and voice. WhatsApp plus email is enough for the story; YouTube and Instagram are stretch goals. A 23k-message thread is about 67 chunks and roughly one to two hours on the local model, so precompute the demo user and run the live progress bar on a small import.

### 6. n8n test matrix (I cannot drive n8n from here; these are the inputs and the outputs to check)

| Input | Normalize to `source_records` | Extraction | Expected rows |
|---|---|---|---|
| WhatsApp export `.txt` | one row per message: `ts, author, text`, media as `[image omitted]` | chunks of 5-10k tokens, the system prompt, JSON out | memories with topic, names, follow-ups; media follow-ups |
| Email `.mbox` / Gmail read-only | one row per email: subject, from, to, thread id, cleaned body, attachment names | one memory per thread slice, with category and quoted entities (amounts, dates) | memories; entities only if the text contains them |
| YouTube history (Google Takeout `watch-history.json`; fields from memory: `title`, `titleUrl`, `subtitles[{name,url}]`, `time`; verify against your file) | one row per watched video | counted, not narrated: per channel and month counts, top topics; a model only labels the top titles | memories like "Watched N videos from X in Oct 2026", certainty stated (counts computed) |
| Instagram analytics export | one row per post or insight record (format varies; check the real file) | counted per period and type | memories about activity and reach, computed numbers |

Checks for every input: the same file imported twice adds nothing (idempotent), a sensitive chunk is flagged and stores no text, every memory cites its source rows, and "forget this source" removes its records, chunks and memories.
