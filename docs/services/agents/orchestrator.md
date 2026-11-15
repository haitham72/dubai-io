# Orchestrator — how agents are combined (DRAFT, 15 Nov 2026)

One orchestrator (Luna) plans; agents are its tools. Agents don't talk to each other — they read and write shared storage (`source_items`, `entities`, tasks).

## Loop

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

## Example: "why didn't my Puffy application pay off?"

1. Emails agent → `job_application` entity `puffy|*` + its email trail
2. Memory → what the user said about Puffy
3. Profile → current title, recent changes
4. (1–3 in parallel) → fast model reads each email → JSON summaries
5. Orchestrator reasons → advice
6. Draft reply in the account the thread lives in (Outlook) → user sends

## Patterns

| Pattern | Use |
|---|---|
| Router | Simple single-agent requests ("my bills") |
| Orchestrator–workers | Default for multi-step requests |
| Plan-and-execute + replan | Long tasks (bundles like moving apartment) |
| Map-reduce fan-out | Bulk reading (emails, chats) |
| Verifier | Anything with numbers, dates, statuses |
| Shared storage | How agents exchange results |

## Design points

- **Plan = data:** stored with tasks, so it shows as a task thread, survives restarts, retries per step.
- **Agent contract:** input/output JSON + allowed tools; the orchestrator sees only the contract.
- **Cheap first:** SQL/rules → small model → strong model for reasoning and the final answer.
- **Budget per plan:** max steps, tokens, time.
