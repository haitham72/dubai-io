# Work package — GrepMem pilot on the founder's own last-week data

- **For:** one builder agent (Gemini or Devin; the founder assigns). Gate: Claude (integrator) reviews the report.
- **Design (read first):** `docs/submissions/shared/research/grepmem-whatsapp-pilot-plan.md`. Paper: GrepMem (Yang, Shi, Zhao, 18 Nov 2026). Memory engine guide: `apps/memory/CLAUDE.md`.
- **Question to answer:** does searching the original message text (regex/ripgrep) find correct, source-backed answers that our temporal_note graph recall misses, or find them faster? If yes, how should Dubai-io use it?
- **Timebox:** one working day after the founder hands over the exports.
- **Prior work to reuse (read the setup files only, not chat contents):** `G:\Haitham\lab-data\mamty-hindsight\` (Antigravity's WhatsApp memory tests with Hindsight: `RUN.md`, `AGENT_PROMPT*.md`, `RESERVATIONS.md`, week-split scripts) and `G:\Haitham\lab-data\memory-bakeoff\` (`DECISION.md`, `LEADERBOARD.md`, `runs/*hindsight*`). Reuse their export handling and week splitting; this pilot still needs **last week's** fresh exports.

## 0. Privacy rules (hard; stop if any can't be met)

1. **Real data never enters the repo or git.** Exports, the harness, prompts with answers, logs and snippets all live under `G:\Haitham\lab-data\grepmem-pilot\` (outside the repo). The only repo output is the aggregate report in §5.
2. **You, the coding agent, must not read the raw chats.** Never `cat`/print export files or matched snippets into your own context. Work through scripts that print **counts, IDs, line ranges and timings only**. Snippets go to files under `lab-data` that the founder reads.
3. **Answer model = local** (LM Studio Qwen at `http://127.0.0.1:1234/v1`). A cloud model (e.g. `claude -p` Haiku) may be used only if the founder types an explicit OK for this pilot.
4. **Isolated memory owner.** Ingest into the local temporal_note (`:5442`) under a dedicated owner such as `grepmem-pilot-2611`, never the founder's main owner. After the pilot, **Lower** that owner's sources (D18/D19: no deletion in normal operation) and report it. The founder decides whether to run "Delete my data" on that owner.
5. Rule 9: no sensitive inference. Regex hits are evidence for an answer only and are **never written back** to temporal_note.
6. Don't edit product code (`apps/**`), and don't touch `apps/web`. The harness is a standalone script under `lab-data`.

## 1. Inputs (founder does this)

- **WhatsApp:** 3–5 chats with real activity in the last 7 days. On the phone: chat → ⋮/name → **Export chat → Without media**. Save the `.txt` files to `G:\Haitham\lab-data\grepmem-pilot\exports\whatsapp\`.
- **Browser history (optional second source):** last 7 days of Chrome history, read by the existing desktop reader (`apps/memory/src/temporal_memory/ingest/desktop/browser.py`) into the same pilot owner, with its existing consent and filter rules.
- The founder confirms in writing which chats are in scope. Search must never leave that file allowlist.

## 2. Build the matched graph snapshot

1. Record SHA-256 checksums and the snapshot cutoff (the export time) in `lab-data/grepmem-pilot/run/manifest.json`.
2. Ingest the exports with the existing WhatsApp importer (`temporal_memory/ingest/whatsapp.py` via the ingest CLI) into the pilot owner; let the normal extraction worker finish. Record how many messages were processed vs skipped (ingestion gaps must stay visible).
3. Freeze: note the owner's `facts_version`. No further ingest during the run.

## 3. Raw-search harness (`lab-data/grepmem-pilot/harness/`)

- Input: query clue(s) → ripgrep (or Python `re` if `rg` is missing) over the **fixed file allowlist only**, with a timeout (2 s), max 20 hits, and ±3 lines of context.
- Output per hit: `chat_id`, `line_start-line_end`, timestamp if parseable, and the full message, written to a file, not stdout. Preserve Arabic, English, spelling and multiline messages.
- Graph path: the existing explicit search (`/v1/owners/{owner}/search?include_lowered=true`) with an owner-device token for the pilot owner. Do **not** reinforce weights during the pilot (`reinforce=false`), so the two paths don't change each other.

## 4. Run the comparison (per the design doc)

1. **24 prompts, frozen before running:** 6 exact-detail (IDs, references, times), 6 paraphrase / Arabic-English variants, 6 correction or cross-message ("was Thursday confirmed or just suggested?"), 6 unanswerable or out-of-scope controls. Draft them with the **local** model from the exports, then the **founder** approves and edits them, together with the expected answer and supporting line ranges. Store them in `lab-data/grepmem-pilot/run/prompts.json`.
2. For each prompt, run two fresh sessions (raw search vs graph recall) with the same local model, answer prompt, evidence budget (≤3 retrieval calls) and a 60 s deadline, in randomized order. Log time to first sufficient evidence, time to final answer, tool calls, tokens and evidence refs.
3. **Blind scoring:** the founder scores, or the local model scores with path labels hidden and the founder spot-checks 8. An answer counts only if both the answer and its cited lines match the expected result. Controls pass only by abstaining without revealing out-of-scope content.
4. Tag misses: `ingestion_gap | retrieval_failure | unsupported_answer | scope_failure`.

## 5. Outputs

- **Private (lab-data):** `run/results.jsonl`, `run/report_private.md` with snippets, for the founder only.
- **Repo:** `apps/memory/upgrade/reports/GREPMEM_pilot.md`, aggregate only (no message text, names, numbers or chat titles):
  1. Setup: chat count, message count, the week's date range, model, budgets, ingestion processed/skipped.
  2. Results table by question type: wins / ties / misses for each path, and miss tags.
  3. Median paired latency (both correct) and the exact-detail latency delta.
  4. **Decision:** advance only if raw search recovers **≥ 3** verified answers the graph missed **or** cuts median latency **≥ 25 %** over **≥ 6** jointly correct exact-detail prompts, **and** there are **0** scope failures. Otherwise keep it as a local diagnostic.
  5. **How to use it (if it advances):** the graph-first fallback rule (when graph evidence is insufficient **and** a searchable clue exists), source scoping, D19/D19b behaviour (lowered sources excluded from passive use, explicit queries only), "Delete my data" and source revocation removing search access, the Rule 9 screen on outputs, no write-back, and the latency budget. Plus the held-out validation still needed.
- Then: append one `STATUS.md` row, commit **only** `GREPMEM_pilot.md` + the `STATUS.md` row on branch `grepmem/pilot-report` from `origin/main`, open a PR, and **STOP**.

## 6. Done means

The founder has the private report; the repo has the aggregate report with a clear advance / don't-advance decision; the pilot owner's sources are Lowered; `git status` shows no exports, harness or snippets anywhere in the repo.
