# E5b review (Claude verifier, 2026-11-24)
Verdict: MERGED into main 48f7ce3 (branch tip d61eee5). No blocking items.
Scope: 25 files, all in apps/community, apps/messenger, apps/api (community memory_routes, identity/service, memory_bridge/bridge list_record_refs, messenger routes_memory/server/store, tests). No apps/memory, shells, scripts, apps/web. Secrets grep clean; old-name gate empty; apps/web identical to baseline.
Checklist
a (B) OK: routes_memory.py:101-121 save requires _writer principal; _message (52-59) -> store.get_message (store.py:255) calls require_member, so non-participants cannot read by id; server reads message["body"] itself (memory_client.save_approved:34); confirmed:true required (104); consent via write_consented + group consent + source_off blocker (74); held_back 422 (106) and quarantined reported (118); set_mode (166-178) require_member before change.
b (B) OK: preview fields come from server (79-97), sensitive => no fields; memoryFlow.ts approve only from ready+can_save_now, cancel sends nothing, done only after server saved:true; tests memory-ui 10 checks.
c (B) OK: bridge.read_community_interest_features (bridge.py:1493-1507) raises when read_enabled off; forget_on_revoke=False in memory_routes; Forget separate route returns server counts/as_of; test_e5b_memory_ui.py:24-50.
d OK: service.py _pair_prune, cap 4096, oldest eviction; code lock is persisted via invalidate_pairing_code so 5-attempt rule unchanged; test_e2_signin_pairing.py:347.
e OK: test_e5_shared_layer.py:284 (auth_code) and :298 (pairing; community/messenger, plus quest redemption of the same code) assert second redemption fails across apps.
f OK: plain markup, existing Button (+optional disabled prop), no shadow strings.
Tests (clean worktree): api 664 passed/16 skipped/0 failed; community vitest 16 passed + next build OK; messenger typecheck, build, test:store, test:memory (10 checks) OK.
Non-blocking: messenger approval card rendered by static markup, no DOM click test; no live engine/browser click-through; pairing test list covers quest as a redeemer only for the second attempt (quest-as-first only in auth_code test); Settings Memory is a section in the AI tab.
