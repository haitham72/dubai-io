"""Connector interface. Every live module implements these operations.

1. Authentication and authorization (prepare / probe)
2. Initial import and 3. incremental sync (fetch_page with the stored cursor)
4. Webhooks or polling (parse_webhook, and sync is the poll)
5. Normalization into RawItem, which the store writes as a universal record
6. Source id and source timestamp are fields on that record and are not rewritten
7. Deduplication and retry live in the store and the sync service
8. Health is written on the connection row
9. Revoke and disconnect
10. User data deletion is store-wide and calls revoke_remote first
11. Outbound send is unreachable until an approved grant matches the payload
"""
from __future__ import annotations

from .types import PermanentFailure


class BaseConnector:
    transport = "http"

    def __init__(self, spec):
        self.spec = spec

    def prepare(self, client, owner: str, credentials: dict) -> tuple[dict, dict]:
        label = self.probe(client, credentials)
        return credentials, {"status": "connected", "account_label": label or self.spec.name}

    def probe(self, client, credentials: dict) -> str:
        raise PermanentFailure("This connector does not have a login")

    def fetch_page(self, client, credentials: dict, cursor):
        raise PermanentFailure("This connector does not sync from a provider")

    def parse_webhook(self, payload: dict):
        raise PermanentFailure("This connector does not accept webhooks")

    def revoke_remote(self, client, credentials: dict) -> str:
        return "local_only"

    def send(self, client, credentials: dict, action: str, payload: dict) -> dict:
        raise PermanentFailure("This connector does not send")

    def reconnect(self, client, credentials: dict) -> dict:
        raise PermanentFailure("This connector does not keep a device session")


class RestConnector(BaseConnector):
    def __init__(self, spec, *, probe, fetch, revoke=None, webhook=None, send=None):
        super().__init__(spec)
        self._probe = probe
        self._fetch = fetch
        self._revoke = revoke
        self._webhook = webhook
        self._send = send

    def probe(self, client, credentials):
        return self._probe(client, credentials)

    def fetch_page(self, client, credentials, cursor):
        return self._fetch(client, credentials, cursor)

    def revoke_remote(self, client, credentials):
        if self._revoke:
            return self._revoke(client, credentials)
        return "local_only"

    def parse_webhook(self, payload):
        if not self._webhook:
            return super().parse_webhook(payload)
        return self._webhook(payload)

    def send(self, client, credentials, action, payload):
        if not self._send:
            return super().send(client, credentials, action, payload)
        return self._send(client, credentials, action, payload)
