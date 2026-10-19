# Handoff: Dubai-io, 19 Oct 2026 (evening)

**Branch:** `redesign`. **Read order:** `CLAUDE.md` → `PLAN.md` (19 Oct decisions in its header) → `ARCHITECTURE.md` → this file → `docs/main-llm-adjudication.md` (review verdicts, critical path §7). The other reviews in `docs/` are frozen.

## 1. Run it

```powershell
cd apps/api
.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

| URL | What |
|---|---|
| `http://<host>:8000/` | The app (`#wifi`, `#intro`, `#services`, `#guide`, `#profile` jump to flows) |
| `http://<host>:8000/merchant.html` | Sandbox merchant inbox + operator Demo triggers. PIN: `MERCHANT_PIN`, or generated into `apps/api/data/merchant.pin` at startup |
| `http://<host>:8001/miniapps/…` | Separate widget origin (same process; `WIDGET_PORT`, 0 disables) |

`.env` (in `apps/api`, not committed): `OPENAI_API_KEY`, `GOOGLE_PLACES_KEY` (Places + Routes), optional `LUNA_EFFORT` (local is `low`: median 2.3 s vs 4.7 s at `high`, same 4/4 accuracy on the bench), `MERCHANT_PIN`. Web assets are served `no-cache`, so phones pick up edits on reload.

## 2. What works end to end (verified in a browser, 19 Oct)

1. **Luna** runs at `/` (gated on `/api/health`, not the URL path). Understanding only; facts the user states show once as "You told me".
2. **One order path.** Partner mini-app (separate origin, `sandbox="allow-scripts"`, CSP `connect-src 'none'`) asks via `order.request` → server rebuilds items/total from `apps/api/app/catalog.py` (widget prices ignored) → one approval card listing exact shared fields → `order.request` capability with the sandbox inbox adapter → `SUBMITTED` with a server reference.
3. **Merchant inbox** (`merchant.py`): separate role, sees only its provider's orders and approved fields. Accept (with ready time) / confirm time / ready / complete / decline; idempotent; canonical states only.
4. **Live status in chat** over SSE (`/api/actions/{id}/stream`, 1.5 s poll fallback); the card survives reload.
5. **Deadline loop:** server compares the merchant's ready time with the user's stated deadline; "Ask for 08:30, same price" → merchant confirms → "meets your deadline. Confirmed by the shop, not by me."
6. **Proactive** (`proactive.py`): outbox with `dedupe_key`, consent, quiet hours 23:00–07:00 Dubai. "Remind me before it's ready" schedules a user reminder; operator triggers (`fast_forward_reminders`, `flight_landed`) arrive labelled **Demo trigger**.
7. **Profile** (`profile.py` + `profile-store.js`): real choices become episodes (allowlisted hypotheses only; sensitive traits cannot be stored); Confirm / Not true / Forget persist; Forget unlinks evidence. Fixture history is labelled "demo history".
8. **Google live:** Routes ETA in the ride card ("Estimate · Google"); Places "Also nearby on Google" list on offers (discovery only, attributed, no prices, no map pins).
9. **UI rule:** no shadows; AI text plain, user turn tinted box, actions in white rounded boxes (`stage-v3.css` "clean chat").

## 3. Tests

`cd apps/api; .\.venv\Scripts\python -m pytest -q tests` → **62 passed, 11 skipped** (live Luna golden set; `$env:RUN_LIVE=1` before rehearsals).
`node apps/web/tests/{profile,recovery,luna-client}.test.mjs` → 92 + 8 + 9.

## 4. Remaining (see adjudication §7)

- Taxi-memory payoff check on the stage path (step 11) and the "Scripted demo" label.
- Rehearsal: 10 timed 4:00 runs on phone + second device; record the fallback video (step 15).
- Optional: push-to-talk voice spike (step 14).
- Stage-only: merchant tablet/phone on the same LAN; pre-warm one Luna turn.
- Not production: SQLite, anonymous cookie sessions, sandbox merchant PIN; no real merchant yet (`PLAN.md` §5).
