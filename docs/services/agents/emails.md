# Emails agent — design (DRAFT, 15 Nov 2026)

First task: **job applications**. "Find my job applications" goes from ~1k emails → ~100 job emails → a list of applications with their status (applied / interview / rejected / offer). The same machinery serves later email tasks (bills, bookings, a project thread).

Sources: Gmail, Outlook (connector details in [../../plan/connectors.md](../../plan/connectors.md)). WhatsApp and Slack messages use the same tables.

## 1. Pipeline

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

## 2. Ingest and clean

- Gmail: Gmail API; Outlook: Microsoft Graph `Mail.Read`.
- Keep only the **new text** of each email: strip quoted replies ("On … wrote:", `>` lines), signatures, footers. Otherwise a 10-email thread stores the first message 10 times.
- Keep headers in `raw` (`From`, `Return-Path`, `Received`, `List-Unsubscribe`): ATS emails sent from a company domain still name the ATS there.
- `sender_domain` = registrable domain of `From` (`jobs-noreply@linkedin.com` → `linkedin.com`).
- Each message's own timestamp = `occurred_at` (not ingest time).
- Embed `subject + first ~2k chars of body_text`.

Shortcut for one-off tasks: Gmail search accepts the Gmail search-box syntax, so a task can pre-filter server side, e.g. `from:(linkedin.com OR greenhouse.io OR lever.co) OR subject:(application OR interview)`.

## 3. Storage (Postgres)

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

## 4. Job applications skill

### 4.1 Seed rules (`owner = NULL`, `origin = 'skill'`, active)

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

### 4.2 Query flow

1. **SQL filter.** Candidates are the union of: active domain/sender/header rules · `fts @@ websearch_to_tsquery('application OR applied OR candidate OR interview OR position OR role')` · `embedding <=> query_embedding < 0.5`. Items that already have a `topic` label are taken from `item_labels` directly.
2. **Rules first.** If active rules agree on topic and status, write `item_labels (source='rule')` with no model call.
3. **Model for the rest.** Small model gets subject + body start → `{is_job, status, company, role, evidence_sentence}` → `item_labels (source='model')`. Conflicts (e.g. "unfortunately the interview needs rescheduling" hits both rejected and interview) always go to the model.
4. **Group.** Upsert `entities (kind='job_application', key='company|role')`, link items in `entity_items`; `state` = status of the newest linked item.
5. **Answer.** "12 applications: 7 rejected, 2 interviews, 3 waiting", each opening its email trail.

## 5. Learning

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

## 6. Bulk backfill vs incremental

- **Backfill** (e.g. 1k emails at connect): ingest everything → embed in batch → run the task query → classify the candidates in batch.
- **Incremental:** new emails from sync are cleaned, embedded and run through active rules on arrival; only unmatched ones queue for the model.

## 7. Later email tasks

Same tables and flow, new skill each: seed rules + classification prompt + entity key. E.g. bills (`biller|account`), bookings (`provider|reference`), a project thread (`project`).
