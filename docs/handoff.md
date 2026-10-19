# Handoff: Dubai-io monorepo build, 19 Oct 2026

**Branch:** `redesign` (current working branch).  
**Read order for any incoming LLM:** `CLAUDE.md` → `PLAN.md` → `ARCHITECTURE.md` → `docs/handoff.md` → `docs/gemini-review.md`.

---

## 1. Clean Monorepo Architecture (Completed 19 Oct)

The repository layout has been modernized to eliminate the confusing `demo/` folder structure:

```
dubai-io/
├── apps/
│   ├── web/                    # Active frontend (HTML/CSS/ES modules; Wi-Fi arrival, coverflow, guide, services, chat)
│   └── api/                    # Backend API (Python 3.13, FastAPI, LangGraph Luna agent, Places/Routes)
├── design/
│   ├── references/             # UI flow reference images (01 - visitor wifi.jpg, carousels, flow PNGs)
│   └── screens/                # High-level mockups & montage exports
├── docs/
│   ├── handoff.md              # This handoff document
│   ├── DUBAI-IO_Product_Enhancement_Review.md # Strategic product review (Oct 18)
│   ├── gemini-review.md        # Architectural review & next steps (Oct 19)
│   ├── references/             # redesign.md, visuals-libraries.md
│   └── services/               # cases.md, intake.md
├── CLAUDE.md                   # Agent engineering rules & constraints
├── PLAN.md                     # Contest plan, scope boundaries, phases
├── ARCHITECTURE.md             # Target contracts & architecture
└── README.md                   # Quickstart guide
```

* **Legacy `demo/` Retired:** The obsolete prototype (`demo/index.html`) has been completely removed from the `redesign` branch (preserved in `main` history).
* **`feat/miniapp-bridge` Stale Branch Deleted:** The stale bridge branch and temporary worktree were pruned.
* **Unified Single Origin:** `apps/api` serves `apps/web` directly at `http://localhost:8000/`. `apps/web/index.html` (the Wi-Fi arrival flow) is the default entry point.

---

## 2. Current Implementation State

- **Wi-Fi Arrival & Onboarding (`apps/web/arrival.js`):**
  - iOS Wi-Fi settings mock (`#wifi`) → Join "Airport Free Wi-Fi" → Captive sign-in sheet ("Welcome to Dubai · sponsored by Dubai-io") → Install sheet ("Dubai-io / Your Dubai companion", GET) → App expands into coverflow onboarding.
- **Home Stage & Services:**
  - Shader coverflow stage (Cyan theme; C1 reflection at 70% intensity = 0.385).
  - Universal services catalog (`apps/web/offers.js`, `services.js`) with grouped categories, published fixed prices, and sandboxed mini-app modal sheets.
- **AI Companion (Luna):**
  - `apps/web/chat.js` communicates with `POST /api/luna/turn` on `apps/api`.
  - Falls back gracefully to the labelled client router if backend is offline.
  - User stated facts stored in `apps/api/data/memory.json` with "You told me" badges and full view/edit/forget endpoints.
- **Action Persistence:**
  - `apps/api/app/actions.py` implements anonymous sessions, SQLite storage, idempotent approval tokens, and strict status gating (`UNKNOWN_STATUS`).

---

## 3. Test Verification (100% Green)

1. **Backend Tests:**
   ```powershell
   cd apps/api
   .\.venv\Scripts\pytest
   # Result: 40 passed, 11 skipped (paid golden cases) in 1.73s
   ```
2. **Frontend Tests:**
   ```powershell
   node apps/web/tests/profile.test.mjs
   node apps/web/tests/recovery.test.mjs
   # Result: 100 passed, 0 failed
   ```

---

## 4. Immediate Next Objectives (For Incoming / Main LLM)

1. **Review Strategic Docs:**
   - Read [`docs/DUBAI-IO_Product_Enhancement_Review.md`](DUBAI-IO_Product_Enhancement_Review.md) (comprehensive product review) and [`docs/gemini-review.md`](gemini-review.md) (architectural recommendations).
2. **Execute the Single Live Agentic Proof:**
   - Connect the chat UI in `apps/web/chat.js` to `apps/api` so a natural language request (e.g. laundry pickup or barber) prompts Luna to return a structured **Approval Card**.
   - User tapping **"Approve and send"** dispatches the request to the backstage merchant inbox (`/merchant` or backstage sheet).
   - Simulating the merchant tapping **"Accept"** sends a verified event back to the chat thread with a confirmed status.
3. **Stage Demo Rehearsal (4-Minute Cut):**
   - Ensure the sequence *Wi-Fi captive sign-in → Coverflow intro → Service ask → Approval card → Merchant dispatch → Fine appeal twist (simulated)* runs smoothly within 4 minutes.
