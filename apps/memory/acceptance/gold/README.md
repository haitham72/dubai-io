# P1A gold set (Muse) — Karim Haddad, synthetic 30-day corpus

Regenerate: `python apps/memory/acceptance/gold/tools/generate.py` (seed 42, deterministic), then `python apps/memory/acceptance/gold/validate.py`.

## Layout

- `ledger.json` — truth: persona, 25 people (2–3 aliases each), 12 subjects, 9 orgs, 8 places,
  110 facts (each with `evidence: [record_ids]`), 43 typed edges, 4 alias traps.
- `sources/whatsapp_best.txt` (310), `whatsapp_work.txt` (310), `whatsapp_family.txt` (310):
  one message per line, `[M/D/YYYY, H:MM:SS AM] Sender: text`.
- `sources/gmail.jsonl` (200): `{id, thread_id, ts, from, subject, body}` — 30 planted,
  42 neutral admin, 128 noise (~64%).
- `sources/notes.md` (42): `[nNNN] YYYY-MM-DD | text`.
- `ingest_order.json` — record IDs in harness ingest order (chronological except 4 late
  records, documented under `late_records` with the newer fact each must not overwrite).
- `probes.json` — 40 live probes with gold MemoryInsight + `must_not_contain` +
  `gold_context_fact_ids`. Buckets: person 7 + person_alias 3, contradiction 10,
  twohop 8, arabic 6, sensitive 4, noise 2.

## Record IDs

WhatsApp `{wab|wag|waf}-NNNN` = 1-based line number in that file. Gmail `gNNN`
(chronological file order). Notes `nNNN` (chronological). The harness maps adapter
memories back to ledger fact IDs through these IDs (`ledger.facts[].evidence`).

## Conventions the scorer should know

- `relation_to_user` follows the PLAN §4 enum: manager/ex-colleague → `colleague`;
  recruiter/neighbour/coach/trainer/dentist/agent/salesman/instructor → `null`.
- Contradiction `memory_id` is the OLD (pre-image) ledger fact ID.
- Sensitive probes: gold `context_memory_ids` deliberately EXCLUDES the gated fact
  (non-sensitive neighbours only); the gate is scored via `gated` + `must_not_contain`.
- Late arrivals (f005 rent receipt, f029 interview confirm, f041 course payment,
  f050 Camry note) ingest after their newer facts; assert newer `valid_from` wins.
- Gated categories used: `family_health`, `third_party_relationship`,
  `third_party_faith`, `credential`, `third_party_money`, `third_party_legal`,
  `third_party_health`.

## P2 additions (milestones / trivia / profile)

- `ledger.milestones` (ms01–ms06): title, `status_by_week` (weeks W1 10-20..10-26, W2 10-27..11-02, W3 11-03..11-09,
  W4 11-10..11-16, W5 11-17..11-19; `null` before first tracking week),
  `fact_ids` (≥2 facts, ≥2 days), `first_week` (week of first supporting fact).
- `ledger.trivia` (tr01–tr12): source-present events that must not become milestones,
  each with existing `record_ids`.
- `ledger.profile` (7 Quest sections, 22 claims with `fact_ids` + `first_week` =
  week by which all cited facts exist) + `ledger.must_not_claim` (3 traps).
- No new source records were needed; all evidence already existed. Base (110 facts,
  1,172 records, 40 probes, ingest order) is byte-identical to the frozen commit —
  enforced by `validate.py` §7 via `git show HEAD:`.

## Known unrealism

- WA noise is template-cycled (~24 templates/chat), so phrasing repeats; planted lines
  carry all scorable content. Family chat includes two neighbours (building coordination).
- Gmail noise senders/domains are invented (`*.example`); OTP codes are fixed strings.
- One extra `changed` pair exists beyond the specified 6 (rent f003→f004, needed so the
  late-arriving receipt has a newer fact to trail).
