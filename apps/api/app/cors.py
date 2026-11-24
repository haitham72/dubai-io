"""CORS for the Dubai-io website (Expo web on :8081). Explicit allowlist, never a wildcard."""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

DEFAULT_WEB_ORIGINS = ("http://localhost:8081", "http://127.0.0.1:8081")
ALLOWED_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
ALLOWED_HEADERS = ["Content-Type", "Authorization", "X-App-Session", "X-App-Id"]


def web_origins() -> list[str]:
    """Defaults plus PUBLIC_WEB_ORIGINS (comma list). A literal `*` is dropped: no wildcard."""
    out = list(DEFAULT_WEB_ORIGINS)
    for raw in os.environ.get("PUBLIC_WEB_ORIGINS", "").split(","):
        o = raw.strip().rstrip("/")
        if o and o != "*" and o not in out:
            out.append(o)
    return out


def install_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=web_origins(),
        allow_credentials=False,
        allow_methods=ALLOWED_METHODS,
        allow_headers=ALLOWED_HEADERS,
    )
