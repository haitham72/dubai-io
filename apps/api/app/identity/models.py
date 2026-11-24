"""Canonical identity models, capability allowlists, and domain errors."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

AppId = Literal["quest", "community", "messenger"]
AgeBand = Literal["under_13", "teen_13_17", "adult_18_plus", "unknown"]
AuthMode = Literal["verified_jwt", "verified_app_session", "verified_ws_ticket"]

VALID_APP_IDS: frozenset[str] = frozenset({"quest", "community", "messenger"})
VALID_AGE_BANDS: frozenset[str] = frozenset({"under_13", "teen_13_17", "adult_18_plus", "unknown"})
DECLARED_AGE_BANDS: frozenset[str] = frozenset({"under_13", "teen_13_17", "adult_18_plus"})

APP_CAPABILITIES: dict[AppId, frozenset[str]] = {
    "quest": frozenset({
        "quest:chat",
        "quest:actions",
        "quest:tasks",
        "memory:read:owner",
        "memory:write:owner",
        "memory:forget:owner",
        "memory:device_token",
    }),
    "community": frozenset({
        "community:read",
        "community:write",
        "community:moderate",
        "memory:read:interests",
        "memory:write:community",
        "memory:forget:community",
    }),
    "messenger": frozenset({
        "messenger:chat",
        "messenger:ws",
        "messenger:actions",
        "memory:read:chat",
        "memory:write:chat",
        "memory:forget:chat",
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
    nonce: Optional[str] = None


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
        """Fail-closed D11 protection: only explicitly self-declared adult_18_plus unlocks memory writes/cross-app personalisation."""
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
    display_name: str = ""
    email: Optional[str] = None
    device_label: Optional[str] = None


@dataclass(frozen=True)
class WsTicketOut:
    ticket: str
    expires_at: str
    session_id: str
    app_id: AppId


class IdentityError(Exception):
    """Domain error mapped cleanly to HTTP status codes at transport boundaries."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
