# U7 final: E6 acceptance harness merge
Verdict: MERGED into main 50f8f4a (f5bd595, no-ff). Remote branch e6/full-test deleted; contest-e6 worktree and local branch kept.
Scope: 8 files, all under apps/memory/acceptance/ (4 e2e helpers, 4 scorer fixes). No product code touched.
Fixtures synthetic (e6-*@synthetic.invalid). No secrets; results/ not tracked, gitignored in apps/memory/.gitignore.
mint_sessions.py lives under acceptance/e2e, test-only; uses identity store test path, not importable by product code.
Tests: apps/memory pytest 443 passed, 8 skipped, 0 failed. No stack-free unit tests exist under acceptance/ (harness scripts need stack/LLM, not run).
apps/web diff vs baseline tag: clean.
