"""Official Google APIs: Gmail, Calendar, Drive, YouTube."""
from __future__ import annotations

import httpx

from ..base import RestConnector
from ..stamp import preserve_timestamp
from ..transport import bearer, call, require_credentials
from ..types import HttpStatus, Page, RawItem, TransientFailure
from . import register

GMAIL = "https://gmail.googleapis.com/gmail/v1/users/me"
REVOKE = "https://oauth2.googleapis.com/revoke"


def google_revoke(client, credentials) -> str:
    token = credentials.get("refresh_token") or credentials.get("access_token")
    if not token:
        return "local_only"
    try:
        response = client.post(REVOKE, data={"token": token})
    except httpx.HTTPError as exc:
        raise TransientFailure("The provider could not be reached") from exc
    if response.status_code in (200, 400):
        return "revoked"
    if response.status_code >= 500:
        raise TransientFailure()
    return "remote_rejected"


def _headers(credentials):
    require_credentials(credentials, "access_token")
    return bearer(credentials["access_token"])


def _header(payload, name: str) -> str:
    for item in (payload or {}).get("headers") or []:
        if str(item.get("name", "")).lower() == name.lower():
            return item.get("value") or ""
    return ""


def _attachment_names(payload) -> list[dict]:
    names = []
    stack = list((payload or {}).get("parts") or [])
    while stack:
        part = stack.pop()
        filename = part.get("filename") or ""
        if filename:
            names.append({"file_name": filename, "mime_type": part.get("mimeType") or ""})
        stack.extend(part.get("parts") or [])
    return names


def _gmail_one(client, headers, message_id: str) -> RawItem:
    data = call(
        client,
        "GET",
        f"{GMAIL}/messages/{message_id}",
        headers=headers,
        params={"format": "metadata", "metadataHeaders": ["Subject", "From", "Date"]},
    )
    payload = data.get("payload") or {}
    date = _header(payload, "Date")
    internal = data.get("internalDate")
    timestamp = date if date else preserve_timestamp(internal)
    subject = _header(payload, "Subject") or "(no subject)"
    sender = _header(payload, "From")
    snippet = data.get("snippet") or ""
    text = f"From {sender}. {snippet}".strip() if sender else snippet or subject
    return RawItem(
        source_id=str(data.get("id") or message_id),
        source_timestamp=timestamp,
        title=subject,
        text=text,
        kind="email",
        metadata={
            "from": sender,
            "internal_date": preserve_timestamp(internal),
            "attachments": _attachment_names(payload),
        },
    )


def gmail_probe(client, credentials) -> str:
    data = call(client, "GET", f"{GMAIL}/profile", headers=_headers(credentials))
    return data.get("emailAddress") or "Gmail"


def gmail_fetch(client, credentials, cursor) -> Page:
    headers = _headers(credentials)
    cursor = cursor or {}
    if cursor.get("history_id") and cursor.get("phase") == "incremental":
        try:
            hist = call(
                client,
                "GET",
                f"{GMAIL}/history",
                headers=headers,
                params={"startHistoryId": cursor["history_id"], "historyTypes": "messageAdded", "maxResults": "20"},
            )
        except HttpStatus as err:
            if err.status != 404:
                raise
            return _gmail_list(client, headers, None)
        ids = []
        for entry in hist.get("history") or []:
            for added in entry.get("messagesAdded") or []:
                message_id = (added.get("message") or {}).get("id")
                if message_id:
                    ids.append(message_id)
        items = [_gmail_one(client, headers, message_id) for message_id in ids]
        history_id = str(hist.get("historyId") or cursor["history_id"])
        return Page(items=items, next_cursor={"history_id": history_id, "phase": "incremental"})
    return _gmail_list(client, headers, cursor.get("page_token"))


def _gmail_list(client, headers, page_token) -> Page:
    params = {"maxResults": "10"}
    if page_token:
        params["pageToken"] = page_token
    listed = call(client, "GET", f"{GMAIL}/messages", headers=headers, params=params)
    items = [_gmail_one(client, headers, message["id"]) for message in listed.get("messages") or [] if message.get("id")]
    profile = call(client, "GET", f"{GMAIL}/profile", headers=headers)
    nxt = {"history_id": str(profile.get("historyId") or "")}
    token = listed.get("nextPageToken")
    if token:
        nxt["page_token"] = token
        nxt["phase"] = "initial"
    else:
        nxt["phase"] = "incremental"
    return Page(items=items, next_cursor=nxt)


def calendar_probe(client, credentials) -> str:
    data = call(
        client,
        "GET",
        "https://www.googleapis.com/calendar/v3/calendars/primary",
        headers=_headers(credentials),
    )
    return data.get("summary") or data.get("id") or "Google Calendar"


def calendar_fetch(client, credentials, cursor) -> Page:
    headers = _headers(credentials)
    params = {"maxResults": "15", "singleEvents": "true", "showDeleted": "false"}
    if cursor and cursor.get("sync_token"):
        params = {"syncToken": cursor["sync_token"]}
    elif cursor and cursor.get("page_token"):
        params["pageToken"] = cursor["page_token"]
    try:
        data = call(
            client,
            "GET",
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers=headers,
            params=params,
        )
    except Exception as exc:
        from ..types import CursorExpired

        if isinstance(exc, CursorExpired) and cursor and cursor.get("sync_token"):
            return calendar_fetch(client, credentials, None)
        raise
    items = []
    for event in data.get("items") or []:
        start = (event.get("start") or {}).get("dateTime") or (event.get("start") or {}).get("date") or ""
        items.append(
            RawItem(
                source_id=str(event.get("id") or ""),
                source_timestamp=str(start),
                title=event.get("summary") or "(no title)",
                text=event.get("summary") or "",
                kind="event",
                metadata={"updated": event.get("updated") or "", "start": str(start)},
            )
        )
    nxt = {}
    if data.get("nextPageToken"):
        nxt["page_token"] = data["nextPageToken"]
    elif data.get("nextSyncToken"):
        nxt["sync_token"] = data["nextSyncToken"]
    return Page(items=items, next_cursor=nxt or None)


def drive_probe(client, credentials) -> str:
    data = call(client, "GET", "https://www.googleapis.com/drive/v3/about", headers=_headers(credentials), params={"fields": "user"})
    user = data.get("user") or {}
    return user.get("emailAddress") or "Google Drive"


def drive_fetch(client, credentials, cursor) -> Page:
    headers = _headers(credentials)
    params = {"pageSize": "30", "fields": "nextPageToken,files(id,name,mimeType,modifiedTime,size)"}
    if cursor and cursor.get("page_token"):
        params["pageToken"] = cursor["page_token"]
    data = call(client, "GET", "https://www.googleapis.com/drive/v3/files", headers=headers, params=params)
    items = []
    for entry in data.get("files") or []:
        items.append(
            RawItem(
                source_id=str(entry.get("id") or ""),
                source_timestamp=str(entry.get("modifiedTime") or ""),
                title=entry.get("name") or "",
                text=entry.get("name") or "",
                kind="file",
                metadata={"mime_type": entry.get("mimeType") or "", "size": entry.get("size")},
            )
        )
    nxt = {"page_token": data["nextPageToken"]} if data.get("nextPageToken") else None
    return Page(items=items, next_cursor=nxt)


def youtube_probe(client, credentials) -> str:
    data = call(
        client,
        "GET",
        "https://www.googleapis.com/youtube/v3/channels",
        headers=_headers(credentials),
        params={"part": "snippet", "mine": "true"},
    )
    items = data.get("items") or []
    if not items:
        return "YouTube"
    return ((items[0].get("snippet") or {}).get("title")) or "YouTube"


def youtube_fetch(client, credentials, cursor) -> Page:
    headers = _headers(credentials)
    channels = call(
        client,
        "GET",
        "https://www.googleapis.com/youtube/v3/channels",
        headers=headers,
        params={"part": "contentDetails", "mine": "true"},
    )
    items = channels.get("items") or []
    uploads = ""
    if items:
        uploads = ((items[0].get("contentDetails") or {}).get("relatedPlaylists") or {}).get("uploads") or ""
    if not uploads:
        return Page(items=[], next_cursor=None, notice="No uploads playlist was returned for this channel.")
    params = {"part": "snippet", "playlistId": uploads, "maxResults": "15"}
    if cursor and cursor.get("page_token"):
        params["pageToken"] = cursor["page_token"]
    data = call(client, "GET", "https://www.googleapis.com/youtube/v3/playlistItems", headers=headers, params=params)
    records = []
    for entry in data.get("items") or []:
        snippet = entry.get("snippet") or {}
        video_id = ((snippet.get("resourceId") or {}).get("videoId")) or entry.get("id") or ""
        records.append(
            RawItem(
                source_id=str(video_id),
                source_timestamp=str(snippet.get("publishedAt") or ""),
                title=snippet.get("title") or "",
                text=snippet.get("description") or snippet.get("title") or "",
                kind="video",
                metadata={"playlist_id": uploads},
            )
        )
    nxt = {"page_token": data["nextPageToken"]} if data.get("nextPageToken") else None
    return Page(items=records, next_cursor=nxt)


@register("gmail")
def build_gmail(spec):
    return RestConnector(spec, probe=gmail_probe, fetch=gmail_fetch, revoke=google_revoke)


@register("google_calendar")
def build_calendar(spec):
    return RestConnector(spec, probe=calendar_probe, fetch=calendar_fetch, revoke=google_revoke)


@register("google_drive")
def build_drive(spec):
    return RestConnector(spec, probe=drive_probe, fetch=drive_fetch, revoke=google_revoke)


@register("youtube")
def build_youtube(spec):
    return RestConnector(spec, probe=youtube_probe, fetch=youtube_fetch, revoke=google_revoke)
