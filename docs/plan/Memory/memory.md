# Memory plan (single source)

**Status:** proposed design + locked rulings from `PLAN.md` §2 · **Date:** 18 Nov 2026  
**Authority:** root `CLAUDE.md` → `PLAN.md` → `ARCHITECTURE.md` §7 → this file. Research dumps live in `_archive/` — do not treat them as the plan.

---

## 1. What we decided (locked)

| Item | Ruling |
|---|---|
| Backend (`MEM-01`) | Hindsight kept as **swappable** `MemoryBackend` + `ScopeGuard`. Fix Dubai-io rule gaps only. Full Postgres/markdown re-fit **after** AC-1–AC-3. |
| Store | One Postgres service (`user_id` everywhere). **Md tree = export/view, not the store.** |
| Engines merged (ideas, not four products) | Hindsight verdicts · Graphiti end-dates · Mem0-style links (checklist) · Quest tree as export · temporal_note read path |
| Mem0 | Rejected as backend |
| Graphiti DB | Deferred |
| GraphRAG / graph DB | **Parked.** Use `links` + hybrid search first |
| Topics | Fixed spine (~10–15 sections / ontology leaves) + **dynamic** subtopics (split/merge/add) |
| User folders | Seven life themes: Career · Learning · Projects · People & family · Events · Home & money · Travel |
| Cards | **App owns UI.** Memory feeds state; it does not render cards |
| Gate | No new memory feature work until **AC-1** (live Hindsight LLM retain), **AC-2** (card lifecycle), **AC-3** (query rewriter) are green |

Lab evidence (`G:\Haitham\lab-data\mamty-hindsight\`): ~57 weeks, ~444 facts = **prompt-level retain only**. Not live Hindsight. Blocked from `mem_*` until schema + aliases + `sensitive.py` + confirm.

---

## 2. Mental model (how to think)

One useful row:

| datetime | topic | semantic (optional) | relation | note |
|---|---|---|---|---|
| `2026-11-14 20:15` | `tech/devices/phone` (`mobile`) | mood only if scored | `user → buy? → mother[phone]` | mother prefers current Samsung; declined new phone |

That maps to tables: **`memories`** + **`topics`** + **`entities`** + **`links`**.  
`user → buy? → mother[mobile]` is a **typed link**, not GraphRAG (no community clustering).

---

## 3. Tables (ten — summary)

`sources` → `source_records` → `chunks` → **`memories`** (temporal facts, `valid_from`/`valid_to`, `superseded_by`) · **`topics`** (section, name, **aliases[]**, embedding) · **`entities`** (aliases, identities) · **`links`** · `followups` · `profile` · `alias_suggestions`.

Append-only: a change **ends** the old row and inserts a new one. Forget-by-source cascades from `sources`.

Fine ontology (engine IDs): `docs/references/residence-ontology-tree.md`  
Example spine leaf for phones: **`tech/devices/phone`** with aliases `{mobile, phone, موبايل, تليفون, هاتف}`.

---

## 4. Mnemosyne vs Hindsight (roles)

| | Mnemosyne-like | Hindsight |
|---|---|---|
| Role here | Live **session** / cheap local layer | Long-term **bank** + weekly backfill |
| Write | Light; extract optional | `retain` → facts, time, entities |
| Recall | FTS + vector + importance | Semantic + BM25 + graph + time (RRF) |
| Consolidate | sleep / episodic | observations + reflect (later) |

**Product hybrid policy (founder 18 Nov):** FTS/BM25 **first** (speed/cost); light semantic second inside the FTS/topic slice — not semantic-first over the whole corpus.

---

## 5. Extract → consolidate → query → card

```
day/week chat
  → retain (Hindsight-shaped JSON: what/when/where/who + entities)
  → place topic (nearest spine leaf + aliases; else provisional subtopic)
  → verdict vs bank: unrelated | repeats | changes | ends
  → code applies (no silent overwrite)
  → profile_interests(topic_key) weights
  → Notice card generators (ScopeGuard: category/entity/person required)
```

**Example card chain:** `mobile` mentions 6mo ↑ last 3 weeks → buy intent (confirm / two-visit) → Amazon.ae AED price-drop card + Because…

**System prompts** fill extract/route/verdict/query-rewrite gaps. **Code** owns FTS schema, aliases, weights, card rank, providers, sensitive gates.

---

## 6. Lab lesson (18 Nov) — week JSON is not the product

| Observation | Implication |
|---|---|
| ~57 files, ~444 facts, busy week ~20 facts / ~300 msgs | File count OK; **unscoped conversation rows** = bloat |
| No `topic` / subjects on facts | Query `"mobile"` misses `موبايل`/`تليفون` |
| Same-week `observations` sparse; cross-week consolidate **not run** | Identity re-stated every week |
| Quest export = topic cards, weak timelines | Good for identity; bad for “again” / “from where” |
| Hindsight weeks = dated events | Good for expanders; need topic+FTS index |

**Do not** promote raw week JSON to Me/profile. Keep events for timelines; lasting identity after consolidate (~few durable bullets per person/topic).

Sample path:

1. **Input:** mother refuses new phone, keeps Samsung (2026-11-14)  
2. **Retain fact** with entities  
3. **Postgres:** `topic_id=tech/devices/phone`, link `user —considering_buy_for→ mamty`, note text  
4. **Repeats later:** bump `last_verified`, no new profile bullet  

---

## 7. Topics: spine vs improvised (cards = the app)

- **Spine** (product): ontology leaves — card generators and adapters attach here.  
- **Dynamic subtopics:** extractor may create under a section; scheduled upkeep merges near-dupes (`mobile`/`phone`/`chat device` → one key + aliases).  
- **Account rules:** noisy improvised clusters → backfill proposes a rule + optional new spine leaf (human/ops).  
- Unknown domains (fashion, quantum, hard languages): provisional topic + embedding; source language kept in text; cards still need confirmed/qualified weight + evidence.

Interest chart `profile_interests(topic_key, weight, scope)` + generators + feedback = **Notice**. That is the product loop.

---

## 8. Benefit to the cards UI (`design/17-11-2026/`) — realistic (18 Nov)

Target visuals: Morning Brief dashboard + mobile Memory / “Why am I seeing this?” (`docs/plan/morning-brief.md` §8).

| Design needs | Mamty week JSON today |
|---|---|
| Category pills + scoped evidence (`family`, `person: Mom`, gifts) | People entities exist — **partial** |
| Birthday + missed-last-year + gift interest | **Missing** (no birthday `fact_key`, no Calendar join) |
| Career funnel counts | **Wrong source** for this chat |
| Gadgets price-drop / Amazon AED | Phone talk exists; **no topic=`mobile`**, no price history |
| Confirm signal (“oud twice?”) | Pattern possible; **not wired** + family/health gated |
| Because… drawer | Timestamps exist; **not card payloads / ScopeGuard audit** |
| Graph node view | **Dev only** — cards do not show a graph |

**Scores:** medium as WhatsApp fuel for Family/Mom person scope · **low** as shippable morning-brief feed until topic+aliases, consolidate, confirm gates, Gmail/Calendar · **~none** for Mermaid co-occurrence as product UI.

Derived diagnostic only (not live Hindsight): `G:\Haitham\lab-data\mamty-hindsight\graph-from-weeks.md`.

**Next slice that actually moves the design:** Gmail + Calendar + one working generator (e.g. `family.birthday` or gated gift interest) — not more week files or graph viz.

---

## 9. Still needed (gaps)

1. Topic + alias on every memory write  
2. Cross-week consolidate into one bank (L5, after AC-1)  
3. Interest weights + rising-window signals  
4. Card generators + ScopeGuard (FTS-first)  
5. Shopping/news adapters (Amazon.ae, …)  
6. Sensitive + `"I noticed"` confirm before family/health surfaces  
7. Thin Postgres E2E slice (import → memory → one query)  
8. Live AC-1 Hindsight LLM retain proof  

Backfill agent: `docs/plan/backfill-agent.md` (gated on AC-1–3).  
Morning cards / ScopeGuard: `docs/plan/morning-brief.md` §8.

---

## 10. Sources (IN / not yet)

| Source | Status |
|---|---|
| WhatsApp **manual** export | IN (lab) |
| Gmail + Calendar | IN (OAuth keys still needed for live) |
| Takeout mbox/ics/vcf | Planned parsers; test data OK |
| YouTube / Instagram activity | **Not IN** as narrated memory — counts only if ever opted; settle before building |
| Quest-style md export | View only; private exports stay in `G:\Haitham\lab-data\` |

---

## 11. Working rules for agents

- Read **this file** for memory decisions — not `_archive/` first.  
- Real chats/exports: `G:\Haitham\lab-data\` only — never under `docs/plan/Memory/data`.  
- Never invent success statuses; every number needs provenance.  
- Family/faith/health: never plain facts without explicit user confirmation (`sensitive.py`).  
- Links ≠ GraphRAG. HNSW = ANN index for embeddings, optional assist after FTS.
