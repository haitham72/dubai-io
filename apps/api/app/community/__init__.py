"""Community social core (CM-B2/B3/B4). Adults-only, cookie-session owner."""
from .routes import router  # noqa: F401
from .store import setup  # noqa: F401

__all__ = ["router", "setup"]
