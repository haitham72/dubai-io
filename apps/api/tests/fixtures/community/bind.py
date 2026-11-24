"""Mint a real community app session for each lab cookie. Tests only."""

from app.actions import COOKIE
from app.identity import IdentityConfig, IdentityService, IdentityStore, JWTVerifier
from tests.fixtures.contest_shared.identity_fixtures import (
    TEST_AUDIENCE,
    TEST_HS256_SECRET,
    TEST_ISSUER,
    default_claims,
    sign_hs256_jwt,
)


def install(app, action_store, tmp_path):
    verifier = JWTVerifier(issuer=TEST_ISSUER, audience=TEST_AUDIENCE, hs256_secret=TEST_HS256_SECRET)
    service = IdentityService(
        IdentityStore(tmp_path / "identity.sqlite3"),
        verifier,
        config=IdentityConfig(jwt_issuer=TEST_ISSUER, jwt_audience=TEST_AUDIENCE, jwt_hs256_secret=TEST_HS256_SECRET),
        legacy_session_resolver=action_store.owner,
    )
    app.state.identity_service = service
    cache: dict[str, str] = {}

    @app.middleware("http")
    async def bind_lab_cookie(request, call_next):
        lab = request.cookies.get(COOKIE)
        if lab and not request.headers.get("x-app-session") and "cs_session_community" not in request.cookies:
            token = cache.get(lab)
            if token is None:
                owner = action_store.owner(lab)
                jwt_token = sign_hs256_jwt(default_claims(sub=f"community-{owner}"))
                principal = service.authenticate_jwt(jwt_token)
                principal = service.set_age_band(principal, age_band="adult_18_plus")
                opened = service.create_app_session(principal, app_id="community")
                token = opened.session_token
                cache[lab] = token
            request.state.community_session_token = token
        return await call_next(request)

    return service
