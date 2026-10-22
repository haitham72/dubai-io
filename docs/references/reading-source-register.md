# Home news source register — 22 Oct 2026

This records the implemented local review pilot. It does not amend either independent review report or claim general publishing rights.

## Retrieval and display

The existing server-side Tavily key retrieves news metadata only: one basic search when the user reaches News, at most 12 search results, filtered to 8 dated unique headlines. News follows the **actual end of inline task history**, not completion of every task. No model writes summaries, no scheduler polls, and no article body, snippet, raw content, image or favicon is stored or displayed. Each result links to its publisher and carries publisher, publication timestamp reported by search, check timestamp and attribution. Missing/old/future/unparseable timestamps, insecure/credential-bearing/unadmitted URLs and duplicate URL/title results are suppressed. URL/title dedupe is not independent-story clustering or corroboration.

Provider contract: [Tavily Search](https://docs.tavily.com/documentation/api-reference/endpoint/search), inspected 22 Oct; `topic=news`, `time_range=week`, `include_published_date=true`, `include_answer=false`, `include_raw_content=false`, `include_images=false`, `auto_parameters=false`. A recency search filter alone never supplies a publication timestamp. Dates are not independently publisher-verified and the UI says so. All upstream requests have an 8-second timeout. A 15-minute process cache contains only public headline metadata keyed by public topics, with a bounded set of reviewed public topic combinations in this pilot; no owner or task/chat content is sent to search. Four uncached requests per owner per minute; no request/retry storm or background refresh. Cache/rate accounting is process-local and needs a shared deployment budget before multi-worker hosting.

## Admitted metadata destinations

| Publisher | Admitted domain | Official-updates eligibility | Display/storage basis and limits |
|---|---|---|---|
| The National | `thenationalnews.com` and subdomains | No | Search-result headline/link metadata for local review; no article/image republication |
| Gulf News | `gulfnews.com` and subdomains | No | Same metadata-only restriction |
| Khaleej Times | `khaleejtimes.com` and subdomains | No | Same metadata-only restriction |
| Emirates News Agency | `wam.ae` and subdomains | Yes | Attributed official-source headline/link; no inference about legal applicability |
| Dubai Media Office | `mediaoffice.ae` and subdomains | Yes | Same official-source restriction |
| Dubai Culture | `dubaiculture.gov.ae` and subdomains | Yes | Same official-source restriction |

**Thumbnails (founder request, 23 Oct):** each admitted headline may show the publisher's own link-preview image (`og:image` / `twitter:image`), read from the article page head (no body kept; at most two same-publisher redirects; public HTTPS hosts only). The browser loads it through `/api/reading/thumbnails/{id}`, which serves only images for headlines this server admitted, image MIME types only, at most 2 MB, cached privately for 15 minutes and not stored otherwise. Each thumbnail is credited "Image: <publisher>" and links to the article. This is link-preview use, as messaging apps do; it is **not** a licence to republish. Public/commercial release still needs the publisher/provider rights review above. Pages that do not answer (e.g. Gulf News during the 23 Oct check) show no thumbnail. No extra API key is needed; Tavily (`TVLY_API_KEY`) still supplies the headlines.

Domain admission establishes publisher identity for a link, not a licence to reuse its articles/photos or a guarantee of accuracy. [Tavily's terms](https://www.tavily.com/terms), inspected 22 Oct, reserve third-party rights; integration does not transfer publisher rights. Public/commercial distribution, article summaries, photos and retained content require an explicit source/reuse review and an appropriate provider plan. The app neither reads paywalled articles nor promises a confirmed RSS/API on UAE portals. NewsAPI is not used; its previously recorded development-only restriction is unchanged.

## Personalization and controls

`For you` uses existing owner-scoped, inspectable, confirmed or qualified positive temporal interests, mapped only to reviewed public topics. Unqualified across-visit observations, negative/rejected/forgotten interests and sensitive/political traits cannot create a personalized query. Cold start is a clearly described general Dubai selection. Explicit topic selection overrides inferred interests. Official updates admits only the three official domains above; it gives no legal advice. Topic controls, Hide/Show, manual Refresh and existing interest correction/Forget remain available. Preferences are checked again after a provider request so mid-flight changes cannot restore old personalized results. News can become transient selected **headline metadata** in Ask; this does not claim that the full article was read or add a confirmed memory.

## Verified and pending

- SQLite tests cover owner/topic guards, publisher/HTTPS/date/dedup filters, no body/image retention, public-only provider inputs, cache/failure behavior, qualification and mid-flight preference changes.
- One live isolated-cookie request returned HTTP 200 / ready / 4 admitted dated headlines on 22 Oct. This verifies retrieval for that query, not continuous coverage or the publishers' underlying claims.
- Browser layout uses labelled controlled fixtures at 390×844 and 428×926, normal/reduced motion; inline history precedes News, with no overview modal or visible computed shadows. A separate 390?844 reduced-motion browser run used four real attributed headlines, selected/cleared a headline as Ask context without submitting a question, and verified ordinary wheel scrolling. The live News screenshot was visually inspected.
- Shared rate accounting, durable preferences across devices, story clustering, publisher reuse approval for broader distribution, independent date verification, provider-wide caps and production/device acceptance remain pending.
