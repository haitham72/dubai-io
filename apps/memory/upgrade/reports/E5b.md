# E5b report - Memory UI for Community and Messenger (builder, 2026-11-24)
Branch e5b/memory-ui, tip d61eee5, from main 9233daf. Pushed, NOT merged. apps/web untouched; old-name gate prints nothing.

## Delivered
1. Community Profile: new MemoryPanel (apps/community/src/components/MemoryPanel.tsx). Three switches (use interests to order Discover = read_enabled; remember my posts/saved discussions = write_enabled; share interest topics = allow_interest_export) load from new GET /api/community/memory/consent; a click POSTs the full next state and the switch changes only from the server response (shows Saving... meanwhile; on error the old state stays plus "Not changed: ..."). Forget calls the real route and shows the server counts and as_of only after the response; error shows no success text. Provenance "You told me" and as_of shown. API fix: switching toggles off used to forget the whole community source as a side effect (forget_on_revoke default); now false, Forget is separate (tested).
2. Messenger: new apps/api/app/messenger/routes_memory.py (preview, save, state, consent switch, per-chat mode, forget). Per-message "Save to memory" (real mode, text messages) opens an approval card listing the server-previewed fields (text, written by, sent at, scope), provenance and as_of; Approve = one POST with confirmed:true, the server reads the text itself (client text ignored); Cancel sends nothing. Sensitive text (pre_write) is never offered (no fields, no approve) and a forced save is refused 422 held_back; quarantined receipts show as not saved. Blockers (chat memory off, other member off, source off) are shown honestly; "Allow memory in this chat" is a separate explicit tap. Settings > AI > Memory section (MemorySettings) shows the consent switch and saved items from the server with per-item Forget (list re-read from server); revoking does not delete. Added bridge.list_record_refs and ChatStore.get_message; added optional disabled prop to the shared Button.
3. Pair rate limit: _pair_ip_failures/_pair_code_failures pruned on access (5 min window; code failures now carry a last-failure time) and capped at 4096 entries each, oldest evicted. Test added.
4. Coordinator test: one Google auth_code and one pairing code redeemed once cannot be redeemed again in community/messenger/quest (tests in test_e5_shared_layer.py).

## Tests / gates
- apps/api full suite from worktree: 664 passed, 16 skipped, 0 failed (new: 8 in test_e5b_memory_ui.py, 2 cross-app redeem, 1 pair-store bounds).
- apps/community: npm ci, vitest 16 passed (5 new MemoryPanel tests: toggle non-optimistic, toggle error, Forget ok, Forget error, load failure), next build OK.
- apps/messenger: typecheck clean, vite build OK, test:store passed, new test:memory 10 checks passed (card fields, cancel, approve once, held back, sensitive, blocked, errors, Forget happy/error). Messenger has no vitest; used the existing esbuild+node pattern, so the React card is rendered via static markup, not clicked in a DOM.
- Shells untouched. Old-name gate clean. apps/web diff vs baseline clean.

## Not done / caveats
- No live-engine or browser click-through; fake memory client only. Messenger memory UI needs real mode with a signed-in session (demo mode shows no Save button).
- Settings "Memory" is a section inside the AI tab, not a new tab.
- Community has no separate per-feature save/post consents on the server; "saved discussions" and "public posts" share write_enabled.
