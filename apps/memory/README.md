# temporal-memory (`apps/memory/`)

temporal_note is the owner-scoped memory engine for Dubai-io, Community and Messenger. It serves dated facts, evidence, hybrid retrieval and the Vault through the shared memory bridge. It turns a person's WhatsApp, email, notes and chat into a dated **entity ↔ subject graph**, a Quest-style markdown tree, and instant context for replies. It lives in the Dubai-io repo at `apps/memory/` (on `main`) and runs as its own service; the Dubai-io backend (`apps/api`) is its first client.

**Status:** under construction (build plan v2.1). Nothing here is production-ready yet.

## What it does

- **Instant context (no LLM, < 150 ms):** alias match (EN / Arabic / Arabizi), dates/AED, and FTS scoped to the people and subjects in the message produce a context pack for the reply model.
- **Queued extraction:** one job per day of a person's records. Any registered worker claims jobs (our cloud model, a local model, an agent CLI, or the user's own Claude/Codex through MCP) and returns its result **with its model name**. The server validates every result before it touches the graph.
- **Graph:** people, places, orgs and projects; a subject tree (theme → topic → subtopic); dated facts with evidence; and the derived **entity ↔ subject** relation with roles ("Omar ↔ Raseef: beta tester").
- **Outputs:** Vault API (Subjects, People & Places), Quests and milestones (as hypotheses until confirmed), the "why do you know this?" evidence view, and a Quest-style md export.
- **Privacy:** a canonical sensitive gate, third-party people never auto-promoted, and Forget-by-source with a generation fence so nothing resurrects.

## Stack

Python 3.12+ · FastAPI · Postgres 17 (+ pgvector, tsvector) · Celery on RabbitMQ · Redis · MCP (streamable HTTP). Everything runs in `docker compose`.

```powershell
cd apps\memory
copy .env.example .env      # fill keys you have; none are required for tests
docker compose up -d postgres rabbitmq redis
docker compose up -d api worker-p0 worker-p1 beat
```

## Layout

```
src/temporal_memory/
  models.py            shared contract (dataclasses + module signatures) — change only via contract request
  config.py  db/       settings, schema.sql, connection            (WP-A)
  core/                graph_store, validator, applier, extract    (WP-A)
  queue/               celery_app, jobs (ledger + claim), outbox, worker (WP-A)
  privacy/             sensitive (canonical gate), policy, forget  (WP-C)
  live/                context (instant L1 path)                   (WP-B)
  api/                 app (WP-A) · vault, export_md, ops (WP-B)
  reflect.py           weekly profile + milestone hypotheses       (WP-B)
  ingest/              whatsapp, email, triage, cli                (WP-D)
  mcp/                 server, tokens                              (WP-D)
hooks/                 owner-hook prompt + example Claude Code / Codex hook configs (WP-D)
tests/                 synthetic fixtures only
```

## Branches

- Branch from `main` for changes (`mem-wp<X>` per work package). Claude verifies and merges finished work into `main` under D16.

## Data rule

**No real personal data in this repo, ever.** Real exports and runs live outside it (e.g. `G:\Haitham\lab-data\`) and come in through `tm import … --owner <id>`. Tests use the synthetic "Karim" corpus only.

## Plan

Build plan: `G:\Haitham\lab-data\memory-bakeoff\planaudit.md` (v2.1). Benchmark and history: `G:\Haitham\lab-data\memory-bakeoff\`.
