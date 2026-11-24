# UI — Mobile Memory Vault on `/vault/graph` (branch `ios`)

Assigned to: **Cursor** (queue `Q_cursor.md`, item 3). The integrator is **Claude**.
**Starts when** `memory` contains U1c (Gemini). Build against the `/vault/graph` sample saved in `reports\U1c.md`.

```powershell
git -C G:\Haitham\VsCode\contest worktree add ..\contest-ios-graph -b ios-graph ios
cd G:\Haitham\VsCode\contest-ios-graph\apps\mobile
```

## Rules

- Only `apps/mobile/src/features/vault/` + its tests. **Never touch `apps/web`**, never edit `G:\Haitham\VsCode\contest` (main).
- Light mode, **zero shadows** (1 px hairlines), the design tokens in `packages/design-tokens/`.
- Target: `design/20-11-2026/Dubai-io Knowledge Graph Vault.jpg`, **except the clusters are the engine's 7** (D-a): Career, Learning, Projects, People & family, Events, Home & money, Travel. There is no Health cluster.

## Deliverables

1. **`vaultApi.ts`:** an additive adapter for the versioned `/vault/graph?view=subjects|people` DTO. If the route is missing (404 on an older engine), fall back to `/vault/subjects` + `/vault/people`. Keep `/timeline` and `/why` as they are. Live errors (401 / 403, forgotten, empty) are shown as such; **only an explicit demo mode** may show fixtures, always with the `Demo data` pill.
2. **Subjects view:** owner centre + the **7 clusters** with counts. `THEME_COLORS` gets 7 entries (`vaultApi.ts:61-63`, today the design's 6). Show `+N more` from `hidden_by_group`.
3. **People & Places view:**
   - people, places (with `place_type`) and projects;
   - the T1 ring drawn **only** from confirmed `tier`;
   - `closeness_suggested` is shown as an **"I noticed"** suggestion with **Confirm** (calls `POST /vault/people/{id}/tier`) and **Not now**.
4. **Truthful labels (Rule 9):**
   - "You told me" only when `provenance=user_supplied`;
   - inferred items say "I noticed" with **Confirm / Edit / Not true / Forget**;
   - **no ✓ on inferred items** (today `VaultScreen.tsx:284`);
   - People & family shows only what the API returns: it is already gated server-side, so never add client-side guesses.
5. **Tests (Jest) + `npx tsc --noEmit`:**
   - the DTO adapter (graph, then the fallback);
   - 7 clusters render;
   - the T1 ring only from confirmed tiers;
   - suggestion Confirm calls the endpoint;
   - inferred items never show "You told me" or ✓;
   - the demo pill only in demo mode.

6. **The Dubai-io website from the same code (founder, 24 Nov: each product needs an iPhone app, a website and a desktop app).**
   - Make `apps/mobile` also run as a website with Expo web: `npx expo start --web`, `npx expo export --platform web` → static `dist/`.
   - Guard native-only modules with `Platform.OS` checks, and lay screens out responsively for a desktop width.
   - Serve `dist/` from the founder's PC (LAN for now, the tunnel later).
   - Then point the existing Dubai-io desktop app (`apps/desktop`, branch `desktop`) at that URL **only if** its renderer doesn't already cover the same screens. Report which you did.
   - Test: `expo export --platform web` succeeds, and the Vault renders in a browser.

**Report** → `reports\UI.md`: branch + commit, test counts, screenshots of both views from a run against the real engine (or fixtures, clearly labelled).
