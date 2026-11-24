# P2 — Gemini: own-build reflection layer + Honcho facts

Paste everything below the line into Gemini. Working directory: `G:\Haitham\lab-data\memory-bakeoff\` (a git repo; commit when done).

**Other agents are working in this repo right now:**
- A Claude agent is building `weekbench/hookproxy.py`, `weekbench/export.py`, `weekbench/configs/hindsight*.py`, `weekbench/edgex.py` and `weekbench/docker/`, and is editing `weekbench/configs/tn_update.py` and `run.py`.
- Muse is editing `gold/`.

**Don't edit any of those.** Only create the files named below, and only append to `research/libraries.md`.

---

The founder is locking a memory stack: Hindsight · Hindsight + Honcho · Hindsight + Honcho + edgextract · updated temporal_note (`tn_update`, our own build). Honcho's job in that stack is **reflection**: writing a Quest-style `USER.md` profile and auto-detecting milestones. To judge whether Honcho earns its cost, we need the cheapest possible competitor, and that's your task, plus the Honcho facts your earlier research skipped.

## Rules (founder's)

- **Model:** Claude Haiku, medium effort, via the subscription hook. Call it **only** through `weekbench/hook.py` (`hook.call(system, prompt, log=run_dir/"calls.jsonl", tag=...)`, about 1k overhead tokens). No API keys. **Zero Gemini API calls.**
- Data: the synthetic corpus in `gold/` (fictional persona "Karim Haddad"), so there's no personal data.
- **Cost is the main criterion.** Simplicity and clarity matter, so keep `reflect.py` under about 150 lines.

## Task 1 — `weekbench/reflect.py` (own-build reflection)

```powershell
python weekbench/reflect.py --run <run folder name under runs/>
```

- **Input:** that run's `graph.json` (`facts` with status / valid_from / evidence, `entities` with `relation_to_user`, `edges`) and its `memory/` md tree. Read-only: don't change anything already in the folder.
- **One LLM call per week of facts,** plus one final merge call (so about 6 calls for a month).
  - Each weekly call gets the previous `USER.md` + `milestones.json`, plus that week's new, changed and ended facts.
  - It returns the updated profile and milestones (Quest style: refresh in batches, never per message).
- **Write to `<run>/reflect/`:**
  - `USER.md`: the 7 Quest sections (Identity, Personality, Values, Strengths & Tensions, Interests, Drive, Relationships). 2–4 claims each; every claim cites the memory file or fact IDs it came from. Uncertain claims say "likely" or "unconfirmed" (Rule 9: inferences are hypotheses, shown as "I noticed…").
  - `milestones.json`: `[{"title", "status": "done|in_progress|planned", "first_seen": "YYYY-MM-DD", "evidence": [fact ids]}]`. **Creation rule, enforced in code:** a milestone needs ≥ 2 supporting facts from ≥ 2 different days, and must not come from sign-ups, OTP logins, subscriptions, newsletters, account linking or one-off deliveries. Facts with `sensitive` set never feed the profile.
  - `stats.json`: calls, tokens in/out, `cost_usd`, seconds (summed from the calls you logged with `tag="reflect_*"`).
- **Test it** on the newest `runs/*_tn_update-day_month` folder (if it doesn't exist yet, use `runs/*_tn_update-day_week1`). Commit the code and the run outputs.

## Task 2 — Honcho facts (append to `research/libraries.md`)

Add `## E. Honcho (plastic-labs/honcho)` with the same 11 numbered headings as sections A–D, using the current version and official docs/repo, with URLs. Must cover:
- **LLM calls per message** (deriver), per dialectic query and per summary, i.e. what a month of about 1,200 messages costs in calls;
- which LLM roles exist and whether **every** role can point at an OpenAI-compatible `base_url` (several default to Gemini);
- licence (and what AGPL means for a hosted commercial app);
- delete-by-session/peer behaviour;
- Arabic.

End with 3 lines: what Honcho adds over a weekly reflection call, what it costs, and the biggest risk.

## Report back (short)

`reflect.py` line count, the reflect run's calls and cost, the paths of the `USER.md` and `milestones.json` it wrote, and the 3-line Honcho summary.
