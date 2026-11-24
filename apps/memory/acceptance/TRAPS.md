# S7 Live-Triple Trap Dataset (`TRAPS.md`)

Labelled dataset: [`traps_dataset.json`](traps_dataset.json) (**84 items**, synthetic only; `apps/memory/acceptance/traps_dataset.json`).

## Breakdown by Category & Language

| Category | Expected Action | EN | AR | ARZ / Mixed | Total |
|---|---|---:|---:|---:|---:|
| `positive` (`buys`, `books`, `visits`, `likes`, `wants`, `owns`, `moves_to`, `joins`) | `emit_triple` | 12 | 8 | 8 | **28** |
| `negation` | `no_triple` | 4 | 3 | 2 | **9** |
| `question` | `no_triple` | 4 | 2 | 2 | **8** |
| `plan` (future / conditional / hedging) | `no_triple` | 4 | 2 | 2 | **8** |
| `third_party` (another person's action) | `no_triple` | 4 | 2 | 2 | **8** |
| `quoted_or_promo` (quotes, forwards, ads, headlines) | `no_triple` | 4 | 2 | 1 | **7** |
| `sarcasm` | `no_triple` | 4 | 1 | 1 | **6** |
| `code_switch_trap` (mixed EN/AR/Arabizi negation/conditional/3rd-party) | `no_triple` | 0 | 0 | 5 | **5** |
| `sensitive_rule9` (health, family health, faith, credential) | `quarantine` | 4 | 1 | 0 | **5** |
| **Total** | | **40** | **21** | **23** | **84** |

## Representative Examples
- **Positives:** `"I bought an iPhone yesterday"` (`buys -> iPhone`), `"booked Zuma for Friday"` (`books -> Zuma`), `"had dinner at Zuma in DIFC, loved it"` (`visits -> Zuma`), `"اشتريت آيفون جديد امبارح من دبي مول"`, `"eshtereet iPhone 16 embara7"`.
- **Negation:** `"I didn't buy the iPhone after all, too expensive"`, `"ما اشتريتش الآيفون في الآخر"`, `"mesh eshtereet el iPhone khalas"`.
- **Questions:** `"Should I buy the iPhone 16 Pro or wait?"`, `"Did I book Zuma for Friday or Saturday?"`, `"ro7t Zuma abl keda"`.
- **Plans:** `"I'm going to buy an iPhone next month if the bonus lands"`, `"رح أشتري لابتوب جديد الشهر الجاي"`.
- **Third-party:** `"Omar bought an iPhone yesterday"`, `"سلمى بتقول إنها حجزت في زوما"`, `"Nour naqalet Marina el shahr elly fat"`.
- **Quoted/Promo:** `"He texted: \"I bought an iPhone yesterday\""`, `"Promo: Buy an iPhone 16 today and save AED 500! Unsubscribe anytime."`.
- **Sarcasm:** `"Yeah sure, I totally bought another iPhone 🙄"`, `"آه طبعاً اشتريت فيلا في النخلة امبارح 😂"`.
- **Rule 9 sensitive:** `"My father takes diabetes tablets every morning"`, `"My wifi password is BarshaL0bby!"`.

## Scoring Protocol (for U2+)
1. **Overall emission precision:** `correct_emitted / total_emitted` (an emission on any `no_triple` or `quarantine` item is a false positive; an emission with wrong actor/predicate/object/polarity is incorrect). Target: **≥ 0.90**.
2. **`user_supplied` emission precision:** `correct_user_supplied / total_user_supplied` (no inferred, negated, third-party, or uncertain item may carry `provenance='user_supplied'`). Target: **≥ 0.98** (plan §6).
3. **Positive recall:** `correct_emitted_on_positives / 28` (and reported per language EN / AR / ARZ).
4. **Trap false-positive rate (per category):** `false_emissions_in_category / category_count`. **Zero** (`0/5`) allowed on `sensitive_rule9`.
5. **Latency:** p95 `< 50 ms` with **0 LLM calls per message**.
