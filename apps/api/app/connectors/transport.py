"""HTTP calls that never echo tokens, URLs, or response bodies in errors."""
from __future__ import annotations

import httpx

from .types import AuthFailed, CursorExpired, HttpStatus, RateLimited, TransientFailure, PermanentFailure


def call(client, method: str, url: str, *, headers=None, params=None, json_body=None, data=None, ok=(200,)):
    try:
        response = client.request(method, url, headers=headers, params=params, json=json_body, data=data)
    except httpx.HTTPError as exc:
        raise TransientFailure("The provider could not be reached") from exc
    status = response.status_code
    if status in (401, 403):
        raise AuthFailed()
    if status == 429:
        retry = response.headers.get("Retry-After")
        seconds = float(retry) if retry and retry.isdigit() else None
        raise RateLimited(seconds)
    if status == 410:
        raise CursorExpired()
    if status in (408, 502, 503, 504) or status >= 500:
        raise TransientFailure()
    if status == 404:
        raise HttpStatus(404)
    if status not in ok:
        raise PermanentFailure(f"The provider returned HTTP {status}")
    if status == 204 or not response.content:
        return {}
    try:
        body = response.json()
    except ValueError as exc:
        raise PermanentFailure("The provider returned a response that was not JSON") from exc
    return body


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json", "User-Agent": "dubai-io-connectors/1"}


def require_credentials(credentials: dict, *keys: str) -> None:
    if any(not credentials.get(key) for key in keys):
        raise AuthFailed("This connection is missing a required credential")
