"""Host checks so a stored credential cannot be turned into a request to a private network."""
from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

from .types import PermanentFailure


def public_https_origin(url: str) -> str:
    parts = urlsplit((url or "").strip())
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.query
        or parts.fragment
        or parts.port not in (None, 443)
    ):
        raise PermanentFailure("The site must be an https host with no user, port, query, or fragment")
    host = parts.hostname
    if host in {"localhost", "127.0.0.1"} or host.endswith(".local") or host.endswith(".internal"):
        raise PermanentFailure("The site must be a public https host")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip and (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast):
        raise PermanentFailure("The site must be a public https host")
    return f"https://{host}"


def https_url_on(url: str, host: str) -> str:
    parts = urlsplit(url or "")
    if parts.scheme != "https" or parts.hostname != host:
        raise PermanentFailure("The stored sync link is not on the expected provider host")
    return url
