# Shared Memory & Cross-App Contract

**Status:** `ready for founder approval`
**Date:** 2026-11-23
**Branch:** `contest-shared`
**Authoritative baselines:** `docs/submissions/shared/founder-decisions.md` (D1–D10) · `docs/submissions/CLAUDE.md` · `origin/memory` @ `fc2e24a` (`apps/memory/`, package `temporal_memory`) · `societal` @ `317de4d` · `business` @ `4f7c675`

---

## 1. Scope, Canon Precedence & Engine Baseline

1. **Governance:** `founder-decisions.md` (D1–D10) and root `CLAUDE.md` rules 1–10 + `PLAN.md` §3 NEVER + D14/D15 govern all three contest entries:
   - **Entry 1:** Quest / Dubai-io (`main`, ChatGPT-like personal companion)
   - **Entry 2:** Dubai-io Community (`societal`, Facebook-like social network; **no P2P messaging**, D3; all-ages self-declared age gate, D9)
   - **Entry 3:** Messenger (`business`, WhatsApp-like messenger, working name pending O2; **owns all P2P messaging**, D3; M0 confirmed & `MG-B1`/`MG-B2` approved, D8)
2. **Single memory engine (D5):** Memory for all three entries is the rewritten **`temporal_note`** engine in `apps/memory/` (package `temporal_memory` on `origin/memory` @ `fc2e24a`, newest `apps/memory` branch on `origin`). **Hindsight and Honcho are not used**, and Hindsight `AC-1` / `MEM-01` gates do not apply.
3. **Entry 1's `apps/api/app/memory/` (`mem_*`) is read-only:** Legacy `mem_*` tables (`schema.py:4-69`, `store.py:21-120`, `/api/memory/*` on anonymous cookie sessions) belong to Entry 1 and are **NOT** a target for `memory_bridge`, Community, or Messenger.
4. **Zero-conflict & operations rules (`docs/submissions/CLAUDE.md` §2, D10):**
   - Shared code lives **only** in `apps/api/app/identity/` and `apps/api/app/memory_bridge/`.
   - Shared DB tables use prefix `cs_*` created via `CREATE TABLE IF NOT EXISTS` in Python using portable `?` SQL (`apps/api/app/db.py` pattern). **Zero** files in `supabase/migrations/`, **zero** edits to `main.py`, `config.py`, `actions.py`, `auth.py`, `communities.py`, `requirements.txt`, or `apps/memory/**`.
   - Entry servers (`app.community.server:app` on `:8060`, `app.messenger.server:app` on `:8070`) mount the shared routers and dependencies directly.
   - Per **D10**, staging uses a separate Supabase project for both entries (sign-up disabled, test users only), with Auth/RLS SQL applied by an entry-owned script from `apps/community/supabase/` and `apps/messenger/supabase/` (`supabase/migrations/` stays frozen).

---

## 2. Identity Contract (`apps/api/app/identity/`)

### 2.1 Current-State Audit Verdict
- `apps/api/app/actions.py:386-393` provides an anonymous cookie `dubaiio_lab_session` (`mode: anonymous_lab_session`), and `apps/api/app/auth.py:65-120` binds Google OAuth connection grants to that cookie. `apps/api/CLAUDE.md:54` notes bearer-token verification is planned and absent.
- Neither `origin/desktop` (`d07ee53`: `electron/main/ownerHook.ts:90-116`, `index.ts:43,55-61`) nor `origin/ios` (`3b12997`: `connectApi.ts:7,27-38,62-70`, `vaultApi.ts:127-133`) has a user JWT auth design — both default to client-editable owner `"karim"`.
- Therefore **B0 defines the canonical identity contract** in `apps/api/app/identity/`.

### 2.2 Canonical `user_id`, D9 Age Gate & Trust Boundaries
1. **One canonical `user_id` across Quest, Community, and Messenger:** Resolved strictly from a verified Bearer JWT (`iss`, `aud`, `exp`, `nbf`, `sub`, cryptographic signature) or an active server-side `cs_app_sessions` record minted from a verified JWT.
   - Initialized from `sub` when `sub` is a valid UUID (Supabase Auth standard), or `usr_<uuid4>` for non-UUID issuers, keyed uniquely on `(issuer, subject)` in `cs_identity_links`.
   - Community `cm_profiles` and Messenger `mg_user_link` store app-specific social/link rows keyed only by this canonical `user_id` — never a second profile-of-record.
2. **Self-declared age band (`D9` — never inferred):**
   - `AgeBand = Literal["under_13", "teen_13_17", "adult_18_plus", "unknown"]` stored on `cs_users (age_band, age_declared_at, age_source='self_declared')`.
   - **Never inferred:** No LLM, recommender, or extractor may infer or mutate `age_band`.
   - **Fail-closed minor protections (`is_minor_protected = (age_band != "adult_18_plus")`):** Any account with `age_band in {"under_13", "teen_13_17", "unknown"}` is treated as minor-protected by default:
     - **Zero cross-app personalisation** (`read_community_interest_features` returns `[]`; enabling export fails closed with `MinorProtectionError` / `403`).
     - **Zero memory writes** (`write_consented` and `record_behavioral_signal` fail closed with `MinorProtectionError` / `403`).
     - Community enforces private-by-default profiles, non-discoverability/non-searchability by adults outside shared groups, and moderation priority on reports involving minor-protected accounts (`D9`).
     - Under-13 sign-up/parental-consent onboarding rules remain gated on Community's pre-`CM-B3` UAE official child digital-safety & child-data legal check (`D9`).
3. **No auto-merge by display name (`ARCHITECTURE.md` §9.2 DB-02):** Two distinct `(issuer, subject)` pairs NEVER merge because of matching `display_name`, handle, or unverified `email`. Linking a second `(issuer, subject)` to an existing `user_id` requires an explicit authenticated nonce challenge (`cs_link_challenges`).
4. **One-time pre-B0 session adoption (`adopt_session_owner`):** Both Community (`societal:docs/submissions/community/identity-memory-needs.md:19`) and Messenger (`business:docs/submissions/messenger/identity-memory-needs.md:20`) need `link_session(session_owner, verified_user_id)` so local pre-B0 rows can attach once to a verified user.
   - Exposed as `IdentityService.adopt_session_owner(principal, legacy_session_owner, *, proof_cookie_token)` (`POST /api/identity/adopt-session`): verifies the caller holds the matching `dubaiio_lab_session` cookie (via `ActionStore.owner`), refuses display-name matching, and records a one-time row in `cs_session_adoptions (session_owner PRIMARY KEY, user_id, adopted_at)` — rejecting any second adoption attempt (`409`).
5. **Hard boundary vs anonymous `dubaiio_lab_session` cookie:**
   - `dubaiio_lab_session` (`actions.py:386`) has `is_verified = False` and `auth_mode = "anonymous_lab_session"`.
   - It can **NEVER** satisfy `require_verified_jwt`, `require_app_principal`, or `require_ws_principal`, can **NEVER** mint `cs_app_sessions`, and can **NEVER** satisfy multi-user cross-app claims.
6. **Server-derived owner — zero caller spoofing:**
   - `owner` / `user_id` is ALWAYS derived from `VerifiedPrincipal` on the server; callers never supply `owner`, `user_id`, `scope`, `provenance`, or `age_band` overrides in headers/query/body.
   - `reject_spoofed_identity_headers` rejects (`400`) requests carrying override headers (`X-User-Id`, `X-Owner`, `X-Owner-Id`, `X-Dubaiio-User`, `X-Principal`, or the retired POC override header).
7. **JWT Verification (Zero New Dependencies):**
   - `apps/api/requirements.txt` includes `cryptography==50.0.2` and `httpx==0.28.1` (no `PyJWT`/`python-jose`, and `requirements.txt` is read-only).
   - `JWTVerifier` implements RFC 7519 verification on stdlib `hmac`/`hashlib`/`base64` (HS256) + `cryptography` (RS256/ES256/EdDSA via JWKS with TTL cache + `kid` refresh rate cap).
   - Strict checks: reject `alg="none"`, reject symmetric/asymmetric algorithm confusion, require `exp`, validate `nbf` within clock skew (`IDENTITY_CLOCK_SKEW_SECONDS`, default `30`, max `120`), exact `iss`/`aud` match, non-empty `sub`, check `cs_revoked_jtis`.
   - Env config read inside `apps/api/app/identity/config.py`: `IDENTITY_JWT_ISSUER`, `IDENTITY_JWT_AUDIENCE` (default `"authenticated"`), `IDENTITY_JWT_JWKS_URL`, `IDENTITY_JWT_HS256_SECRET`, `IDENTITY_CLOCK_SKEW_SECONDS`, `IDENTITY_SESSION_TTL_SECONDS` (default `86400`), `IDENTITY_WS_TICKET_TTL_SECONDS` (default `60`), `IDENTITY_TOKEN_KEY`.
8. **Per-App Sessions & Closed Capability Catalog:**
   - `AppId = Literal["quest", "community", "messenger"]`
   - Closed capability allowlists:
     - `quest`: `quest:chat`, `quest:actions`, `quest:tasks`, `memory:read:owner`, `memory:write:owner`, `memory:forget:owner`, `memory:device_token`
     - `community`: `community:read`, `community:write`, `community:moderate`, `memory:read:interests`, `memory:write:community`, `memory:forget:community`
     - `messenger`: `messenger:chat`, `messenger:ws`, `messenger:actions`, `memory:read:chat`, `memory:write:chat`, `memory:forget:chat`
   - A `community` session is rejected (`403`) on `messenger` or `quest` routes (and vice versa), even for the same `user_id`.

### 2.3 Messenger Realtime Transport & Entry `ActionEngine` Binding
- **Messenger Realtime Transport (settles `business:docs/submissions/messenger/open-questions.md`):**
  - Messenger uses a **FastAPI WebSocket on `app.messenger.server:app` (`:8070`)** bound to **B0 verified `user_id`** (Gate S).
  - Clients exchange a B0-verified Bearer JWT (`POST /api/identity/sessions` with `app_id="messenger"`) for a **same-origin HttpOnly `cs_session_messenger` cookie** or a **single-use, 60-second `Origin`-bound WS ticket** (`POST /api/identity/ws-ticket`).
  - Handshake validates `Origin` + session/ticket; subscribe, send, and replay recheck `assert_session_active` and `mg_memberships`; revoking a session or removing membership disconnects active sockets immediately.
  - **Prohibited:** Anonymous `dubaiio_lab_session` for live multi-user chat (`MG-B3` waits for Gate S); browser Supabase Realtime against `dubaiio` (`supabase/migrations/20261021000100_backend.sql:5-7,32-36` + frozen `supabase/migrations/`).
- **Entry `ActionEngine` & `CAPABILITIES` Wiring (settles `XC-M09` & `XC-C06`/`XC-CP05`):**
  - Both Community (`apps/api/app/community/`) and Messenger (`apps/api/app/messenger/`) register their action IDs (e.g. `workspace.task.create`, `community.post.publish`, `community.reply.publish`, `community.event.propose`) into `actions.CAPABILITIES` at import time — **zero edits to `apps/api/app/actions.py`**.
  - Entry HTTP routes on `:8060` / `:8070` authenticate via `require_app_principal(...)`, then call `engine().prepare(principal.user_id, ...)` and `engine().approve(principal.user_id, ...)` server-side.
  - Because `actions.py:29-33,253` types `InputValue.value: str` and `provenance: Literal["user_supplied"]`, entry callers serialize list inputs (`evidence_message_ids`, `citation_urls`) as comma-joined or JSON strings inside `InputValue` and render `demo_fixture` provenance badges on the entry's approval card envelope.

### 2.4 Relationship to `temporal_memory` Tokens (`origin/memory:mcp/tokens.py`)
- **Auth header:** All `temporal_memory` endpoints (`api/app.py:321-348`, `api/vault.py:45-58`, `api/ops.py:25`, `mcp/server.py:67-75`) use **`Authorization: Bearer <token>`** (no `X-Vault-Token` exists).
- **1:1 immutable owner ID:** `temporal_memory.owners.id == cs_users.user_id`. Never use `display_name`, email, or `"karim"`.
- **Per-user `owner-device` token isolation (defense in depth):**
  - `identity` / `memory_bridge` ensures the owner row exists (`POST /v1/owners`, `kind="real"`) using server-only `TM_ADMIN_TOKEN` and mints a per-user `owner-device` token (`POST /v1/tokens`, `role="owner-device"`, `owner=principal.user_id`, `label="cs-bridge"`).
  - The raw token is Fernet-encrypted in `cs_memory_tokens (kind='bridge_service')`; every user-scoped call from `memory_bridge` uses **that user's `owner-device` token**, never `TM_ADMIN_TOKEN` and never a `worker` token (mitigating `origin/memory:api/vault.py:55-58` until upstream fix lands).
  - Desktop/external MCP clients obtain their own `owner-device` token via `POST /api/identity/memory-device-token` (`quest` principal with `memory:device_token`, `encrypted_token=NULL`, raw token shown once for Electron `safeStorage`); `DELETE /api/identity/memory-device-token/{tm_token_id}` calls `DELETE /v1/tokens/{tm_token_id}` immediately.

### 2.5 Identity `cs_*` DDL (`apps/api/app/identity/store.py`)
```sql
CREATE TABLE IF NOT EXISTS cs_users (
    user_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL DEFAULT '',
    age_band TEXT NOT NULL DEFAULT 'unknown',     -- 'under_13' | 'teen_13_17' | 'adult_18_plus' | 'unknown' (NEVER inferred, D9)
    age_declared_at TEXT,
    age_source TEXT NOT NULL DEFAULT 'self_declared',
    status TEXT NOT NULL DEFAULT 'active',          -- active | suspended | deleted
    session_version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cs_identity_links (
    issuer TEXT NOT NULL,
    subject TEXT NOT NULL,
    user_id TEXT NOT NULL,
    email_verified INTEGER NOT NULL DEFAULT 0,      -- metadata only; NEVER auto-merges
    linked_at TEXT NOT NULL,
    link_proof TEXT NOT NULL,                       -- 'primary_jwt' | 'verified_challenge:<id>'
    PRIMARY KEY (issuer, subject),
    FOREIGN KEY (user_id) REFERENCES cs_users(user_id)
);
CREATE INDEX IF NOT EXISTS cs_identity_links_user ON cs_identity_links(user_id);

CREATE TABLE IF NOT EXISTS cs_session_adoptions (
    session_owner TEXT PRIMARY KEY,                 -- legacy anonymous cookie owner; one-time adoption only
    user_id TEXT NOT NULL,
    adopted_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES cs_users(user_id)
);

CREATE TABLE IF NOT EXISTS cs_link_challenges (
    challenge_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    nonce_hash TEXT NOT NULL,
    target_issuer TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    consumed_at TEXT,
    FOREIGN KEY (user_id) REFERENCES cs_users(user_id)
);

CREATE TABLE IF NOT EXISTS cs_app_sessions (
    session_id TEXT PRIMARY KEY,
    token_hash TEXT NOT NULL UNIQUE,
    user_id TEXT NOT NULL,
    app_id TEXT NOT NULL,                           -- 'quest' | 'community' | 'messenger'
    capabilities JSON NOT NULL,
    session_version INTEGER NOT NULL,
    source_jti TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    revocation_reason TEXT,
    FOREIGN KEY (user_id) REFERENCES cs_users(user_id)
);
CREATE INDEX IF NOT EXISTS cs_app_sessions_user_app ON cs_app_sessions(user_id, app_id, revoked_at);

CREATE TABLE IF NOT EXISTS cs_revoked_jtis (
    jti TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    revoked_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cs_ws_tickets (
    ticket_hash TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    app_id TEXT NOT NULL,
    origin TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    consumed_at TEXT,
    FOREIGN KEY (session_id) REFERENCES cs_app_sessions(session_id)
);

CREATE TABLE IF NOT EXISTS cs_memory_tokens (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    tm_owner_id TEXT NOT NULL,
    tm_token_id TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,                             -- 'bridge_service' | 'owner_device'
    label TEXT NOT NULL DEFAULT '',
    encrypted_token BLOB,
    created_at TEXT NOT NULL,
    revoked_at TEXT,
    FOREIGN KEY (user_id) REFERENCES cs_users(user_id)
);
CREATE INDEX IF NOT EXISTS cs_memory_tokens_user ON cs_memory_tokens(user_id, kind, revoked_at);

CREATE TABLE IF NOT EXISTS cs_identity_audit (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    app_id TEXT,
    session_id TEXT,
    event_kind TEXT NOT NULL,
    at TEXT NOT NULL,
    detail JSON NOT NULL
);
CREATE INDEX IF NOT EXISTS cs_identity_audit_user_at ON cs_identity_audit(user_id, at);
```

### 2.6 Identity Python Signatures (`apps/api/app/identity/`)
```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Literal, Optional
from fastapi import Header, Request, WebSocket

AppId = Literal["quest", "community", "messenger"]
AgeBand = Literal["under_13", "teen_13_17", "adult_18_plus", "unknown"]
AuthMode = Literal["verified_jwt", "verified_app_session", "verified_ws_ticket"]

APP_CAPABILITIES: dict[AppId, frozenset[str]] = {
    "quest": frozenset({
        "quest:chat", "quest:actions", "quest:tasks",
        "memory:read:owner", "memory:write:owner", "memory:forget:owner", "memory:device_token",
    }),
    "community": frozenset({
        "community:read", "community:write", "community:moderate",
        "memory:read:interests", "memory:write:community", "memory:forget:community",
    }),
    "messenger": frozenset({
        "messenger:chat", "messenger:ws", "messenger:actions",
        "memory:read:chat", "memory:write:chat", "memory:forget:chat",
    }),
}

@dataclass(frozen=True)
class VerifiedClaims:
    issuer: str
    subject: str
    audience: tuple[str, ...]
    exp: int
    iat: Optional[int] = None
    jti: Optional[str] = None
    display_name: str = ""
    email_verified: bool = False

@dataclass(frozen=True)
class VerifiedPrincipal:
    user_id: str
    app_id: Optional[AppId]
    capabilities: frozenset[str]
    auth_mode: AuthMode
    age_band: AgeBand = "unknown"
    is_verified: Literal[True] = True
    session_id: Optional[str] = None
    issuer: Optional[str] = None
    subject: Optional[str] = None
    session_version: int = 1
    expires_at: Optional[str] = None

    @property
    def is_minor_protected(self) -> bool:
        """Fail-closed D9 protection: only explicitly self-declared adult_18_plus unlocks memory writes/cross-app personalisation."""
        return self.age_band != "adult_18_plus"

@dataclass(frozen=True)
class AppSessionOut:
    session_id: str
    session_token: str
    user_id: str
    app_id: AppId
    capabilities: tuple[str, ...]
    age_band: AgeBand
    expires_at: str

@dataclass(frozen=True)
class WsTicketOut:
    ticket: str
    expires_at: str
    session_id: str
    app_id: AppId

class JWTVerificationError(Exception):
    def __init__(self, code: str, message: str) -> None: ...

class JWTVerifier:
    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        hs256_secret: str = "",
        jwks_url: str = "",
        static_jwks: Optional[dict] = None,
        allowed_algs: tuple[str, ...] = ("RS256", "ES256", "EdDSA", "HS256"),
        clock_skew_s: int = 30,
        jwks_ttl_s: int = 300,
    ) -> None: ...
    def verify(self, raw_jwt: str, *, now_ts: Optional[int] = None) -> VerifiedClaims: ...

class IdentityService:
    def authenticate_jwt(self, raw_jwt: str) -> VerifiedPrincipal: ...
    def set_age_band(self, principal: VerifiedPrincipal, *, age_band: AgeBand) -> VerifiedPrincipal: ...
    def adopt_session_owner(self, principal: VerifiedPrincipal, *, proof_cookie_token: str) -> dict: ...
    def create_app_session(
        self, principal: VerifiedPrincipal, *, app_id: AppId,
        requested_capabilities: Optional[set[str]] = None, ttl_seconds: Optional[int] = None,
    ) -> AppSessionOut: ...
    def authenticate_session(
        self, raw_session_token: str, *, expected_app: AppId,
        required_capabilities: frozenset[str] = frozenset(),
    ) -> VerifiedPrincipal: ...
    def assert_session_active(self, session_id: str, *, expected_app: AppId) -> VerifiedPrincipal: ...
    def revoke_session(self, user_id: str, session_id: str, *, reason: str = "user_logout") -> bool: ...
    def revoke_all_sessions(self, user_id: str, *, app_id: Optional[AppId] = None, reason: str = "global_revoke") -> int: ...
    def revoke_jti(self, user_id: str, jti: str, expires_at: str) -> None: ...
    def create_ws_ticket(self, principal: VerifiedPrincipal, *, origin: str) -> WsTicketOut: ...
    def consume_ws_ticket(self, raw_ticket: str, *, expected_app: AppId, origin: str) -> VerifiedPrincipal: ...
    def start_identity_link(self, principal: VerifiedPrincipal, *, target_issuer: str) -> dict: ...
    def complete_identity_link(self, principal: VerifiedPrincipal, *, challenge_id: str, proof_jwt: str) -> dict: ...

def reject_spoofed_identity_headers(request: Request) -> None: ...
def require_verified_jwt(request: Request, authorization: str | None = Header(default=None)) -> VerifiedPrincipal: ...
def require_app_principal(
    app_id: AppId, required_capabilities: frozenset[str] = frozenset(), *, allow_jwt_fallback: bool = False,
) -> Callable[..., VerifiedPrincipal]: ...
def require_ws_principal(
    websocket: WebSocket, *, app_id: AppId, required_capabilities: frozenset[str] = frozenset(),
) -> VerifiedPrincipal: ...
```
**Router (`apps/api/app/identity/router.py`, prefix `/api/identity`):**
- `GET /api/identity/me` · `POST /api/identity/age-band` · `POST /api/identity/adopt-session` · `POST /api/identity/sessions` · `DELETE /api/identity/sessions/{session_id}` · `POST /api/identity/sessions/revoke-all` · `POST /api/identity/ws-ticket` · `POST /api/identity/links/start` · `POST /api/identity/links/complete` · `POST /api/identity/memory-device-token` · `DELETE /api/identity/memory-device-token/{tm_token_id}`.

---

## 3. Messages vs Memories & Messaging Boundary (D3)

1. **Messages & social posts are not memories (`docs/submissions/CLAUDE.md:109`):** Messenger chats (`mg_*`) and Community posts/comments (`cm_*`) are stored and permissioned inside their own entry tables. They enter `temporal_memory` **only** through `MemoryBridge` after explicit consent, D9 adult age-gate check, Rule 9 screening, and source/actor/time attribution.
2. **Other people's messages & posts are third-party content:** Content authored by another participant (`author_id != principal.user_id`) may only be recorded as `Record` evidence where chat consent permits (never from scraped Community comments or another user's post); it is **never** written as confirmed `user_supplied` facts about `owner_id`, and third-party people entities never auto-promote without `user_confirmed=True` (`temporal_memory/privacy/policy.py:51-65`).
3. **Messaging boundary (D3):** Community owns **no** P2P messaging or DMs (Inbox = notifications only; "Message this person" hands off to Messenger via deep-link once Gate S passes). Parked `communities.py` `chat_*` tables remain frozen.

---

## 4. Memory Bridge Architecture (`apps/api/app/memory_bridge/` → `temporal_note`)

### 4.1 Protocol Choice: HTTP API Primary (+ Transitional `/mcp` Adapter)
- **Primary transport:** `temporal_memory` HTTP REST API (`origin/memory:api/app.py`, `api/vault.py`, `api/export_md.py`), because Vault subjects/people, quests, hypotheses, timeline, `why/{fact_id}`, Markdown export ZIP, and owner/token management exist **only** on HTTP REST (`mcp/server.py:552-571` truncates `memory_vault` and lacks `why`/`timeline`/`hypotheses`/`export`), HTTP avoids per-request StreamableHTTP session setup (`mcp/server.py:257-261`) and the 120 req/min MCP token rate limit (`mcp/server.py:271`), and MCP is designed primarily for owner-device CLI hooks (`apps/memory/README.md:10,39`).
- **Transitional MCP adapter:** Until `CR-TM-4` lands, `HttpTemporalMemoryClient.context_pack()` and `.search_facts()` may call `POST {TM_BASE_URL}/mcp/` (`tools/call` for `memory_context` / `memory_search`).

### 4.2 Upstream Handoff (`docs/submissions/shared/handoff-temporal-note.md`, D10)
Full specification is recorded in `docs/submissions/shared/handoff-temporal-note.md` for PC2's `temporal_memory` team:
1. **`CR-TM-1`:** `POST /v1/owners/{owner}/records` (record upsert + `extract.live|day|none` enqueue + optional `direct_fact` with mandatory `evidence`).
2. **`CR-TM-2`:** `POST /v1/owners/{owner}/forget` (HTTP wrapper for `forget_source` / `forget_fact`).
3. **`CR-TM-3`:** `POST /v1/owners/{owner}/facts/{fact_id}/resolve` (`confirm | edit | reject | supersede`).
4. **`CR-TM-4`:** `POST /v1/owners/{owner}/context` & `GET /v1/owners/{owner}/search?q=...&source_prefix=...` (`source_prefix` isolates `messenger:<conv_id>` and `community:`).
5. **Two upstream fixes:** `api/vault.py:55-58` (block `worker` role on vault routes) and `privacy/forget.py:147` (extend job requeue filter to `kind IN ('extract.day', 'extract.live')`).

### 4.3 Real vs Faked in B0 (`MEMORY_BRIDGE_BACKEND=fake|http`)
- Selection is env-driven inside `apps/api/app/memory_bridge/config.py`: defaults to `"fake"` when `TM_BASE_URL` is unset; setting `MEMORY_BRIDGE_BACKEND=http` without `TM_BASE_URL` / `TM_SERVICE_TOKEN` **fails closed** (`MemoryBridgeUnavailable`).
- **Real in B0:** Verified `owner_id` + D9 `is_minor_protected` enforcement, `cs_consent_grants` default-off store, Rule 9 fail-closed `sensitive.py` gate, `cs_two_visit_signals` tracker, Community strict `InterestFeature` projection + own-activity listing, Messenger chat-scope + `GroupConsentSnapshot` gate, metadata-only `cs_memory_record_refs` index, immutable `cs_memory_audit`, and `HttpTemporalMemoryClient` code (mock-transport tested).
- **Faked until `memory` merges to `main`:** `FakeTemporalMemoryClient` (clearly named fake implementing the exact `TemporalMemoryClient(Protocol)` and mirroring `origin/memory:tests/fixtures/fake_store.py` generation-fence, erase-vs-trim, `forget_rules`, and `context_pack` semantics).

---

## 5. Write Path, Trust Tiers, D9 Age Gate & Rule 9 Sensitive Filter

1. **D9 Under-18 Hard Fence (First Gate):**
   - Both `MemoryBridge.write_consented(...)` and `MemoryBridge.record_behavioral_signal(...)` check `principal.is_minor_protected` FIRST. If `True` (`age_band != "adult_18_plus"`), fail closed immediately with `MinorProtectionError` (`403`) — zero writes to `temporal_memory`, `cs_memory_record_refs`, or `cs_two_visit_signals`.
2. **Server-assigned envelope (`MemoryBridge.write_consented`):**
   - `owner_id` from `VerifiedPrincipal` (never caller-supplied).
   - Canonical attribution per entry:
     - **Messenger:** `source_kind="messenger"`, `source_id=f"messenger:{conversation_id}"`, `record_id=f"mgmsg:{message_id}"`
     - **Community (`societal:docs/submissions/community/identity-memory-needs.md`):**
       - Saved discussion: `source_kind="community"`, `source_id=f"community:post:{post_id}"`, `record_id=f"cmsave:{save_id}"` (topic-level signal only; never another user's post text as a fact about the reader)
       - Joined group: `source_kind="community"`, `source_id=f"community:group:{group_id}"`, `record_id=f"cmjoin:{membership_id}"` (weak signal routed through `record_behavioral_signal` requiring two-visit qualification; one click is never a confirmed interest)
       - Authored public post: `source_kind="community"`, `source_id=f"community:post:{post_id}"`, `record_id=f"cmpost:{post_id}"` (`author_id == principal.user_id` only)
     - **Quest / Connectors:** `quest:<thread_id>` / `qmsg:<id>`, `gmail:<id>`, `outlook:<id>`, `youtube:<id>`, `chrome:<id>`, `whatsapp_export:<id>`.
   - Carries `host_app`, `author_id`, `valid_time` (source timestamp → `Record.at` / `Fact.valid_from`), `recorded_time` (server UTC), `scope` (`owner_private | chat_scoped | cross_app_interest`), and `consent_generation`.
3. **Fail-closed consent gate:**
   - Source grant (`scope_kind="source"`) must have `enabled=True`.
   - App grant (`scope_kind="app"`) must have `write_enabled=True`.
   - Messenger writes require conversation grant (`scope_kind="conversation"`, `scope_id=f"messenger:{conversation_id}"`) with `ai_mode == "save"` AND a valid `GroupConsentSnapshot` (`caller_is_member=True`, `all_active_members_ai_enabled=True`, `cited_authors_save_enabled=True`). `ai_mode in {"off", "session"}` fails closed (`ConsentDeniedError`).
   - Post/account privacy settings and memory consent toggles are independent controls (`community/identity-memory-needs.md:52`).
4. **Rule 9 sensitive fail-closed gate:**
   - Runs Layer 1 deterministic regex/allowlist (`temporal_memory/privacy/sensitive.py` & `apps/api/app/lab/sensitive.py`: NFKC, Arabic word-boundaries, Dubai allowlist `Sheikh <Name>` / `Golden Visa` / `Dubai Police` / `ضغط الشغل`, credential/Wi-Fi detection) + optional fail-closed Layer 2 semantic screen (`ScreenUnavailable` blocks rather than publishing unscreened).
   - `credential` is **always rejected** even with `explicit_user_confirm=True`.
   - `health`, `religion`, `ethnicity_nationality`, `gender_sexuality`, `politics`, `third_party_private`, `family_third_party` are **never inferred** (`quarantined` with category-only audit entry, never dropped text). First-person explicit owner confirmations (`explicit_user_confirm=True` and `author_id == owner_id`, excluding `credential`/`family_third_party`/`third_party_private`) may store only as `owner_private` with `sensitive_cat != None` so they never export to Community.
5. **Trust tiers ↔ `temporal_memory.Provenance`:**
   - `T0_user_confirmed` → `provenance="user_supplied"`, `status="active"` (never decays per §R-ND).
   - `T1_provider_confirmed` → `provenance="provider_confirmed"`, `status="active"` (verified provider evidence only; an email body is not proof).
   - `T2_inferred_qualified` → `provenance="inferred"`, `status="hypothesis"` (**two-visit qualification required**: `>= 2` distinct signals across visits `>= 6h` apart or `>= 2` distinct days). Displayed as `"I noticed …"` with `Confirm / Edit / Not true / Forget`; never pre-fills fields, sits on approval cards, triggers proactive sends, or sets statuses.
   - `T3_demo_fixture` → `provenance="demo_fixture"`, `demo_data=True`.
6. **Supersession & correction (`resolve_fact`):**
   - `confirm` promotes `hypothesis` → `active` (`user_supplied`).
   - `edit` / `supersede` closes old fact (`valid_to=now`, `status="superseded"`, `superseded_by=new_fact_id`) and appends new evidence-linked fact.
   - `reject` (`"Not true"`) calls `forget_fact`, unlinks evidence, writes `forget_rules` if requested, and invalidates Community interest cache synchronously.

---

## 6. Per-App Read Policies (Least-Privilege Isolation)

| App | Allowed Bridge Methods | Scope, Age Gate & Consent Requirements | Output & Hard Exclusions |
|---|---|---|---|
| **Quest (Entry 1)** | `read_quest_context`, `read_quest_timeline`, `read_quest_hypotheses`, `read_why_fact`, `export_owner_markdown` | Verified `owner_id` across consented sources (`cs_consent_grants.enabled=True`). | Full provenance (`"You told me"` vs `"I noticed …"`), `as_of`, `demo_data`, evidence-limits. Excludes other owners, revoked sources, forgotten facts, and Messenger `off`/`session` threads. |
| **Community (Entry 2)** | `read_community_interest_features`, `read_community_own_activity` | **D9 Age Gate:** if `principal.is_minor_protected`, `read_community_interest_features` returns `[]` and enabling cross-app export raises `MinorProtectionError` (`403`). Adults require `app=community` `read_enabled=True` **AND** `allow_interest_export_to_community=True` (default `False`) **AND** per-source `allow_interest_export=True` (default `False`; Messenger requires `ai_mode=="save"` + conversation `allow_interest_export=True`). `read_community_own_activity` reads owner's Community-origin `cs_memory_record_refs` only (`"saved from Community, topic only"`). | **Strict allowlist `InterestFeature` DTO ONLY:** `feature_id`, `topic_slug`, `topic_label`, `weight` (decayed `[0.0, 1.0]`, floor > 0 per §R-ND), `confidence_tier` (`confirmed \| qualified_hypothesis`), `source_app`, `why_this_token`, safe template `why_this_text`, `as_of`, `consent_generation`. **NEVER** raw Quest chats, Gmail/Outlook bodies or subjects, Messenger text or `conversation_id`, Rule 9 sensitive categories, family/people names, third-party contacts, single-click signals, OAuth tokens, or ad/moderation targeting payloads. |
| **Messenger (Entry 3)** | `read_messenger_chat_scope`; opt-in `read_messenger_owner_recall` | `read_chat_scope`: verified `owner_id` + live `GroupConsentSnapshot.caller_is_member` + `ai_mode in {"session", "save"}` + facts evidenced exclusively from `messenger:<conversation_id>`. `read_owner_recall`: requires `app=messenger` `allow_cross_source_recall=True` + per-source grants; private to caller only. | Dated facts + `why` pointers (click-through re-authorizes at Messenger origin). **NEVER** raw `mg_messages`, **NEVER** cross-chat leakage (`conv-A` facts in `conv-B`), **NEVER** reads when `ai_mode == "off"`, and cross-source owner recall never auto-posts into a group. |

---

## 7. Consent Objects (`cs_*` DDL), Forget/Revoke Propagation & Audit Trail

### 7.1 `cs_*` Memory Bridge Tables (`apps/api/app/memory_bridge/schema.py`)
All grants are **default-off** (absence of row = denied):
```sql
CREATE TABLE IF NOT EXISTS cs_consent_grants (
    owner_id TEXT NOT NULL,
    scope_kind TEXT NOT NULL,                       -- 'source' | 'app' | 'conversation'
    scope_id TEXT NOT NULL,                         -- SourceKind | AppId | 'messenger:<conv_id>'
    enabled INTEGER NOT NULL DEFAULT 0,
    read_enabled INTEGER NOT NULL DEFAULT 0,
    write_enabled INTEGER NOT NULL DEFAULT 0,
    ai_mode TEXT NOT NULL DEFAULT 'off',            -- 'off' | 'session' | 'save'
    allow_interest_export INTEGER NOT NULL DEFAULT 0,
    allow_cross_source_recall INTEGER NOT NULL DEFAULT 0,
    generation INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL,
    updated_by TEXT NOT NULL,
    PRIMARY KEY (owner_id, scope_kind, scope_id)
);

CREATE TABLE IF NOT EXISTS cs_memory_record_refs (
    owner_id TEXT NOT NULL,
    record_id TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    source_id TEXT NOT NULL,
    host_app TEXT NOT NULL,
    author_is_owner INTEGER NOT NULL,
    consent_generation INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    erased_at TEXT,
    PRIMARY KEY (owner_id, record_id)
);                                                  -- Metadata & IDs ONLY; stores ZERO fact, post, or message text

CREATE TABLE IF NOT EXISTS cs_two_visit_signals (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    source_id TEXT NOT NULL,
    topic_slug TEXT NOT NULL,
    option_key TEXT NOT NULL,
    visit_at TEXT NOT NULL,
    weight REAL NOT NULL,
    promoted_fact_id TEXT,
    erased_at TEXT
);

CREATE TABLE IF NOT EXISTS cs_interest_projection_cache (
    owner_id TEXT PRIMARY KEY,
    consent_generation_sig TEXT NOT NULL,
    facts_version INTEGER NOT NULL,
    features_json JSON NOT NULL,
    computed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cs_memory_audit (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    host_app TEXT NOT NULL,
    action TEXT NOT NULL,
    scope_kind TEXT,
    scope_id TEXT,
    target_ids_json JSON NOT NULL,
    consent_generation INTEGER NOT NULL,
    outcome TEXT NOT NULL,                          -- 'ok' | 'denied' | 'quarantined' | 'partial' | 'error'
    reason_code TEXT,                               -- category/code ONLY; NEVER sensitive text or secrets
    receipt_json JSON NOT NULL,
    idempotency_key TEXT UNIQUE,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS cs_memory_audit_owner_at ON cs_memory_audit(owner_id, created_at);
```

### 7.2 Forget & Revoke Propagation Pipeline (Messenger & Community Controls)
- **Two distinct Messenger controls:**
  1. *"Forget memories from this chat"* → `MemoryBridge.forget_conversation(...)`; erases derived memories via `temporal_memory` `forget_source`, leaving Messenger's `mg_messages` intact.
  2. *"Delete chat"* → Messenger tombstones eligible `mg_messages` + removes attachments, then calls `MemoryBridge.forget_conversation(...)` (or `forget_records`).
- **Two distinct Community controls (`societal:docs/submissions/community/identity-memory-needs.md:54-58`):**
  1. *"Forget memory"* (per item or `"forget everything from Community"`) → `MemoryBridge.forget_records(...)` / `forget_source(..., source_kind="community")`; removes memory items, unlinks evidence, and wipes Community ranking/projection caches immediately while **keeping social posts intact**.
  2. *"Delete post"* → Community deletes the `cm_posts` row separately and offers/triggers `forget_records` for its derived memory signal. Withdrawing `Save-to-memory` consent stops future writes and offers Forget without silently deleting posts.
- **Synchronous 4-step cascade (`revoke_consent` with `forget_derived=True`, or `forget_*`):**
  1. **Atomic generation bump & gate close:** Increment `cs_consent_grants.generation = generation + 1` and disable the grant so concurrent reads and stale-generation writes fail closed immediately.
  2. **Synchronous local derived wipe:** Hard-delete `cs_interest_projection_cache` for `owner_id`; stamp `erased_at = now()` on matching `cs_two_visit_signals` and `cs_memory_record_refs`.
  3. **Generation-fenced `temporal_memory` Forget:** Call `TemporalMemoryClient.forget_source(owner_id, record_ids)` (mirroring `temporal_memory/privacy/forget.py:36-212`): bumps `records.generation`, erases facts whose evidence is solely in `record_ids`, trims `fact_evidence` on multi-source facts, recomputes `entity_subjects`, writes `forget_rules` to block re-import, invalidates `live/context.py` caches, and rejects any late in-flight worker via `fence_stale` (`core/applier.py:85`) / `generation_stale` (`core/validator.py:154-155`).
  4. **Idempotent audit receipt:** Write `ForgetReceipt` to `cs_memory_audit` keyed by `idempotency_key`. If `temporal_memory` HTTP is transiently unreachable, local revocation + cache invalidation STILL take effect immediately and `status="pending_reconciliation"` is recorded for idempotent retry.

---

## 8. Python Signatures (`apps/api/app/memory_bridge/`)

**Modules (`contest-shared` owned only):** `__init__.py`, `config.py`, `models.py`, `schema.py`, `sensitive.py`, `client.py`, `fake_client.py`, `consent.py`, `audit.py`, `forget.py`, `bridge.py`, `router.py` (`/api/v1/memory-bridge/*`).

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable
from app.identity.models import VerifiedPrincipal

AppId = Literal["quest", "community", "messenger"]
HostApp = Literal["quest", "community", "messenger", "connector"]
SourceKind = Literal[
    "quest", "community", "messenger", "gmail", "outlook", "youtube", "chrome", "whatsapp_export"
]
ConsentScopeKind = Literal["source", "app", "conversation"]
ConversationAIMode = Literal["off", "session", "save"]
MemoryScope = Literal["owner_private", "chat_scoped", "cross_app_interest"]
TrustTier = Literal["T0_user_confirmed", "T1_provider_confirmed", "T2_inferred_qualified", "T3_demo_fixture"]
Provenance = Literal["user_supplied", "inferred", "provider_confirmed", "demo_fixture"]
FactStatus = Literal["active", "superseded", "ended", "history", "hypothesis"]
FactResolutionAction = Literal["confirm", "edit", "reject", "supersede"]

class MinorProtectionError(PermissionError):
    """Raised when a minor-protected principal (age_band != 'adult_18_plus') attempts memory write or cross-app personalisation."""

@dataclass(frozen=True)
class MemoryRecordInput:
    record_id: str
    source_kind: SourceKind
    source_id: str
    host_app: HostApp
    author_id: str
    text: str
    valid_time: str
    scope: MemoryScope = "owner_private"
    text_orig: str | None = None
    subject_path: str | None = None
    explicit_user_confirm: bool = False
    allow_sensitive_confirmed: bool = False
    demo_data: bool = False

@dataclass(frozen=True)
class GroupConsentSnapshot:
    conversation_id: str
    caller_is_member: bool
    all_active_members_ai_enabled: bool
    cited_authors_save_enabled: bool
    membership_revision: int

@dataclass(frozen=True)
class WriteReceipt:
    ok: bool
    record_id: str
    owner_id: str
    consent_generation: int
    trust_tier: TrustTier
    provenance: Provenance
    status: Literal["applied", "queued", "quarantined", "denied"]
    fact_ids: list[str] = field(default_factory=list)
    job_id: str | None = None
    quarantine_category: str | None = None
    recorded_at: str = ""

@dataclass(frozen=True)
class MemoryFactView:
    fact_id: str
    text: str
    text_orig: str | None
    subject_id: str
    subject_path: str
    valid_from: str
    valid_to: str | None
    status: FactStatus
    superseded_by: str | None
    provenance: Provenance
    trust_tier: TrustTier
    display_prefix: Literal["You told me", "I noticed", "Confirmed source", "Demo data"]
    evidence_record_ids: list[str]
    source_ids: list[str]
    as_of: str
    demo_data: bool
    actions: list[str] = field(default_factory=list)

@dataclass(frozen=True)
class InterestFeature:
    feature_id: str
    topic_slug: str
    topic_label: str
    weight: float
    confidence_tier: Literal["confirmed", "qualified_hypothesis"]
    source_app: Literal["quest", "community", "messenger", "youtube"]
    why_this_token: str
    why_this_text: str
    as_of: str
    consent_generation: int
    demo_data: bool = False

@dataclass(frozen=True)
class ConsentGrant:
    owner_id: str
    scope_kind: ConsentScopeKind
    scope_id: str
    enabled: bool = False
    read_enabled: bool = False
    write_enabled: bool = False
    ai_mode: ConversationAIMode = "off"
    allow_interest_export: bool = False
    allow_cross_source_recall: bool = False
    generation: int = 1
    updated_at: str = ""

@dataclass(frozen=True)
class ForgetReceipt:
    idempotency_key: str
    owner_id: str
    scope_kind: ConsentScopeKind | Literal["record", "fact"]
    scope_id: str
    consent_generation: int
    temporal_generation: int | None
    records_forgotten: int
    facts_erased: int
    facts_trimmed: int
    jobs_requeued: int
    projections_invalidated: bool
    status: Literal["completed", "pending_reconciliation"]
    recorded_at: str

@runtime_checkable
class TemporalMemoryClient(Protocol):
    def ensure_owner(self, owner_id: str, *, label: str, display_name: str = "",
                     kind: Literal["real", "simulated", "demo"] = "real",
                     timezone: str = "Asia/Dubai") -> dict[str, Any]: ...
    def upsert_record_and_enqueue(
        self, owner_id: str, *, record_id: str, source: str, at: str, author: str,
        text: str, enqueue: Literal["extract.live", "extract.day", "none"] = "extract.live",
        direct_fact: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...
    def context_pack(self, owner_id: str, text: str, *, max_tokens: int = 1500) -> dict[str, Any]: ...
    def search_facts(self, owner_id: str, query: str, *, limit: int = 20,
                     source_prefix: str | None = None) -> list[dict[str, Any]]: ...
    def get_vault_subjects(self, owner_id: str) -> dict[str, Any]: ...
    def get_vault_people(self, owner_id: str) -> dict[str, Any]: ...
    def get_hypotheses(self, owner_id: str) -> dict[str, Any]: ...
    def get_timeline(self, owner_id: str, *, date_from: str | None = None,
                     date_to: str | None = None, limit: int = 200) -> dict[str, Any]: ...
    def get_why_fact(self, owner_id: str, fact_id: str) -> dict[str, Any]: ...
    def resolve_fact(self, owner_id: str, fact_id: str, *, action: FactResolutionAction,
                     new_text: str | None = None, valid_from: str | None = None,
                     evidence_record_id: str | None = None) -> dict[str, Any]: ...
    def forget_source(self, owner_id: str, record_ids: list[str]) -> dict[str, Any]: ...
    def forget_fact(self, owner_id: str, fact_id: str) -> dict[str, Any]: ...
    def export_markdown_zip(self, owner_id: str) -> bytes: ...

class MemoryBridge:
    def __init__(self, db: Any, client: TemporalMemoryClient, *, screen_fn: Any | None = None) -> None: ...
    def get_consent(self, principal: VerifiedPrincipal, scope_kind: ConsentScopeKind, scope_id: str) -> ConsentGrant: ...
    def set_source_consent(self, principal: VerifiedPrincipal, source_kind: SourceKind, *,
                           enabled: bool, allow_interest_export: bool = False,
                           forget_on_revoke: bool = True, idempotency_key: str | None = None) -> tuple[ConsentGrant, ForgetReceipt | None]: ...
    def set_app_consent(self, principal: VerifiedPrincipal, app_id: AppId, *,
                        read_enabled: bool, write_enabled: bool,
                        allow_interest_export_to_community: bool = False,
                        allow_cross_source_recall: bool = False) -> ConsentGrant: ...
    def set_conversation_consent(self, principal: VerifiedPrincipal, conversation_id: str, *,
                                 ai_mode: ConversationAIMode, allow_interest_export: bool = False,
                                 forget_on_withdraw: bool = False, idempotency_key: str | None = None) -> tuple[ConsentGrant, ForgetReceipt | None]: ...
    def write_consented(self, principal: VerifiedPrincipal, item: MemoryRecordInput, *,
                        group_consent: GroupConsentSnapshot | None = None,
                        expected_consent_generation: int | None = None) -> WriteReceipt: ...
    def record_behavioral_signal(self, principal: VerifiedPrincipal, *, source_kind: SourceKind,
                                 source_id: str, topic_slug: str, option_key: str,
                                 at: str, weight: float = 1.0) -> dict[str, Any]: ...
    def resolve_fact(self, principal: VerifiedPrincipal, fact_id: str, *,
                     action: FactResolutionAction, host_app: AppId,
                     new_text: str | None = None, valid_from: str | None = None) -> dict[str, Any]: ...
    def read_quest_context(self, principal: VerifiedPrincipal, query: str, *, max_tokens: int = 1500) -> dict[str, Any]: ...
    def read_quest_timeline(self, principal: VerifiedPrincipal, *, limit: int = 100) -> list[MemoryFactView]: ...
    def read_quest_hypotheses(self, principal: VerifiedPrincipal) -> list[MemoryFactView]: ...
    def read_why_fact(self, principal: VerifiedPrincipal, fact_id: str, *, host_app: AppId) -> dict[str, Any]: ...
    def read_community_interest_features(self, principal: VerifiedPrincipal, *, limit: int = 20) -> list[InterestFeature]: ...
    def read_community_own_activity(self, principal: VerifiedPrincipal, *, limit: int = 50) -> list[dict[str, Any]]: ...
    def read_messenger_chat_scope(self, principal: VerifiedPrincipal, conversation_id: str, *,
                                  group_consent: GroupConsentSnapshot, query: str = "", limit: int = 20) -> list[MemoryFactView]: ...
    def read_messenger_owner_recall(self, principal: VerifiedPrincipal, conversation_id: str, *,
                                    query: str, limit: int = 10) -> list[MemoryFactView]: ...
    def forget_records(self, principal: VerifiedPrincipal, record_ids: list[str], *,
                       host_app: AppId, idempotency_key: str) -> ForgetReceipt: ...
    def forget_conversation(self, principal: VerifiedPrincipal, conversation_id: str, *,
                            idempotency_key: str) -> ForgetReceipt: ...
    def forget_source(self, principal: VerifiedPrincipal, source_kind: SourceKind, *,
                      host_app: AppId, idempotency_key: str) -> ForgetReceipt: ...
    def list_audit_events(self, principal: VerifiedPrincipal, *, limit: int = 100) -> list[dict[str, Any]]: ...
```

---

## 9. B0 Contract Test Matrix (Required for Gate S)

Every test suite runs on SQLite and Postgres with synthetic fixtures only, shipping both **happy-path** and **failure-path** assertions:

### 9.1 Identity Tests (`apps/api/tests/test_identity_*.py`)
1. **ID-01 (`test_identity_two_users_isolated`):** Two verified JWTs (`sub_a`, `sub_b`) resolve to distinct `user_id`s identically across `quest`, `community`, `messenger` (happy); User A cannot inspect/revoke User B's sessions or WS tickets (`403`/`404`, failure).
2. **ID-02 (`test_identity_expiry`):** Valid unexpired JWT/session/WS ticket succeeds (happy); expired JWT past skew, future `nbf`, missing `exp`, expired `cs_app_sessions`, and expired `cs_ws_tickets` fail with `401` (failure).
3. **ID-03 (`test_identity_jwt_signature_and_claims`):** Valid HS256 and RS256/EdDSA via JWKS return verified principal (happy); tampered payload/signature, `alg="none"`, HS256-with-RSA-pubkey confusion, wrong `iss`/`aud`, empty `sub`, unknown `kid` fail with `401` (failure).
4. **ID-04 (`test_identity_revocation_immediate`):** Active session & WS ticket succeed once (happy); `revoke_session`, `revoke_all_sessions` (`session_version` bump), `cs_revoked_jtis`, WS ticket replay, and wrong `Origin` fail immediately (`401`/`403`, failure).
5. **ID-05 (`test_identity_cross_app_capability_isolation`):** App session works on its own app with granted capabilities (happy); `community` session rejected on `messenger`/`quest`, `messenger` session rejected on `community`, out-of-allowlist capability request rejected, missing capability rejected (`403`/`422`, failure).
6. **ID-06 (`test_identity_no_merge_by_display_name`):** Explicit challenge-based linking binds a second `(issuer, subject)` (happy); two distinct `(issuer, subject)` tokens sharing identical `display_name` + unverified email NEVER merge, and replayed/expired/wrong-user link challenges fail (`400`/`403`, failure).
7. **ID-07 (`test_identity_anon_cookie_boundary`):** Legacy `/api/session` & `/api/actions` remain green (happy); valid `dubaiio_lab_session` cookie (even copied into `cs_session_*`) fails verified identity routes with `401` (failure).
8. **ID-08 (`test_identity_spoofing_rejected`):** Normal JWT/session succeeds (happy); `X-User-Id`, `X-Owner`, `X-Owner-Id`, `X-Dubaiio-User`, `X-Principal`, or retired POC header returns `400`, and mismatched body/query `owner`/`user_id` returns `403`/`422` (failure).
9. **ID-09 (`test_identity_tm_token_binding_and_revocation`):** Minting `owner-device` token binds `owner == principal.user_id` and works for that owner (happy); revoking calls `DELETE /v1/tokens/{id}` and blocks subsequent calls, and User A's token fails `403` on User B's scope (failure).
10. **ID-10 (`test_identity_age_band_self_declared`):** `POST /api/identity/age-band` sets `adult_18_plus` / `teen_13_17` / `under_13` with `age_source="self_declared"` and sets `is_minor_protected=False` only for `adult_18_plus` (happy); default `unknown`, `teen_13_17`, and `under_13` all enforce `is_minor_protected=True`, and invalid/inferred age overrides are rejected `400`/`422` (failure).
11. **ID-11 (`test_identity_session_owner_adoption`):** Valid `dubaiio_lab_session` cookie proof adopts `session_owner` once into `cs_session_adoptions` (happy); missing/wrong cookie proof, display-name-only match, or adopting an already-adopted `session_owner` by another user fails `401`/`409` (failure).

### 9.2 Memory Bridge, Consent, Age Gate & Forget Tests (`apps/api/tests/test_memory_bridge_*.py`)
1. **MB-01 (`test_mb_default_off_consent`):** Enabling explicit source + app/conversation grant for an `adult_18_plus` user permits write/read (happy); fresh user attempting Quest, Community, or Messenger write/read fails closed with `ConsentDeniedError` (failure).
2. **MB-02 (`test_mb_two_user_isolation`):** User A reads own vault/context/timeline/`why`/chat scope/interests/audit (happy); User B gets empty/`403`/`404` on all User A endpoints (failure).
3. **MB-03 (`test_mb_no_owner_or_provenance_spoof`):** Server sets `owner_id` and `provenance` from verified principal + flow (happy); caller payload attempting to set another `owner` or forge `user_supplied` is rejected (failure).
4. **MB-04 (`test_mb_rule9_sensitive_fail_closed`):** Dubai allowlist (`Sheikh Zayed`, `Golden Visa`, `Dubai Police`, `ضغط الشغل`) passes (happy); credentials (`OTP`, `IBAN`, `password`, Wi-Fi key, `كلمة السر`) always reject even when confirmed, inferred sensitive categories (EN/AR/Arabizi) quarantine with category-only audit, and Layer 2 `ScreenUnavailable` fails closed (failure).
5. **MB-05 (`test_mb_third_party_message_rule`):** Owner's confirmed statement writes `Fact` (happy); `author_id != owner_id` (or scraped Community comment/another user's post) never writes a confirmed fact about `owner_id` and never auto-promotes third-party people (`may_promote == False`) (failure).
6. **MB-06 (`test_mb_two_visit_qualification`):** `>= 2` distinct signals `>= 6h` apart (or `>= 2` distinct days) qualify as `"I noticed …"` `hypothesis` (happy); single click or two signals `< 6h` apart never creates a hypothesis or Community `InterestFeature` (failure).
7. **MB-07 (`test_mb_community_strict_allowlist`):** With `adult_18_plus` + `allow_interest_export_to_community=True` + source export ON, returns `InterestFeature` DTO only (happy); default OFF returns `[]`, payload asserts zero raw Quest/Gmail/Outlook/Messenger text, zero `conversation_id`, zero sensitive/family/people names, and toggling OFF immediately clears results on next call (failure).
8. **MB-08 (`test_mb_messenger_chat_scope_and_group_gate`):** Consented group with all members active returns facts from `messenger:conv-A` only (happy); `ai_mode="off"`/`"session"` blocks writes, one `off` group member blocks chat-scope read/write, and `conv-A` facts never appear in `conv-B` (failure).
9. **MB-09 (`test_mb_supersession_and_correction`):** `confirm` promotes hypothesis to `user_supplied`, `edit`/`supersede` closes prior fact (`valid_to`, `superseded_by`) and invalidates Community projection (happy); `reject` hides immediately from search/timeline/Community (failure).
10. **MB-10 (`test_mb_forget_revoke_generation_fence_and_audit`):** `forget_conversation` / `forget_source` erases only-evidence facts, trims multi-source facts (surviving evidence keeps fact visible), bumps `consent_generation` and `temporal_generation`, invalidates Community cache synchronously, and emits idempotent `ForgetReceipt` in `cs_memory_audit` (happy); stale-generation in-flight worker is rejected by fence (zero resurrection), idempotent replay returns prior receipt without double-erase, transient HTTP outage still revokes locally and records `pending_reconciliation`, and audit log contains zero leaked secret text (failure).
11. **MB-11 (`test_mb_minor_age_gate_blocks_writes_and_personalisation`):** Self-declared `adult_18_plus` user with consent writes and reads `InterestFeature` (happy); `under_13`, `teen_13_17`, and `unknown` users fail closed (`MinorProtectionError` / `403`) on `write_consented`, `record_behavioral_signal`, and `allow_interest_export_to_community`, and `read_community_interest_features` returns `[]` (failure).
12. **MB-12 (`test_mb_community_activity_and_forget_keeps_posts`):** Saved Community discussion (`cmsave:*`) and authored post (`cmpost:*`) appear in `read_community_own_activity` (`"saved from Community, topic only"`) and Quest recall, and `forget_source("community")` erases them from Quest & Community ranking while leaving the user's social post intact (happy); another user sees `[]`/`403` and forgotten signal never resurrects on re-query (failure).

### 9.3 Cross-App Gate S E2E (`apps/api/tests/test_memory_bridge_e2e.py`)
1. **E2E-01 (`test_gate_s_three_app_roundtrip`):** Single verified `adult_18_plus` `user_id` across Quest, Community, and Messenger: Quest confirms interest → Community reads `InterestFeature` with zero private text leak → Community saves discussion → Quest recalls within scope → Messenger saves consented chat decision → Quest recalls within scope → Forget removes Community & Messenger derived memories immediately across all 3 apps while social posts & `mg_messages` remain intact; minor-protected account writes nothing; second user sees zero data; legacy `/api/session` & `apps/web` untouched.
