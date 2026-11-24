# Sub-agent playbook (for Codex, Gemini, Muse as lead agents)

Each lead agent owns one work package. **Use sub-agents** whenever the work splits into independent pieces. You stay the only one who commits.

## Sub-agent model per lead (founder, 23 Nov — quota)

| Lead | Sub-agent model | Never |
|---|---|---|
| **Muse** | **Muse 1.3 Contributor** | "Wonder" (burns quota) |
| **Gemini** (lead runs as the Neo orchestrator) | a **lower / cheaper Gemini tier** | Neo for sub-agents |
| **Codex** | **gpt-6.2 sol** | — |

Keep it to 2–4 sub-agents. Read-only roles (scout, verifier) can be the smallest model available.

## Roles (factor your work into these)

| Role | Use it for | Gets | Returns | May write? |
|---|---|---|---|---|
| **scout** (read-only) | Find code to reuse; read external docs (MCP SDK, Celery, Anthropic ids, psycopg) | 1 question + paths/URLs | ≤ 15-line answer with file:line or URL + version | no |
| **implementer** | One module or one function group | module path, the `models.py` signatures it implements, the tests it must pass, owned paths | the diff (uncommitted) + a test run | only its listed files |
| **porter** | Port one function from `contest/apps/api/app/lab/`, `weekbench/` or temporal_note | source file:line, target path | ported code with a `# ported from <path>:<line>` header + one test | only its target file |
| **red-team** | Write failure-path tests that try to break validator, privacy, Forget, queue fencing | the spec section (planaudit §6.4 / §0 Rule 9) + module API | new failing-then-passing tests + a list of holes found | only `tests/` files it creates |
| **verifier** (read-only) | Before every commit: full `pytest -q`, ownership check, contract check, frozen `apps/web` check | your branch | pass/fail counts, any file outside your ownership, any `models.py` drift | no |

## Rules for sub-agents

1. **Disjoint files only** when running in parallel. Two implementers never touch the same file.
2. **Sub-agents never commit, push or merge.** The lead reviews and commits.
3. **Brief ≤ 1 page:** goal, exact paths, signatures, tests to pass, "don't touch" list, report format. Never forward the whole plan.
4. Same hard rules as the lead (`B0_common_rules.md`): synthetic data only, no real model calls in tests, no Gemini API in extraction code, only files under `apps/memory/`, never `main`, never `apps/web`.
5. **Every lead commit is preceded by a verifier run.** Paste its counts into your report.
6. Prefer **2–4 sub-agents** per package. More just adds merge work.

## Suggested split per package

- **Core engine (WP-A):** implementer × (schema + graph store | validator | applier | queue) + red-team (fences, duplicates) + verifier.
- **Surfaces (WP-B):** implementer × (live | vault + export | reflect + ops) + verifier.
- **Privacy (WP-C):** implementer (forget), red-team (gate matrix + Forget races), verifier.
- **Ingest + MCP (WP-D):** porter × (WhatsApp parser | email parser), implementer × (MCP server | tokens + routing | hooks + `agent_worker.py`), scout (MCP SDK docs), verifier.
- **End-to-end + Docker (WP-E):** implementer × (Docker/compose | e2e harness), red-team (kill/duplicate/Forget races), verifier.
