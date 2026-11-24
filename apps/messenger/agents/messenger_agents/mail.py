"""Gmail: a dedicated test account linked with Google sign-in (OAuth). Read and search run directly; sending needs an
explicit `confirmed` flag from a visible confirmation in the app. Without a linked account the app keeps its demo inbox.

Setup (once): create an OAuth client of type "Web application" in Google Cloud, add the redirect URI
`<AGENTS_PUBLIC_URL>/mail/oauth/callback`, add the test account as a test user, save the client JSON to
agents/.secrets/gmail_client.json, then open <AGENTS_PUBLIC_URL>/mail/oauth/start. In Google's testing mode the
sign-in lasts 7 days.
"""
from __future__ import annotations

import asyncio
import base64
import json
import re
from email.message import EmailMessage
from email.utils import parseaddr
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send"]


class MailNotLinked(RuntimeError):
    pass


class Gmail:
    def __init__(self, client_file: Path, token_file: Path, redirect_uri: str) -> None:
        self.client_file, self.token_file, self.redirect_uri = client_file, token_file, redirect_uri
        self._state: str | None = None
        self._verifier: str | None = None

    # ---------------------------------------------------------------- auth
    def status(self) -> dict:
        return {"configured": self.client_file.exists(), "linked": self.token_file.exists(),
                "mode": "gmail" if self.token_file.exists() else "demo"}

    def _flow(self):
        from google_auth_oauthlib.flow import Flow
        return Flow.from_client_secrets_file(str(self.client_file), scopes=SCOPES, redirect_uri=self.redirect_uri)

    def auth_url(self) -> str:
        if not self.client_file.exists():
            raise MailNotLinked(f"Missing OAuth client file: {self.client_file.name}")
        flow = self._flow()
        url, self._state = flow.authorization_url(access_type="offline", prompt="consent", include_granted_scopes="true")
        self._verifier = flow.code_verifier
        return url

    def finish(self, code: str, state: str) -> None:
        if not self._state or state != self._state:
            raise MailNotLinked("Sign-in expired; start again")
        flow = self._flow()
        flow.code_verifier = self._verifier
        flow.fetch_token(code=code)
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(flow.credentials.to_json(), encoding="utf-8")
        self.token_file.chmod(0o600)

    def unlink(self) -> None:
        self.token_file.unlink(missing_ok=True)

    def _service(self):
        if not self.token_file.exists():
            raise MailNotLinked("Gmail is not linked")
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        creds = Credentials.from_authorized_user_info(json.loads(self.token_file.read_text(encoding="utf-8")), SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self.token_file.write_text(creds.to_json(), encoding="utf-8")
        return build("gmail", "v1", credentials=creds, cache_discovery=False)

    # ---------------------------------------------------------------- read
    async def list(self, query: str = "in:inbox", limit: int = 25) -> list[dict]:
        return await asyncio.to_thread(self._list, query, limit)

    def _list(self, query: str, limit: int) -> list[dict]:
        svc = self._service()
        ids = svc.users().messages().list(userId="me", q=query, maxResults=min(limit, 50)).execute().get("messages", [])
        return [_summary(svc.users().messages().get(userId="me", id=m["id"], format="metadata",
                                                    metadataHeaders=["From", "Subject", "Date"]).execute()) for m in ids]

    async def get(self, mid: str) -> dict:
        return await asyncio.to_thread(self._get, mid)

    def _get(self, mid: str) -> dict:
        msg = self._service().users().messages().get(userId="me", id=mid, format="full").execute()
        return {**_summary(msg), "body": _body(msg.get("payload", {}))}

    # ---------------------------------------------------------------- send (confirmed only)
    async def send(self, to: str, subject: str, body: str, confirmed: bool) -> dict:
        if not confirmed:
            raise PermissionError("Sending needs a confirmation in the app")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", parseaddr(to)[1] or ""):
            raise ValueError("Invalid recipient address")
        return await asyncio.to_thread(self._send, to, subject, body)

    def _send(self, to: str, subject: str, body: str) -> dict:
        m = EmailMessage()
        m["To"], m["Subject"] = to, subject
        m.set_content(body)
        raw = base64.urlsafe_b64encode(m.as_bytes()).decode()
        sent = self._service().users().messages().send(userId="me", body={"raw": raw}).execute()
        return {"id": sent.get("id"), "threadId": sent.get("threadId")}


def _header(msg: dict, name: str) -> str:
    return next((h["value"] for h in msg.get("payload", {}).get("headers", []) if h["name"].lower() == name.lower()), "")


def _summary(msg: dict) -> dict:
    sender_name, sender_addr = parseaddr(_header(msg, "From"))
    labels = msg.get("labelIds", [])
    category = next((c for c, l in (("Social", "CATEGORY_SOCIAL"), ("Updates", "CATEGORY_UPDATES"),
                                    ("Promotions", "CATEGORY_PROMOTIONS")) if l in labels), "Primary")
    return {"id": msg["id"], "threadId": msg.get("threadId"), "sender": sender_name or sender_addr, "address": sender_addr,
            "subject": _header(msg, "Subject") or "(no subject)", "date": _header(msg, "Date"), "preview": msg.get("snippet", ""),
            "unread": "UNREAD" in labels, "starred": "STARRED" in labels, "category": category,
            "internalDate": int(msg.get("internalDate", 0))}


def _body(part: dict) -> str:
    """Plain text of a message: the first text/plain part, else text/html with tags removed."""
    def walk(p: dict, mime: str) -> str:
        if p.get("mimeType") == mime and p.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(p["body"]["data"]).decode("utf-8", "replace")
        for sub in p.get("parts", []) or []:
            if found := walk(sub, mime):
                return found
        return ""
    text = walk(part, "text/plain")
    if not text:
        html = walk(part, "text/html")
        text = re.sub(r"\s+\n", "\n", re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style).*?</\1>", "", html)))
    return text.strip()[:20000]
