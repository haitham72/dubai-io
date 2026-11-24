# E1 — One command starts everything on the founder's PC (Gemini)

Read `E0_real_data_round.md` first. Branch `e1/run-stack` from `main`.

## Owned files

- new `scripts/dev/` (`start-all.ps1`, `stop-all.ps1`, `health.ps1`, `README.md`)
- `.env.example` files: add **names** only, never values
- nothing in `apps/*` source

## Deliverables

1. **`start-all.ps1`**, idempotent and safe to rerun. It starts, in order:
   - **Memory stack:** `apps/memory` docker compose: postgres, rabbitmq, redis, then `api` (:8040) + `worker-p0` + `worker-p1` + `beat`.
   - **Workers' LLM:** the CLI runner with the founder's `claude -p` subscription (`config.py` `cli_command`, Haiku, medium effort). If LM Studio is up on :1234, the local Qwen pool is used first for owner-device jobs. Print which runner is active.
   - **`apps/api`** on :8000 with its own venv. Set `MEMORY_BRIDGE_BACKEND=http`, `TM_BASE_URL=http://localhost:8040` and a service token created through the memory API's admin flow (store it in `apps/api/.env`, never print it).
   - **Website:** Expo web for `apps/mobile` (`npx expo start --web` or a served `expo export`) on a fixed port; print the URL.
   - **iPhone:** the Expo dev server bound to the LAN, printing the QR. Plus the one-time Windows firewall rule for the ports (document it; ask before adding it).
   - **Desktop app:** `apps/desktop` dev start.
2. **`health.ps1`:** a green / red table: each container, `/health` of the memory API and `apps/api`, the queue depth, the active LLM runner, the website URL, the LAN IP. It exits non-zero on any red.
3. **`stop-all.ps1`:** stops everything cleanly. The database volume is kept.
4. **`scripts/dev/README.md`:** prerequisites (Docker Desktop, Node, Python venvs, the `claude` CLI signed in) and the founder's one-time Google Cloud Console steps:
   - the authorized redirect URIs that E2 uses (`http://localhost:<port>/...`; get the exact paths from E2's report, or leave placeholders and say so);
   - enable the Gmail, Calendar and YouTube Data APIs;
   - consent screen in **Testing**, with the founder's Gmail as a test user.
5. **Test:** run `start-all` → `health` (all green) → `stop-all` → `start-all` again (idempotent). Paste the outputs in the report. Secrets must not appear in any output.

**Report** → `reports\E1.md`.
