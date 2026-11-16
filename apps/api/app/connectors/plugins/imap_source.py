"""IMAP over TLS. The password is stored encrypted and is never put in an error."""
from __future__ import annotations

import email
import re
from email.header import decode_header

from ..base import BaseConnector
from ..types import AuthFailed, Page, PermanentFailure, RawItem
from . import register

_INTERNAL = re.compile(br'INTERNALDATE "([^"]+)"')


def decode_mime(value: str) -> str:
    if not value:
        return ""
    parts = []
    for text, charset in decode_header(value):
        if isinstance(text, bytes):
            parts.append(text.decode(charset or "utf-8", "replace"))
        else:
            parts.append(text)
    return "".join(parts)


def parse_imap_fetch(uid: bytes, parts) -> RawItem:
    meta = b""
    blobs = []
    for part in parts or []:
        if isinstance(part, tuple):
            meta += b" " + part[0]
            blobs.append(part[1] or b"")
        elif isinstance(part, (bytes, bytearray)):
            meta += b" " + bytes(part)
    internal = ""
    match = _INTERNAL.search(meta)
    if match:
        internal = match.group(1).decode("utf-8", "replace")
    header_blob = blobs[0] if blobs else b""
    body = ""
    if len(blobs) > 1:
        body = blobs[-1].decode("utf-8", "replace")
    message = email.message_from_bytes(header_blob)
    subject = decode_mime(message.get("Subject") or "") or "(no subject)"
    sender = decode_mime(message.get("From") or "")
    date_header = message.get("Date") or ""
    timestamp = date_header or internal
    text = body.strip() or subject
    if sender:
        text = f"From {sender}. {text}"
    return RawItem(
        source_id=uid.decode("ascii", "replace"),
        source_timestamp=timestamp,
        title=subject,
        text=text[:8000],
        kind="email",
        metadata={"from": sender, "internaldate": internal, "date_header": date_header},
    )


class ImapConnector(BaseConnector):
    transport = "imap"

    def _client(self, module, credentials):
        host = str(credentials.get("host") or "")
        if not host or any(char in host for char in " \r\n\t/@"):
            raise PermanentFailure("The mail host is not valid")
        try:
            port = int(credentials.get("port") or 993)
        except (TypeError, ValueError):
            raise PermanentFailure("The mail port is not valid")
        if not 1 <= port <= 65535:
            raise PermanentFailure("The mail port is not valid")
        username = credentials.get("username")
        password = credentials.get("password")
        if not username or not password:
            raise AuthFailed("This connection is missing a required credential")
        try:
            client = module.IMAP4_SSL(host, port)
            client.login(username, password)
        except AuthFailed:
            raise
        except Exception:
            raise AuthFailed("The mailbox rejected the login") from None
        return client

    def probe(self, client, credentials) -> str:
        imap = self._client(client, credentials)
        try:
            imap.logout()
        except Exception:
            pass
        return str(credentials.get("username"))

    def fetch_page(self, client, credentials, cursor) -> Page:
        imap = self._client(client, credentials)
        mailbox = str(credentials.get("mailbox") or "INBOX")
        if any(char in mailbox for char in "\r\n"):
            raise PermanentFailure("The mailbox name is not valid")
        try:
            imap.select(mailbox, readonly=True)
            start = 1
            if cursor and str(cursor.get("uid") or "").isdigit():
                start = int(cursor["uid"]) + 1
            _typ, data = imap.uid("search", None, "UID", f"{start}:*")
            raw_uids = (data[0] or b"").split() if data else []
            uids = [uid for uid in raw_uids if uid.isdigit() and int(uid) >= start][:30]
            items = []
            max_uid = int(cursor["uid"]) if cursor and str(cursor.get("uid") or "").isdigit() else 0
            for uid in uids:
                _typ, fetched = imap.uid(
                    "fetch",
                    uid,
                    "(UID INTERNALDATE BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)] BODY.PEEK[TEXT]<0.2000>)",
                )
                items.append(parse_imap_fetch(uid, fetched))
                max_uid = max(max_uid, int(uid))
            return Page(items=items, next_cursor={"uid": str(max_uid)} if max_uid else None)
        finally:
            try:
                imap.logout()
            except Exception:
                pass

    def revoke_remote(self, client, credentials) -> str:
        return "remove_the_app_password_at_the_mailbox_host"


@register("imap")
def build(spec):
    return ImapConnector(spec)
