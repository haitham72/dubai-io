# E12: Wire the Community website to its real API (Devin, after E11b)

Read `E0_real_data_round.md` first. Branch `e12/community-wiring` from `main`. Open one PR into `main`. Do not touch `apps/web`, which is frozen.

## Why

The Community backend, `apps/api/app/community/` (served on :8060), is a real multi-user social core:

- posts with edit and soft-delete;
- threaded comments;
- likes and bookmarks;
- follows;
- public and private groups;
- notifications;
- search;
- moderation;
- rule-based discovery with a "Why this?" chip.

About 66 API tests cover it. The website (`apps/community/src`) calls only 4 of these endpoints: groups, notifications, my profile and create post. The feed renders `lib/feedFixture.ts`, so **a user who posts never sees their own post**. Like, reply, follow and search have no working UI.

Goal: **two testers can sign in, post, follow, like and reply to each other.** This is wiring, not a design pass. Keep the current look and these UI rules:

- no shadows;
- plain AI text, a tinted user box and white rounded action boxes;
- light mode.

## Owned files

- `apps/community/src/**` and `apps/community/tests/**`
- `apps/community/package.json`, for test scripts only

**Read-only:** `apps/api/app/community/**`. If a backend bug blocks you, write it up in the report with the file, line and a suggested fix. Don't patch it.

## Deliverables

1. **Real feed:**
   - `FeedScreen` uses `getFeed()` (`GET /api/community/feed`). A new post shows at the top straight away.
   - Fixtures appear only when signed out or when the API can't be reached, always with the `Demo data` pill (rule 2).
   - Sort and lane tabs work on real data:
     - **Following:** the real follow set.
     - **Communities:** the user's groups.
     - **For you:** item 6 below.
   - Never show a fake count. Every number comes from the API, or there is none.
2. **Post actions:**
   - Like toggle (`/reactions`).
   - Bookmark.
   - Reply and threaded replies (`/comments` with `parent_id`).
   - Edit and delete for your own posts.
   - Counts come from the API.
3. **People:**
   - Follow and unfollow from the post author and from the profile page (`/follows/{handle}`).
   - A create/edit profile form for handle, display name and interests. The API enforces the 18+ gate; show its error honestly.
   - Remove the `seedProfile` fallback for signed-in users.
4. **Groups:**
   - Create, join and leave.
   - Group feed.
   - Private groups stay fenced; show what the API returns.
5. **Search:** the search icon opens a search over `/api/community/search`, covering groups, people and posts.
6. **For you:**
   - Calls `GET /api/community/discovery` and shows its "Why this?" chip from the API response. Delete the hard-coded "why" text in `lib/seed.ts`.
   - Cold start shows the API's public-group fallback, labelled as such.
   - The recommender stays rule-based. Wire it; don't change it.
7. **Notifications:** real-first. Fall back to `seedNotifications` only when signed out or offline, with the pill.

## Tests

- **Unit (vitest):** each API client call, plus an honest empty or error state for each screen.
- **Two-user end-to-end (Playwright), against a local API with two synthetic accounts, using the API's existing test or dev session path:**
  - A posts → B follows A → B sees the post in Following → B likes and replies → A gets a reply notification and sees the like count.
  - **Failure paths:**
    - a post in a private group is invisible to a non-member;
    - with the API down, the feed shows the honest offline state with the `Demo data` pill, and no fake "Posted";
    - a reply to a deleted post shows the API's error.
- Run the existing suites too: `apps/community` web, mobile and desktop shells, and `apps/api tests/test_community_*.py`.

## Real check (for the founder; you can't sign in with real Google)

Write a 6-step checklist in the report. With the founder's Gmail and the tester's Gmail, on the founder's PC (`scripts/dev/start-all.ps1`), the testers do the A/B flow above.

## Not in E12 (waiting for founder decisions)

- Reposts and quotes.
- Hashtags.
- Blocking and muting.
- Any learned recommender.
- Community's memory "Forget" (see D18).
- Splitting the consent flag for saved discussions vs public posts (§E #8).

## Report

- Write `reports/E12.md` with:
  - which endpoints were wired, before and after;
  - test counts for each suite;
  - screenshots of the feed, a thread, a profile, search and For you, saved under `apps/community/tests/e2e/screens/`;
  - the founder checklist.
- Add a line to `reports/STATUS.md` at `ready-for-review`.
