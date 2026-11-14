"""Slack, Telegram Bot API, and Discord bot. Personal-account history is not claimed."""
from __future__ import annotations

import re

from ..base import RestConnector
from ..stamp import preserve_timestamp
from ..transport import bearer, call, require_credentials
from ..types import AuthFailed, Page, PermanentFailure, RateLimited, RawItem
from . import register

_TELEGRAM_TOKEN = re.compile(r"^[0-9]+:[A-Za-z0-9_-]+$")


def slack_probe(client, credentials) -> str:
    data = _slack(client, "GET", "https://slack.com/api/auth.test", credentials)
    return data.get("user") or data.get("team") or "Slack"


def slack_fetch(client, credentials, cursor) -> Page:
    params = {"limit": "3", "types": "public_channel,private_channel,mpim,im"}
    if cursor and cursor.get("list_cursor"):
        params["cursor"] = cursor["list_cursor"]
    listed = _slack(client, "GET", "https://slack.com/api/conversations.list", credentials, params=params)
    items = []
    newest = ""
    for channel in (listed.get("channels") or [])[:3]:
        channel_id = channel.get("id")
        if not channel_id:
            continue
        history = _slack(
            client,
            "GET",
            "https://slack.com/api/conversations.history",
            credentials,
            params={"channel": channel_id, "limit": "15"},
        )
        for message in history.get("messages") or []:
            ts = str(message.get("ts") or "")
            if not ts:
                continue
            if ts > newest:
                newest = ts
            text = message.get("text") or ""
            items.append(
                RawItem(
                    source_id=f"{channel_id}:{ts}",
                    source_timestamp=ts,
                    title=text[:120],
                    text=text,
                    kind="message",
                    metadata={"channel": channel_id, "user": message.get("user") or ""},
                )
            )
    nxt = {"since": newest} if newest else None
    next_cursor = (listed.get("response_metadata") or {}).get("next_cursor")
    if next_cursor:
        nxt = {"list_cursor": next_cursor, "since": newest}
    return Page(items=items, next_cursor=nxt)


def _slack(client, method, url, credentials, params=None):
    require_credentials(credentials, "token")
    data = call(client, method, url, headers=bearer(credentials["token"]), params=params)
    if isinstance(data, dict) and data.get("ok") is False:
        error = str(data.get("error") or "refused")
        if error in {"invalid_auth", "not_authed", "token_revoked", "account_inactive"}:
            raise AuthFailed()
        if error == "ratelimited":
            raise RateLimited()
        raise PermanentFailure(f"Slack refused the request ({error})")
    return data


def telegram_probe(client, credentials) -> str:
    data = call(client, "GET", _telegram(credentials, "getMe"))
    _telegram_ok(data)
    result = data.get("result") or {}
    return result.get("username") or "Telegram bot"


def telegram_fetch(client, credentials, cursor) -> Page:
    params = {"timeout": "0", "allowed_updates": '["message"]'}
    if cursor and cursor.get("offset"):
        params["offset"] = cursor["offset"]
    data = call(client, "GET", _telegram(credentials, "getUpdates"), params=params)
    _telegram_ok(data)
    items = []
    offset = int(cursor["offset"]) if cursor and str(cursor.get("offset") or "").isdigit() else 0
    for update in data.get("result") or []:
        update_id = update.get("update_id")
        if isinstance(update_id, int):
            offset = max(offset, update_id + 1)
        message = update.get("message") or update.get("channel_post") or {}
        item = _telegram_message(message)
        if item:
            items.append(item)
    nxt = {"offset": str(offset)} if offset else None
    return Page(items=items, next_cursor=nxt)


def telegram_webhook(payload: dict) -> list[RawItem]:
    message = payload.get("message") or payload.get("channel_post") or {}
    item = _telegram_message(message)
    return [item] if item else []


def telegram_send(client, credentials, action: str, payload: dict) -> dict:
    if action != "send_message":
        raise PermanentFailure("This connector does not send")
    data = call(
        client,
        "POST",
        _telegram(credentials, "sendMessage"),
        json_body={"chat_id": payload["chat_id"], "text": payload["text"]},
    )
    _telegram_ok(data)
    result = data.get("result") or {}
    return {
        "provider_accepted": True,
        "source_id": str(result.get("message_id") or ""),
        "notice": "Telegram accepted the message. That is not a delivery receipt.",
    }


def telegram_revoke(client, credentials) -> str:
    data = call(client, "POST", _telegram(credentials, "deleteWebhook"), json_body={"drop_pending_updates": False})
    _telegram_ok(data)
    return "webhook_deleted_token_remains_until_botfather"


def _telegram(credentials, method: str) -> str:
    token = str(credentials.get("bot_token") or "")
    if not _TELEGRAM_TOKEN.match(token):
        raise AuthFailed("This connection is missing a required credential")
    return f"https://api.telegram.org/bot{token}/{method}"


def _telegram_ok(data: dict) -> None:
    if data.get("ok") is False:
        if data.get("error_code") == 401:
            raise AuthFailed()
        raise PermanentFailure("Telegram refused the request")


def _telegram_message(message: dict) -> RawItem | None:
    chat = message.get("chat") or {}
    message_id = message.get("message_id")
    if message_id is None or chat.get("id") is None:
        return None
    kind = "group_message" if chat.get("type") in {"group", "supergroup"} else "message"
    text = message.get("text") or message.get("caption") or ""
    return RawItem(
        source_id=f"{chat['id']}:{message_id}",
        source_timestamp=preserve_timestamp(message.get("date")),
        title=text[:120],
        text=text,
        kind=kind,
        metadata={"chat_id": str(chat["id"]), "chat_type": chat.get("type") or ""},
    )


def discord_probe(client, credentials) -> str:
    data = call(client, "GET", "https://discord.com/api/v10/users/@me", headers=_discord_headers(credentials))
    return data.get("username") or "Discord bot"


def discord_fetch(client, credentials, cursor) -> Page:
    channel_id = str(credentials.get("channel_id") or "")
    if not channel_id:
        return Page(
            items=[],
            next_cursor=None,
            notice="Discord is connected as a bot. Set channel_id to a channel the bot can view. Personal DMs are not available and were not read.",
        )
    if not channel_id.isdigit():
        raise PermanentFailure("channel_id must be the numeric channel id")
    params = {"limit": "25"}
    if cursor and cursor.get("before"):
        params["before"] = cursor["before"]
    data = call(
        client,
        "GET",
        f"https://discord.com/api/v10/channels/{channel_id}/messages",
        headers=_discord_headers(credentials),
        params=params,
    )
    items = []
    oldest = ""
    for message in data if isinstance(data, list) else []:
        message_id = str(message.get("id") or "")
        if not message_id:
            continue
        oldest = message_id
        content = message.get("content") or ""
        items.append(
            RawItem(
                source_id=message_id,
                source_timestamp=str(message.get("timestamp") or ""),
                title=content[:120],
                text=content,
                kind="message",
                metadata={"channel_id": channel_id},
            )
        )
    nxt = {"before": oldest} if oldest and len(data) == 25 else None
    return Page(items=items, next_cursor=nxt)


def _discord_headers(credentials) -> dict:
    require_credentials(credentials, "token")
    return {"Authorization": f"Bot {credentials['token']}", "Accept": "application/json", "User-Agent": "dubai-io-connectors/1"}


@register("slack")
def build_slack(spec):
    return RestConnector(spec, probe=slack_probe, fetch=slack_fetch)


@register("telegram")
def build_telegram(spec):
    return RestConnector(
        spec,
        probe=telegram_probe,
        fetch=telegram_fetch,
        revoke=telegram_revoke,
        webhook=telegram_webhook,
        send=telegram_send,
    )


@register("discord")
def build_discord(spec):
    return RestConnector(spec, probe=discord_probe, fetch=discord_fetch)
