# Voice command eval — report

Run from the repo root: `npm run agents:eval` and `npm run agents:eval -- --set holdout`.
Use `npm.cmd` on Windows when PowerShell blocks `.ps1` wrappers.
Raw per-utterance results land in `eval/results/` (git-ignored); the regression gate is `tests/test_eval_gate.py`.

## Current snapshot (2026-10-08)

169 tests passed, 1 Redis test skipped. Offline dev 113/113, holdout 32/32, zero wrong recipients or premature
sends/unconfirmed paid actions; typecheck/build pass. The current closed catalog has 14 actions, including final-only
meeting drafts. q01-q03 are development regressions derived from the owner's restaurant case, not fresh holdout evidence.
Multi-turn items score the answer's final turn; asynchronous tests additionally verify the complete dependent sequence.

Current defaults: stability 0.35 s, act threshold 0.80, margin 0.30, simulated STT lag 0.35 s, eval silence 1.4 s.
Browser reply silence is 4 s; active streamed speech is capped at 120 s. These browser limits and live STT lag are
not reproduced by the fixed-silence eval. Cloud model connectivity, model accuracy/calibration and actual audio/UI
behavior remain unverified. Local models are deferred. Old cost estimates below belong to the historical 76-item run;
estimate a new paid run using the current corpus and configured budget before requesting approval.

## Historical baseline: what was measured (76 dev / 24 holdout)

- **Decider: the offline rule decider, not the model.** Tests and the eval use fakes unless a live run is approved.
  These numbers measure the *pipeline*: streaming, stability gate, clause splitting, self-corrections, the recipient
  guard, the act / undo / confirm / ask policy, and the argument rules. They do **not** measure the Decisions model's
  accuracy or calibration; the rule decider's probabilities are pseudo-probabilities, so its "calibration" below only
  proves the measurement works. Model numbers need one live run (≈ 7 decisions × 76 utterances × ~1k tokens ≈
  0.5 M input tokens ≈ **$0.06**; command: `AGENTS_LIVE=1 python -m eval.run_eval --live --name model`).
- **Latency is simulated.** Speech is 0.30 s + 0.03 s per letter per word, a comma adds 0.25 s, a partial transcript
  arrives 0.35 s after its word ends (assumed for `delay=minimal`, unmeasured), the engine ticks every 100 ms, end of
  speech is 0.6 s of silence. "−" latency would mean the action ran before the person finished.
- **Sets.** `utterances.jsonl` — 76 utterances in 8 categories (development set; it was used to find and fix rule
  gaps). `holdout.jsonl` — 24 utterances written after those fixes and never used to fix anything before its first
  run. **The honest generalisation figure is the held-out first run.**

## Historical results

| | Baseline (dev, before any tuning) | Held-out, first run | Dev, after fixes + tuning | Held-out, after fixes |
|---|---|---|---|---|
| Correct action, all steps | 81.6% | 87.5% | 100% | 100% |
| Correct action **and** arguments | **80.3%** | **83.3%** | 100% | 100% |
| Wrong-recipient sends/opens (target 0) | **0** | **1** | **0** | **0** |
| Paid without confirm / send before end of speech | **0** | **0** | **0** | **0** |
| Ask recall (should ask → asked) | 77.8% | 75.0% | 100% | 100% |
| Unneeded questions | 7 | 1 | 0 | 0 |
| In-app: last word → action, p50 / p95 | 0.60 / 0.60 s | 0.60 / 0.60 s | **0.50** / 0.60 s | **0.46** / 0.60 s |
| In-app: trigger word → action, p50 / p95 | 0.60 / 1.14 s | 0.60 / 1.14 s | 0.51 / 1.14 s | 0.49 / 1.14 s |
| Send/paid: last word → undo or confirm card, p50 | 0.60 s | 0.60 s | 0.60 s | 0.60 s |
| Decisions per utterance | 5.7 | 6.0 | 7.3 | 7.8 |
| Calibration of last decision (rules; ECE / Brier) | 0.016 / 0.051 | 0.049 / 0.015 | 0.030 / 0.029 | 0.024 / 0.001 |

The held-out wrong recipient was `tell Arif Kahn I'm here`: the first name matched exactly, so it sent to Arif Khan
with the text "Kahn I'm here". It now asks "Did you mean Arif Khan?" whenever the word after a first name is a
near-miss of that contact's surname.

## What changed between baseline and final

Generic fixes, each covered by a unit test (`tests/test_contacts_text.py`, `tests/test_engine.py`):

1. The per-utterance decision cap also blocked the *final* decision on long sentences (they fell through to chat).
   The cap now limits only early decisions.
2. Self-corrections: "…, actually never mind" withdraws the clause; long corrections splice in where the replacement's
   first word appears ("research electric cars, I mean electric motorbikes…"); a repeated preposition is handled
   ("in Dubai, no wait, in Sharjah").
3. Pronouns: "open Travel Buddies and send *them* …" uses the contact named earlier in the same sentence.
4. Message text: "the Study Group", "a message saying …", "let the Gaming Squad know …", "ask X if he's …" → "Are you …?".
5. A lone verb ("open"), a bare name ("Sara") or "make something cool" now asks instead of going to chat.
6. Words like "I'm" are never treated as a name; a message body ("it's sunny") no longer votes for another action.
7. Recipient guard: when a near-namesake exists, only a spoken multi-word full name is accepted ("Sara Ali"); "Sara",
   "Omar" or "Lena" alone ask, because the transcriber takes no vocabulary hint and can swap them.
8. Eval scorer bug: two-turn items scored the expected first-turn question as an error.

## Tuning: the stability gate

A partial transcript is decided once it has been unchanged for `stable_s`. Sweep on the dev set (accuracy and safety
identical in every row):

| stable_s | added decision latency | in-app last word → action p50 / p95 | send/paid p50 | decisions / utterance |
|---|---|---|---|---|
| 0.30 (baseline) | 0 ms | 0.60 / 0.60 s | 0.60 s | 5.6 |
| 0.20 | 0 ms | 0.60 / 0.60 s | 0.60 s | 6.7 |
| **0.10 (chosen)** | 0 ms | **0.50 / 0.60 s** | 0.60 s | 7.3 |
| 0.00 | 0 ms | 0.40 / 0.60 s | 0.60 s | 7.3 |
| 0.10 | 150 ms (vendor claim, unverified) | 0.65 / 0.75 s | 0.75 s | 7.3 |

Historical choice: 0.10 s (current default is 0.35 s). 0.00 is faster in simulation, but real transcription deltas arrive in sub-word pieces, so a small
debounce avoids deciding on half words. The extra decisions cost ≈ $0.0002 per utterance at the approved price.

**Where the time goes:** the floor is transcription lag (assumed 0.35 s) for in-app actions and the end-of-speech
silence (0.6 s) for sends and paid actions, which wait for the end on purpose. The decision step adds its own latency
on top (rules ≈ 0 ms; the model's is unmeasured). The next real gains are a live measurement of the transcriber's lag
at each `delay` setting, and a shorter silence window once false end-of-speech is measured.

## Thresholds (act ≥ 0.80, margin ≥ 0.30)

Not tuned: the rule decider's probabilities are not real, so a threshold sweep on them would tune nothing. After a
live run, sweep `--threshold` / `--margin` on the dev set and choose the lowest threshold with zero wrong recipients
and zero wrong actions; then report the held-out set once.

## Phase 3 (2026-10-08): fast commands, "last chat", email, and the live model

New closed actions: `read_messages`, `check_notifications` (in-app), `compose_email` (in-app: opens a filled-in email,
never sends), `plan_trip` (confirm: it files leave and searches flights) — 13 actions in all. "My last chat" resolves to
the most recent conversation (the browser sends contacts most-recent first).

**Held-out first runs, written before any rule for them existed:** 6 items → **5/6** (`show me my research` tied
*open screen* with *research a topic* and asked; generic fix: "my/the/your research" is the screen, "research X" the
verb); 2 later items (`open the latest chat`, `write an email to Omar …`) → **2/2**. Wrong recipients: **0** throughout.

| Now (rules, offline) | Dev (92) | Held-out (32) |
|---|---|---|
| Correct action and arguments | 100% | 100% |
| Wrong-recipient sends/opens | **0** | **0** |
| Paid without confirm / send before end of speech | **0** | **0** |
| In-app last word → action, p50 / p95 | 0.51 / 0.60 s | 0.49 / 0.60 s |

**The fast path (measured live, end of speech → event over the voice socket).** Short in-app commands that name nobody
and that the rules decide at p ≥ 0.95 skip the model: `check my notifications` 33 ms, `read my messages` 25 ms,
`open my mail` 26 ms, `open my last chat` 30 ms — versus 220–550 ms when the Decisions model decides. Anything with a
person's name, anything outward or paid, and long clauses always go to the model and the exact-name guard
(`tests/test_fast_path.py`).

**Live Decisions model, a handful of probes (not a measured set):** it first answered *none* (0.72) to
`what did Mazen say` and hesitated on `open my last chat` (0.55); sharper action descriptions fixed both (0.80 → read
Mazen's messages; the last-chat commands now act). A proper live eval run is still the open item above.

**Speech-to-text.** Fixed in the browser: the 24 kHz conversion dropped samples without filtering (aliasing); it now
averages them. Transcriber settings now match each model (SDK types, `tests/test_stt_config.py`): `gpt-realtime-whisper`
takes `delay` only (default raised from `minimal` to `medium`: steadier words, a little later); `gpt-live-transcribe` /
`gpt-transcribe` take `keywords` (contact names + app words) and English + Arabic. Not yet measured live.

**Timing, re-tuned for live speech (2026-10-08).** In live use a turn ended after 0.6 s of quiet, which cut people off
mid-thought ("Open… my last chat" became "Open."), and clauses were decided after 0.1 s of a steady transcript, which
acted on half-heard words. Now: end of speech = **1.4 s** of quiet (`STREAM_SILENCE_MS`), a clause must be steady for
**0.35 s** (`AGENTS_STABLE_S`). In-app actions still run mid-sentence once steady; sends and paid actions wait for the
end. Simulated cost, same sets: in-app last word → action p50 0.75 s (dev) / 0.78 s (held-out), sends 1.4 s; accuracy
and safety unchanged (100%, 0 wrong recipients). A quick correction ("open mail, actually calendar") no longer opens
Mail first (`tests/test_engine.py`).

## Phase 4 (2026-10-08): open-then-dictate, the also-router, regions, mention-only groups

"Open the last chat and reply with …" used to lose the reply: bare "reply" scored `none` and the clause vanished.
Now bare "reply (with/saying) …" heads a send; a reply that names nobody goes to the chat this turn opened or read
(same sentence or, carried across turns for 60 s, the next one); a spoken name always wins and the exact-name guard
is unchanged. "Open chat" opens the chats screen, while "the Gaming Squad chat" still opens that conversation. When
the chat opens mid-sentence with dictation still coming, the act carries `awaiting: "reply"` and the browser holds
the turn open (4 s quiet, 30 s max) instead of cutting it at 1.4 s.

"But also / and also / also" goes through a router: it splits only when a preset command head follows ("…and also
plan the trip" → message + plan, the plan taking the reply's recipient as its companion, still confirmed): anything
else stays dictation ("…but also bring chips" is sent whole). `@mirsal open/read/reply …` is decided by the same
engine (`POST /agents/mirsal/command`, this user's chats most-recent first) instead of the generic chat model.

The planner no longer forces a country: 9 European destinations added, a region ("europe") or no destination asks
which country, and the group step appears only for explicitly mentioned people — unrecognized names ride along as
`suggested` for the in-card "Select users" picker rather than being dropped. New items o01–o08 (dev, 100 total):
100% action and args on both sets, 0 wrong recipients (`npm run agents:eval`, `--set holdout`).

Answers to open questions are classified, not bounced to chat: a bare name or "my last chat/message" settles an
unresolved recipient ("reply with hello" → "my last chat" sends it to the most recent chat); words to a settled
recipient are the dictated message ("tell Arif" → "I'm on my way" sends it); a full command as the answer runs as
one. Unfinished sends ("tell him", "tell him that") hold the turn open like bare replies do. A dangling "reply
him/her …" with no other context defaults to the most recent chat (g05, x22 reclassified — x22's holdout
expectation updated for the new contract; the undo card names them, so a wrong guess stays cancellable).

## Phase 5 (2026-10-08): trace-driven dictation repair

The supplied live trace had 7 voice turns, 23 recorded rule decisions with model connection errors and 6 fast-path
decisions; no model-sourced decisions. Its final utterance combined the reply and a visit-planning request into the
outgoing message. Review also reproduced a wrong-recipient case: "open Study Group and reply to him saying Arif is
coming too" targeted Arif because contact matching read the body. Recipient parsing now happens before dictation;
body names/dates cannot override the recipient. Unfinished pronoun replies ask for the words to send.

Streaming and final routing share the same command boundaries. `read` splits; "and bring chips" / ". Bring drinks
too" stay in the body. Visit planning clarifies trip vs appointment, retains the original date and companion, and
only starts a trip through Confirm. The final clause plan and dictation-hold status are recorded in the voice trace.

Eight new dev items p01–p08 were derived from these failures, so these are regression numbers, not new held-out
generalisation evidence. Message arguments now require the same words in the same order after case/punctuation
normalisation; the old ≥0.8 token-overlap scorer could accept leaked command prefixes or missing message words.

| Offline `trace-fixes` run | Dev (110) | Unchanged holdout (32) |
|---|---|---|
| Correct action and arguments | 100% | 100% |
| Wrong-recipient sends/opens | 0 | 0 |
| Premature sends or unconfirmed paid execution | 0 | 0 |

Tests: 161 passed, 1 Redis test skipped. The transport tests cover standalone dictation and a reply arriving after a
chat already opened; the hold is a listening status, not a repeated navigation act. The browser now keeps 4 s quiet /
30 s total for the remainder of dictation, without the old 8 s expiry, and the voice island leaves the screen clear.
The eval still uses fixed 1.4 s silence: its latency figures do **not** model this browser hold or live transcription
lag. No paid/live calls were started for this repair. Connectivity, STT quality and the new hold still need live
verification after restarting the service.

## Long-audio follow-up (2026-10-08)

Streamed active speech now has a 120-second limit (replacing the earlier 15/30-second limits above); reply silence
remains 4 seconds. Asynchronous regressions verify that a revised transcript discards an in-flight old decision,
and that dictation hold arrives while the classifier is blocked; final classification waits for cancellation,
then sends the whole long reply once. 161 tests passed, 1 Redis test skipped. Dev 110/110 and holdout 32/32 remain
offline results; the owner's long-audio live test and cloud model connectivity are not yet verified.

## Meeting draft follow-up (2026-10-08)

Added `plan_meeting`, a final-only calendar draft action. q01-q03 are dev regressions derived from the owner's
restaurant example: a proposal plus meeting draft; the full first utterance including Sara clarification; the
recipient answer resuming Sara's message and draft. The eval scores a multi-turn item's last turn, so the complete
sequence is separately checked in `tests/test_meeting.py` for both streamed and final-only input, including a
contact-list reorder between the question and answer. Unchanged holdout remains untouched.

169 tests passed, 1 skipped; dev 113/113 and holdout 32/32, zero wrong recipients or premature/unconfirmed paid
actions. These are offline fallback regressions, not new cloud generalisation evidence. Date/place extraction is
bounded and drafts require review/save. Frontend executor/form/store integration checks passed; live audio/cloud
and an actual browser interaction with the draft are still unverified. Local models remain deferred.
