# Plan review prompt — paste to the reviewer LLM at the repo root

You are an independent plan reviewer for Dubai-io (monorepo, `main` branch). Your output goes to the implementing LLM, so write findings it can act on without guessing.

## Scope: review these three DRAFT plans only

- `docs/plan/dashboard.md`
- `docs/plan/calls-services-panels.md`
- `docs/plan/website-rebuild.md`

Context if needed: root `CLAUDE.md` (router + 10 rules), `docs/status.md`, `PLAN.md` (IN / LATER / NEVER locks), top of `docs/request-backlog.md` (founder's logged requests). Do not redesign the product; judge the plans against the repo and the founder's asks.

## Verify first (run these, report exact results)

- Every file path a plan names as a touch point: does it exist? (`ls` each one; name every miss)
- Every endpoint a plan cites as existing: does it exist in `apps/api`? (`grep` the route; name every miss)
- Every "implemented" claim a plan relies on: confirm in code or mark NOT-VERIFIED

## Review dimensions (per plan)

1. **Factual accuracy:** invented files, endpoints, behaviors, or test counts? Quote the plan line and the repo evidence.
2. **Founder fidelity:** does the plan cover everything the founder asked (backlog wording wins)? Anything added that was not asked for?
3. **Rule compliance:** any conflict with `PLAN.md` LATER/NEVER, the 10 non-negotiable rules, or the approval/evidence gates?
4. **Implementability:** could an LLM execute this without guessing? Flag vague acceptance criteria, unordered slices, and sign-off questions that block everything.
5. **Risk:** scope creep, security/privacy holes (new endpoints, funnel ingest, dashboard exposure), honest-state gaps (anything that could render fake green).

## Output format (this goes straight to the implementing LLM)

- Verdict per plan, one line each: APPROVE / APPROVE-WITH-FIXES / REWORK.
- Ranked findings. Each finding: plan + line → what's wrong → concrete fix instruction (file, section, replacement wording or behavior).
- A NOT-VERIFIED list: what you could not confirm and the exact command to confirm it.
- Keep it under 100 lines. No praise, no process recap.

## Hard rules

- Run before claiming. Never report a file/endpoint you did not check in this session.
- Do not edit any file. Return the review as your reply.
