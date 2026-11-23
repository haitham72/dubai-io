"""Canonical cross-app identity package for Quest, Community, and Messenger."""
from __future__ import annotations

from .config import IdentityConfig, get_identity_config
from .deps import (
    get_identity_service,
    reject_spoofed_identity_headers,
    require_app_principal,
    require_verified_jwt,
    require_ws_principal,
)
from .jwt import JWTVerificationError, JWTVerifier
from .memory_tokens import MemoryTokenService
from .models import (
    APP_CAPABILITIES,
    AgeBand,
    AppId,
    AppSessionOut,
    AuthMode,
    IdentityError,
    VerifiedClaims,
    VerifiedPrincipal,
    WsTicketOut,
)
from .router import create_identity_router
from .service import IdentityService
from .store import IdentityStore

__all__ = [
    "APP_CAPABILITIES",
    "AgeBand",
    "AppId",
    "AppSessionOut",
    "AuthMode",
    "IdentityConfig",
    "IdentityError",
    "IdentityService",
    "IdentityStore",
    "JWTVerificationError",
    "JWTVerifier",
    "MemoryTokenService",
    "VerifiedClaims",
    "VerifiedPrincipal",
    "WsTicketOut",
    "create_identity_router",
    "get_identity_config",
    "get_identity_service",
    "reject_spoofed_identity_headers",
    "require_app_principal",
    "require_verified_jwt",
    "require_ws_principal",
]
