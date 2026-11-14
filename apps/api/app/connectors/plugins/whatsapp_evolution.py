"""Optional WhatsApp link through Evolution API's Baileys provider.

Unofficial. Default off. One Evolution instance per Dubai-io user. Media bytes
are not downloaded. Outbound send is a separate, approval-gated call.
"""
from __future__ import annotations

import hashlib
import json
import re

import httpx

from ..base import BaseConnector
from ..stamp import preserve_timestamp
from ..types import AuthFailed, DisabledConnector, Page, PermanentFailure, RateLimited, RawItem, TransientFailure
from . import register

RISKS = (
    "Unofficial integration. This is not WhatsApp's Cloud API or Business API.",
    "Baileys emulates a linked device. WhatsApp can ban the number or log the device out.",
    "Sessions break when WhatsApp changes its private protocol. Treat the link as unreliable.",
    "History sync is best-effort and often incomplete. An empty result is not proof the chat is empty.",
    "Run Evolution on infrastructure you control. The instance holds the linked-device session.",
    "Outgoing messages stay off until you approve the exact recipient and text.",
)

NOTICE = (
    "Unofficial Baileys session. History may be incomplete, and the WhatsApp account can be banned. "
    "Media bytes were not downloaded."
)

MEDIA_KEYS = {
    "imageMessage": "image",
    "videoMessage": "video",
    "audioMessage": "audio",
    "documentMessage": "document",
    "stickerMessage": "sticker",
}


def instance_name(owner: str) -> str:
    return "dbi" + hashlib.sha256(owner.encode()).hexdigest()[:20]


def _instance(credentials: dict) -> str:
    name = str(credentials.get("instance_name") or "")
    if not re.fullmatch(r"dbi[a-f0-9]{20}", name):
        raise AuthFailed("Link WhatsApp before syncing")
    return name


def evolution_settings():
    from ...config import settings

    return settings


def _enabled():
    settings = evolution_settings()
    if not settings.whatsapp_evolution_enabled:
        raise DisabledConnector(
            "WhatsApp linking is off. Set WHATSAPP_EVOLUTION_ENABLED only if you accept the unofficial Baileys risks."
        )
    base = (settings.evolution_api_base_url or "").strip().rstrip("/")
    key = (settings.evolution_api_key or "").strip()
    if not base or not key:
        raise DisabledConnector("Set EVOLUTION_API_BASE_URL and EVOLUTION_API_KEY on the server you control.")
    from urllib.parse import urlsplit

    parts = urlsplit(base)
    local = parts.hostname in {"localhost", "127.0.0.1"}
    if parts.username or parts.password or parts.query or parts.fragment:
        raise PermanentFailure("Evolution API base URL must not include a user or a query")
    if parts.scheme == "https" or (parts.scheme == "http" and local):
        return base, key
    raise DisabledConnector("EVOLUTION_API_BASE_URL must be https, or http on localhost")


def _request(client, method: str, url: str, *, key: str, json_body=None, ok=(200, 201)):
    headers = {"apikey": key, "Accept": "application/json"}
    try:
        response = client.request(method, url, headers=headers, json=json_body)
    except httpx.HTTPError as exc:
        raise TransientFailure("The provider could not be reached") from exc
    if response.status_code in (401, 403):
        raise AuthFailed("Evolution API rejected the server key")
    if response.status_code == 429:
        raise RateLimited()
    if response.status_code >= 500:
        raise TransientFailure()
    if response.status_code not in ok:
        raise PermanentFailure(f"Evolution API returned HTTP {response.status_code}")
    if not response.content:
        return {}
    try:
        return response.json()
    except ValueError as exc:
        raise PermanentFailure("Evolution API returned a response that was not JSON") from exc


def extract_messages(payload) -> list:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    messages = payload.get("messages")
    if isinstance(messages, dict) and isinstance(messages.get("records"), list):
        return [item for item in messages["records"] if isinstance(item, dict)]
    if isinstance(messages, list):
        return [item for item in messages if isinstance(item, dict)]
    data = payload.get("data")
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        nested = data.get("messages")
        if isinstance(nested, list):
            return [item for item in nested if isinstance(item, dict)]
        if "key" in data or "message" in data:
            return [data]
    if "key" in payload and "message" in payload:
        return [payload]
    return []


def normalize_evolution_message(record: dict) -> RawItem | None:
    key = record.get("key") or {}
    source_id = key.get("id")
    if not source_id:
        return None
    jid = str(key.get("remoteJid") or "")
    message = record.get("message") or {}
    text = ""
    if isinstance(message.get("conversation"), str):
        text = message["conversation"]
    extended = message.get("extendedTextMessage") or {}
    if not text and isinstance(extended.get("text"), str):
        text = extended["text"]
    media = []
    for field, kind in MEDIA_KEYS.items():
        block = message.get(field)
        if isinstance(block, dict):
            media.append(
                {
                    "kind": kind,
                    "mimetype": block.get("mimetype") or "",
                    "file_length": "" if block.get("fileLength") is None else str(block.get("fileLength")),
                    "file_name": block.get("fileName") or "",
                    "caption": block.get("caption") or "",
                }
            )
            if not text and block.get("caption"):
                text = str(block["caption"])
    kind = "group_message" if jid.endswith("@g.us") else "message"
    timestamp = record.get("messageTimestamp")
    return RawItem(
        source_id=str(source_id),
        source_timestamp=preserve_timestamp(timestamp) if not isinstance(timestamp, dict) else json.dumps(timestamp, sort_keys=True, separators=(",", ":")),
        title=(record.get("pushName") or text or jid)[:120],
        text=text,
        kind=kind,
        metadata={
            "remote_jid": jid,
            "from_me": bool(key.get("fromMe")),
            "push_name": record.get("pushName") or "",
            "media": media,
            "group": jid if jid.endswith("@g.us") else "",
        },
    )


def _qr_fields(payload: dict) -> dict:
    nested = payload.get("qrcode") if isinstance(payload.get("qrcode"), dict) else {}
    base64 = payload.get("base64") or nested.get("base64") or ""
    code = payload.get("code") or nested.get("code") or payload.get("pairingCode") or ""
    return {"base64": base64 or None, "code": code or None}


def _state(payload: dict) -> str:
    if isinstance(payload.get("instance"), dict) and payload["instance"].get("state"):
        return str(payload["instance"]["state"])
    if payload.get("state"):
        return str(payload["state"])
    return "close"


class EvolutionWhatsAppConnector(BaseConnector):
    def prepare(self, client, owner: str, credentials: dict):
        base, key = _enabled()
        name = instance_name(owner)
        try:
            created = client.post(
            f"{base}/instance/create",
            headers={"apikey": key, "Accept": "application/json"},
            json={
                "instanceName": name,
                "integration": "WHATSAPP-BAILEYS",
                "qrcode": True,
                "rejectCall": True,
                "groupsIgnore": False,
                "syncFullHistory": True,
            },
        )
        except httpx.HTTPError as exc:
            raise TransientFailure("The provider could not be reached") from exc
        if created.status_code in (401, 403):
            raise AuthFailed("Evolution API rejected the server key")
        if created.status_code not in (200, 201, 409):
            if created.status_code >= 500:
                raise TransientFailure()
            raise PermanentFailure(f"Evolution API returned HTTP {created.status_code}")
        qr_body = _request(client, "GET", f"{base}/instance/connect/{name}", key=key)
        state = _state(_request(client, "GET", f"{base}/instance/connectionState/{name}", key=key))
        qr = _qr_fields(qr_body if isinstance(qr_body, dict) else {})
        public = {
            "status": "connected" if state == "open" else "pending",
            "account_label": None,
            "qr_base64": qr["base64"],
            "pairing_code": qr["code"],
            "risks": list(RISKS),
            "account_risk": self.spec.account_risk,
        }
        return {"instance_name": name}, public

    def fetch_page(self, client, credentials, cursor) -> Page:
        base, key = _enabled()
        name = _instance(credentials)
        state = _state(_request(client, "GET", f"{base}/instance/connectionState/{name}", key=key))
        if state != "open":
            raise AuthFailed("WhatsApp is not linked. Scan the QR code again.")
        body = {"limit": 50}
        since = str(cursor.get("since")) if cursor and cursor.get("since") else ""
        if since:
            body["where"] = {"messageTimestamp": {"gt": since}}
        payload = _request(client, "POST", f"{base}/chat/findMessages/{name}", key=key, json_body=body)
        items = []
        newest = since
        for record in extract_messages(payload):
            item = normalize_evolution_message(record)
            if not item:
                continue
            items.append(item)
            if item.source_timestamp.isdigit() and (not str(newest).isdigit() or int(item.source_timestamp) > int(newest)):
                newest = item.source_timestamp
        groups = []
        try:
            group_payload = _request(client, "GET", f"{base}/group/fetchAllGroups/{name}?getParticipants=false", key=key)
        except PermanentFailure as exc:
            if "404" not in str(exc):
                raise
            group_payload = []
        entries = group_payload if isinstance(group_payload, list) else group_payload.get("groups") or []
        for group in entries:
            if not isinstance(group, dict) or not group.get("id"):
                continue
            subject = group.get("subject") or str(group["id"])
            groups.append(
                RawItem(
                    source_id=str(group["id"]),
                    source_timestamp="",
                    title=subject,
                    text=subject,
                    kind="group",
                    metadata={"group": str(group["id"])},
                )
            )
        nxt = {"since": newest} if newest else (cursor or None)
        return Page(items=items + groups, next_cursor=nxt, partial=True, notice=NOTICE)

    def parse_webhook(self, payload: dict):
        _enabled()
        event = str(payload.get("event") or "")
        if event and "message" not in event.lower():
            return []
        items = []
        for record in extract_messages(payload):
            item = normalize_evolution_message(record)
            if item:
                items.append(item)
        return items

    def send(self, client, credentials, action: str, payload: dict) -> dict:
        base, key = _enabled()
        if action != "send_message":
            raise PermanentFailure("This connector does not send")
        name = _instance(credentials)
        data = _request(
            client,
            "POST",
            f"{base}/message/sendText/{name}",
            key=key,
            json_body={"number": payload["to"], "text": payload["text"]},
        )
        source_id = ""
        if isinstance(data, dict):
            source_id = str(((data.get("key") or {}).get("id")) or data.get("id") or "")
        return {
            "provider_accepted": True,
            "source_id": source_id,
            "notice": "Evolution accepted the send request. That is not a delivery receipt, and the integration is unofficial.",
        }

    def reconnect(self, client, credentials) -> dict:
        base, key = _enabled()
        name = _instance(credentials)
        state = _state(_request(client, "GET", f"{base}/instance/connectionState/{name}", key=key))
        qr = {"base64": None, "code": None}
        if state != "open":
            qr = _qr_fields(_request(client, "GET", f"{base}/instance/connect/{name}", key=key))
        return {"state": state, "qr_base64": qr["base64"], "pairing_code": qr["code"]}

    def revoke_remote(self, client, credentials) -> str:
        base, key = _enabled()
        try:
            name = _instance(credentials)
        except AuthFailed:
            return "local_only"
        last = "logout_requested"
        for path in (f"/instance/logout/{name}", f"/instance/delete/{name}"):
            try:
                _request(client, "DELETE", base + path, key=key, ok=(200, 201, 204))
            except PermanentFailure as exc:
                if "404" in str(exc):
                    continue
                raise
        return last


@register("whatsapp")
def build(spec):
    return EvolutionWhatsAppConnector(spec)
