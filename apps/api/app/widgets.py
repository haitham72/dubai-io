"""Separate widget origin (CLAUDE.md rule 10, ARCHITECTURE.md §6).

Merchant mini-apps are served from their own port, so they never share the app's
origin. The app frames them with sandbox="allow-scripts" (opaque origin); this CSP
blocks every network call, and the only channel back is the allowlisted postMessage bridge.
"""
import threading

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from .config import settings

CSP = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; form-action 'none'; base-uri 'none'"

app = FastAPI(title="Dubai-io widgets", docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def lock_down(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = CSP
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


app.mount("/miniapps", StaticFiles(directory=settings.web_dir / "miniapps"), name="miniapps")


def serve_in_background(host: str, port: int):
    """Run the widget origin beside the main app in the same process (local/LAN demo)."""
    import uvicorn
    server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_level="warning"))
    threading.Thread(target=server.run, name="widget-origin", daemon=True).start()
    return server
