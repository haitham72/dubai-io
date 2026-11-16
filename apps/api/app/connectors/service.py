"""Sync, health, revocation, deletion, and the default-deny outbound gate."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import httpx

from .catalog import catalog_by_id
from .registry import build_implementations
from .retry import MAX_ATTEMPTS, add_seconds, retry_delay_seconds
from .store import ConnectorStore, payload_hash
from .types import (
    AuthFailed,
    ConnectorError,
    ConnectorSpec,
    DisabledConnector,
    Page,
    PermanentFailure,
    PermissionDenied,
    RateLimited,
    TransientFailure,
    UnavailableConnector,
)

WHATSAPP_FLAG = "WHATSAPP_EVOLUTION_ENABLED"
GRANT_TTL_SECONDS = 600
OUTBOUND_FIELDS = {
    "whatsapp": frozenset({"to", "text"}),
    "telegram": frozenset({"chat_id", "text"}),
}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _secret_hash(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def evolution_ready() -> bool:
    from ..config import settings

    return bool(
        settings.whatsapp_evolution_enabled
        and (settings.evolution_api_base_url or "").strip()
        and (settings.evolution_api_key or "").strip()
    )


class ConnectorService:
    def __init__(self, store: ConnectorStore, *, clock=None, transport=None, specs=None, impls=None):
        self.store = store
        self.clock = clock or utcnow
        self.transport = transport
        self.specs: dict[str, ConnectorSpec] = specs or catalog_by_id()
        self.impls = build_implementations(self.specs) if impls is None else impls

    def is_available(self, spec: ConnectorSpec) -> bool:
        if spec.mode == "unavailable":
            return False
        if spec.feature_flag == WHATSAPP_FLAG:
            return evolution_ready()
        return spec.available

    def blocker(self, spec: ConnectorSpec) -> str | None:
        if spec.mode == "unavailable":
            return spec.summary
        if spec.feature_flag == WHATSAPP_FLAG and not self.is_available(spec):
            return (
                "WhatsApp linking is off. It uses the unofficial Evolution API (Baileys) and stays disabled "
                "until WHATSAPP_EVOLUTION_ENABLED, EVOLUTION_API_BASE_URL and EVOLUTION_API_KEY are set on a server you control."
            )
        return None

    def describe(self, connector_id: str, owner: str | None = None) -> dict:
        spec = self._spec(connector_id)
        data = spec.model_dump()
        data["priority"] = spec.priority
        data["available"] = self.is_available(spec)
        data["outbound_enabled"] = bool(spec.outbound and data["available"])
        data["blocker"] = self.blocker(spec)
        if owner is not None:
            data["connection"] = self.store.public_connection(owner, connector_id)
        return data

    def list_connectors(self, owner: str) -> list[dict]:
        rows = [self.describe(spec.id, owner) for spec in self.specs.values()]
        rows.sort(key=lambda row: (-row["priority"], row["id"]))
        return rows

    def connect(self, owner: str, connector_id: str, credentials: dict) -> dict:
        spec = self._spec(connector_id)
        self._require_runnable(spec)
        if spec.mode == "export":
            raise PermanentFailure("This connector accepts a file you import. It does not take a remote login.")
        impl = self._impl(connector_id)
        with self.open_client(impl) as client:
            stored, public = impl.prepare(client, owner, credentials)
        now = self.clock()
        self.store.save_credentials(owner, connector_id, stored, now)
        extra = {}
        fields = {
            "status": public.get("status") or "connected",
            "health": "unknown",
            "account_label": public.get("account_label"),
            "connected_at": now,
            "updated_at": now,
            "attempt": 0,
            "last_error": None,
            "next_retry_at": None,
            "notice": public.get("account_risk") or None,
        }
        if "webhook" in spec.realtime:
            hook_id = secrets.token_urlsafe(32)
            secret = secrets.token_urlsafe(32)
            fields["hook_id"] = hook_id
            fields["secret_hash"] = _secret_hash(secret)
            extra["webhook_path"] = f"/api/connectors/hooks/{connector_id}/{hook_id}"
            extra["webhook_secret"] = secret
        self.store.upsert_connection(owner, connector_id, **fields)
        body = {
            "connector_id": connector_id,
            "status": fields["status"],
            "account_label": fields["account_label"],
            "integration": spec.integration,
            "unofficial": spec.integration == "unofficial",
            "account_risk": spec.account_risk or None,
        }
        for key in ("qr_base64", "pairing_code", "risks"):
            if public.get(key):
                body[key] = public[key]
        body.update(extra)
        return body

    def sync(self, owner: str, connector_id: str, *, force: bool = False) -> dict:
        spec = self._spec(connector_id)
        self._require_runnable(spec)
        if spec.mode == "export":
            raise PermanentFailure("Import a file you exported. This connector does not call a remote API.")
        conn = self._connected(owner, connector_id)
        now = self.clock()
        if not force and conn.get("next_retry_at") and conn["next_retry_at"] > now:
            return self._result(spec, conn, status="retry_wait", imported=0, duplicate=0, updated=0, skipped=0)
        if not force and (conn.get("attempt") or 0) >= MAX_ATTEMPTS and conn.get("health") in {"error", "rate_limited"}:
            raise PermanentFailure("Sync stopped after repeated failures. Call sync again with force after the cause is fixed.")
        creds = self.store.credentials(owner, connector_id)
        if not creds:
            raise AuthFailed("Connect this source first")
        impl = self._impl(connector_id)
        attempt = int(conn.get("attempt") or 0)
        try:
            with self.open_client(impl) as client:
                page = impl.fetch_page(client, creds, conn.get("cursor"))
        except AuthFailed as exc:
            self._fail(owner, connector_id, conn, now, attempt + 1, "auth_required", str(exc), delay=None)
            raise
        except RateLimited as exc:
            return self._fail(owner, connector_id, conn, now, attempt + 1, "rate_limited", str(exc), delay=retry_delay_seconds(attempt + 1, retry_after=exc.retry_after))
        except TransientFailure as exc:
            return self._fail(owner, connector_id, conn, now, attempt + 1, "error", str(exc), delay=retry_delay_seconds(attempt + 1))
        except ConnectorError as exc:
            self._fail(owner, connector_id, conn, now, attempt + 1, "error", str(exc), delay=None)
            raise
        if not isinstance(page, Page):
            raise PermanentFailure("The connector returned an unexpected page")
        counts = self.store.upsert_records(owner, connector_id, page.items, now=now, provenance="provider_confirmed")
        health = "degraded" if spec.integration == "unofficial" or page.partial else "healthy"
        notice = page.notice or (spec.account_risk if spec.integration == "unofficial" else None)
        self.store.upsert_connection(
            owner,
            connector_id,
            status="connected",
            health=health,
            cursor=page.next_cursor,
            last_sync_at=now,
            last_error=None,
            next_retry_at=None,
            attempt=0,
            notice=notice,
            updated_at=now,
        )
        self.store.log_sync(
            owner,
            connector_id,
            started_at=now,
            finished_at=self.clock(),
            status="ok",
            attempt=0,
            imported=counts["imported"],
            duplicate=counts["duplicate"],
        )
        conn = self.store.connection(owner, connector_id)
        result = self._result(spec, conn, status="ok", **counts)
        result["partial"] = page.partial
        result["notice"] = notice
        return result

    def import_file(self, owner: str, connector_id: str, filename: str, content: str) -> dict:
        spec = self._spec(connector_id)
        if spec.mode != "export":
            raise PermanentFailure("This connector does not accept a file import")
        impl = self._impl(connector_id)
        items = impl.parse(content)
        now = self.clock()
        counts = self.store.upsert_records(owner, connector_id, items, now=now, provenance="user_supplied")
        self.store.upsert_connection(
            owner,
            connector_id,
            status="connected",
            health="healthy",
            account_label=(filename or "import")[:200],
            last_sync_at=now,
            last_error=None,
            attempt=0,
            notice="Imported from a file you supplied. Nothing was fetched from the provider.",
            connected_at=now,
            updated_at=now,
        )
        return {"connector_id": connector_id, "provenance": "user_supplied", **counts}

    def ingest_webhook(self, connector_id: str, hook_id: str, secret: str, payload: dict) -> dict:
        spec = self._spec(connector_id)
        self._require_runnable(spec)
        conn = self.store.connection_by_hook(hook_id)
        presented = _secret_hash(secret or "")
        if not conn or conn["connector_id"] != connector_id or not conn.get("secret_hash"):
            raise AuthFailed("Unknown webhook")
        if not hmac.compare_digest(presented, conn["secret_hash"]):
            raise AuthFailed("Unknown webhook")
        impl = self._impl(connector_id)
        items = impl.parse_webhook(payload if isinstance(payload, dict) else {})
        now = self.clock()
        counts = self.store.upsert_records(conn["owner"], connector_id, items, now=now, provenance="provider_confirmed")
        return {"connector_id": connector_id, **counts}

    def disconnect(self, owner: str, connector_id: str) -> dict:
        self._spec(connector_id)
        now = self.clock()
        self.store.delete_credentials(owner, connector_id)
        if self.store.connection(owner, connector_id):
            self.store.upsert_connection(
                owner,
                connector_id,
                status="disconnected",
                health="unknown",
                cursor=None,
                secret_hash=None,
                hook_id=None,
                last_error=None,
                next_retry_at=None,
                attempt=0,
                updated_at=now,
            )
        return {"connector_id": connector_id, "status": "disconnected", "records_kept": True}

    def revoke(self, owner: str, connector_id: str) -> dict:
        spec = self._spec(connector_id)
        remote = "local_only"
        creds = self.store.credentials(owner, connector_id)
        impl = self.impls.get(connector_id)
        if creds and impl and spec.mode == "live" and self.is_available(spec):
            try:
                with self.open_client(impl) as client:
                    remote = impl.revoke_remote(client, creds) or "local_only"
            except ConnectorError:
                remote = "remote_failed"
            except Exception:
                remote = "remote_failed"
        self.store.delete_credentials(owner, connector_id)
        now = self.clock()
        if self.store.connection(owner, connector_id) or creds:
            self.store.upsert_connection(
                owner,
                connector_id,
                status="revoked",
                health="unknown",
                cursor=None,
                secret_hash=None,
                hook_id=None,
                account_label=None,
                last_error=None,
                next_retry_at=None,
                attempt=0,
                notice="Credentials were deleted on this server.",
                updated_at=now,
            )
        return {"connector_id": connector_id, "status": "revoked", "remote": remote, "records_kept": True}

    def delete_user_data(self, owner: str, connector_id: str) -> dict:
        spec = self._spec(connector_id)
        remote = "local_only"
        creds = self.store.credentials(owner, connector_id)
        impl = self.impls.get(connector_id)
        if creds and impl and spec.mode == "live" and self.is_available(spec):
            try:
                with self.open_client(impl) as client:
                    remote = impl.revoke_remote(client, creds) or "local_only"
            except Exception:
                remote = "remote_failed"
        counts = self.store.delete_user_data(owner, connector_id)
        return {"connector_id": connector_id, "deleted": counts, "remote": remote}

    def reconnect(self, owner: str, connector_id: str) -> dict:
        spec = self._spec(connector_id)
        self._require_runnable(spec)
        impl = self._impl(connector_id)
        creds = self.store.credentials(owner, connector_id)
        if not creds:
            raise AuthFailed("Connect this source first")
        with self.open_client(impl) as client:
            outcome = impl.reconnect(client, creds)
        now = self.clock()
        state = outcome.get("state")
        health = "degraded" if state == "open" else "auth_required"
        self.store.upsert_connection(
            owner,
            connector_id,
            status="connected" if state == "open" else "pending",
            health=health,
            notice=spec.account_risk,
            updated_at=now,
        )
        return {
            "connector_id": connector_id,
            "state": state,
            "health": health,
            "qr_base64": outcome.get("qr_base64"),
            "pairing_code": outcome.get("pairing_code"),
            "unofficial": True,
            "account_risk": spec.account_risk,
        }

    def propose_outbound(self, owner: str, connector_id: str, action: str, payload: dict) -> dict:
        spec = self._spec(connector_id)
        if not spec.outbound or not self.is_available(spec):
            raise PermissionDenied("This connector cannot send. Nothing was sent.")
        allowed = OUTBOUND_FIELDS.get(connector_id)
        if action != "send_message" or not allowed or set(payload) != allowed:
            raise PermissionDenied("The approval must list exactly the recipient and the text. Nothing was sent.")
        if any(not isinstance(payload[key], str) or not payload[key].strip() for key in allowed):
            raise PermissionDenied("Recipient and text are required. Nothing was sent.")
        now = self.clock()
        expires = (datetime.fromisoformat(now) + timedelta(seconds=GRANT_TTL_SECONDS)).isoformat(timespec="seconds")
        shares = sorted(allowed)
        grant_id = self.store.create_grant(owner, connector_id, action, payload, shares, now, expires)
        return {
            "grant_id": grant_id,
            "status": "pending",
            "sent": False,
            "connector_id": connector_id,
            "action": action,
            "shares": shares,
            "preview": payload,
            "expires_at": expires,
            "unofficial": spec.integration == "unofficial",
            "account_risk": spec.account_risk or None,
        }

    def decide_outbound(self, owner: str, grant_id: str, approve: bool) -> dict:
        grant = self.store.grant(owner, grant_id)
        if not grant:
            raise PermissionDenied("That approval does not exist")
        now = self.clock()
        if grant["expires_at"] <= now:
            self.store.set_grant(owner, grant_id, "expired", now)
            raise PermissionDenied("This approval expired. Nothing was sent.")
        if grant["status"] != "pending":
            raise PermissionDenied("This approval is no longer pending. Nothing was sent.")
        status = "approved" if approve else "denied"
        if not self.store.set_grant(owner, grant_id, status, now, expected="pending"):
            raise PermissionDenied("This approval is no longer pending. Nothing was sent.")
        return {"grant_id": grant_id, "status": status, "sent": False}

    def execute_outbound(self, owner: str, connector_id: str, grant_id: str, payload: dict) -> dict:
        spec = self._spec(connector_id)
        if not spec.outbound or not self.is_available(spec):
            raise PermissionDenied("This connector cannot send. Nothing was sent.")
        grant = self.store.grant(owner, grant_id)
        if not grant or grant["connector_id"] != connector_id:
            raise PermissionDenied("That approval does not exist. Nothing was sent.")
        now = self.clock()
        if grant["expires_at"] <= now:
            self.store.set_grant(owner, grant_id, "expired", now)
            raise PermissionDenied("This approval expired. Nothing was sent.")
        if grant["status"] != "approved":
            raise PermissionDenied("Outbound actions stay blocked until you approve this exact message. Nothing was sent.")
        if grant["action"] != "send_message" or payload_hash(payload) != grant["payload_hash"]:
            raise PermissionDenied("The message does not match the approval. Nothing was sent.")
        if not self.store.set_grant(owner, grant_id, "consumed", now, expected="approved"):
            raise PermissionDenied("This approval was already used. Nothing further was sent.")
        creds = self.store.credentials(owner, connector_id)
        if not creds:
            raise AuthFailed("Connect this source first")
        impl = self._impl(connector_id)
        with self.open_client(impl) as client:
            provider = impl.send(client, creds, "send_message", payload)
        return {
            "grant_id": grant_id,
            "sent": True,
            "provider_accepted": bool(provider.get("provider_accepted")),
            "source_id": provider.get("source_id"),
            "notice": provider.get("notice") or "The provider accepted the request. That is not a delivery receipt.",
            "provenance": "provider_confirmed",
            "as_of": self.clock(),
        }

    def records(self, owner: str, connector_id: str, limit: int = 50) -> dict:
        self._spec(connector_id)
        return {"items": self.store.records(owner, connector_id, limit)}

    def health(self, owner: str, connector_id: str) -> dict:
        described = self.describe(connector_id, owner)
        connection = described.pop("connection")
        return {
            "connector_id": connector_id,
            "integration": described["integration"],
            "available": described["available"],
            "blocker": described["blocker"],
            **connection,
        }

    @contextmanager
    def open_client(self, impl):
        if impl.transport == "local":
            yield None
            return
        if impl.transport == "imap":
            import imaplib

            yield imaplib
            return
        kwargs = {"timeout": 20.0}
        if self.transport is not None:
            kwargs["transport"] = self.transport
        client = httpx.Client(**kwargs)
        try:
            yield client
        finally:
            client.close()

    def _spec(self, connector_id: str) -> ConnectorSpec:
        spec = self.specs.get(connector_id)
        if not spec:
            raise PermanentFailure("Unknown connector")
        return spec

    def _impl(self, connector_id: str):
        impl = self.impls.get(connector_id)
        if not impl:
            raise UnavailableConnector(self.specs[connector_id].summary)
        return impl

    def _require_runnable(self, spec: ConnectorSpec) -> None:
        if spec.mode == "unavailable":
            raise UnavailableConnector(spec.summary)
        if spec.feature_flag == WHATSAPP_FLAG and not self.is_available(spec):
            raise DisabledConnector(self.blocker(spec) or "This connector is disabled")

    def _connected(self, owner: str, connector_id: str) -> dict:
        conn = self.store.connection(owner, connector_id)
        if not conn or conn["status"] in {"disconnected", "revoked"}:
            raise AuthFailed("Connect this source first")
        return conn

    def _fail(self, owner, connector_id, conn, now, attempt, health, error, delay):
        scheduled = None
        status = "failed"
        if delay is not None and attempt < MAX_ATTEMPTS:
            scheduled = add_seconds(now, delay)
            status = "retry"
        self.store.upsert_connection(
            owner,
            connector_id,
            health=health,
            attempt=attempt,
            last_error=error,
            next_retry_at=scheduled,
            updated_at=now,
        )
        self.store.log_sync(
            owner,
            connector_id,
            started_at=now,
            finished_at=self.clock(),
            status=status,
            attempt=attempt,
            error=error,
        )
        fresh = self.store.connection(owner, connector_id)
        if health == "auth_required":
            return None
        return self._result(self.specs[connector_id], fresh, status=status, imported=0, duplicate=0, updated=0, skipped=0)

    def _result(self, spec, conn, *, status, imported, duplicate, updated, skipped) -> dict:
        return {
            "connector_id": spec.id,
            "status": status,
            "health": conn.get("health") if conn else "unknown",
            "imported": imported,
            "duplicate": duplicate,
            "updated": updated,
            "skipped": skipped,
            "attempt": conn.get("attempt") if conn else 0,
            "next_retry_at": conn.get("next_retry_at") if conn else None,
            "last_error": conn.get("last_error") if conn else None,
            "notice": conn.get("notice") if conn else None,
            "integration": spec.integration,
        }
