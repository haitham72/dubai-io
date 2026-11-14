"""Per-user credential encryption. Same Fernet approach as Google OAuth grants."""
from __future__ import annotations

import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from ..oauth import local_key


def cipher_for(key: bytes | str | None = None):
    if isinstance(key, str) and key:
        raw = key.encode()
    elif isinstance(key, bytes) and key:
        raw = key
    else:
        from ..config import settings

        raw = local_key(settings.data_dir / "connector.key", settings.connector_token_key or settings.oauth_token_key)
    return Fernet(raw)


def encrypt_json(cipher: Fernet, payload: dict[str, Any]) -> bytes:
    return cipher.encrypt(json.dumps(payload, sort_keys=True).encode())


def decrypt_json(cipher: Fernet, blob: bytes) -> dict[str, Any] | None:
    try:
        data = json.loads(cipher.decrypt(bytes(blob)))
    except (InvalidToken, ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None
