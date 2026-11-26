# Shared B0 Build Slices (`contest-shared`)

**Status:** `approved — 23 Nov 2026 (founder, D11)`
**Date:** 2026-11-23
**Branch:** `contest-shared` (lane branches: `cs/<slice-id>`, cut from `contest-shared`)
**Note on execution:** B0 (`docs/submissions/shared/briefs/3-build-shared.md` (removed 26 Nov; see git history)) starts **only after** the founder sets this document's status line to `approved — <date>`.

---

## Dependency & Parallelism Map

```text
  [CS-B1: Identity Core, JWT, Age Gate, Session Adoption, App Sessions & WS Tickets]
         │
         ▼
  [CS-B2: temporal_note Client, FakeClient & Rule 9 Sensitive Gate]
         │
         ├──────────────────────────────────────┐
         ▼                                      ▼
  [CS-B3: Consent Store, Minor Fence,    [CS-B4: Forget/Revoke Cascade,
   Writes, Two-Visit & Per-App Reads]     Audit Log & HTTP Router]
         │                                      │
         └──────────────────┬───────────────────┘
                            ▼
  [CS-B5: temporal_memory Token Binding & Gate S Cross-App E2E]
```

All slices touch **only** `contest-shared` owned paths (`apps/api/app/identity/**`, `apps/api/app/memory_bridge/**`, `apps/api/tests/test_identity_*.py`, `apps/api/tests/test_memory_bridge_*.py`, `apps/api/tests/fixtures/contest_shared/**`, `docs/submissions/shared/**`). Zero edits to `main.py`, `config.py`, `actions.py`, `auth.py`, `communities.py`, `requirements.txt`, `apps/memory/**`, `apps/web/**`, or `supabase/migrations/`.

---

## `CS-B1` — Identity Core, JWT Verifier, D9 Age Gate, App Sessions & WS Tickets

- **Goal:** Deliver the single verified `user_id` across Quest, Community, and Messenger with cryptographic Bearer JWT verification (HS256 + RS256/ES256/EdDSA via `cryptography`, zero new packages), `(issuer, subject)` identity linking (no display-name auto-merge), D9 self-declared `age_band` (`cs_users.age_band`, `VerifiedPrincipal.is_minor_protected`, never inferred), one-time proof-based `adopt_session_owner`, per-app sessions + closed capability allowlists, single-use `Origin`-bound WebSocket tickets, anti-spoofing dependency guards, and strict isolation from anonymous `dubaiio_lab_session` cookies.
- **Owned files (no overlap):**
  - `apps/api/app/identity/__init__.py`
  - `apps/api/app/identity/config.py`
  - `apps/api/app/identity/models.py`
  - `apps/api/app/identity/jwt.py`
  - `apps/api/app/identity/store.py` (`cs_users`, `cs_identity_links`, `cs_session_adoptions`, `cs_link_challenges`, `cs_app_sessions`, `cs_revoked_jtis`, `cs_ws_tickets`, `cs_identity_audit`)
  - `apps/api/app/identity/service.py`
  - `apps/api/app/identity/deps.py`
  - `apps/api/app/identity/router.py` (`/api/identity/*`)
  - `apps/api/tests/fixtures/contest_shared/identity_fixtures.py`
  - `apps/api/tests/test_identity_jwt.py`
  - `apps/api/tests/test_identity_sessions.py`
  - `apps/api/tests/test_identity_isolation.py`
- **Depends on:** None (builds first after Founder Gate).
- **Happy-path tests:**
  - Valid HS256 and RS256/EdDSA JWTs resolve identically across `quest`, `community`, and `messenger` to one canonical `user_id` (ID-01, ID-03).
  - Minting and authenticating per-app sessions + capability subset checks pass for matching app (ID-05).
  - Explicit `start_identity_link` + `complete_identity_link` binds a second `(issuer, subject)` via valid challenge proof (ID-06).
  - Minting and consuming a single-use WS ticket with matching `Origin` returns verified principal (ID-04).
  - `POST /api/identity/age-band` records self-declared `adult_18_plus` / `teen_13_17` / `under_13`; `POST /api/identity/adopt-session` adopts a valid `dubaiio_lab_session` owner once (ID-10, ID-11).
- **Failure-path tests:**
  - Two-user cross-session/ticket access fails `403`/`404` (ID-01).
  - Expired JWT/session/WS ticket, future `nbf`, missing `exp`, `alg="none"`, HS256/RSA confusion, tampered sig, wrong `iss`/`aud`/empty `sub`/unknown `kid` fail `401` (ID-02, ID-03).
  - `revoke_session`, `revoke_all_sessions` (`session_version` bump), `cs_revoked_jtis`, WS ticket replay, and wrong `Origin` fail `401`/`403` (ID-04).
  - Cross-app session use and out-of-allowlist capability requests fail `403`/`422` (ID-05).
  - Identical `display_name` + unverified email never merge; replayed/expired link challenges fail; second adoption of `session_owner` fails `409` (ID-06, ID-11).
  - `dubaiio_lab_session` cookie rejected `401` on all verified routes while legacy `/api/session` & `/api/actions` pass untouched (ID-07).
  - Spoof headers (`X-User-Id`, `X-Owner`, `X-Owner-Id`, `X-Dubaiio-User`, `X-Principal`, legacy POC header) fail `400`; mismatched body/query `owner`/`user_id` and invalid/inferred `age_band` overrides fail `400`/`403`/`422` (ID-08, ID-10).
- **Unblocks:** `CS-B2`..`CS-B5`; Community `CM-B5` (identity hookup); Messenger `MG-B3` (live WebSocket chat on `:8070`) & `MG-B6` (`ActionEngine` approvals under verified `user_id`).

---

## `CS-B2` — `temporal_note` Client Protocol, `FakeTemporalMemoryClient` & Rule 9 Sensitive Gate

- **Goal:** Implement the transport-agnostic `TemporalMemoryClient(Protocol)`, `HttpTemporalMemoryClient` (HTTP `/v1/*` + transitional `/mcp` JSON-RPC adapter for `CR-TM-4`), clearly named `FakeTemporalMemoryClient` (mirroring `origin/memory:tests/fixtures/fake_store.py` generation fence, erase-vs-trim, `forget_rules`, `context_pack`), `cs_*` memory-bridge schema initializer, and the two-layer fail-closed Rule 9 sensitive filter.
- **Owned files (no overlap):**
  - `apps/api/app/memory_bridge/__init__.py`
  - `apps/api/app/memory_bridge/config.py` (`MEMORY_BRIDGE_BACKEND=fake|http`)
  - `apps/api/app/memory_bridge/models.py`
  - `apps/api/app/memory_bridge/schema.py` (`cs_consent_grants`, `cs_memory_record_refs`, `cs_two_visit_signals`, `cs_interest_projection_cache`, `cs_memory_audit`)
  - `apps/api/app/memory_bridge/sensitive.py`
  - `apps/api/app/memory_bridge/client.py`
  - `apps/api/app/memory_bridge/fake_client.py`
  - `apps/api/tests/fixtures/contest_shared/memory_fixtures.py`
  - `apps/api/tests/test_memory_bridge_client.py`
  - `apps/api/tests/test_memory_bridge_sensitive.py`
- **Depends on:** `CS-B1` (`VerifiedPrincipal` contract).
- **Happy-path tests:**
  - `HttpTemporalMemoryClient` serializes `/v1/owners`, `/v1/owners/{owner}/vault/*`, `/hypotheses`, `/timeline`, `/why/{fact_id}`, `/export/md.zip`, `/records`, `/forget`, `/facts/{id}/resolve`, and `/mcp` JSON-RPC cleanly against mock HTTP transport, matching `FakeTemporalMemoryClient` return shapes.
  - Rule 9 gate allows Dubai allowlist phrases (`Sheikh Zayed`, `Golden Visa`, `Dubai Police`, `ضغط الشغل`) and clean non-sensitive statements (MB-04).
- **Failure-path tests:**
  - `MEMORY_BRIDGE_BACKEND=http` without `TM_BASE_URL` or `TM_SERVICE_TOKEN` fails closed (`MemoryBridgeUnavailable`), never falling back to fake.
  - Credentials (`OTP`, `IBAN`, `password`, Wi-Fi key, `كلمة السر`) ALWAYS reject even with `explicit_user_confirm=True`; inferred sensitive categories (EN/AR/Arabizi) quarantine fail-closed with category-only metadata (zero leaked secret text); Layer 2 `ScreenUnavailable` fails closed (MB-04).
- **Unblocks:** `CS-B3`, `CS-B4`, `CS-B5`.

---

## `CS-B3` — Consent Store, D9 Minor Fence, Write Path, Two-Visit & Per-App Read Projections

- **Goal:** Build default-off `ConsentStore` (`cs_consent_grants` with monotonic `generation`) and `MemoryBridge` write/read orchestration: D9 under-18 fail-closed fence (`MinorProtectionError` on writes, behavioral signals, and cross-app personalisation), consent gates, `GroupConsentSnapshot`, third-party message/post rule, `cs_two_visit_signals`, fact resolution/supersession, Community canonical source namespaces (`community:post:*`, `community:group:*`) + strict `InterestFeature` projection + `read_community_own_activity`, Quest owner reads, and Messenger chat-scoped + opt-in private owner recall.
- **Owned files (no overlap with `CS-B4`):**
  - `apps/api/app/memory_bridge/consent.py`
  - `apps/api/app/memory_bridge/bridge.py`
  - `apps/api/tests/test_memory_bridge_consent.py`
  - `apps/api/tests/test_memory_bridge_writes.py`
  - `apps/api/tests/test_memory_bridge_reads.py`
- **Depends on:** `CS-B1`, `CS-B2`.
- **Happy-path tests:**
  - Explicit source + app/conversation grant unlocks write/read for `adult_18_plus` (MB-01).
  - Owner confirmed statement writes `user_supplied` fact (MB-05); `>= 2` signals `>= 6h` apart promote to `"I noticed …"` `hypothesis` (MB-06).
  - `confirm` / `edit` / `supersede` updates lifecycle and invalidates Community projection (MB-09).
  - Community `read_community_interest_features` returns `InterestFeature` DTOs only when dual opt-in is active; `read_community_own_activity` lists owner's Community-origin signals only (MB-07, MB-12).
  - Messenger `read_messenger_chat_scope` returns facts scoped strictly to `messenger:<conversation_id>` (MB-08).
- **Failure-path tests:**
  - Fresh default-off user fails closed (`ConsentDeniedError`, MB-01); caller cannot spoof `owner` or `provenance` (MB-03).
  - `under_13`, `teen_13_17`, and `unknown` users fail closed (`MinorProtectionError` / `403`) on `write_consented`, `record_behavioral_signal`, and `allow_interest_export_to_community`, and `read_community_interest_features` returns `[]` (MB-11).
  - Two-user cross-read isolation returns empty/`403`/`404` (MB-02).
  - Third-party `author_id != owner_id` (and scraped Community comments / other users' posts) never writes a confirmed owner fact or auto-promotes third-party people (MB-05).
  - Single click or `< 6h` signals never create a hypothesis or `InterestFeature` (MB-06).
  - Community payload asserts zero raw Quest/Gmail/Outlook/Messenger text, zero `conversation_id`, zero sensitive/family/people names; toggling export OFF returns `[]` immediately (MB-07).
  - Messenger `ai_mode="off"`/`"session"`, any `off` group member, or cross-chat query (`conv-A` vs `conv-B`) is blocked/isolated (MB-08); `reject` hides facts immediately (MB-09).
- **Unblocks:** Community `CM-B8` (memory bridge integration) & `CM-B9` (cross-app Discovery Agent); Messenger `MG-B5` (scoped memory).

---

## `CS-B4` — Forget & Revoke Propagation, Generation Fence, Immutable Audit & Router

- **Goal:** Build immutable `AuditStore` (`cs_memory_audit` with category-only Rule 9 hygiene), `ForgetCoordinator` (synchronous 4-step cascade: atomic `consent_generation` bump → cache/signals/refs wipe → `temporal_memory` `forget_source` generation fence → idempotent `ForgetReceipt`), and FastAPI router `/api/v1/memory-bridge/*` for consent, reads, writes, forget, and audit.
- **Owned files (no overlap with `CS-B3`):**
  - `apps/api/app/memory_bridge/audit.py`
  - `apps/api/app/memory_bridge/forget.py`
  - `apps/api/app/memory_bridge/router.py`
  - `apps/api/tests/test_memory_bridge_forget.py`
  - `apps/api/tests/test_memory_bridge_audit.py`
- **Depends on:** `CS-B2`, `CS-B3`.
- **Happy-path tests:**
  - `forget_conversation` / `forget_source` / `revoke_consent(forget_derived=True)` erases only-evidence facts, trims shared-evidence facts (keeping multi-source facts visible), clears `cs_interest_projection_cache` & `cs_two_visit_signals`, leaves Messenger `mg_messages` and Community social posts intact on memory-only forget, and writes `ForgetReceipt` (MB-10, MB-12).
  - Idempotent replay with same `idempotency_key` returns prior receipt without re-erasing (MB-10).
- **Failure-path tests:**
  - Simulated stale-generation in-flight extraction worker attempting commit post-Forget is rejected (`generation_stale`/`fence_stale`) with zero resurrection (MB-10, MB-12).
  - Transient `temporal_memory` HTTP outage still closes local consent & wipes local projections immediately and records `status="pending_reconciliation"` (MB-10).
  - Audit endpoints enforce owner isolation and never leak quarantined secret text (MB-02, MB-10).
- **Unblocks:** Community `CM-B8` (delete/revoke propagation) & `CM-B11` demo hardening; Messenger `MG-B5` ("Forget memories from this chat" & "Delete chat"); Quest Forget auditability.

---

## `CS-B5` — `temporal_memory` Token Binding & Gate S Cross-App E2E Suite

- **Goal:** Implement `apps/api/app/identity/memory_tokens.py` (per-user `owner-device` token provisioning, Fernet storage in `cs_memory_tokens`, and immediate `DELETE /v1/tokens/{id}` revocation so `memory_bridge` and desktop/MCP clients never share `TM_ADMIN_TOKEN` or `worker` tokens), and run the full Gate S end-to-end suite across Quest, Community, and Messenger facades plus full API regression & frozen `apps/web` gates.
- **Owned files:**
  - `apps/api/app/identity/memory_tokens.py`
  - `apps/api/tests/test_identity_tm_tokens.py`
  - `apps/api/tests/test_memory_bridge_e2e.py`
- **Depends on:** `CS-B1`, `CS-B2`, `CS-B3`, `CS-B4`.
- **Happy-path tests:**
  - Per-user `owner-device` token binds `owner == principal.user_id` and unlocks owner Vault/bridge calls (ID-09).
  - Cross-app E2E (`E2E-01`): verified `adult_18_plus` `user_id` signs into Quest, Community, and Messenger → Quest confirms interest → Community reads `InterestFeature` → Community saves discussion → Messenger saves business decision → Quest recalls both within scope → Forget removes derived memories immediately across all 3 apps while social posts & `mg_messages` stay intact.
- **Failure-path tests:**
  - Revoking `tm_token_id` immediately blocks subsequent calls; User A's `owner-device` token fails `403` on User B's owner path (ID-09).
  - Minor-protected account (`under_13` / `teen_13_17` / `unknown`) writes nothing and sees zero cross-app personalisation; User B sees zero memories, interests, or audit events from User A across all three app facades; legacy `/api/session` & `apps/web` remain untouched (E2E-01).
- **Unblocks:** **Gate S** — merge `contest-shared` into `societal` (`CM-B5`, `CM-B8`, `CM-B9`) and `business` (`MG-B3`, `MG-B5`, `MG-B6`, `MG-B7`).
