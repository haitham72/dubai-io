# Domain Agents & Orchestrator (Proposed Draft — 15 Nov 2026)

**Status:** proposed draft rescued from branch origin/docs/consolidate-plan-agents (76516cf), not approved or built · **Scope:** PLAN.md

---

## Part 1: Agents Catalog & Template

One doc per agent: how it works end to end. How agents are combined to answer a request: [Part 2](#part-2-orchestrator--how-agents-are-combined-draft-15-nov-2026). Connectors that feed agents: [../connectors/README.md](../connectors/README.md).

### Designed

| Agent | Doc | State |
|---|---|---|
| Emails (job applications first) | [Part 3](#part-3-emails-agent--design-draft-15-nov-2026) | Design draft |

### Candidates (high level, 15 Nov)

Contest picks (proposed): **Lost item in transport**, **Documents & expiry + Bills**, **Job applications**.

#### Work & admin
| Agent | What it does | Sources |
|---|---|---|
| Job applications | Applications + status | Email |
| What needs me | Unanswered messages, promises made ("I'll send it tomorrow") | Email, WhatsApp, Slack |
| Follow-up nudger | "You emailed Ali 5 days ago, no reply" | Email |
| Meeting prep | Brief on the person/company before an event | Calendar + all |
| Documents & expiry | Visa, Emirates ID, passport, licence, trade licence dates → reminders | Email, uploads |

#### Household & money
| Agent | What it does | Sources |
|---|---|---|
| Bills | DEWA, e&/du, Empower, Salik amounts, due dates, spikes | Email |
| Rent & tenancy | Ejari renewal, rent cheque schedule, notice periods | Email, uploads |
| Subscriptions | Recurring charges from receipts | Email |
| Orders, returns & warranty | Return windows, warranty end dates | Email |
| Deliveries | Shipment status in one place | Email, WhatsApp |
| Home maintenance | AC service history, next service → Services | Email, orders |
| School (parents) | School emails + class groups → events, fees, forms | Email, WhatsApp |
| Spending | Monthly spend by category, salary day, unusual charges | Bank emails/SMS |
| Split with friends | "You owe me 120" from groups | WhatsApp |
| Insurance | Renewals, claim status | Email |
| Deposit disputes | Car rental / tenancy deposits returned or not, with evidence | Email, uploads |
| Household staff | Domestic worker visa, salary dates, leave | Email, uploads |

#### Places & trips
| Agent | What it does | Sources |
|---|---|---|
| Lost item in transport | Ride receipts → time, route, plate → prefilled report | Email, memory |
| Trips | Bookings → itinerary, check-in, DXB guide | Email |
| Car | Mulkiya, insurance, service dates, fines | Email, uploads |
| Home search | Property alerts → shortlist, price changes | Email |

#### Social & personal
| Agent | What it does | Sources |
|---|---|---|
| Group digests | Building/family/community groups → key items | WhatsApp |
| Invites & events | Invitations → calendar suggestions | WhatsApp, email |
| People | Birthdays, people you've lost touch with | WhatsApp, Instagram |
| Voice notes | Transcribe + summarize, pull out actions | WhatsApp |
| Official letters | Photo of a letter → meaning, deadline, what to do | Uploads |
| Health admin | Appointments, refills, insurance approvals | Email |
| Creator analytics | Reach, best times, top posts, comment themes | Instagram |
| Know me | Profile built from all agents | All |

#### Small business & freelancers
| Agent | What it does | Sources |
|---|---|---|
| DM leads → orders | Customer questions in DMs → lead list, unanswered | Instagram, WhatsApp |
| Invoices & unpaid | Sent invoices, unpaid, reminder drafts | Email |
| Tax & licence deadlines | VAT, corporate tax, trade licence dates | Email, uploads |

#### Bundles (several agents together)
| Bundle | Combines |
|---|---|
| Moving apartment | Ejari, DEWA move-out/in, internet transfer, movers, address change |
| New job / leaving a job | Offer, visa transfer, labour card, end-of-service, salary bank |
| New arrival in Dubai | Emirates ID, bank, SIM, DEWA, licence conversion, airport guide |
| Weekly briefing | Sunday "your week" from all agents |

### Shared pieces

- **Connectors:** Gmail, Outlook, WhatsApp, Slack, Instagram, Calendar, document upload.
- **Storage + learning:** `source_items`, `item_labels`, `label_rules`, `entities`, `entity_items` ([Part 3 §3](#33-storage-postgres)).
- **Reminders:** one scheduler for expiry, due dates, follow-ups.
- **Document reading:** PDFs/photos (visa, Ejari, Mulkiya, warranties).
- **Test set per agent:** ~20 real examples with the right answer.

### Agent doc template

Each new agent doc has these sections:

1. **Trigger** — what question or event starts it
2. **Inputs** — connectors and tables it reads
3. **Contract** — input / output JSON the orchestrator sees
4. **Skill** — seed rules + prompt
5. **Output** — what the user sees
6. **Test set** — examples with the right answer

---

## Part 2: Orchestrator — how agents are combined (DRAFT, 15 Nov 2026)

One orchestrator (Luna) plans; agents are its tools. Agents don't talk to each other — they read and write shared storage (`source_items`, `entities`, tasks).

### Loop

```
request ─► orchestrator writes a plan (steps + dependencies)
             │
             ├─ independent steps run in parallel (agents as tools / LangGraph sub-graphs)
             ├─ bulk reading → fast-model fan-out, one strong model combines
             ├─ surprise or empty result → replan
             ├─ user choice / approval needed → pause, ask
             │
          verifier checks dates, numbers, statuses against evidence ─► answer
```

### Example: "why didn't my Puffy application pay off?"

1. Emails agent → `job_application` entity `puffy|*` + its email trail
2. Memory → what the user said about Puffy
3. Profile → current title, recent changes
4. (1–3 in parallel) → fast model reads each email → JSON summaries
5. Orchestrator reasons → advice
6. Draft reply in the account the thread lives in (Outlook) → user sends

### Patterns

| Pattern | Use |
|---|---|
| Router | Simple single-agent requests ("my bills") |
| Orchestrator–workers | Default for multi-step requests |
| Plan-and-execute + replan | Long tasks (bundles like moving apartment) |
| Map-reduce fan-out | Bulk reading (emails, chats) |
| Verifier | Anything with numbers, dates, statuses |
| Shared storage | How agents exchange results |

### Design points

- **Plan = data:** stored with tasks, so it shows as a task thread, survives restarts, retries per step.
- **Agent contract:** input/output JSON + allowed tools; the orchestrator sees only the contract.
- **Cheap first:** SQL/rules → small model → strong model for reasoning and the final answer.
- **Budget per plan:** max steps, tokens, time.

---

## Part 3: Emails agent — design (DRAFT, 15 Nov 2026)

First task: **job applications**. "Find my job applications" goes from ~1k emails → ~100 job emails → a list of applications with their status (applied / interview / rejected / offer). The same machinery serves later email tasks (bills, bookings, a project thread).

Sources: Gmail, Outlook (connector details in [../connectors/README.md#5-proposed-tester-onboarding-notes-15-nov-draft--not-built](../connectors/README.md#5-proposed-tester-onboarding-notes-15-nov-draft--not-built)). WhatsApp and Slack messages use the same tables.

### 3.1 Pipeline

```
connector sync ─► clean ─► source_items (domain + full-text + embedding)
                                 │
task query ("job applications") ─► SQL filter (rules + FTS + vector) ─► ~150 candidates
                                 │
                 small model classifies ─► item_labels ─► ~100 job emails with status
                                 │
                 group by company|role ─► entities (one row per application)
                                 │
                 labels feed back ─► label_rules learn, promoted rules skip the model next time
```

### 3.2 Ingest and clean

- Gmail: Gmail API; Outlook: Microsoft Graph `Mail.Read`.
- Keep only the **new text** of each email: strip quoted replies ("On … wrote:", `>` lines), signatures, footers. Otherwise a 10-email thread stores the first message 10 times.
- Keep headers in `raw` (`From`, `Return-Path`, `Received`, `List-Unsubscribe`): ATS emails sent from a company domain still name the ATS there.
- `sender_domain` = registrable domain of `From` (`jobs-noreply@linkedin.com` → `linkedin.com`).
- Each message's own timestamp = `occurred_at` (not ingest time).
- Embed `subject + first ~2k chars of body_text`.

Shortcut for one-off tasks: Gmail search accepts the Gmail search-box syntax, so a task can pre-filter server side, e.g. `from:(linkedin.com OR greenhouse.io OR lever.co) OR subject:(application OR interview)`.

### 3.3 Storage (Postgres)

Follows existing conventions (`owner TEXT`, `extensions.vector(1536)`). Tokens reuse the existing `oauth_grants` table.

```sql
CREATE TABLE source_items (
  id            TEXT PRIMARY KEY,
  owner         TEXT NOT NULL,
  provider      TEXT NOT NULL,            -- gmail | outlook | whatsapp | slack | instagram
  external_id   TEXT NOT NULL,
  thread_key    TEXT,                     -- gmail threadId / chat id / slack channel
  sender_name   TEXT,
  sender_addr   TEXT,
  sender_domain TEXT,
  subject       TEXT,
  body_text     TEXT,                     -- cleaned new text only
  occurred_at   TIMESTAMPTZ NOT NULL,
  raw           JSONB,                    -- headers, original ids
  fts           TSVECTOR GENERATED ALWAYS AS
                  (to_tsvector('english', coalesce(subject,'') || ' ' || coalesce(body_text,''))) STORED,
  embedding     extensions.vector(1536),
  UNIQUE (owner, provider, external_id)
);
CREATE INDEX ON source_items (owner, provider, occurred_at DESC);
CREATE INDEX ON source_items (owner, sender_domain);
CREATE INDEX ON source_items USING GIN (fts);
CREATE INDEX ON source_items USING hnsw (embedding extensions.vector_cosine_ops);

CREATE TABLE item_labels (
  owner       TEXT NOT NULL,
  item_id     TEXT NOT NULL REFERENCES source_items(id) ON DELETE CASCADE,
  label_set   TEXT NOT NULL,              -- 'topic' | 'job_status'
  value       TEXT NOT NULL,              -- 'job_application' | 'rejected' | ...
  source      TEXT NOT NULL,              -- 'rule' | 'model' | 'user'
  rule_id     TEXT,
  confidence  REAL,
  evidence    TEXT,                       -- matched sentence
  created_at  TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (item_id, label_set, source)
);
CREATE INDEX ON item_labels (owner, label_set, value);

CREATE TABLE label_rules (
  id          TEXT PRIMARY KEY,
  owner       TEXT,                       -- NULL = app-wide (skill); else learned per user
  label_set   TEXT NOT NULL,
  value       TEXT NOT NULL,
  kind        TEXT NOT NULL,              -- sender_domain | sender_addr | header | phrase | regex | prototype
  pattern     TEXT,
  prototype   extensions.vector(1536),    -- centroid of confirmed examples
  negative    BOOLEAN DEFAULT false,      -- rule says "NOT this value"
  origin      TEXT NOT NULL,              -- skill | learned | user
  hits        INT DEFAULT 0,
  correct     INT DEFAULT 0,
  wrong       INT DEFAULT 0,
  active      BOOLEAN DEFAULT false,
  updated_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE entities (
  id         TEXT PRIMARY KEY,
  owner      TEXT NOT NULL,
  kind       TEXT NOT NULL,               -- job_application | person | company ...
  key        TEXT NOT NULL,               -- 'puffy|senior designer'
  state      TEXT,                        -- latest status
  state_at   TIMESTAMPTZ,
  data       JSONB,
  UNIQUE (owner, kind, key)
);
CREATE TABLE entity_items (
  entity_id TEXT REFERENCES entities(id) ON DELETE CASCADE,
  item_id   TEXT REFERENCES source_items(id) ON DELETE CASCADE,
  role      TEXT,                         -- application_sent | status_update ...
  PRIMARY KEY (entity_id, item_id)
);
```

### 3.4 Job applications skill

#### Seed rules (`owner = NULL`, `origin = 'skill'`, active)

**Job boards (`sender_domain`)**: linkedin.com, indeed.com, glassdoor.com, bayt.com, naukrigulf.com, gulftalent.com, wellfound.com, ziprecruiter.com, monster.com.

**ATS (`sender_domain` + `header`)** — where most status emails come from: greenhouse.io, lever.co, myworkdayjobs.com, workday.com, ashbyhq.com, smartrecruiters.com, icims.com, taleo.net, successfactors.com, jobvite.com, workable.com, bamboohr.com, recruitee.com, teamtailor.com, personio.de, breezy.hr.

**Sender-specific (`sender_addr`)**, because a domain alone is too broad:
- `jobs-noreply@linkedin.com` + subject "your application was sent" → `applied`
- `jobalerts-noreply@linkedin.com` → `job_application`, `negative = true` (alerts, not applications)

**Status phrases (`phrase`)**:

| Phrases | → `job_status` |
|---|---|
| "thank you for applying", "received your application", "application was sent" | applied |
| "move forward", "next steps", "schedule an interview", "availability for a call" | interview |
| "unfortunately", "not moving forward", "other candidates", "regret to inform" | rejected |
| "pleased to offer", "offer letter" | offer |

#### Query flow

1. **SQL filter.** Candidates are the union of: active domain/sender/header rules · `fts @@ websearch_to_tsquery('application OR applied OR candidate OR interview OR position OR role')` · `embedding <=> query_embedding < 0.5`. Items that already have a `topic` label are taken from `item_labels` directly.
2. **Rules first.** If active rules agree on topic and status, write `item_labels (source='rule')` with no model call.
3. **Model for the rest.** Small model gets subject + body start → `{is_job, status, company, role, evidence_sentence}` → `item_labels (source='model')`. Conflicts (e.g. "unfortunately the interview needs rescheduling" hits both rejected and interview) always go to the model.
4. **Group.** Upsert `entities (kind='job_application', key='company|role')`, link items in `entity_items`; `state` = status of the newest linked item.
5. **Answer.** "12 applications: 7 rejected, 2 interviews, 3 waiting", each opening its email trail.

### 3.5 Learning

Two sources feed `label_rules`:

- **App skills:** seed rules above, shipped with the skill.
- **The user's own emails:** after each run:
  1. Take items labelled by the model with high confidence, plus user corrections.
  2. For each status, find phrases and senders that are frequent in that status and rare in others (log-odds count).
  3. Insert as `origin='learned'`, `owner=<user>`, `active=false`.
  4. Each time a rule fires, compare with the model/user label → update `correct` / `wrong`.
  5. Promote to active at ~90% precision over ≥5 hits; demote when it drops.
  6. `prototype` rules: average embedding of confirmed items per status; catches wording no phrase rule has.
- **New senders:** a model-confirmed job email from an unknown sender (`careers@startup.ae`) adds a learned `sender_addr` rule.
- **User corrections** (`source='user'`) override other labels and count as strong evidence for or against the rules that fired.
- **Across users:** a learned rule active for many users can be promoted to `owner = NULL`. Only the pattern moves, not email content.

Over time most emails are answered by rules; the model sees only new wording and conflicts.

### 3.6 Bulk backfill vs incremental

- **Backfill** (e.g. 1k emails at connect): ingest everything → embed in batch → run the task query → classify the candidates in batch.
- **Incremental:** new emails from sync are cleaned, embedded and run through active rules on arrival; only unmatched ones queue for the model.

### 3.7 Later email tasks

Same tables and flow, new skill each: seed rules + classification prompt + entity key. E.g. bills (`biller|account`), bookings (`provider|reference`), a project thread (`project`).
