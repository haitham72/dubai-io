# Developer Test Bench

Branch `dev/dubai-io` starts from `origin/main` at `1ea0d3b`. The main API mounts the buildless page at `/testbench/` only with `DEV_TESTBENCH=1`. The dev launcher supplies that flag and makes the Test Bench origin available to the Community and Messenger APIs. If the stack was already running, restart the three APIs to load the new process environment.

## Endpoints covered

| Area | Existing endpoints exercised |
| --- | --- |
| Identity | `GET /api/identity/google/start`, `POST /api/identity/google/exchange`, `POST /api/identity/pair/start`, `POST /api/identity/pair/complete`, `GET /api/identity/me`, `GET /api/identity/sessions`, `POST /api/identity/sessions/revoke-all`, and `POST /api/identity/delete-my-data`. Delete requires typing `DELETE` and sends `{"confirm":true}`. |
| Dubai IO | `GET /api/ingest/status`, `PUT /api/ingest/consent/{source}`, `POST /api/ingest/google/{source}/connect` for Gmail, Calendar, and YouTube, `POST /api/chat/turn`, `POST /api/identity/memory-device-token`, `GET /v1/owners/{owner}/search` with and without `include_lowered=true`, `GET /api/vault/timeline` with and without `lowered=true`, `POST /api/vault/lower` for fact or source and Lower or Restore, and `GET /api/today`. |
| Community | `GET /api/identity/me`, `GET /api/community/feed`, `GET /api/community/follows`, `POST /api/community/posts`, `POST /api/community/posts/{id}/comments`, `POST /api/community/posts/{id}/vote`, `GET /api/community/discovery`, `PUT /api/community/profile/usage/settings`, `POST /api/community/context/heartbeat` with a manually picked coarse area, `GET /api/community/profile/usage`, `POST /api/community/memory/lower`, and `GET/PUT /api/community/memory/consent`. |
| Messenger | `GET /api/identity/me`, `GET /api/messenger/conversations`, `POST /api/messenger/conversations/{id}/messages`, `POST /api/v1/memory-bridge/messenger/conversations/{id}/recall`, `GET /api/messenger/memory`, and `POST /api/messenger/memory/lower` for both Lower and Restore. |
| Health | `:8000/api/health`, `:8060/api/health`, `:8070/api/messenger/health`, and `:8040/health`. |

The page reports the method, URL, app-controlled headers and body, HTTP status, and server response. Credential fields are redacted in the display. Session and memory bearer tokens stay in page memory. Google sign-in also uses the existing HttpOnly cookie option. The page immediately removes the server-issued, single-use OAuth exchange code from the callback URL. OAuth redirects use browser navigation and have no JSON status panel for the redirect itself. The exchange and connector start JSON responses have their own panels. Connector authorization links come from the server.

## Existing endpoint limits

- Community has no dedicated Following feed endpoint. The bench keeps both raw responses and displays the subset of feed posts whose owners appear in the follows response.
- The memory server exposes health and search at port 8040 without browser CORS headers. Those requests can be blocked from the port 8000 page. When blocked, the page reports the browser error, and memory health can also be opened directly. The main API has no existing session-authenticated general memory search or explicit-recall proxy. Product memory and its CORS behavior remain outside this change.
- Google sign-in accepts loopback web return URLs. Pairing is the existing LAN flow. A code is single-use, so use a fresh code per app. Google ingest authorization needs a Quest cookie for its browser callback, available after PC Google sign-in.

## Account deletion fixes

The identity route always calls the Community purge. The purge obtains its store through `engine()`, which initializes it on first use in a Messenger process. The isolated deletion regression starts with an empty engine, uses a Messenger session, and checks that the other app session is revoked too.

## Verification

- Standalone Messenger-session account deletion regression passed.
- API suite with `DATABASE_URL=' '` and both worktree source paths on `PYTHONPATH` passed with 696 passed, 16 skipped, and one Celery eager-mode warning.
- Both Test Bench API tests passed. A synthetic LAN form smoke test verified port routing, the pairing session header, typed deletion confirmation, and the Following filter.
- JavaScript syntax, PowerShell syntax, and frozen `apps/web` checks passed.
- Live OAuth and iPhone testing remain for the founder's dev stack.
