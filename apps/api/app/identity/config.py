"""Environment-driven configuration for CS-B1 identity core."""
from __future__ import annotations

from dataclasses import dataclass
import os


def _bounded_int(name: str, default: int, *, min_value: int, max_value: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    return max(min_value, min(value, max_value))


@dataclass(frozen=True)
class IdentityConfig:
    jwt_issuer: str = ""
    jwt_audience: str = "authenticated"
    jwt_jwks_url: str = ""
    jwt_hs256_secret: str = ""
    clock_skew_seconds: int = 30
    session_ttl_seconds: int = 86400
    max_session_ttl_seconds: int = 604800
    ws_ticket_ttl_seconds: int = 60
    token_key: str = ""
    jwks_ttl_seconds: int = 300
    jwks_refresh_cooldown_seconds: int = 10

    @classmethod
    def from_env(cls) -> "IdentityConfig":
        """Load identity configuration strictly from environment variables."""
        clock_skew = _bounded_int("IDENTITY_CLOCK_SKEW_SECONDS", 30, min_value=0, max_value=120)
        session_ttl = _bounded_int("IDENTITY_SESSION_TTL_SECONDS", 86400, min_value=60, max_value=604800)
        ws_ticket_ttl = _bounded_int("IDENTITY_WS_TICKET_TTL_SECONDS", 60, min_value=5, max_value=300)
        jwks_ttl = _bounded_int("IDENTITY_JWKS_TTL_SECONDS", 300, min_value=10, max_value=3600)
        jwks_cooldown = _bounded_int("IDENTITY_JWKS_REFRESH_COOLDOWN_SECONDS", 10, min_value=1, max_value=300)
        return cls(
            jwt_issuer=os.getenv("IDENTITY_JWT_ISSUER", "").strip(),
            jwt_audience=os.getenv("IDENTITY_JWT_AUDIENCE", "authenticated").strip() or "authenticated",
            jwt_jwks_url=os.getenv("IDENTITY_JWT_JWKS_URL", "").strip(),
            jwt_hs256_secret=os.getenv("IDENTITY_JWT_HS256_SECRET", ""),
            clock_skew_seconds=clock_skew,
            session_ttl_seconds=session_ttl,
            max_session_ttl_seconds=604800,
            ws_ticket_ttl_seconds=ws_ticket_ttl,
            token_key=os.getenv("IDENTITY_TOKEN_KEY", "").strip(),
            jwks_ttl_seconds=jwks_ttl,
            jwks_refresh_cooldown_seconds=jwks_cooldown,
        )


def get_identity_config() -> IdentityConfig:
    """Return the current environment-backed IdentityConfig."""
    return IdentityConfig.from_env()
