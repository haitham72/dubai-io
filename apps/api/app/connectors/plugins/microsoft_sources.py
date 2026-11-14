"""Official Microsoft Graph: Outlook mail, Outlook calendar, OneDrive."""
from __future__ import annotations

from ..base import RestConnector
from ..hosts import https_url_on
from ..transport import bearer, call, require_credentials
from ..types import Page, RawItem
from . import register

GRAPH = "https://graph.microsoft.com"


def _headers(credentials):
    require_credentials(credentials, "access_token")
    return bearer(credentials["access_token"])


def _graph_get(client, credentials, url: str, params=None):
    if url.startswith("https://"):
        https_url_on(url, "graph.microsoft.com")
    return call(client, "GET", url, headers=_headers(credentials), params=params)


def _cursor_from(data: dict, key: str) -> dict | None:
    link = data.get("@odata.deltaLink") or data.get("@odata.nextLink")
    if not link:
        return None
    https_url_on(link, "graph.microsoft.com")
    return {key: link}


def outlook_probe(client, credentials) -> str:
    data = _graph_get(client, credentials, f"{GRAPH}/v1.0/me", params={"$select": "mail,userPrincipalName"})
    return data.get("mail") or data.get("userPrincipalName") or "Outlook"


def outlook_fetch(client, credentials, cursor) -> Page:
    link = (cursor or {}).get("delta_link")
    if link:
        data = _graph_get(client, credentials, link)
    else:
        data = _graph_get(
            client,
            credentials,
            f"{GRAPH}/v1.0/me/mailFolders/inbox/messages/delta",
            params={"$top": "15", "$select": "id,subject,receivedDateTime,bodyPreview,from"},
        )
    items = []
    for message in data.get("value") or []:
        if not message.get("id"):
            continue
        sender = (((message.get("from") or {}).get("emailAddress") or {}).get("address")) or ""
        subject = message.get("subject") or "(no subject)"
        preview = message.get("bodyPreview") or ""
        items.append(
            RawItem(
                source_id=str(message["id"]),
                source_timestamp=str(message.get("receivedDateTime") or ""),
                title=subject,
                text=f"From {sender}. {preview}".strip() if sender else preview or subject,
                kind="email",
                metadata={"from": sender},
            )
        )
    return Page(items=items, next_cursor=_cursor_from(data, "delta_link"))


def outlook_calendar_fetch(client, credentials, cursor) -> Page:
    link = (cursor or {}).get("delta_link")
    if link:
        data = _graph_get(client, credentials, link)
    else:
        data = _graph_get(
            client,
            credentials,
            f"{GRAPH}/v1.0/me/events/delta",
            params={"$top": "15", "$select": "id,subject,start,bodyPreview"},
        )
    items = []
    for event in data.get("value") or []:
        if not event.get("id"):
            continue
        start = ((event.get("start") or {}).get("dateTime")) or ""
        subject = event.get("subject") or "(no title)"
        items.append(
            RawItem(
                source_id=str(event["id"]),
                source_timestamp=str(start),
                title=subject,
                text=event.get("bodyPreview") or subject,
                kind="event",
                metadata={"start": str(start)},
            )
        )
    return Page(items=items, next_cursor=_cursor_from(data, "delta_link"))


def onedrive_fetch(client, credentials, cursor) -> Page:
    link = (cursor or {}).get("next_link")
    if link:
        data = _graph_get(client, credentials, link)
    else:
        data = _graph_get(
            client,
            credentials,
            f"{GRAPH}/v1.0/me/drive/root/children",
            params={"$top": "30", "$select": "id,name,lastModifiedDateTime,size,file"},
        )
    items = []
    for entry in data.get("value") or []:
        if not entry.get("id"):
            continue
        items.append(
            RawItem(
                source_id=str(entry["id"]),
                source_timestamp=str(entry.get("lastModifiedDateTime") or ""),
                title=entry.get("name") or "",
                text=entry.get("name") or "",
                kind="file",
                metadata={"size": entry.get("size"), "mime_type": (entry.get("file") or {}).get("mimeType") or ""},
            )
        )
    return Page(items=items, next_cursor=_cursor_from(data, "next_link"))


@register("outlook")
def build_outlook(spec):
    return RestConnector(spec, probe=outlook_probe, fetch=outlook_fetch)


@register("outlook_calendar")
def build_outlook_calendar(spec):
    return RestConnector(spec, probe=outlook_probe, fetch=outlook_calendar_fetch)


@register("onedrive")
def build_onedrive(spec):
    return RestConnector(spec, probe=outlook_probe, fetch=onedrive_fetch)
