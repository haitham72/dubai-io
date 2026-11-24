# P1B — Gemini: memory-library facts sheet

Paste everything below the line into Gemini.

---

You are researching memory libraries for a bake-off. Read `G:\Haitham\lab-data\memory-bakeoff\PLAN.md` §1, §3, §4 and §5 for the goal and the hard gates. **This is a web and docs research task only.** Don't open any personal data folders.

The founder picks the final stack: one tool, a combination, or an own build. Nothing is pre-rejected, so report facts and don't recommend dropping anything.

For each of **Hindsight (vectorize-io/hindsight)**, **Graphiti (getzep/graphiti)**, **Mem0 (mem0ai/mem0, open-source)** and **Honcho (plastic-labs/honcho, self-hosted)**, and briefly **Cognee**, find the facts below from the **current** official docs and repos (state the version and date you read). Every claim needs a URL. If the docs don't say, write "not documented". Don't guess.

1. **Install and run on Windows 11 + Docker:** the exact commands, the required services (graph DB, Postgres, vector store) and the minimum RAM.
2. **LLM config:** the bake-off feeds every library through a local OpenAI-compatible proxy at `http://127.0.0.1:8787/v1`, which calls Claude Haiku via CLI. Can the library use a custom `base_url` and model name? Which calls need `response_format` / `json_schema` / tool-calling (function calling)? A proxy can emulate JSON schema but **not** native tool-calling easily, so flag any hard dependency on tool calls. Are small models (4B–12B) known to break it? Can it use a custom embedding endpoint (nomic-embed-text, 768-dim)?
3. **Ingest API:** the call for one message or document, with metadata (`source_id`, timestamp, author). Is it async or sync? How many LLM calls does one ingest make? Any published latency or throughput numbers?
4. **Entities and relations:** does it extract people and orgs with **custom entity or edge types** (e.g. `person.relation_to_user = friend`)? How does it resolve aliases and duplicates (`Omar` / `عمر` / `3omar`)?
5. **Contradiction and time:** what happens when a new fact contradicts an old one (invalidate, delete, update, versioned)? Does it keep `valid_at` / `invalid_at`? Can it return **which** old memory was contradicted, in the ingest response?
6. **Recall:** the search API, hybrid (BM25 + vector + graph)? Multi-hop or graph traversal? Filtering by user and by time?
7. **Delete / Forget:** delete by document or source ID? Does it cascade to derived facts, edges and embeddings? Any known slow-delete issues?
8. **Pre-write hook:** is there a supported way to inspect or block an extracted fact before it's persisted (dry-run extract, callbacks, custom pipeline step)?
9. **Multilingual:** any Arabic support notes or issues?
10. **License** (core and any server), hosted-vs-OSS feature gaps, and the last release date.
11. **Known issues:** the top 5 open GitHub issues relevant to the items above (performance, small models, delete, multilingual).

## Output

Write `G:\Haitham\lab-data\memory-bakeoff\research\libraries.md` with:
- one section per library, using the 11 numbered headings;
- a final **comparison table** (rows = the hard gates and score items from `PLAN.md` §5, cells = yes / no / partial plus a link);
- a **minimal adapter sketch** per library: the ~10 Python calls that implement `ingest`, `live_turn` (ingest + whatever returns contradictions/entities), `recall`, `forget_source`.

Also add, per library, **what it's best at as a layer** (extraction, contradiction/time, graph, recall, reflection/milestones) and which pairs could combine cleanly (shared store? double ingest?).

End with 5 lines: which library looks strongest on paper for the §1 chain, and the single biggest risk for each.
