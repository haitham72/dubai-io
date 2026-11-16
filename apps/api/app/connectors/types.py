"""Shared connector types. The universal record is stable across sources."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


CRITERIA = (
    "user_value",
    "api_access",
    "completeness",
    "reliability",
    "privacy_legal",
    "maintainability",
)

INTEGRATIONS = ("official_api", "unofficial", "export_import", "unavailable")
MODES = ("live", "export", "unavailable")
ATTACHMENTS = ("none", "metadata", "content")
REALTIME = ("none", "polling", "webhook", "webhook_or_polling")
CONTENT = ("none", "metadata", "full")


class ConnectorError(Exception):
    def __init__(self, message: str, *, code: str = "error"):
        super().__init__(message)
        self.code = code


class AuthFailed(ConnectorError):
    def __init__(self, message: str = "The provider rejected these credentials"):
        super().__init__(message, code="auth_required")


class RateLimited(ConnectorError):
    def __init__(self, retry_after: float | None = None):
        super().__init__("The provider rate limit was reached", code="rate_limited")
        self.retry_after = retry_after


class TransientFailure(ConnectorError):
    def __init__(self, message: str = "The provider did not complete the request"):
        super().__init__(message, code="transient")


class PermanentFailure(ConnectorError):
    def __init__(self, message: str):
        super().__init__(message, code="permanent")


class UnavailableConnector(ConnectorError):
    def __init__(self, message: str):
        super().__init__(message, code="unavailable")


class DisabledConnector(ConnectorError):
    def __init__(self, message: str):
        super().__init__(message, code="disabled")


class PermissionDenied(ConnectorError):
    def __init__(self, message: str = "Outbound actions stay blocked until you approve this exact message"):
        super().__init__(message, code="denied")


class HttpStatus(ConnectorError):
    def __init__(self, status: int):
        super().__init__(f"The provider returned HTTP {status}", code="http")
        self.status = status


class CursorExpired(ConnectorError):
    def __init__(self):
        super().__init__("The sync cursor expired", code="cursor_expired")


@dataclass
class RawItem:
    source_id: str
    source_timestamp: str
    text: str
    kind: str
    title: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Page:
    items: list[RawItem]
    next_cursor: dict[str, Any] | None
    partial: bool = False
    notice: str = ""


class ConnectorSpec(BaseModel):
    """Honest capability declaration. One spec per source, no shared assumptions."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    category: str
    integration: str
    mode: str
    available: bool
    read_records: bool
    read_history: bool
    attachment_access: str
    realtime: str
    outbound: bool
    content_access: str
    auth_method: str
    rate_limits: str
    limitations: str
    reliability: str
    summary: str
    account_risk: str = ""
    feature_flag: str | None = None
    scores: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def honest(self):
        if self.integration not in INTEGRATIONS:
            raise ValueError(f"{self.id}: integration")
        if self.mode not in MODES:
            raise ValueError(f"{self.id}: mode")
        if self.attachment_access not in ATTACHMENTS or self.realtime not in REALTIME or self.content_access not in CONTENT:
            raise ValueError(f"{self.id}: capability enum")
        if set(self.scores) != set(CRITERIA) or any(not isinstance(v, int) or not 1 <= v <= 5 for v in self.scores.values()):
            raise ValueError(f"{self.id}: scores must be the six criteria, each 1–5")
        if self.mode == "unavailable":
            if self.available or self.outbound or self.read_records or self.read_history or self.integration != "unavailable":
                raise ValueError(f"{self.id}: unavailable connectors do not claim access")
        if self.mode == "export":
            if self.integration != "export_import" or not self.available or self.outbound or self.realtime != "none":
                raise ValueError(f"{self.id}: export connectors only read a file the user supplies")
        if self.mode == "live" and self.integration == "official_api" and not self.available:
            raise ValueError(f"{self.id}: an official live connector must be implemented")
        if self.mode == "live" and not self.available and not self.feature_flag:
            raise ValueError(f"{self.id}: a disabled live connector needs a feature flag")
        if self.integration == "unofficial" and not self.account_risk:
            raise ValueError(f"{self.id}: unofficial connectors must state the account risk")
        if self.integration == "official_api" and self.account_risk:
            raise ValueError(f"{self.id}: official connectors do not carry an unofficial ban warning")
        return self

    @property
    def priority(self) -> int:
        return sum(self.scores[name] for name in CRITERIA)
