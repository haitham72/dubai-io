"""Community owner resolution. Identity is the only source of a user id."""

from fastapi import HTTPException, Request

from app.identity.deps import get_identity_service, reject_spoofed_identity_headers
from app.identity.models import IdentityError

from ..actions import engine


def resolve(request: Request):
    """Return the action store and the verified community user id.

    Spoofed identity headers are rejected. An anonymous lab cookie is not an
    owner. A minor-protected account fails closed (adults only, D11).
    """
    reject_spoofed_identity_headers(request)
    store = engine().store
    service = get_identity_service(request)
    token = (request.headers.get("x-app-session") or "").strip() or (request.cookies.get("cs_session_community") or "").strip()
    if not token:
        token = (getattr(request.state, "community_session_token", "") or "").strip()
    if not token:
        raise HTTPException(401, detail={"code": "missing_app_session", "message": "Verified community session is required"})
    try:
        principal = service.authenticate_session(token, expected_app="community")
    except IdentityError as exc:
        raise HTTPException(exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc
    if principal.is_minor_protected:
        raise HTTPException(403, detail={"code": "adults_only", "message": "Community is adults only (18+)."})
    request.state.community_principal = principal
    return store, principal.user_id
