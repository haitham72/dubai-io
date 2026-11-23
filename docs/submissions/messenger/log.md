# Messenger log

## 23 Nov 2026 — P1 (Cursor)

Checked the founder spec, the Community inbox and memory sections, `PLAN.md` §1–§5 and §7, `ARCHITECTURE.md` §2, §3, §7, §9 and §11, `actions.py`, `auth.py`, `communities.py`, and `origin/memory:apps/memory/src/temporal_memory/models.py` (via `git show`, branch not checked out). Audited `haitham72/Mirsal-redesign` at `6b45ba4` without copying it and without switching `main`.

Reran `python agents/run.py test` in `D:\Vscode\_scratch\mirsal-p1-tests`. Result: **200 passed, 1 skipped** (`tests/test_store.py:20`, no local Redis). The README’s 169 and 10 were not reproduced.

Wrote `ip-and-baseline.md`, `audit.md`, `IMPLEMENTATION_GAP_MATRIX.md`, `DELIVERY_ROADMAP.md`, `identity-memory-needs.md`, `demo-script.md`, `sources.md`, `open-questions.md`, and this log. M0 recommendation is **clean-room**. No application code.

Top risks:

1. Clean-room plus Gate S means the visual POC cannot be imported, and the 18 Dec package is tight if shared identity slips.
2. There is still no verified `user_id`. Cross-app “same person” must not be shown.
3. The spec’s compact Updates tray and commit `6b45ba4` disagree. A later reuse decision is blocked until the founder picks one.
4. Community already has per-owner `chat_*` tables. A second full messenger on that side would split the product.
5. `workspace.task.create` is not registered. The business tap has nowhere to go until `MS-B5`, and a seeded thread is not the two-user test.

## 23 Nov 2026 — P1 verification (Codex)

Cross-checked Cursor’s nine-file P1 commit and preserved its slice order. Reproduced 200 agent passes with one Redis skip, all 145 offline routing eval items, 40 provider-mock server tests, TypeScript and four photo-window cases. The sandbox prevented a Vite build. Verified the source SHA on GitHub and added the organizer’s originality constraint to M0. Reconciled chat ownership with verified B0 identity and source deletion with memory revocation. The demo calendar now agrees with the approval payload.

## 23 Nov 2026 — P1b (Cursor)

Revised the plan to founder decisions D1–D7. M0 is a rebranded snapshot of the founder-authored code: keep 12, exclude 8, rebuild 16. The old product name is retired. The working name is Messenger.

Rename inventory at `6b45ba4`: 908 matching lines in 172 files (285 identifiers, 193 paths, 430 strings) plus 2 image filenames. The rebrand slice is `MG-B2`. Its gate is a grep that prints nothing under `apps/messenger` and `apps/api/app/messenger`.

D4 keeps the 19 Nov AI workspace. D3 leaves Community’s `chat_*` tables parked. D5 points memory at temporal_note (`api/app.py`, `mcp/server.py`, `models.py`, `privacy/forget.py`), not Hindsight, Honcho, or the Redis store. D6 and D7 drop the Builder and all AI image, video, and sticker generation. Packs are finished files. A user sticker is a photo plus on-device MediaPipe Selfie Segmentation (Apache-2.0).

Transport stays open for P2: a cookie-authenticated FastAPI WebSocket until B0 identity exists. O2, the final name, stays open. No application code. No file outside `docs/submissions/messenger/` was edited.

## 23 Nov 2026 — MG-B1 and MG-B2 (Cursor)

Dubai-io API suite before the snapshot, from `apps/api` with the main worktree interpreter: 409 passed, 12 skipped, 3 failed. The failures are `test_filesystem_is_scoped` (a symlink the process cannot create on this Windows login) and two try-on tests that need `python-multipart` in that interpreter. Nothing under `apps/api` was edited.

Imported agents suite, before the drops: 200 passed, 1 skipped. After the drops and the rebrand: 158 passed, 1 skipped. Typecheck (`tsc -b --noEmit` and `tsc -p tsconfig.api.json --noEmit`) passed.

Concept sheets and screen frames were removed after the opened frames showed the old name or the M mark. Video clips and motion-graphics audio and photos were kept and were not frame-checked.

## 23 Nov 2026 — founder confirmation (Cursor)

The founder confirmed M0 and approved MG-B1 and MG-B2 only. Concept sheets, the named screen frames, the video clips, and the motion-graphics audio and photos are kept, except images that show the old name or logo, and except the dynamic-island scrapes. The Diwan connector, the Nadi connector, and watermark removal are dropped. User stickers, when that later slice is approved, use U²-Net (Apache-2.0, official repository, checked 23 Nov 2026) for any subject. MediaPipe selfie segmentation is only a fallback. Transport and the final name stay open.

## 23 Nov 2026 — D8 (Cursor)

Founder addition: there is no Higgsfield at all. `lib/higgsCli.ts` was already gone. This slice also drops the HTTP client, the CLI job, the `HF_CREDENTIALS` and `HIGGS_*` keys, and every UI hook and test that called or named that provider. Recorded as an exclude row in `ip-and-baseline.md`.

## 23 Nov 2026 — D11 gate (Cursor)

Merged `contest-shared` (`f19db5c`) into `business`. D11 approves MG-B3 through MG-B9. Transport is the shared-contract WebSocket on `:8070`, bound to the B0 `user_id`. `apps/api/app/identity/` is not on `contest-shared` or `business`, so Gate S is not merged. `MG-B3` and `MG-B5` wait. UI slices wait for a staged visual review. The working name stays Messenger until the final name, before MG-B7.

## 23 Nov 2026 — D12 and MG-B4 (Cursor)

Merged `contest-shared` (`f7465a5`). D12: local Supabase first, temporal_note is being rebuilt, the name stays parked.

MG-B4, without voice-on-real-messages. One placeholder pack, `demo-dot`, labelled Demo data, read from `apps/messenger/public/packs/manifest.json`. No Builder call. User cut-out primary is BiRefNet general, MIT, official ONNX not vendored; the phone path keeps the photo until a smaller official weight exists. MediaPipe selfie is the person-only fallback. Sticker tests: 6 passed. Agents suite: 158 passed, 1 skipped. Typecheck and `npm run build` passed. The old-name grep printed nothing.

## 23 Nov 2026 — MG-B3, MG-B6, MG-B5, voice, U²-Net-P (Cursor)

Gate S is on `business` (`720d0a4`). MG-B3 stores `mg_*` chat for two verified users and serves the WebSocket on `:8070` with an Origin-bound ticket. MG-B6 prepares `workspace.task.create` and leaves it blocked without an adapter. MG-B5 writes through the memory bridge and `FakeTemporalMemoryClient`. A voice draft is not inserted until the person confirms. The phone cut-out fallback is U²-Net-P (Apache-2.0, `u2netp.pth` not vendored) because BiRefNet does not fit the phone WebGPU buffer. UI slices still wait for the founder's visual review. Live Supabase still waits for local Docker (D12).

## Founder visual review — pending

Staged at `http://127.0.0.1:5173/` on 23 Nov 2026. The UI was not changed for these frames. Desktop is the 1440×900 window. Phone is the layout at 390×844.

- `docs/submissions/messenger/review/founder-review-desktop-chats.png` — desktop Chats
- `docs/submissions/messenger/review/founder-review-desktop-ai.png` — desktop Messenger AI
- `docs/submissions/messenger/review/founder-review-phone-chats.png` — phone Chats
- `docs/submissions/messenger/review/founder-review-phone-ai.png` — phone Messenger AI
