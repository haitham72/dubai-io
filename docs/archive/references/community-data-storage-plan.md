# Community database and media plan — 23 Oct 2026

Status: implementation plan, not a deployed database or bucket. Current work remains on `redesign-community`; web/iOS and main integration are paused by the founder. Keep FastAPI and Supabase/PostgreSQL as the target. SQLite remains the isolated development/test fallback.

## Current state and the gap

`communities.py` persists personas, communities, membership, posts, comments, chat threads/messages, reads, contacts and call logs. The current branch adds nested comment parents and persisted identity-bound AI replies. The initial Supabase community migration mirrors the demo schema; `20261023000300_social_personas.sql` adds persona avatar/profile fields, comment parents, message persona IDs, generation model/trigger fields and `social_generations` receipts. Their presence in source does not prove they have been applied to the runtime database. This is useful demo infrastructure, not yet a Reddit-like multi-user production model:

- Personas are fictional identities, not authenticated accounts. Cookie owners isolate each tester's additions; shared seeds are visible across testers.
- Display author names are duplicated in rows. Real account identity, immutable author references and participant permissions need normalization.
- Most relationships lack database foreign keys. Reply validity is checked by the API; database enforcement and deletion behavior remain required.
- Images are local fixture paths or external URLs. There is no integrated upload pipeline, attachment catalog, Storage bucket policy or lifecycle worker.
- AI generation receipts are durable but synchronous. They are not a durable background queue, notification system or real-human messaging service.
- PostgreSQL migration application/write health and hosted Auth/Storage integration are not verified by SQLite tests.

## Target identity and tenancy

Keep real humans and AI personas distinct. `accounts` maps a verified Supabase Auth subject to an internal account ID. `actors` supplies a stable content author ID, with `kind=human|ai_demo|system`, display name, handle and avatar asset. A human actor has exactly one account; an AI actor has a persona profile and no human login. Check constraints enforce those alternatives and a separate system-actor case; unique account-to-human-actor ownership must also be enforced. World membership and persona-profile references need foreign keys or transaction checks in addition to row-local constraints. Users never send an arbitrary actor ID to impersonate someone; FastAPI resolves the author from authenticated ownership or the generation job.

Demo interactions belong to a private `demo_world` owned by one account/session. Shared seed content is immutable source material; an individual's posts, replies, relationship personas and generated continuations are scoped to their world. Do not silently convert private demo conversations into public community content when real accounts launch. A mother's/wife's persona is a fictional role attached to that demo world, not an inferred real relationship or an impersonation of an actual contact.

Provide an explicit anonymous-session → authenticated-account transfer transaction: prove ownership of the existing session, lock the source, transfer only that session's records, record an idempotent receipt, and invalidate the old binding. No global demo-user fallback.

## Tables and relationships

| Table | Purpose and important constraints |
|---|---|
| `accounts` | Internal UUID, unique Auth subject, account status and timestamps; no model credentials. |
| `actors` | Stable author identity, kind, optional account FK, handle unique within world/public scope, avatar asset FK, tombstone status. |
| `persona_profiles` | Actor FK, versioned biography, voice, interests, declared expertise; demo-only. No private chat transcripts in shared profile JSON. |
| `demo_worlds` / `world_actors` | Owner account or temporary session, persona membership and relationship to that world; isolate each tester's family/friends/boss. |
| `communities` | Slug, title, description, visibility, world/public scope, creator actor, cover asset, moderation status. |
| `community_memberships` | Composite unique community/account, role, status, joined/left timestamps. Separate role from a displayed member count. |
| `posts` | Community FK, actor FK, world scope, title/body, kind, visibility/state, revision, created/edited/deleted timestamps, provenance, source seed ID. |
| `comments` | Post FK, actor FK, parent comment, world scope, body, revision/state/timestamps. Composite parent FK ties `(post_id,parent_id)` to `(post_id,id)`; prohibit self-parent, reject cycles and cross-world parents. Parent is immutable after creation. |
| `post_votes` / `comment_votes` | One vote per account and target, value constrained to -1/+1. Human votes separate from demo fixture counts; no AI engagement counted as genuine popularity. |
| `saved_posts`, `content_hides`, `reports`, `moderation_actions` | Account-specific saves/hides; auditable reports and moderator decisions. Authorization checked independently of UI visibility. |
| `conversations` | Direct/group/community chat, world scope, optional community FK, lifecycle timestamps. |
| `conversation_participants` | Conversation/actor unique, role, joined/left timestamps, last-read message; direct chat requires the actual authorized participants. |
| `messages` | Conversation FK, actor FK, optional same-conversation reply FK, text, revision/tombstone, provenance, generation job FK. |
| `media_assets` | Storage bucket/object key unique, uploader account, world/visibility, MIME/size/dimensions/hash, processing state, source/license/attribution, deletion status. |
| `post_assets`, `comment_assets`, `message_assets` | Explicit attachment junctions with target and asset FKs plus sort position; avoid unvalidated generic object-ID links. |
| `generation_jobs` / `generation_replies` | Owner/world, unique trigger+policy version, assigned actors, target/revision, requested and actual model, status/attempts, timestamps, safe failure category. Unique job+actor reply. |
| `outbox_events` | Transactionally recorded content/job/media events with unique dedupe key; a worker processes them after commit. |

Use UUIDs, timezone-aware timestamps and explicit FK deletion rules. Soft-delete content to a tombstone so children remain readable; hard-delete/anonymize through a deliberate retention workflow. Never cascade one post's deletion into unrelated replies or shared assets. Database constraints enforce relationships; the API still enforces permission and content policy. PostgreSQL supports self-referential and composite foreign keys; cross-row cycle prevention needs application/transaction logic or a trigger, not a row-local CHECK alone. [PostgreSQL constraints](https://www.postgresql.org/docs/current/ddl-constraints.html)

## Nested thread retrieval and indexing

Use adjacency-list `parent_id` as the canonical relation. Paginate top-level comments, then load replies per parent with stable `(created_at,id)` cursors. Return child counts and a continuation cursor; do not fetch every descendant for every feed card. Preserve unlimited stored nesting but cap visual indentation after a few levels, with a readable thread view. Apply visibility/world checks at every depth.

Index posts on `(community_id,state,created_at DESC,id)`, comments on `(post_id,parent_id,created_at,id)`, memberships on `(account_id,status,community_id)`, messages on `(conversation_id,created_at,id)`, jobs on `(status,next_attempt_at)` and media on `(state,created_at)`. Start with PostgreSQL full-text search for admitted public/community content. Vector search is optional and must not bypass world or conversation filters. Counts are transactional or recomputable projections, never invented numbers.

## Storage buckets and upload lifecycle

Use Supabase Storage for bytes, PostgreSQL for metadata/ownership. Store object keys rather than expiring signed URLs in the database.

| Bucket | Access and content |
|---|---|
| `community-media` | Private by default; post/comment attachments, with access resolved from the parent community/world/content status. |
| `chat-media` | Private; only current authorized conversation participants may obtain access. |
| `profile-media` | Private by default; avatars exposed only according to actor/profile visibility. |
| `demo-media` | Public only for audited reusable demo images with no private user content; otherwise private. Source and license recorded per asset. |

Private bucket operations support RLS; downloads can use authenticated requests or time-limited signed URLs. Public buckets make file retrieval public, so they are unsuitable for private conversations. Apply bucket MIME/size restrictions as well as server validation. [Supabase bucket fundamentals](https://supabase.com/docs/guides/storage/buckets/fundamentals), [Storage access control](https://supabase.com/docs/guides/storage/security/access-control)

1. Client requests an upload intent for a specific post draft/chat/avatar. API verifies membership/ownership, quota and allowed file class; generates an opaque asset UUID and object key. Client cannot choose another owner's path.
2. API creates a pending asset and returns a signed upload token scoped to that object. Start with JPEG/PNG/WebP images, 10 MiB per image and a bounded attachment count; video/documents need separate processing before enablement. These are proposed product limits, not existing implementation.
3. Client uploads; finalize endpoint is idempotent. Server verifies existence, actual bytes/MIME, size and decodability, removes location EXIF, scans as appropriate, then writes thumbnails and marks ready. Pending/unvalidated bytes are never publicly served. Upload even eventual public demo assets into private staging first; copying approved derivatives to a public bucket happens only after validation, because a public bucket cannot hide pending objects through read policies.
4. Publishing attaches only ready assets owned by the caller and permitted for that target, within the content transaction. Recheck membership; an upload token does not authorize publishing.
5. Read endpoint checks access then returns a short-lived URL. A leaked signed URL remains usable until expiry, so use short TTLs and avoid logging them. For stricter immediate revocation, proxy reads with authorization per request rather than promising signed-URL revocation. [Serving private assets](https://supabase.com/docs/guides/storage/serving/downloads)
6. A durable cleanup worker removes abandoned uploads and unreferenced derivatives after a grace period. Delete through the Storage API, with retries and receipts; do not mutate `storage.objects` directly. Shared referenced assets must survive one post's deletion.

Do not fetch arbitrary user-supplied remote image URLs server-side; use controlled import tooling for licensed seed images to avoid SSRF and undocumented reuse. Record source URL, creator, license and download checksum. No buckets are created or public policies applied by this plan.

## Authorization boundary

The existing `dubaiio` schema is backend-only, outside the Data API; keep it that way during this transition. RLS enabled without policies is not proof of application isolation when the backend role bypasses it. Every query still needs verified owner/world/participant predicates. If direct client database access is introduced later, design explicit JWT-based RLS and test it with real anon/authenticated roles first.

Never expose a service-role key to web/Swift. FastAPI may use server credentials to sign a narrowly scoped upload/download only after checking access. Public/closed/private communities need an explicit visibility matrix for reads, joins, posting, uploads, moderation and deleted content. Being able to guess a UUID grants nothing.

## AI response pipeline

A committed user post/comment/message creates a generation job and outbox event in the same transaction. A worker leases the job; backend relevance policy assigns about ten distinct actors for a new post, two related actors for a reply (prioritizing parent/post author), or the exact direct-chat actor. Each receives only their allowed persona data and the authorized conversation branch/history. Relationship context is world-scoped.

Agnes supplies reply text; the backend owns actor IDs, parent IDs, provenance and persistence. Validate structured output, length and assigned slots. Store model-request identity separately from the actual provider model when reported. Persist each actor reply at most once. Retry transient failures with bounded attempts/backoff; do not retry invalid credentials endlessly or invent filler responses. Recheck target visibility/revision and membership before saving a late response. UI shows pending/partial/failed state and can refresh after leaving the screen. No self-triggering bot loop; AI replies do not automatically create new generation jobs.

Current branch's synchronous receipt-based generation is an intermediate step. A worker, durable scheduling, cancellation and restart recovery require a later implementation slice.

## Migration and acceptance sequence

1. Inventory actual runtime DB/schema, back up rows and media, confirm write health; do not assume the old Windows Supabase checkpoint describes this Mac.
2. Add normalized identity/world/attachment/job tables and indexes with versioned migrations. Backfill stable mappings from existing persona and cookie-owner IDs; retain legacy IDs/source references.
3. Validate counts, orphan/cycle queries, role/world isolation and repeatable migration on a copy. Add foreign keys only after repairing or explicitly quarantining invalid legacy rows.
4. Adapt API contracts behind the same endpoints, add cursor pagination and versioned updates. Keep fixture import idempotent and never overwrite user-authored content.
5. Implement private bucket upload/finalize/read/delete flow and the cleanup worker. Test forbidden MIME, oversize/fake image, wrong owner, revoked membership, expired URL, duplicate finalize and interrupted deletion.
6. Move generation to leased jobs/outbox and test retries, duplicate requests, concurrent comments, crashes, late responses and deletion while generating.
7. Run the full suite on SQLite and PostgreSQL; verify actual Storage policies using two accounts and anonymous access. Roll out with backed-up reversible migrations and monitored jobs. Only then mark the durable community backend complete.

## Recommender status and community integration

Existing recommendation code implements deterministic ranking, deduplicated events, session/long-term interest projections, repeat-visit qualification, decay and explanation/control surfaces. Trusted provider retrieval and radius/open-now/type filtering exist specifically in `/api/discovery/places`; generic `/api/recommendations` still accepts bounded client-supplied IDs/topics and does not verify prices, availability or stock. Both paths are covered by tests. On this review, the recommendation/discovery suites pass **43 tests on SQLite**, with mocked provider batches; this is not a live-provider or PostgreSQL verification. Expired records are pruned on ingestion/ranking/rebuild activity, rather than by a scheduled task. Closest/price in the generic ranker preserve caller order; only discovery computes its own distance baseline, and there is no verified price-sort provider pipeline. REC-03C (service/product eligibility and verified completion signals), REC-04 (measurement and scheduled cleanup) and PostgreSQL adoption remain open. No implemented Reddit-style community/post recommender is claimed.

Before adding community ranking, define eligible signals: the real user's explicit joins, follows, saves, hides and qualified reading events. AI replies, seeded likes and bot activity must not count as human engagement or train inferred user preferences. Filter world/community visibility and blocks before ranking. Begin with followed communities + freshness + diversity, retain a chronological option, explain why an item appears and measure useful interactions against that baseline. Reuse event deduplication and Forget controls; do not feed private chats into public recommendations.
