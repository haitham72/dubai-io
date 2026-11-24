"""Read-only, owner-scoped Google source pulls for E3."""
from __future__ import annotations

from datetime import datetime, timedelta
from html import unescape
from urllib.parse import quote

import httpx

from ..oauth import GMAIL_READONLY
from .plugins.google_sources import _header

SCOPES = {
    "gmail": GMAIL_READONLY,
    "calendar": "https://www.googleapis.com/auth/calendar.events.readonly",
    "youtube": "https://www.googleapis.com/auth/youtube.readonly",
}
_GMAIL = "https://gmail.googleapis.com/gmail/v1/users/me"
_CALENDAR = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
_YOUTUBE = "https://www.googleapis.com/youtube/v3"
GMAIL_TOKEN_CAP = 50_000


def _pages(client, url, params, label="items"):
    cursor = None
    visited = set()
    while True:
        page = client.get(url, params={**params, **({"pageToken": cursor} if cursor else {})})
        page.raise_for_status()
        data = page.json()
        yield from data.get(label, ())
        cursor = data.get("nextPageToken")
        if not cursor:
            return
        if cursor in visited:
            raise ValueError("Provider returned a repeated page token")
        visited.add(cursor)


def _stable_record(source, item_id, at, text, author):
    if not item_id or not at or not text.strip():
        return None
    return {"id": f"e3:{source}:{item_id}", "source": source, "at": at, "text": text, "author": author}


def _gmail(client, now):
    start = now - timedelta(days=90)
    params = {
        "q": f"after:{int(start.timestamp())} category:primary -category:promotions -in:spam -in:trash",
        "includeSpamTrash": "false", "maxResults": 100,
    }
    # UTF-8 bytes are a conservative bound for byte-tokenized model input.
    remaining = GMAIL_TOKEN_CAP
    for stub in _pages(client, f"{_GMAIL}/messages", params, "messages"):
        message_id = stub.get("id")
        if not message_id:
            continue
        response = client.get(f"{_GMAIL}/messages/{quote(message_id, safe='')}", params={
            "format": "metadata", "metadataHeaders": ["From", "Subject"],
        })
        if response.status_code == 404:
            continue
        response.raise_for_status()
        message = response.json()
        labels = set(message.get("labelIds") or ())
        if labels & {"SPAM", "TRASH", "CATEGORY_PROMOTIONS"}:
            continue
        stamp = message.get("internalDate")
        if not stamp:
            continue
        at = datetime.fromtimestamp(int(stamp) / 1000, now.tzinfo)
        if at < start or at > now:
            continue
        payload = message.get("payload", {})
        subject = _header(payload, "Subject")
        sender = _header(payload, "From")[:200] or "gmail"
        text = "\n".join(part for part in (subject, unescape(message.get("snippet") or "")) if part)[:1800]
        if not text:
            continue
        cost = len((text + sender + message_id).encode("utf-8")) + 96
        if cost > remaining:
            return
        remaining -= cost
        yield _stable_record("gmail:primary", message_id, at.isoformat(), text, sender)


def _calendar(client, now):
    days = timedelta(days=90)
    for event in _pages(client, _CALENDAR, {
        "timeMin": (now - days).isoformat(), "timeMax": (now + days).isoformat(),
        "singleEvents": "true", "showDeleted": "false", "maxResults": 250,
    }):
        if event.get("status") == "cancelled" or event.get("visibility") == "private":
            continue
        start = event.get("start", {})
        at = start.get("dateTime") or start.get("date")
        if not at or not event.get("summary") or not event.get("id"):
            continue
        version = event.get("updated") or at
        text = f"Calendar event: {event['summary']}\nStarts at: {at}"
        if event.get("location"):
            text += f"\nLocation: {event['location']}"
        yield _stable_record("calendar:primary", f"{event.get('id', '')}:{version}", at, text[:1800], "google-calendar")


def _youtube_records(items, name, now):
    source = f"youtube:api:{name}"
    for item in items:
        snippet = item.get("snippet", {})
        title = snippet.get("title", "")
        if not title or title in {"Deleted video", "Private video"}:
            continue
        # The videos.list response contains video publication time, not like time.
        at = now.isoformat() if name == "likes" else (snippet.get("publishedAt") or now.isoformat())
        suffix = {"likes": "Liked video", "subscriptions": "Subscription", "playlists": "Playlist", "uploads": "Upload"}
        text = f"YouTube {suffix[name]}: {title}"
        if snippet.get("channelTitle"):
            text += f"\nChannel: {snippet['channelTitle']}"
        yield _stable_record(source, item.get("id"), at, text[:1800], "youtube")


def _youtube(client, now):
    common = {"part": "snippet", "maxResults": 50}
    yield from _youtube_records(_pages(client, f"{_YOUTUBE}/videos", {**common, "myRating": "like"}), "likes", now)
    for name in ("subscriptions", "playlists"):
        yield from _youtube_records(_pages(client, f"{_YOUTUBE}/{name}", {**common, "mine": "true"}), name, now)
    for channel in _pages(client, f"{_YOUTUBE}/channels", {"part": "contentDetails", "mine": "true"}):
        uploads = channel.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
        if uploads:
            yield from _youtube_records(_pages(client, f"{_YOUTUBE}/playlistItems", {**common, "playlistId": uploads}), "uploads", now)


def pull(source, token, now, *, transport=None):
    fetch = {"gmail": _gmail, "calendar": _calendar, "youtube": _youtube}[source]
    with httpx.Client(headers={"Authorization": f"Bearer {token}"}, timeout=20, transport=transport) as client:
        return [record for record in fetch(client, now) if record]
