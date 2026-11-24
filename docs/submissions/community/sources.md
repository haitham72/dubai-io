# Dubai-io Community — Sources and outcome metrics

**Status:** planned (revised to D1-D10) — awaiting founder approval. Every number carries publisher, URL and as-of date (root `CLAUDE.md` rule 2). Lane D fetched each URL below; the lead independently re-fetched the Government of Dubai Media Office survey and confirmed the 84% figure. Anything not official is labelled **reported**; arithmetic on official counts is labelled **derived**.

## The newcomer story must be measurable

Spec outcome: *newcomers finding reliable local knowledge*. Method note: Dubai moved to a register-based population count in 2025/26 — old-method end-2024 = 3,863,600 vs register-based end-2024 = 4,248,200. **Do not mix the two series in one chart.**

| # | Figure (quoted) | Publisher / as-of | URL | Status |
|---|---|---|---|---|
| 1 | Resident population **4.58 million**, up from **4.248 million in 2024** and **3.974 million in 2023**; **7.53% increase** 2024→2025 (≈ +332,000 in one year) | Digital Dubai / Dubai Data & Statistics Establishment (DDSE), end-2025 release, 30 Jul 2026 | https://whatson.ae/2026/08/dubai-population-over-the-years/ · https://connector.ae/updates/15386/dubai-population-passes-458-million-by-end-of-2025 | Official figure, reported via press (fetched 200 OK) |
| 2 | Daytime population **6.392 million**; **1.812 million** commute into Dubai daily | DDSE, end-2025 | Same two URLs as #1 | Official figure, reported via press |
| 3 | End-2024 residents **4,248,200**; 68.5% male (2,911,500), 31.5% female (1,336,700) | DDSE, *Population Bulletin — 2024* | Bulletin via search-indexed mirror; direct statistics-site PDF fetch failed (HTTP 403) — re-pull from https://data.dubai/services before print | Official bulletin; direct fetch failed |
| 4 | **299,600 Emirati citizens** and **3,564,000 non-citizens** (2024) → ≈92% non-citizen | DDSE counts reported 1 May 2025 | https://www.emirates247.com/uae/dubai-s-peak-time-population-hits-5-13-million-59-600-new-households-added-in-2024-2025-05-01-1.739043 | Official counts; the 92% is **derived** (299,600 ÷ 3,863,600 = 7.75% citizens) — label derived on-slide |
| 5 | **59,600 new households** added in 2024; peak daytime population **5.13m** (2024) | DDSE, 2024 bulletin | Same Emirates 24\|7 URL as #4 (fetched) | Official figure, via press |
| 6 | 8th Social Survey (2024–2025): social support — "someone to rely on when needed" — **84%**; volunteerism rose **8.4% → 13.2%**; happiness **8.6/10**; ≈95% call Dubai their preferred place to live | Community Development Authority (CDA) + DDSE, announced 4 May 2026 | https://mediaoffice.ae/en/news/2026/may/04-05/community-development-authority-in-dubai-announces-results-of-8th-social-survey | Official (Government of Dubai Media Office; lead re-fetched and confirmed the 84% sentence) |
| 7 | Dubai Social Agenda 33: **AED 208 billion** to 2033, addressing social cohesion | Government of Dubai / UAE federal portal | https://u.ae/en/about-the-uae/strategies-initiatives-and-awards/strategies-plans-and-visions/social-affairs/dubai-social-agenda-33 | Official (federal portal; fetched) |

Pitch lines (one per slide, citations attached): "+332,000 residents in a single year" (#1); "≈9 in 10 residents are non-citizens" (#4, derived); "59,600 new households in 2024" (#5); "1 in 6 residents has no one to rely on" (#6 — **derived** complement of the official 84%; an honest gap inside an official strength, not an invented loneliness crisis).

**Gaps, stated plainly:** no official Dubai loneliness/isolation prevalence percentage was found — do not invent one. The old statistics domain now redirects to data.dubai; re-pull the Population Bulletin from there before print (row #3). InterNations/YouGov/relocation-blog figures are **reported**, never official; if one is ever used, the slide names the source and labels it reported.

## Outcome metrics (demo/test thresholds — no baseline exists yet)

Never quote a "% better" without a measured baseline.

| Metric | Definition | Measured in demo/test | Target |
|---|---|---|---|
| Time-to-first-trusted-group | Minutes from account creation to joining ≥ 1 group whose recommendation shows a *Why this?* the user rates relevant | Timed Scene A runs (n ≥ 5 test users); relevance = user taps "relevant" on the explanation | Median ≤ 3 min; ≥ 80% of first-screen recommendations rated relevant |
| Sourced-answer integrity | % of Community Answer posts published with ≥ 1 live citation that resolves (HTTP 200) and an approval record matching the exact posted revision | Log check on every Scene C publication; citation URLs re-fetched at packaging | 100% — any failure blocks the take |
| Scoped-recall correctness | After save (Scene D), Quest recalls the topic only inside the consented scope; after Forget, recall returns nothing in either app; a second test user sees none of it | Two-user isolation test (spec §7 gates) | 100% pass; 0 cross-user or out-of-scope leaks |

## Deck outline (10 slides, English, stands alone)

Packaging target **Fri 18 Dec 2026** (deck, video, hosting/tunnel, small user test) ahead of the January 2027 official submission. No Meta-affiliation claims, no civic-integration claims.

| # | Title | One line | Evidence / asset |
|---|---|---|---|
| 1 | Dubai-io Community | A social network where Dubai newcomers find reliable local knowledge — agents that cite, memory that asks. | Original branding only |
| 2 | A city of newcomers | +332,000 residents in one year; ≈9 in 10 are non-citizens. | #1 + #4 with DDSE citation + as-of |
| 3 | Belonging hasn't kept pace | 1 in 6 residents has no one to rely on; AED 208bn invested in cohesion. | #6 (derived, labelled) + #7 |
| 4 | Why feeds fail newcomers | Unverified advice threads; newcomers can't tell signal from noise. | Anonymised example thread, labelled reported if from press |
| 5 | Meet Dubai-io Community | Feed, groups, discovery for settling in — AI explains itself with *Why this?*. | Scene A capture |
| 6 | One identity, interest-only memory | Same `user_id` in Quest and Community; only consented interest labels travel, never private text. | Scene B toggle + temporal_note bridge diagram (D5) |
| 7 | Answers you can check | Community Answer drafts from cited public sources; a human approves the exact words. | Scene C citation card + approval sheet |
| 8 | Memory you can erase | Save → scoped signal → scoped recall → Forget, propagating on camera. | Scene D before/after |
| 9 | Measured, not promised | Three outcome metrics with test thresholds — no invented baselines. | Metrics table above |
| 10 | Roadmap to January 2027 | Packaged 18 Dec 2026; live functional demo for the January submission. | Timeline + "real vs seeded" disclosure box |
