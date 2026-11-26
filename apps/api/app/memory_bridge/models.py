"""Closed enums, exceptions, DTOs, and TemporalMemoryClient protocol for CS-B2."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

AppId = Literal["quest", "community", "messenger"]
HostApp = Literal["quest", "community", "messenger", "connector"]
SourceKind = Literal[
    "quest",
    "community",
    "messenger",
    "gmail",
    "outlook",
    "youtube",
    "chrome",
    "whatsapp_export",
]
ConsentScopeKind = Literal["source", "app", "conversation"]
ConversationAIMode = Literal["off", "session", "save"]
MemoryScope = Literal["owner_private", "chat_scoped", "cross_app_interest"]
TrustTier = Literal[
    "T0_user_confirmed",
    "T1_provider_confirmed",
    "T2_inferred_qualified",
    "T3_demo_fixture",
]
Provenance = Literal["user_supplied", "inferred", "provider_confirmed", "demo_fixture"]
FactStatus = Literal["active", "superseded", "ended", "history", "hypothesis"]
FactResolutionAction = Literal["confirm", "edit", "reject", "supersede"]

APP_IDS: frozenset[str] = frozenset({"quest", "community", "messenger"})
HOST_APPS: frozenset[str] = frozenset({"quest", "community", "messenger", "connector"})
SOURCE_KINDS: frozenset[str] = frozenset(
    {"quest", "community", "messenger", "gmail", "outlook", "youtube", "chrome", "whatsapp_export"}
)
CONSENT_SCOPE_KINDS: frozenset[str] = frozenset({"source", "app", "conversation"})
CONVERSATION_AI_MODES: frozenset[str] = frozenset({"off", "session", "save"})
MEMORY_SCOPES: frozenset[str] = frozenset({"owner_private", "chat_scoped", "cross_app_interest"})
TRUST_TIERS: frozenset[str] = frozenset(
    {"T0_user_confirmed", "T1_provider_confirmed", "T2_inferred_qualified", "T3_demo_fixture"}
)
PROVENANCES: frozenset[str] = frozenset(
    {"user_supplied", "inferred", "provider_confirmed", "demo_fixture"}
)
FACT_STATUSES: frozenset[str] = frozenset({"active", "superseded", "ended", "history", "hypothesis"})
FACT_RESOLUTION_ACTIONS: frozenset[str] = frozenset({"confirm", "edit", "reject", "supersede"})


class MemoryBridgeError(Exception):
    """Base error for memory bridge operations."""

    def __init__(
        self,
        message: str = "memory bridge error",
        *,
        code: str = "memory_bridge_error",
        status_code: int = 400,
    ) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class ConsentDeniedError(MemoryBridgeError, PermissionError):
    """Raised when required consent, membership, or token scope is missing or denied."""

    def __init__(
        self,
        message: str = "consent denied",
        *,
        code: str = "consent_denied",
        status_code: int = 403,
    ) -> None:
        super().__init__(message, code=code, status_code=status_code)


class MinorProtectionError(MemoryBridgeError, PermissionError):
    """Raised when a minor-protected principal (age_band != 'adult_18_plus') attempts memory write or cross-app personalisation."""

    def __init__(
        self,
        message: str = "minor-protected account cannot perform this operation",
        *,
        code: str = "minor_protection_required",
        status_code: int = 403,
    ) -> None:
        super().__init__(message, code=code, status_code=status_code)


class MemoryBridgeUnavailable(MemoryBridgeError, RuntimeError):
    """Raised fail-closed when the temporal_memory backend or required configuration is unavailable."""

    def __init__(
        self,
        message: str = "memory bridge backend unavailable",
        *,
        code: str = "memory_bridge_unavailable",
        status_code: int = 503,
    ) -> None:
        super().__init__(message, code=code, status_code=status_code)


class SensitiveContentError(MemoryBridgeError, ValueError):
    """Raised when content is blocked by the Rule 9 sensitive gate (category only, never raw text)."""

    def __init__(
        self,
        category: str,
        message: str | None = None,
        *,
        status_code: int = 400,
    ) -> None:
        self.category = category
        super().__init__(
            message or f"content blocked by sensitive privacy gate ({category})",
            code=f"sensitive_{category}",
            status_code=status_code,
        )


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
    def ensure_owner(
        self,
        owner_id: str,
        *,
        label: str,
        display_name: str = "",
        kind: Literal["real", "simulated", "demo"] = "real",
        timezone: str = "Asia/Dubai",
    ) -> dict[str, Any]: ...

    def mint_owner_device_token(
        self,
        owner_id: str,
        *,
        label: str = "cs-bridge",
    ) -> dict[str, Any]: ...

    def revoke_token(self, token_id: str) -> dict[str, Any]: ...

    def upsert_record_and_enqueue(
        self,
        owner_id: str,
        *,
        record_id: str,
        source: str,
        at: str,
        author: str,
        text: str,
        enqueue: Literal["extract.live", "extract.day", "none"] = "extract.live",
        direct_fact: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    def context_pack(
        self,
        owner_id: str,
        text: str,
        *,
        max_tokens: int = 1500,
    ) -> dict[str, Any]: ...

    def reinforce_recall(self, owner_id: str, fact_ids: list[str]) -> dict[str, float]: ...

    def search_facts(
        self,
        owner_id: str,
        query: str,
        *,
        limit: int = 20,
        source_prefix: str | None = None,
        include_lowered: bool = False,
    ) -> list[dict[str, Any]]: ...

    def set_memory_lowered(self, owner_id: str, *, lower: bool = True, **target: Any) -> dict[str, Any]: ...

    def lowered_record_ids(self, owner_id: str) -> set[str]: ...

    def get_vault_subjects(self, owner_id: str) -> dict[str, Any]: ...

    def get_vault_people(self, owner_id: str) -> dict[str, Any]: ...

    def get_hypotheses(self, owner_id: str) -> dict[str, Any]: ...

    def get_timeline(
        self,
        owner_id: str,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 200,
    ) -> dict[str, Any]: ...

    def get_why_fact(self, owner_id: str, fact_id: str) -> dict[str, Any]: ...

    def resolve_fact(
        self,
        owner_id: str,
        fact_id: str,
        *,
        action: FactResolutionAction,
        new_text: str | None = None,
        valid_from: str | None = None,
        evidence_record_id: str | None = None,
    ) -> dict[str, Any]: ...

    def forget_source(self, owner_id: str, record_ids: list[str]) -> dict[str, Any]: ...

    def forget_fact(self, owner_id: str, fact_id: str) -> dict[str, Any]: ...

    def export_markdown_zip(self, owner_id: str) -> bytes: ...
