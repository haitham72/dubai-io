"""Inbox profiler → Grok-style 'Needs a reply' cards + memory events.

Live Gmail requires Google OAuth with gmail.readonly. Without it we return an honest
blocker (or DEMO_MAIL=1 fixture cards labelled demo_fixture).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request

from .actions import COOKIE, engine
from .auth import configured, google, same_host
from .memory.store import MemoryStore

router = APIRouter(prefix="/api/mail", tags=["mail"])

GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"

DEMO_NEEDS_REPLY = [
    {
        "id": "demo-mail-1",
        "title": "IDC Technologies, QA Automation (Arabic speaker), Abu Dhabi onsite.",
        "body": (
            "Shweta from Naukrigulf (Oct 2) asked for your CV, current salary, and notice period "
            "for a chatbot QA role (7–15 years). This still looks unanswered."
        ),
        "provenance": "demo_fixture",
        "demo": True,
        "lane": "needs_reply",
    }
]


def _demo_enabled() -> bool:
    return os.getenv("DEMO_MAIL", "").strip().lower() in {"1", "true", "yes"}


def _owner(request: Request) -> str:
    return engine().store.owner(request.cookies.get(COOKIE))


@router.get("/status")
def mail_status(request: Request):
    out: dict[str, Any] = {
        "oauth_configured": configured() and same_host(request),
        "gmail_scope": GMAIL_SCOPE,
        "connected": False,
        "demo_available": _demo_enabled(),
        "account_label": None,
    }
    if not out["oauth_configured"]:
        out["blocker"] = (
            "Set GOOGLE_OAUTH_CLIENT_ID / SECRET / REDIRECT_URI (+ OAUTH_TOKEN_KEY), "
            "enable Gmail API, then Connect Google with mail scope."
        )
        return out
    try:
        meta = google().metadata(_owner(request))
        out["connected"] = meta.get("status") == "connected" and GMAIL_SCOPE in (meta.get("scopes") or [])
        out["account_label"] = meta.get("account_label")
        if meta.get("status") == "connected" and not out["connected"]:
            out["blocker"] = "Google is connected for identity only — reconnect with Gmail read access."
        elif meta.get("status") != "connected":
            out["blocker"] = "Connect Google with Gmail read access to profile your inbox."
    except HTTPException:
        out["blocker"] = "Connect Google with Gmail read access to profile your inbox."
    return out


async def _gmail_needs_reply(owner: str) -> list[dict]:
    token = await google().access_token(owner, [GMAIL_SCOPE])
    q = "newer_than:60d (subject:(interview OR application OR offer OR CV OR resume) OR from:(recruit OR careers OR naukri))"
    async with httpx.AsyncClient(timeout=20) as http:
        listed = await http.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            params={"q": q, "maxResults": 8},
            headers={"Authorization": f"Bearer {token}"},
        )
        if listed.status_code == 403:
            raise HTTPException(403, "Gmail permission missing — reconnect Google with mail scope")
        listed.raise_for_status()
        ids = [m["id"] for m in listed.json().get("messages", [])]
        cards = []
        for mid in ids[:5]:
            detail = await http.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{mid}",
                params={"format": "metadata", "metadataHeaders": ["Subject", "From", "Date"]},
                headers={"Authorization": f"Bearer {token}"},
            )
            detail.raise_for_status()
            payload = detail.json()
            headers = {h["name"].lower(): h["value"] for h in (payload.get("payload") or {}).get("headers", [])}
            subject = headers.get("subject") or "(no subject)"
            sender = headers.get("from") or "unknown sender"
            date = headers.get("date") or ""
            snippet = (payload.get("snippet") or "")[:280]
            cards.append(
                {
                    "id": mid,
                    "title": subject[:160],
                    "body": f"From {sender}. {date}. {snippet}".strip(),
                    "provenance": "provider_confirmed",
                    "demo": False,
                    "lane": "needs_reply",
                    "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                }
            )
        return cards


@router.get("/needs-reply")
async def needs_reply(request: Request):
    """Grok-style result cards for job/application mail worth a look."""
    owner = _owner(request)
    status = mail_status(request)
    cards: list[dict] = []
    source = "none"
    if status.get("connected"):
        try:
            cards = await _gmail_needs_reply(owner)
            source = "gmail"
        except HTTPException:
            raise
        except httpx.HTTPError as err:
            raise HTTPException(502, "Gmail is temporarily unavailable") from err
    elif _demo_enabled():
        cards = list(DEMO_NEEDS_REPLY)
        source = "demo"
    else:
        return {
            "items": [],
            "source": "none",
            "blocker": status.get("blocker") or "Connect Google mail to scan your inbox.",
            "status": status,
        }

    # Link into temporal profiler (visible memory).
    mem = MemoryStore(engine().store.db)
    for card in cards:
        mem.add_event(
            owner,
            kind="mail_needs_reply",
            text=f"{card['title']} — {card['body'][:240]}",
            source=source,
            provenance=card.get("provenance") or "provider_confirmed",
            ontology_path="career/applications/inbox",
        )
        if not card.get("demo"):
            mem.upsert_entity(
                owner,
                kind="org",
                name=card["title"].split(",")[0][:80],
                ontology_path="career/applications/inbox",
                provenance="provider_confirmed",
            )

    return {
        "heading": "Needs a reply",
        "items": cards,
        "source": source,
        "status": status,
        "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
