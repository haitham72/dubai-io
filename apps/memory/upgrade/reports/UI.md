# UI — Mobile Memory Vault on `/vault/graph`

- **Branch:** `ios-graph`
- **Commit:** `e3125bb` (from `ios` @ `037656d`)
- **Worktree:** `G:\Haitham\VsCode\contest-ios-graph`
- **Status:** ready-for-review. Not merged, not pushed.

Built against the sample `/vault/graph` DTO in `reports/U1c.md`. U1c itself is still `mem-wpU1c` `c86db4e` (ready-for-review), not yet in `memory`. No UI review file asked for fixes.

## What the phone shows

- `loadVault` reads `GET /vault/graph?view=subjects` and `view=people`. A 404, or a body that is not a graph, falls back to `/vault/subjects` and `/vault/people`. `/timeline` and `/why` are unchanged.
- 401 / 403 render as "Sign-in required". They do not swap in fixtures.
- The Demo data pill is the existing analytics pill, and it shows only when `demo_data` is true or the screen is opened with `demo`.
- Subjects: owner centre plus the engine's 7 clusters (Career, Learning, Projects, People & family, Events, Home & money, Travel). `hidden_by_group` renders as `+N more`.
- People and places: `tier` is the only T1 ring. `closeness_suggested` is an "I noticed" row with Confirm (`POST /vault/people/{id}/tier`) and Not now. Places show `place_type`.
- "You told me" and the check mark only when `provenance` is `user_supplied`. Inferred rows say "I noticed" and offer Confirm / Edit / Not true / Forget. No check mark.

## Website

`apps/mobile` exports with `npx expo export --platform web` to `dist/` (gitignored). Web settings use `localStorage` instead of the keychain. The Memory route forwards `demo`, so the exported site shows the Karim fixture vault.

Checked in a browser at `http://127.0.0.1:8766/memory`. The accessibility tree listed Career, Learning, Projects, People & family, Events, Home & money, and Travel. The browser window was hidden, so there is no screenshot file. The people view (T1 ring, Confirm) was checked by Jest, not by a second browser pass.

The desktop app on branch `desktop` has no Memory Vault screen. `apps/desktop` is not in this worktree, so it was not pointed at the export. The website is this Expo web build.

## Tests

- Jest: **30 passed**, 8 suites (7 of them in `vault.test.tsx`, including graph, fallback, 401, T1-only ring, and the tier POST).
- `tsc --noEmit`: clean.
- `expo export --platform web`: succeeded (`dist/`).
