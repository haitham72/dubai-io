# AI Image Cleaner ("Clean AI Detection")

Wraps `agents/mirsal_agents/ai_cleaner_engine.py` (the battle-tested script, do not
edit its settings from code) in one shared FastAPI backend used by the Apps screen
and the `@mirsal clean …` chat skill.

## Run it

The engine must import where the service runs: the interpreter behind
`npm run agents` needs `remove-ai-watermarks==0.45.1`, CUDA torch, and Pillow.
Today that is the sibling env (`../remove-ai-watermarks/venv`), **not**
`agents/.venv`. Either run the service from that env:

```powershell
cd agents
G:\Haitham\VsCode\remove-ai-watermarks\venv\Scripts\python.exe -m uvicorn mirsal_agents.app:app --port 8787 --reload --timeout-graceful-shutdown 2
```

or install the engine deps into `agents/.venv` (torch CUDA wheel is several GB).
Then start the app as usual (`npm run dev` + the service above).

Settings live in `mirsal_agents/config.py` (`Cleaner`, `CLEANER_*` env vars) — tune via env
and restarting the service (`--reload` picks it up). There is no settings API.

## Stages (server-owned)

`GET /agents/ai-cleaner/jobs/{id}` returns `{stage, note, percent?, done, …}` and
the frontend renders it verbatim — no stage logic in the UI:

`Checking image → Resizing image → Cleaning AI traces → Faces found (N) / No faces found / Preserving faces → Presenting result`

`resize` skips cleaning/faces; `sdxl` skips resizing. The SDXL child's terminal
flood (model logs, progress bars) is piped server-side, tailed to the last 200
lines in server logs only, and classified into the stages above — raw logs never
reach the client. The faces count appears only if the installed CLI prints a
parseable one; otherwise the stage reads "Preserving faces" with no number.

## Endpoints

- `POST /agents/ai-cleaner/jobs` (multipart `image` + `mode`, default `resize_then_sdxl`; needs `python-multipart`) → `{job_id}` (400 bad file/mode)
- `GET /agents/ai-cleaner/jobs/{id}` → stage payload (per-user isolated; 404 unknown or another user's job).
  The payload carries `stages`: the server-owned ordered checklist for the job's mode. The frontend renders
  `stages` verbatim and slots the live faces wording before "Presenting result" (`visibleStages` in
  `src/apiclient/cleaner.ts`); stage order/filtering lives nowhere else.
- `GET /agents/ai-cleaner/jobs/{id}/file` → cleaned JPEG (409 until ready)
- `GET /agents/ai-cleaner/capabilities` → `{modes, engine: "ai_cleaner_engine", verify_openai}`
- `POST /agents/ai-cleaner/verify` → official OpenAI Content Provenance check (401 bad key, 502 OpenAI error).
  **Registered only when `OPENAI_API_KEY` is set**; each call is one explicit tap
  (private images never leave the device automatically). Maps the real response
  into `{c2pa, synthid, overall}`; unknown fields stay `unknown`, never invented.
  A negative result reads `No supported OpenAI provenance signal detected` —
  that is not a claim the image is AI-free.

One GPU job runs at a time; extras queue FIFO. Limits: JPEG/PNG/WebP, 50 MB.

## Privacy

Uploads live under `agents/.data/ai-cleaner/<job_id>/` with random IDs, isolated
per `x-mirsal-user`. No keys in frontend code or logs, no raw pixels in logs.

**No local scanner can guarantee whether Instagram will label an image as
AI-generated.** Absent metadata is not proof nothing AI happened. There is no
Instagram integration of any kind.

## Frontend + chat skill

- Screen `src/screens/ai-cleaner/` (registered as `"ai-cleaner"` in `src/screens.ts`; Apps tile "Clean AI Detection", desktop nav "Clean AI"). Renders the stage payload verbatim — no stage logic in the UI.
- `@mirsal clean …` (`clean` skill in `src/chats/skills.ts`): trigger words remove/clean/strip/erase/wipe/bypass/evade/fool + AI/watermark/fingerprint/trace/signature/mark/tag/label (incl. Arabic and "make undetectable"). Default mode `resize_then_sdxl` (`resize only`/`fast` → `resize`, bare `sdxl` → `sdxl`); polls the job every 1 s up to 600 times, then points at the Apps screen. Client functions live in `src/api.ts` (`CleanMode`, `CleanJob`, `CleanerCapabilities`, `OpenAiVerify`, `startCleanJob`, `getCleanJob`, `cleanFileUrl`, `verifyCleanImage`, `getCleanerCapabilities`).

Modes: `resize` skips cleaning/faces, `sdxl` skips resizing; anything else defaults to `resize_then_sdxl`.

Backend tests: `agents/tests/test_ai_cleaner.py` (10, socket-free). Job uploads live under `agents/.data/ai-cleaner/` and model weights under `agents/*/models/` — both git-ignored, never committed.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Job fails "remove-ai-watermarks CLI missing" | Service is running from an env without the package — see Run it above. |
| Job fails "GPU unavailable" / CUDA OOM | Close GPU-heavy apps (needs ~6 GiB free); RTX 4080 16 GB is the tested box. |
| `agents:test` socket errors in locked-down shells | Pre-existing: TestClient/event loops need loopback sockets. `test_ai_cleaner.py` is socket-free and runs anywhere. |
| Stale CA errors on pip | Clear `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` (see run.md). |
