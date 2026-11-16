# Persocial intake — social profiling + local live analyzer (proposal)

Recorded 2026-11-09 from founder direction. Status: **proposal, not scoped, not built.**

## 0. Project boundary (read first)

**This is ONE of TWO separate projects the founder is building — they are not the same product:**

1. **Dubai-io** (`G:\Haitham\VsCode\contest`) — the **GrokBot-style personal AI agent** (contest lane: Best Personal AI Agent). Everything else in this Researches folder mostly serves it.
2. **Social companion (Persocial)** — its **own, separate project** with **its own repo**: `G:\Haitham\VsCode\Persocial`; plan of record at `proposals\sanitize\persocial\plan.md` (sanitize queue row 3). This intake file is the companion's **research only** — do not build any of it into Dubai-io, and do not merge surfaces. Shared infrastructure (e.g. whichever memory engine Dubai-io decides on in the decision package) *may* be adopted by the companion later, **by owner decision only**.

The Persocial plan of record remains `proposals\sanitize\persocial\plan.md` — the sections below are additional direction toward it and must be reviewed by the founder before touching that plan.

## 1. The two products, one label store

| Lane | Who it serves | How |
|---|---|---|
| **Own-account comment triage** (existing Persocial core) | The user's own medium–large accounts | Official platform APIs where they exist (§2) |
| **Live on-screen analyzer** ("JEV-like, but local — NOT JEV") | Everyone, and mainly the useful feature for **low-engagement accounts** | Desktop app watches the visible screen (X.com, Instagram, etc.), reads live comments/posts locally, and rates each as **negative / spam / not true / related** with confidence + evidence. No platform integration at all. |
| **Later: hot/fake layer** (live community-notes-style) | The network effect | When a matrix of user labels accumulates, aggregate them so users see other users' labels next to posts, and results can be exported/ported as the user chooses. Founder phrasing: "posts maybe ported from users and saved the result for social media." |

Founder's framing (verbatim intent): "sematic analysis for high-follower profiles mainly, but what low engagement accounts can mainly use is the live on-screen analyzer. The big issue is using an extension to pull the posts from HTML vs applying to Meta/X.com for official pull — that needs checking."

## 2. Official-API reality (checked 2026-11-09 — re-check before building)

- **Instagram/Meta:** the comment API reads comments **only on media owned by a professional account that authorized your app** — the user's own or clients' accounts. It cannot read other accounts' comments on public posts. Connecting customer accounts needs Advanced Access: **Meta App Review + Business Verification** (lead time; plan for it). Limitations worth knowing: 50 comments per page, replies hidden unless expanded, live-video comments readable only during the broadcast, ad comments live in the Marketing API. Sources: `developers.facebook.com` IG Platform overview + `/comments` reference (2026), tryadeli.com IG comments guide (9 Oct 2026).
- **X:** since Feb 2026 it is **pay-per-use, no tiers**: $0.005 per post read ($0.001 own-data reads), $0.015 per post created ($0.20 with a URL), 3,000,000 post reads per billing cycle then Enterprise (reported ~$42k/mo entry). Replies are only permitted if the replying account was "summoned" by the original author — replies to strangers' posts are rejected; whether a reply *to your post* counts as a summons is explicitly untested by X's docs. No official route to monitor arbitrary third-party profiles at scale. Sources: docs.x.com rate card via outstand.so (Sept 2026), blotato.com (31 Jul 2026), xautopilot.app (7 Jun 2026).
- **Consequence:** "official pull" solves **own-account triage** only. Profiling other people's posts/comments is extension-or-screen territory on both platforms.

### 2.1 Extension exemplars, checked (9 Nov 2026)

The founder referenced two live exemplars of the $18/mo scraping-extension economy — both verified on their Chrome Web Store listings the same day:

| Exemplar | Users / rating | Patch cadence | What it does | Risk posture |
|---|---|---|---|---|
| **IGFollowExporter** (EchoWebBot Team) | 20,000 users · 3.2★ (22 ratings) | Updated 9 Nov 2026, same day as this check | Exports followers/following of any typed username + public emails/bios to CSV/XLSX | Listing claims all-local processing ("never passes our web server"); no password involvement |
| **InsC** (listmore.info) | 3,000 users · 4.7★ (87) | v7.0.44, updated 6 Nov 2026 | Exports comments from any **viewable** post; giveaway picker (own posts); pause/resume; freemium gate: first 100 records free, premium unlimited | Explicit disclaimer: "not affiliated with Instagram… users are responsible for complying with applicable platform terms" |

Survival formula this confirms: **read-only surface + client-only processing + no credential harvesting + user-carries-the-ToS-risk disclaimer + freemium volume caps + paid patch cadence for endpoint breakage** (near-identical patch dates across the catalogue). The Store's own "might also like" carousel lists ~10 near-identical exporters (several 4★+; one extracts emails *and* phone numbers) — Store enforcement is demonstrably complaint-reactive, not category-frontal.

### 2.2 Second exemplar batch, checked (9 Nov 2026) — includes a verified takedown-and-reincarnation

| Exemplar | Users / rating | Key facts | What it proves |
|---|---|---|---|
| **IG Sorter — Sort Feed — Instagram™ US** (v2.4.2, updated 26 Aug 2026) | ~7,000 users · 5.0★ (21) | Sorts/filter/exports feed, Reels, hashtags, Explore, Saved by likes/comments/reposts/views; ER overlay; paid: auto-scroll bulk collection, bulk HD download, Excel export. **Only 3 permissions: `activeTab`, `sidePanel`, `storage` — no host access** (no scary install warning) | This is the **takedown survivor**: the original global version (2–30k users) was pulled from the Store on 26 Aug 2026 for "Policy Violation"; the same day its pre-built byte-identical "US version" (trademark shim — the listing says so) took over and grew 1,000→7,000 users by Nov. Store takedowns are real, complaint/trademark-shaped, and survivable by staged backups + shared account systems. Source: Stringers (stringers.io) + chrome-stats, checked 9 Nov 2026 |
| **YouTube Subtitle Downloader — SRT, VTT, TXT** | free, Manifest V3, named dev (Anton Khoteev) | Downloads caption text from public video pages; privacy section discloses a server-stored FingerprintJS ID + email ("identification") | **Public-page data ≠ logged-in-session data**: near-zero user-ban exposure — the risk class is entirely different from IG exporters. Also shows "all local" claims are not universal in the genre |
| **YT Playlist Title Grabber** (v1.0, 11 KB, published Apr 2023) | ~3,000 users · 4.5★ (22) | Listing states **"The code and the promotional copy for this browser extension were created by ChatGPT"**; permissions `scripting` + `activeTab`; never updated since 2023; reads only the loaded DOM (stops at 100 playlist items unless scrolled) | An **LLM-built scraper-tool shipped 3 years ago and still live** — LLM-written code is not itself a risk factor; surface, permissions and behaviour are. Also the minimal viable build: activeTab-only, no backend, no subscription |

Convergent lesson across §2.1–2.2: user bans correlate with **write-actions and session-harvesting volume**; Store takedowns with **complaints/trademark**; both combatable and neither caused by "LLM built it". Viable posture for a build: minimal permissions, read-only, activeTab-fenced, freemium volume gating, staged backup identity, honest disclaimers.

Still unverified for all exemplars: actual wire behaviour inside the CRX packages (the "all local" claims need unzip/traffic-capture to confirm). Mark unverified wherever reused.

### 2.3 Correction — installed code inspected (9 Nov 2026, supersedes §2.1–2.2 where they conflict)

Manifests and bundled JS of the installed copies were read (static inspection; no traffic capture):

| Exemplar | What the code shows | Claim it corrects |
|---|---|---|
| **IG Sorter** v2.4.2 | Permissions `activeTab`, `storage`, `sidePanel` and no `host_permissions` — but content scripts on every `https://www.instagram.com/*` page (that is page access by another route). Calls Instagram's **private web API** with the user's session: `api/v1/feed/user/`, `feed/saved/posts/`, `feed/collection/`, `discover/web/explore_grid/`, `fbsearch/web/top_serp/`, `graphql/query`, `x-ig-app-id`. Payments via extensionpay.com. **The US backup listing is now flagged by Chrome as violating Web Store policy.** | "no host access", "reads the DOM", "takedown survivor", "backup-listing insurance" |
| **InsC** v7.0.44 | Private web API with `fb_dtsg`, `csrftoken`, `doc_id` and Instagram's own web app ID. Google sign-in (`identity`; openid / email / profile), Mixpanel analytics, Sentry, own backend `insc.listmore.info`. Content scripts on Instagram's `scraping_warning`, `suspended`, `checkpoint`, `challenge`, `recaptcha` pages, mapped to "action-blocked" / "account-challenged". | "all local", "near-zero ban exposure" — the vendor builds for users getting flagged |
| **YT Playlist Title Grabber** v1.0 | `scripting` + `activeTab`, content script on youtube.com; reads only the loaded page. | Confirmed: the one genuinely page-reading-only exemplar |

Consequence: the IG exemplars are **session-replay scrapers**, the class §6 says flips the verdict. Hootsuite, for contrast, uses only official sign-in for owned accounts plus a licensed data feed (Talkwalker, an X Official Partner with the full firehose; Instagram listening limited to pages/hashtags added per project).

## 3. Capture lanes for profile-scale profiling (the founder's open issue, resolved)

| Lane | Pros | Cons | Verdict |
|---|---|---|---|
| **Local on-screen analyzer** | Zero platform integration → no ToS/API exposure; works on anything visible; matches the repo's other connectors' philosophy (iPhone/Android notification research: live-only capture, no history); local-first (nothing leaves the machine unless the user enables cloud analysis) | Fragile vs page changes/scroll/encoding; loses message structure; requires Chromium/desktop work | **Recommended v1** |
| **Browser extension** | Structured DOM data; can be silent; larger reach | No-platform automation risk → account-flag and ToS exposure; ships its own legal copy burden; volume looks like scraping | Usable, honest positioning, later |
| **Official API** | Legal, structured, webhooks | Only own/authorized accounts; costs (X per-read; Meta review) | Already Persocial's core lane |

## 4. Rule compliance (root CLAUDE.md, non-negotiable)

1. **Labels are opinions, not statuses (rule 1).** "Negative / spam / not true / related / hot / fake" render with model confidence + evidence + `as_of`; no success/fact framing; influencer reputations are never declared as fact.
2. **Publishing anything outward (comment replies, exported labels) is an outbound action (rule 6):** exact side-effect approval card first; platform-legal send paths only (respect the X "summoned reply" wall — test it before promising reply features).
3. **Imported posts/comments/screens are untrusted data, never instructions.**
4. **"Not true" judgments carry the sensitive-claim discipline:** a debunk claim still shows its evidence; contested ones stay labelled as contested. Never hook account reputation into status vocabulary.
5. **Aggregate labels cross users privately:** the hot/fake layer follows the same condition decided for the recommender (9 Nov, see `CLAUDE.md` intro): per-user stores isolated; only aggregate label-counts/weights travel; visible opt-out; no raw post text or screen content leaves a user's device into another user's context.

## 6. Verdict — the one-liners to cite

**Question: "Can we (via an LLM) build a similar app that reads the DOM and produces analytics? Will we get banned?"**

**Revised 9 Nov (after §2.3): YES only for visible-page reading; NO for session scraping.**

- **YES:** the local on-screen analyzer, or an extension that reads only what is rendered on the page and sends no requests to the platform (the YT Playlist Title Grabber shape). Read-only, local processing, honest disclaimer.
- **NO:** anything that replays the user's logged-in session against platform endpoints (what IG Sorter and InsC actually do). It is not a Meta-licensed route, Instagram flags it (InsC's own handlers prove it), and the Store pulled IG Sorter twice — the "backup listing as insurance" model failed.
- **Still NO:** write-actions (auto-follow/unfollow/DM/like) and server-side collection of session data.

Cost is not the blocker: AI labelling on a Haiku-class model is roughly $0.00004 per comment (~$2.40/month at 10 users × 200 comments/day; ~$2,400 at 10k). Official X reads at scale are the expensive part. Founder decision 9 Nov: Persocial deprioritised.

## 7. Open questions (owner decides)

- **O1** — Which platforms in v1: X.com live + Instagram comments on screen? (screen analyzers work platform-agnostically; pick by demo value)
- **O2** — Does the hot/fake matrix require >=N distinct users per post before it can render another user's label? (privacy + reliability floor; suggest N≥3 as hypothesis to test)
- **O3** — Do labels persist offline on-device only for v1, or does label sharing need accounts? (ties to PDPL + the 10k-users aggregate decision)
- **O4** — Screen-capture engine: Chromium DevTools-vision vs desktop OS capture; revisit after the ownership-review of extensions (account-flag risk evidence needed, not assumed)
- **O5** — Test X's "summoned reply" semantics with a real thread before any triage reply feature is promised.
- **O6** — Persocial repo split: comments-triage (existing plan) vs live-analyzer — one product with two modes, or the analyzer as a Dubai-io companion surface? Founder leans: analyzer first, profiling second. Confirm.
